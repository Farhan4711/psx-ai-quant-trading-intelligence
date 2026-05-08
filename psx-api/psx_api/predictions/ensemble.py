"""
Stacked-ensemble prediction interface.

Phase 2 ships a **heuristic placeholder** ensemble. Real LSTM + XGBoost +
RandomForest training requires:

  - 5+ years of clean OHLCV across the top-50 PSX names
  - Labelled training data + proper time-series CV
  - GPU/CPU budget for training + ONNX serialisation
  - A retraining cron (Step 46)

None of which we have running yet. So we keep the **interface** real (a
3-model ensemble + logistic stacking + variance-based confidence) but
swap in a deterministic heuristic that scores the feature vector using
hand-tuned weights derived from the published research baseline (the
build plan cites Williams %R, Momentum, Disparity 5 as the three
strongest features on PSX).

When real ONNX models drop in, the only file that changes is this one —
the service, schema, and UI keep working.

Output contract:
  - probability_up:  P(close[t+1] > close[t]) ∈ [0,1]
  - per-model probabilities for the stacking layer
  - variance-based confidence label
  - top-3 contributing features
  - model_version string (lets the client cache + invalidate cleanly)
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp
from statistics import variance


MODEL_VERSION = "heuristic-v0.1.0"


@dataclass(frozen=True)
class FeatureContribution:
    name: str
    value: float | None
    contribution: str           # "positive" | "negative" | "neutral"


@dataclass(frozen=True)
class Prediction:
    probability_up: float
    confidence: str             # "high" | "medium" | "low"
    confidence_score: float     # 0..1, raw
    sub_model_probabilities: dict[str, float]
    top_features: list[FeatureContribution]
    model_version: str
    horizon_days: int


# ── Heuristic sub-models ────────────────────────────────────────────────
#
# Each sub-model returns a probability ∈ [0,1] that the next-day close
# will be higher than today's. We deliberately keep them **different
# enough** that the stacking layer's confidence signal (1-variance)
# behaves realistically — high agreement = high confidence.


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = exp(-x)
        return 1 / (1 + z)
    z = exp(x)
    return z / (1 + z)


def _model_lstm_proxy(f: dict) -> float:
    """Momentum-heavy: weights recent log returns + Williams %R + RSI."""
    score = 0.0
    if f.get("log_return_5d") is not None:
        score += f["log_return_5d"] * 8
    if f.get("log_return_10d") is not None:
        score += f["log_return_10d"] * 4
    if f.get("williams_r_14") is not None:
        # Williams %R is in [-100, 0]; -20 is overbought, -80 oversold
        score += (-50 - f["williams_r_14"]) / 50 * 0.4
    if f.get("rsi_14") is not None:
        score += (50 - f["rsi_14"]) / 50 * 0.3
    return _sigmoid(score)


def _model_xgb_proxy(f: dict) -> float:
    """Mean-reversion + Bollinger feature-mix (matches XGBoost's typical bias)."""
    score = 0.0
    if f.get("bollinger_pct_b") is not None:
        # %B near 0 → near lower band → mean-revert long bias
        score += (0.5 - f["bollinger_pct_b"]) * 0.8
    if f.get("disparity_5") is not None:
        score -= f["disparity_5"] * 4   # stretched above SMA → pullback
    if f.get("macd_histogram") is not None:
        score += f["macd_histogram"] * 0.05
    if f.get("volume_z_20") is not None and f.get("log_return_1d") is not None:
        # Volume + price together (PSV signal)
        score += f["volume_z_20"] * (1 if f["log_return_1d"] > 0 else -1) * 0.15
    return _sigmoid(score)


def _model_rf_proxy(f: dict) -> float:
    """Trend-following: SMA disparity + KSE-100 context."""
    score = 0.0
    if f.get("disparity_10") is not None:
        score += f["disparity_10"] * 3
    if f.get("momentum_10") is not None:
        score += f["momentum_10"] * 4
    if f.get("kse100_return_pct") is not None:
        score += f["kse100_return_pct"] / 100 * 1.5
    if f.get("rsi_14") is not None:
        score += (f["rsi_14"] - 50) / 50 * 0.2
    return _sigmoid(score)


# ── Stacking + confidence ──────────────────────────────────────────────


def _stacked_probability(probs: list[float]) -> float:
    """
    Logistic regression with hand-tuned weights — learnt weights would
    replace the constants here. Average + soft-bias toward agreement.
    """
    if not probs:
        return 0.5
    mean = sum(probs) / len(probs)
    # Slight contraction toward 0.5 when models disagree heavily
    spread = max(probs) - min(probs)
    contracted = mean - (mean - 0.5) * spread * 0.4
    return max(0.01, min(0.99, contracted))


def _confidence(probs: list[float]) -> tuple[str, float]:
    """High agreement → high confidence. Variance-based per build plan."""
    if len(probs) < 2:
        return "low", 0.0
    var = variance(probs)
    # Variance of three points all in [0,1] caps around 0.083; scale to 0..1.
    score = max(0.0, 1 - var * 12)
    if score > 0.75:
        return "high", score
    if score > 0.45:
        return "medium", score
    return "low", score


# ── Top features ───────────────────────────────────────────────────────


_FEATURE_DIRECTION: dict[str, int] = {
    # +1 = higher value pushes probability up; -1 = pushes down
    "log_return_5d": 1,
    "log_return_10d": 1,
    "momentum_10": 1,
    "disparity_5": -1,           # stretched above SMA → pullback risk
    "disparity_10": 1,            # uptrend confirmation at 10-day scale
    "rsi_14": -1,                 # >70 overbought → bearish
    "williams_r_14": -1,          # closer to 0 = more overbought
    "macd_histogram": 1,
    "bollinger_pct_b": -1,
    "kse100_return_pct": 1,
    "volume_z_20": 1,
}


def _top_contributions(features: dict, probability: float) -> list[FeatureContribution]:
    """
    Pick the 3 features with the largest absolute "directional impact"
    relative to a neutral baseline — magnitude × direction × baseline.
    Heuristic, but enough for the UI's "key features" list until SHAP
    values from real models replace it.
    """
    scored: list[tuple[float, FeatureContribution]] = []
    for name, dir_sign in _FEATURE_DIRECTION.items():
        v = features.get(name)
        if v is None:
            continue
        # Normalise by typical scale per feature so all weights are comparable
        normaliser = {
            "rsi_14": 50.0,
            "williams_r_14": 50.0,
            "kse100_return_pct": 1.0,
            "volume_z_20": 1.0,
            "log_return_5d": 0.05,
            "log_return_10d": 0.05,
            "momentum_10": 0.05,
            "disparity_5": 0.05,
            "disparity_10": 0.05,
            "macd_histogram": 1.0,
            "bollinger_pct_b": 0.5,
        }.get(name, 1.0)
        normed = v / normaliser if normaliser else v
        impact = abs(normed)
        # Direction relative to current prediction
        signed = normed * dir_sign
        if probability >= 0.5:
            contribution = "positive" if signed >= 0 else "negative"
        else:
            contribution = "negative" if signed >= 0 else "positive"
        if abs(signed) < 0.05:
            contribution = "neutral"
        scored.append((impact, FeatureContribution(name=name, value=v, contribution=contribution)))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [fc for _, fc in scored[:3]]


# ── Public ──────────────────────────────────────────────────────────────


def predict(features: dict, *, horizon_days: int = 1) -> Prediction:
    """One-shot: features → ensembled probability + confidence + top features."""
    probs = {
        "lstm": _model_lstm_proxy(features),
        "xgboost": _model_xgb_proxy(features),
        "random_forest": _model_rf_proxy(features),
    }
    stacked = _stacked_probability(list(probs.values()))
    confidence, score = _confidence(list(probs.values()))
    top = _top_contributions(features, stacked)
    return Prediction(
        probability_up=stacked,
        confidence=confidence,
        confidence_score=score,
        sub_model_probabilities=probs,
        top_features=top,
        model_version=MODEL_VERSION,
        horizon_days=horizon_days,
    )
