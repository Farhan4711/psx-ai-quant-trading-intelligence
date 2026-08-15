"""Tests for the Phase 2C pure modules: features + heuristic ensemble."""

from psx_api.predictions.ensemble import predict
from psx_api.predictions.features import (
    FEATURE_NAMES,
    MarketContext,
    OhlcvBar,
    compute_features,
)

# ── Fixtures ───────────────────────────────────────────────────────────


def _ramp(start: float, n: int, daily_pct: float) -> list[OhlcvBar]:
    out: list[OhlcvBar] = []
    p = start
    for i in range(n):
        out.append(
            OhlcvBar(
                open=p,
                high=p * 1.005,
                low=p * 0.995,
                close=p,
                volume=1_000_000 + (i * 1_000),
            )
        )
        p *= 1 + daily_pct
    return out


# ── Features ────────────────────────────────────────────────────────────


class TestFeatures:
    def test_returns_all_feature_names(self) -> None:
        bars = _ramp(100.0, 80, 0.001)
        f = compute_features(bars)
        for name in FEATURE_NAMES:
            assert name in f, f"Missing feature {name}"

    def test_short_history_yields_nones_for_long_windows(self) -> None:
        bars = _ramp(100.0, 5, 0.001)
        f = compute_features(bars)
        # 5 bars: 1d return computable, 20d not
        assert f["log_return_1d"] is not None
        assert f["log_return_20d"] is None
        assert f["price_z_50"] is None  # needs 50

    def test_macro_context_passes_through(self) -> None:
        bars = _ramp(100.0, 80, 0.001)
        ctx = MarketContext(kse100_return_pct=0.5, kibor_6m_pct=12.5, pkr_usd_change_pct=-0.2)
        f = compute_features(bars, ctx)
        assert f["kse100_return_pct"] == 0.5
        assert f["kibor_6m_pct"] == 12.5
        assert f["pkr_usd_change_pct"] == -0.2

    def test_uptrend_yields_positive_disparity_5(self) -> None:
        bars = _ramp(100.0, 80, 0.005)  # steady uptrend
        f = compute_features(bars)
        assert f["disparity_5"] is not None
        assert f["disparity_5"] > 0  # current price above 5-day SMA

    def test_empty_bars_returns_empty_dict(self) -> None:
        assert compute_features([]) == {}

    def test_bollinger_pct_b_in_typical_range(self) -> None:
        bars = _ramp(100.0, 80, 0.001)
        f = compute_features(bars)
        b = f["bollinger_pct_b"]
        assert b is not None
        # In a steady uptrend %B is well-defined; should be > 0
        assert 0 <= b <= 1.5


# ── Ensemble ────────────────────────────────────────────────────────────


class TestEnsemble:
    def test_uptrend_predicts_above_50_pct(self) -> None:
        bars = _ramp(100.0, 80, 0.005)
        f = compute_features(bars)
        p = predict(f)
        assert p.probability_up > 0.5

    def test_returns_within_0_1(self) -> None:
        bars = _ramp(100.0, 80, 0.0)
        f = compute_features(bars)
        p = predict(f)
        assert 0 <= p.probability_up <= 1

    def test_three_sub_models(self) -> None:
        bars = _ramp(100.0, 80, 0.001)
        f = compute_features(bars)
        p = predict(f)
        assert set(p.sub_model_probabilities.keys()) == {"lstm", "xgboost", "random_forest"}

    def test_top_features_max_3(self) -> None:
        bars = _ramp(100.0, 80, 0.002)
        f = compute_features(bars)
        p = predict(f)
        assert len(p.top_features) <= 3

    def test_confidence_levels_valid(self) -> None:
        bars = _ramp(100.0, 80, 0.001)
        f = compute_features(bars)
        p = predict(f)
        assert p.confidence in ("high", "medium", "low")
        assert 0 <= p.confidence_score <= 1

    def test_high_agreement_high_confidence(self) -> None:
        """All three sub-models on a strong uptrend should mostly agree."""
        bars = _ramp(100.0, 80, 0.005)
        f = compute_features(bars)
        p = predict(f)
        # On a clear regime, models should agree → confidence high or medium
        assert p.confidence in ("high", "medium")
