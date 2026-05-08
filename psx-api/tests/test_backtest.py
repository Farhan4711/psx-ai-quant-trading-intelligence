"""Tests for the pure-Python backtest engine + strategies."""

from datetime import date, timedelta

import pytest

from psx_api.backtest.engine import Bar, run
from psx_api.backtest.metrics import buy_and_hold_return_pct, compute_metrics
from psx_api.backtest.narrate import lessons, narrate_trade
from psx_api.backtest.strategies import get_strategy, list_strategies


# ── Synthetic bar generators ────────────────────────────────────────────


def _bars(prices: list[float], start: date = date(2024, 1, 1)) -> list[Bar]:
    """Build daily bars from a list of closes. open=close-1, high=close+1, low=close-1."""
    out: list[Bar] = []
    for i, p in enumerate(prices):
        out.append(
            Bar(
                date=start + timedelta(days=i),
                open=p,
                high=p + 0.5,
                low=p - 0.5,
                close=p,
                adjusted_close=p,
                volume=1_000_000,
            )
        )
    return out


def _ramp(start_price: float, n: int, daily_pct: float) -> list[float]:
    p = start_price
    out = [p]
    for _ in range(n - 1):
        p *= 1 + daily_pct
        out.append(p)
    return out


# ── Engine basics ───────────────────────────────────────────────────────


class TestEngine:
    def test_buy_and_hold_captures_full_run(self) -> None:
        bars = _bars(_ramp(100, 250, 0.001))
        bt = run(
            bars,
            strategy=get_strategy("buy_and_hold"),
            initial_capital_pkr=100_000,
            commission_per_side_pct=0.0,
            warmup_bars=0,
        )
        # With 0% commission, final ≈ initial * (last/first), close to 1.001^249 ≈ 1.284
        assert bt.final_equity_pkr == pytest.approx(100_000 * (bars[-1].close / bars[1].open), rel=0.01)
        assert len(bt.trades) == 1  # entered + closed at end

    def test_no_trades_when_strategy_always_flat(self) -> None:
        bars = _bars([100.0] * 100)

        def flat(_b: list[Bar], _i: int) -> int:
            return 0

        bt = run(bars, strategy=flat, initial_capital_pkr=50_000, warmup_bars=0)
        assert bt.trades == []
        assert bt.final_equity_pkr == 50_000

    def test_commission_reduces_returns(self) -> None:
        bars = _bars([100.0, 110.0, 110.0, 110.0, 110.0])

        def long_then_flat(bs: list[Bar], i: int) -> int:
            return 1 if i == 0 else 0

        bt_no_commish = run(
            bars, strategy=long_then_flat, initial_capital_pkr=10_000,
            commission_per_side_pct=0.0, warmup_bars=0,
        )
        bt_commish = run(
            bars, strategy=long_then_flat, initial_capital_pkr=10_000,
            commission_per_side_pct=0.5, warmup_bars=0,
        )
        assert bt_commish.final_equity_pkr < bt_no_commish.final_equity_pkr

    def test_force_close_at_end(self) -> None:
        bars = _bars(_ramp(100, 50, 0.005))

        def always_long(_b: list[Bar], _i: int) -> int:
            return 1

        bt = run(bars, strategy=always_long, initial_capital_pkr=10_000, warmup_bars=0)
        assert len(bt.trades) == 1
        assert bt.trades[0].exit_date == bars[-1].date
        assert "End of backtest period" in bt.trades[0].reason_close

    def test_empty_bars_raises(self) -> None:
        with pytest.raises(ValueError):
            run([], strategy=get_strategy("buy_and_hold"), initial_capital_pkr=10_000)


# ── Strategies ──────────────────────────────────────────────────────────


class TestStrategies:
    def test_all_strategies_registered(self) -> None:
        keys = {s["key"] for s in list_strategies()}
        assert keys == {
            "sma_crossover", "rsi_oversold", "macd_signal",
            "bollinger_revert", "buy_and_hold",
        }

    def test_unknown_strategy_raises(self) -> None:
        with pytest.raises(ValueError):
            get_strategy("nonexistent")

    def test_sma_crossover_on_uptrend(self) -> None:
        # 250 days steadily rising — 50 SMA stays above 200 SMA → strategy stays long
        bars = _bars(_ramp(100, 250, 0.002))
        strategy = get_strategy("sma_crossover", {"fast_period": 10, "slow_period": 30})
        bt = run(bars, strategy=strategy, initial_capital_pkr=10_000,
                 commission_per_side_pct=0.0, warmup_bars=30)
        assert bt.final_equity_pkr > 10_000

    def test_buy_and_hold_matches_underlying_return(self) -> None:
        # buy_and_hold returns 1 starting at i=1, so the engine fills at bars[2].open
        # (the next bar after the first signal). End is bars[-1].close (force-close).
        bars = _bars(_ramp(100, 100, 0.003))
        bt = run(bars, strategy=get_strategy("buy_and_hold"),
                 initial_capital_pkr=10_000, commission_per_side_pct=0.0,
                 warmup_bars=0)
        underlying_return = (bars[-1].close - bars[2].open) / bars[2].open
        strategy_return = (bt.final_equity_pkr - 10_000) / 10_000
        assert strategy_return == pytest.approx(underlying_return, rel=0.005)


# ── Metrics ─────────────────────────────────────────────────────────────


class TestMetrics:
    def test_metrics_for_steady_uptrend(self) -> None:
        bars = _bars(_ramp(100, 250, 0.001))  # ~28% over the period
        bt = run(bars, strategy=get_strategy("buy_and_hold"),
                 initial_capital_pkr=100_000, commission_per_side_pct=0.0,
                 warmup_bars=0)
        bench = buy_and_hold_return_pct(bt)
        m = compute_metrics(bt, benchmark_return_pct=bench)
        assert m.total_return_pct > 0
        assert m.max_drawdown_pct >= 0
        assert m.num_trades == 1

    def test_buy_and_hold_excess_return_near_zero(self) -> None:
        bars = _bars(_ramp(100, 250, 0.001))
        bt = run(bars, strategy=get_strategy("buy_and_hold"),
                 initial_capital_pkr=100_000, commission_per_side_pct=0.0,
                 warmup_bars=0)
        bench = buy_and_hold_return_pct(bt)
        m = compute_metrics(bt, benchmark_return_pct=bench)
        # Buy-and-hold strategy should track benchmark within rounding
        assert abs(m.excess_return_pct) < 0.5


# ── Narration ───────────────────────────────────────────────────────────


class TestNarration:
    def test_narrate_trade_includes_dates_and_pnl(self) -> None:
        bars = _bars(_ramp(100, 50, 0.005))
        bt = run(bars, strategy=get_strategy("buy_and_hold"),
                 initial_capital_pkr=10_000, commission_per_side_pct=0.1,
                 warmup_bars=0)
        assert bt.trades, "buy-and-hold should produce 1 trade"
        text = narrate_trade(bt.trades[0], "ENGRO")
        assert "ENGRO" in text
        assert bt.trades[0].entry_date.isoformat() in text
        assert bt.trades[0].exit_date.isoformat() in text

    def test_lessons_handles_no_trades(self) -> None:
        # Strategy that never triggers
        bars = _bars([100.0] * 50)
        bt = run(bars, strategy=lambda _b, _i: 0,
                 initial_capital_pkr=10_000, warmup_bars=0)
        bench = buy_and_hold_return_pct(bt)
        m = compute_metrics(bt, benchmark_return_pct=bench)
        ls = lessons(m, strategy_label="Test")
        assert any("never triggered" in l for l in ls)
