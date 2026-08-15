"""
Inference-time loader.

Used both from `psx-ingest` jobs (test the model after training) and
from `psx-api` (`AlertService` lazy-loads on first use). Imports
sklearn + joblib lazily so a missing dep just disables the model
path; the L2 baseline in `pump_dump.anomaly_score()` keeps working.

Scoring convention
------------------
`predict_anomaly_score(model, features)` returns a non-negative float
in the same direction as the L2 baseline: higher = more anomalous.
We map sklearn's `score_samples` (negative for anomalies, more
negative = more anomalous) by negating and shifting to [0, ∞).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import structlog

from psx_ingest.anomaly.features import FEATURE_ORDER
from psx_ingest.anomaly.train import model_path

logger = structlog.get_logger(__name__)


def load_model(symbol: str, *, model_dir: Path | None = None) -> Any | None:
    """Returns the joblib payload `{"model", "feature_order", "trained_at"}`
    or None if the file doesn't exist / can't be read."""
    path = model_path(symbol, model_dir=model_dir)
    if not path.exists():
        return None
    try:
        import joblib

        payload = joblib.load(path)
    except Exception as exc:
        logger.warning("anomaly.load_failed", symbol=symbol, path=str(path), error=str(exc))
        return None
    # Defensive: a payload from an older feature order would silently
    # mis-align columns at scoring time.
    if list(payload.get("feature_order", [])) != list(FEATURE_ORDER):
        logger.warning(
            "anomaly.feature_order_mismatch",
            symbol=symbol,
            payload_order=payload.get("feature_order"),
        )
        return None
    return payload


def predict_anomaly_score(payload: Any, features: Sequence[float]) -> float:
    """Score one feature vector. `features` must be in `FEATURE_ORDER`."""
    if len(features) != len(FEATURE_ORDER):
        raise ValueError(f"Expected {len(FEATURE_ORDER)} features, got {len(features)}.")
    model = payload["model"]
    # sklearn's score_samples: more negative = more anomalous. Shift
    # to a non-negative "louder = more anomalous" scale aligned with
    # the L2 baseline in psx_api.alerts.pump_dump.
    raw = float(model.score_samples([list(features)])[0])
    return round(max(0.0, -raw), 4)
