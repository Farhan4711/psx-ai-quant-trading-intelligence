"""
Tests for the IsolationForest anomaly trainer.

No DB needed — we exercise the pure-Python feature builder and the
sklearn round-trip on synthetic bars. Skipped if sklearn isn't
installed locally so the test suite stays green in light dev envs.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from psx_ingest.anomaly.features import (
    FEATURE_ORDER,
    Bar,
    features_for_bars,
    vol_ma,
)

# ── Pure-Python feature builder ───────────────────────────────────


def test_vol_ma_skips_warmup() -> None:
    out = vol_ma([1.0] * 25, window=20)
    # First 19 entries are 0 (warmup); 20th onward is the running mean.
    assert out[:19] == [0.0] * 19
    assert out[19] == pytest.approx(1.0)
    assert out[24] == pytest.approx(1.0)


def test_features_for_bars_shape_matches_feature_order() -> None:
    bars = [Bar(open=100, high=102, low=99, close=101, volume=10_000) for _ in range(30)]
    matrix = features_for_bars(bars)
    assert len(matrix) == 30
    for row in matrix:
        assert len(row) == len(FEATURE_ORDER)


def test_features_gap_pct_uses_prev_close() -> None:
    bars = [
        Bar(open=100, high=101, low=99, close=100, volume=1_000),
        Bar(open=110, high=112, low=109, close=111, volume=1_000),
    ]
    matrix = features_for_bars(bars)
    # gap_pct on bar 2 = (open=110 - prev_close=100) / 100 * 100 = 10
    gap_idx = FEATURE_ORDER.index("gap_pct")
    assert matrix[1][gap_idx] == pytest.approx(10.0)


# ── Trainer (lazy sklearn import) ─────────────────────────────────


def _make_bars(n: int) -> list[Bar]:
    """Synthetic trending bars with a small Gaussian noise pattern."""
    rng = random.Random(42)  # noqa: S311 — synthetic test fixture, not security-sensitive
    bars: list[Bar] = []
    price = 100.0
    for _ in range(n):
        drift = rng.gauss(0.0005, 0.01)
        price *= 1 + drift
        rng_low = price * (1 - abs(rng.gauss(0, 0.005)))
        rng_high = price * (1 + abs(rng.gauss(0, 0.005)))
        bars.append(
            Bar(
                open=price,
                high=rng_high,
                low=rng_low,
                close=price * (1 + rng.gauss(0, 0.005)),
                volume=rng.uniform(10_000, 30_000),
            )
        )
    return bars


def _has_sklearn() -> bool:
    try:
        import sklearn  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _has_sklearn(), reason="sklearn not installed")
def test_fit_one_returns_none_for_short_history() -> None:
    from psx_ingest.anomaly.train import fit_one

    assert fit_one(_make_bars(50)) is None


@pytest.mark.skipif(not _has_sklearn(), reason="sklearn not installed")
def test_fit_one_trains_on_long_history() -> None:
    from psx_ingest.anomaly.train import fit_one

    model = fit_one(_make_bars(300))
    assert model is not None
    # Sanity: scoring a "weird" bar (3× normal volume + 6% jump)
    # should be more anomalous than a normal one.
    from psx_ingest.anomaly.features import features_for_bars

    weird = _make_bars(300)
    weird.append(Bar(open=200, high=220, low=200, close=215, volume=200_000))
    normal_features = features_for_bars(weird[:-1])[-1]
    weird_features = features_for_bars(weird)[-1]
    # IsolationForest score_samples: more negative = more anomalous
    s_normal = model.score_samples([normal_features])[0]
    s_weird = model.score_samples([weird_features])[0]
    assert s_weird < s_normal


@pytest.mark.skipif(not _has_sklearn(), reason="sklearn not installed")
def test_save_and_load_round_trip(tmp_path: Path) -> None:
    from psx_ingest.anomaly.score import load_model, predict_anomaly_score
    from psx_ingest.anomaly.train import fit_one, save_model

    bars = _make_bars(300)
    model = fit_one(bars)
    assert model is not None
    save_model(model, "HBL", model_dir=tmp_path)
    payload = load_model("HBL", model_dir=tmp_path)
    assert payload is not None
    # Score is non-negative
    from psx_ingest.anomaly.features import features_for_bars

    feats = features_for_bars(bars)[-1]
    score = predict_anomaly_score(payload, feats)
    assert score >= 0.0


def test_load_model_returns_none_when_missing(tmp_path: Path) -> None:
    from psx_ingest.anomaly.score import load_model

    assert load_model("DOES_NOT_EXIST", model_dir=tmp_path) is None
