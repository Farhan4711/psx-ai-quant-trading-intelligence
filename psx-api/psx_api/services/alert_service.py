"""
Pump/dump alert service.

Three responsibilities:
  1. Read suspicious-day alerts (latest per symbol, paginated history,
     and the "for symbols I watch/own" view).
  2. Compute a fresh alert for a (symbol, date) on demand by running
     Layers 1+2 of the pump/dump detector against current OHLCV. This
     is what the daily after-close worker would call; we expose it as
     an endpoint so callers can recompute on demand without waiting
     for the cron.
  3. Persist new alerts to suspicious_days, dedup by (symbol, date).
"""

from __future__ import annotations

from datetime import UTC, date, timedelta
from decimal import Decimal

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.alerts.pump_dump import (
    DailyBar,
    anomaly_score,
    detect_rule,
    escalate_severity,
    features_from,
)
from psx_api.models.alerts import SuspiciousDay
from psx_api.models.corporate_actions import CorporateAction
from psx_api.models.news import ArticleMention, ArticleSentiment, NewsArticle
from psx_api.models.ohlcv import OhlcvDaily
from psx_api.models.portfolios import HoldingsSnapshot, Portfolio
from psx_api.models.watchlist import WatchlistItem


class AlertService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── Reads ─────────────────────────────────────────────────────

    async def latest_for_symbol(self, symbol: str) -> SuspiciousDay | None:
        result = await self._db.execute(
            select(SuspiciousDay)
            .where(SuspiciousDay.symbol == symbol.upper())
            .order_by(desc(SuspiciousDay.alert_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def for_user(self, user_id: str, *, limit: int = 50) -> list[SuspiciousDay]:
        """Suspicious-day alerts for any symbol the user holds or watches."""
        wl_subq = select(WatchlistItem.symbol).where(WatchlistItem.user_id == user_id)
        portfolio_ids = select(Portfolio.id).where(Portfolio.user_id == user_id)
        holdings_subq = select(HoldingsSnapshot.symbol).where(
            HoldingsSnapshot.portfolio_id.in_(portfolio_ids)
        )

        rows = (
            (
                await self._db.execute(
                    select(SuspiciousDay)
                    .where(
                        (SuspiciousDay.symbol.in_(wl_subq))
                        | (SuspiciousDay.symbol.in_(holdings_subq))
                    )
                    .order_by(desc(SuspiciousDay.alert_date), desc(SuspiciousDay.created_at))
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    # ── Compute ───────────────────────────────────────────────────

    async def evaluate_today(self, symbol: str) -> SuspiciousDay | None:
        """
        Pull last ~25 bars for `symbol`, compute Layers 1+2+3, and persist
        a SuspiciousDay row if any layer triggers. Returns the row or None.
        """
        symbol = symbol.upper()
        rows = (
            await self._db.execute(
                select(
                    OhlcvDaily.date,
                    OhlcvDaily.open,
                    OhlcvDaily.high,
                    OhlcvDaily.low,
                    OhlcvDaily.close,
                    OhlcvDaily.volume,
                )
                .where(OhlcvDaily.symbol == symbol)
                .order_by(desc(OhlcvDaily.date))
                .limit(70)
            )
        ).all()
        if len(rows) < 22:
            return None
        rows = list(reversed(rows))  # chronological

        bars: list[DailyBar] = []
        for i, r in enumerate(rows):
            if any(v is None for v in (r[1], r[2], r[3], r[4])):
                continue
            prev_close = float(rows[i - 1][4]) if i > 0 and rows[i - 1][4] is not None else None
            bars.append(
                DailyBar(
                    open=float(r[1]),
                    high=float(r[2]),
                    low=float(r[3]),
                    close=float(r[4]),
                    volume=float(r[5] or 0),
                    prev_close=prev_close,
                )
            )

        if len(bars) < 22:
            return None

        today_bar = bars[-1]
        today_date: date = rows[-1][0]
        prior_bars = bars[-21:-1]
        vol_ma_20 = sum(b.volume for b in prior_bars) / 20

        rule = detect_rule(today_bar, vol_ma_20)

        # Anomaly score over last 60 bars
        feat_history = [features_from(b, vol_ma_20) for b in bars[-61:-1]]
        feat_today = features_from(today_bar, vol_ma_20)
        score_value = anomaly_score(feat_today, feat_history)

        # News context
        has_announcement = await self._has_recent_announcement(symbol, today_date)
        has_high_impact_news, sentiment_pulse = await self._news_context(symbol, today_date)

        if not rule.triggered and score_value < 5.0:
            return None

        severity = escalate_severity(
            rule_triggered=rule.triggered,
            anomaly_score_value=score_value,
            has_announcement_today=has_announcement,
            has_high_impact_news_today=has_high_impact_news,
            sentiment_pulse=sentiment_pulse,
        )

        if not rule.triggered and severity == "low":
            # Pure statistical bump with low severity → don't pollute the inbox
            return None

        explanation = (
            rule.explanation
            if rule.triggered
            else (f"Statistical anomaly score {score_value:.1f} (≥5 sigma).")
        )
        if has_announcement or has_high_impact_news:
            explanation += " Context: announced news today reduced severity."
        else:
            explanation += " No announced news context — extra caution."

        row = SuspiciousDay(
            symbol=symbol,
            alert_date=today_date,
            alert_type=rule.alert_type or ("pump" if rule.price_change_pct >= 0 else "dump"),
            severity=severity,
            vol_spike=Decimal(str(rule.vol_spike)),
            price_change_pct=Decimal(str(rule.price_change_pct)),
            anomaly_score=Decimal(str(score_value)),
            has_news_context=has_announcement or has_high_impact_news,
            explanation=explanation,
        )
        self._db.add(row)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            # Already exists for (symbol, date) — return the existing one
            existing = (
                await self._db.execute(
                    select(SuspiciousDay).where(
                        SuspiciousDay.symbol == symbol,
                        SuspiciousDay.alert_date == today_date,
                    )
                )
            ).scalar_one_or_none()
            return existing
        return row

    # ── Internals ─────────────────────────────────────────────────

    async def _has_recent_announcement(self, symbol: str, on: date) -> bool:
        cutoff = on - timedelta(days=3)
        result = await self._db.execute(
            select(CorporateAction.id)
            .where(
                CorporateAction.symbol == symbol,
                CorporateAction.announcement_date >= cutoff,
                CorporateAction.announcement_date <= on,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def _news_context(self, symbol: str, on: date) -> tuple[bool, float]:
        """
        Returns (has_high_impact_news_today, sentiment_pulse_today).
        High-impact = any earnings/regulatory/mna/scandal article today.
        """
        from datetime import datetime, time

        start = datetime.combine(on, time.min, tzinfo=UTC)
        end = datetime.combine(on, time.max, tzinfo=UTC)

        rows = (
            await self._db.execute(
                select(ArticleSentiment.polarity, ArticleSentiment.event_type)
                .join(NewsArticle, NewsArticle.id == ArticleSentiment.article_id)
                .join(ArticleMention, ArticleMention.article_id == NewsArticle.id)
                .where(
                    ArticleMention.symbol == symbol,
                    NewsArticle.published_at >= start,
                    NewsArticle.published_at <= end,
                )
            )
        ).all()
        high_impact_events = {"earnings", "regulatory", "mna", "scandal"}
        has_high_impact = any(r[1] in high_impact_events for r in rows)
        # crude pulse: average polarity of today's articles, scaled
        if rows:
            pulse = (sum(float(r[0]) for r in rows) / len(rows)) * 100
        else:
            pulse = 0.0
        return has_high_impact, pulse
