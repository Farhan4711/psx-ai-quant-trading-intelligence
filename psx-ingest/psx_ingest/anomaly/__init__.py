"""
Per-symbol anomaly detection — sklearn IsolationForest trained on 2
years of OHLCV-derived features.

Why a real model instead of staying with the L2 z-norm baseline?
----------------------------------------------------------------
The L2 norm in `psx_api/alerts/pump_dump.py:anomaly_score()` works as
a baseline but treats every feature as Gaussian and i.i.d. — it can't
learn that some symbols have naturally fat-tailed volume, or that high
intraday range without a price move is more anomalous than range +
price together. IsolationForest is the smallest model that captures
those joint patterns and is also cheap to train per-symbol nightly.

The contract with psx-api stays identical: a single non-negative float
`anomaly_score` per (symbol, day). Old rows scored by the L2 baseline
stay valid because we don't store the score's source; consumers only
ever compare scores within a (symbol, window).

Layout
------
- `features.py`  — pure-Python feature builder mirroring AnomalyFeatures
                   in psx_api.alerts.pump_dump so the trainer and the
                   detector see identical inputs
- `train.py`     — trainer; one `IsolationForest(contamination=0.02)`
                   per symbol, fit on the trailing 2y of bars
- `score.py`     — inference helper for psx-api (loads .joblib lazily)
- `tasks/anomaly.py` (in tasks/) — Celery wrapper
"""
