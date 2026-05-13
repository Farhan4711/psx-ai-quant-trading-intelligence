from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.cache import TTL_FUNDAMENTALS, TTL_LIST, TTL_LIVE, TTL_OHLCV, TTL_SECTORS, cached
from psx_api.models.corporate_actions import CorporateAction
from psx_api.models.ohlcv import OhlcvDaily
from psx_api.models.securities import Security
from psx_api.schemas.securities import (
    AnnouncementResponse,
    AnnouncementsListResponse,
    FundamentalsResponse,
    IndexPerformance,
    OhlcvListResponse,
    OhlcvResponse,
    Quote,
    QuotesResponse,
    SecuritiesListResponse,
    SecurityCreate,
    SecurityResponse,
)


class SecuritiesService:
    def __init__(self, db: AsyncSession, redis: Redis | None = None) -> None:  # type: ignore[type-arg]
        self._db = db
        self._redis = redis

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _cached(self, key: str, ttl: int, loader: object) -> object:
        if self._redis is None:
            import inspect
            return await loader()  # type: ignore[call-arg,misc]
        return await cached(self._redis, key, ttl, loader)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Securities list
    # ------------------------------------------------------------------

    async def list_securities(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        sector: str | None = None,
        kmi_only: bool = False,
        kse100_only: bool = False,
        search: str | None = None,
        active_only: bool = True,
    ) -> SecuritiesListResponse:
        cache_key = f"sec_list:{page}:{page_size}:{sector}:{kmi_only}:{kse100_only}:{search}:{active_only}"

        async def _load() -> dict:  # type: ignore[type-arg]
            query = select(Security)
            if active_only:
                query = query.where(Security.is_active.is_(True))
            if sector:
                query = query.where(Security.sector == sector)
            if kmi_only:
                query = query.where(Security.is_kmi_compliant.is_(True))
            if kse100_only:
                query = query.where(Security.is_kse100.is_(True))
            if search:
                pattern = f"%{search.upper()}%"
                query = query.where(
                    Security.symbol.like(pattern) | Security.company_name.ilike(f"%{search}%")
                )
            count_query = select(func.count()).select_from(query.subquery())
            total = (await self._db.execute(count_query)).scalar_one()
            offset = (page - 1) * page_size
            query = query.order_by(Security.symbol).offset(offset).limit(page_size)
            items = (await self._db.execute(query)).scalars().all()
            resp = SecuritiesListResponse(
                items=[SecurityResponse.model_validate(s) for s in items],
                total=total,
                page=page,
                page_size=page_size,
                has_next=(offset + len(items)) < total,
            )
            return resp.model_dump()

        data = await self._cached(cache_key, TTL_LIST, _load)
        return SecuritiesListResponse.model_validate(data)

    # ------------------------------------------------------------------
    # Single security
    # ------------------------------------------------------------------

    async def get_security(self, symbol: str) -> SecurityResponse | None:
        cache_key = f"sec:{symbol.upper()}"

        async def _load() -> dict | None:  # type: ignore[type-arg]
            result = await self._db.execute(
                select(Security).where(Security.symbol == symbol.upper())
            )
            security = result.scalar_one_or_none()
            if security is None:
                return None
            return SecurityResponse.model_validate(security).model_dump()

        data = await self._cached(cache_key, TTL_LIST, _load)
        return SecurityResponse.model_validate(data) if data else None

    async def upsert_security(self, data: SecurityCreate) -> SecurityResponse:
        result = await self._db.execute(
            select(Security).where(Security.symbol == data.symbol)
        )
        existing = result.scalar_one_or_none()
        if existing:
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(existing, field, value)
            security = existing
        else:
            security = Security(**data.model_dump())
            self._db.add(security)
        await self._db.flush()
        await self._db.refresh(security)
        return SecurityResponse.model_validate(security)

    # ------------------------------------------------------------------
    # OHLCV
    # ------------------------------------------------------------------

    async def get_ohlcv(
        self,
        symbol: str,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 252,
        adjusted: bool = True,
    ) -> OhlcvListResponse:
        cache_key = f"ohlcv:{symbol.upper()}:{date_from}:{date_to}:{limit}:{adjusted}"

        async def _load() -> dict:  # type: ignore[type-arg]
            query = select(OhlcvDaily).where(OhlcvDaily.symbol == symbol.upper())
            if date_from:
                query = query.where(OhlcvDaily.date >= date_from)
            if date_to:
                query = query.where(OhlcvDaily.date <= date_to)
            query = query.order_by(OhlcvDaily.date.desc()).limit(limit)
            rows = (await self._db.execute(query)).scalars().all()
            return OhlcvListResponse(
                symbol=symbol.upper(),
                interval="daily",
                items=[OhlcvResponse.model_validate(r) for r in rows],
                total=len(rows),
            ).model_dump()

        data = await self._cached(cache_key, TTL_OHLCV, _load)
        return OhlcvListResponse.model_validate(data)

    # ------------------------------------------------------------------
    # Fundamentals (OHLCV-derived + securities table)
    # ------------------------------------------------------------------

    async def get_fundamentals(self, symbol: str) -> FundamentalsResponse | None:
        sym = symbol.upper()
        cache_key = f"fundamentals:{sym}"

        async def _load() -> dict | None:  # type: ignore[type-arg]
            sec_result = await self._db.execute(
                select(Security).where(Security.symbol == sym)
            )
            security = sec_result.scalar_one_or_none()
            if security is None:
                return None

            # 52-week window from today
            today = datetime.now(tz=timezone.utc).date()
            year_ago = today.replace(year=today.year - 1)

            stats = await self._db.execute(
                select(
                    func.max(OhlcvDaily.high).label("high_52w"),
                    func.min(OhlcvDaily.low).label("low_52w"),
                    func.avg(OhlcvDaily.volume).label("avg_vol_30d"),
                ).where(
                    OhlcvDaily.symbol == sym,
                    OhlcvDaily.date >= year_ago,
                )
            )
            row = stats.one()

            # 30-day avg volume
            vol_stats = await self._db.execute(
                select(func.avg(OhlcvDaily.volume).label("avg_vol")).where(
                    OhlcvDaily.symbol == sym,
                    OhlcvDaily.date >= today.replace(month=today.month - 1)
                    if today.month > 1
                    else today.replace(year=today.year - 1, month=12),
                )
            )
            vol_row = vol_stats.one()

            return FundamentalsResponse(
                symbol=sym,
                week_52_high=Decimal(str(row.high_52w)) if row.high_52w else None,
                week_52_low=Decimal(str(row.low_52w)) if row.low_52w else None,
                avg_volume_30d=int(vol_row.avg_vol) if vol_row.avg_vol else None,
                market_cap_pkr=security.market_cap_pkr,
                shares_outstanding=security.shares_outstanding,
            ).model_dump()

        data = await self._cached(cache_key, TTL_FUNDAMENTALS, _load)
        return FundamentalsResponse.model_validate(data) if data else None

    # ------------------------------------------------------------------
    # Announcements (corporate actions)
    # ------------------------------------------------------------------

    async def get_announcements(
        self, symbol: str, limit: int = 50
    ) -> AnnouncementsListResponse:
        sym = symbol.upper()
        cache_key = f"announcements:{sym}:{limit}"

        async def _load() -> dict:  # type: ignore[type-arg]
            result = await self._db.execute(
                select(CorporateAction)
                .where(CorporateAction.symbol == sym)
                .order_by(CorporateAction.announcement_date.desc())
                .limit(limit)
            )
            items = result.scalars().all()
            return AnnouncementsListResponse(
                symbol=sym,
                items=[AnnouncementResponse.model_validate(i) for i in items],
                total=len(items),
            ).model_dump()

        data = await self._cached(cache_key, TTL_LIST, _load)
        return AnnouncementsListResponse.model_validate(data)

    # ------------------------------------------------------------------
    # Sectors
    # ------------------------------------------------------------------

    async def list_sectors(self) -> list[str]:
        async def _load() -> list[str]:
            result = await self._db.execute(
                select(Security.sector)
                .where(Security.is_active.is_(True))
                .distinct()
                .order_by(Security.sector)
            )
            return list(result.scalars().all())

        if self._redis is None:
            return await _load()

        data = await cached(self._redis, "sectors", TTL_SECTORS, _load)
        return data if isinstance(data, list) else []

    # ------------------------------------------------------------------
    # Quotes (batch latest close + day change)
    # ------------------------------------------------------------------

    async def get_quotes(self, symbols: list[str]) -> QuotesResponse:
        if not symbols:
            return QuotesResponse(items=[])

        normalised = [s.upper().strip() for s in symbols if s.strip()]
        cache_key = f"quotes:{','.join(sorted(set(normalised)))}"

        async def _load() -> list[dict]:  # type: ignore[type-arg]
            from sqlalchemy import tuple_

            # For each symbol get the two most recent OHLCV rows.
            # Use a subquery with ROW_NUMBER for portability across SQLite (tests) and Postgres.
            from sqlalchemy import func as _f

            row_num = (
                _f.row_number()
                .over(partition_by=OhlcvDaily.symbol, order_by=OhlcvDaily.date.desc())
                .label("rn")
            )
            subq = (
                select(
                    OhlcvDaily.symbol,
                    OhlcvDaily.date,
                    OhlcvDaily.close,
                    row_num,
                )
                .where(OhlcvDaily.symbol.in_(normalised))
                .subquery()
            )
            rows = (
                await self._db.execute(
                    select(subq.c.symbol, subq.c.date, subq.c.close, subq.c.rn).where(
                        subq.c.rn <= 2
                    )
                )
            ).all()

            by_symbol: dict[str, list[tuple]] = {}  # type: ignore[type-arg]
            for sym, dt, close, rn in rows:
                by_symbol.setdefault(sym, []).append((rn, dt, close))

            items: list[dict] = []  # type: ignore[type-arg]
            for sym in normalised:
                entries = sorted(by_symbol.get(sym, []), key=lambda x: x[0])
                last = entries[0] if len(entries) >= 1 else None
                prev = entries[1] if len(entries) >= 2 else None
                last_close = Decimal(str(last[2])) if last and last[2] is not None else None
                prev_close = Decimal(str(prev[2])) if prev and prev[2] is not None else None
                change = (
                    last_close - prev_close
                    if last_close is not None and prev_close is not None
                    else None
                )
                change_pct = (
                    (change / prev_close) * Decimal("100")
                    if change is not None and prev_close
                    else None
                )
                items.append(
                    Quote(
                        symbol=sym,
                        last_close=last_close,
                        prev_close=prev_close,
                        last_date=last[1] if last else None,
                        change=change,
                        change_pct=change_pct,
                    ).model_dump()
                )
            return items

        if self._redis is None:
            data = await _load()
        else:
            data = await cached(self._redis, cache_key, TTL_LIVE, _load)
        return QuotesResponse(items=[Quote.model_validate(d) for d in data])

    # ------------------------------------------------------------------
    # Indices
    # ------------------------------------------------------------------

    async def get_indices(self) -> list[IndexPerformance]:
        async def _load() -> list[dict]:  # type: ignore[type-arg]
            indices = [
                ("KSE-100", Security.is_kse100),
                ("KSE-30", Security.is_kse30),
                ("KMI-30", Security.is_kmi_compliant),
            ]
            results = []
            today = datetime.now(tz=timezone.utc).date()

            for name, flag in indices:
                count_result = await self._db.execute(
                    select(func.count()).where(Security.is_active.is_(True), flag.is_(True))
                )
                count = count_result.scalar_one()

                perf = IndexPerformance(
                    name=name,
                    constituent_count=count,
                    last_close_date=None,
                    change_1d_pct=None,
                    change_1w_pct=None,
                    change_1m_pct=None,
                    change_ytd_pct=None,
                )
                results.append(perf.model_dump())

            return results

        if self._redis is None:
            data = await _load()
        else:
            data = await cached(self._redis, "indices", TTL_LIVE, _load)
        return [IndexPerformance.model_validate(d) for d in data]
