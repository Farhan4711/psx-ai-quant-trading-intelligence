# psx-inference — ML Model Training & Inference Service

Separate FastAPI microservice for serving ML price prediction models.
Isolated so model deploys never restart the main API.

## Tech Stack

- Python 3.11+, FastAPI
- ONNX Runtime (inference — fast, no PyTorch dependency at serve time)
- PyTorch + scikit-learn + XGBoost (training only)
- pandas-ta (feature engineering)

## Why Separate?

- Model reloads (~2–10 seconds) must not interrupt the main API
- GPU dependency isolated here — main API runs on CPU
- Can scale independently during prediction-heavy periods
- Model versioning and rollback scoped to this service

## Directory Structure (to be created in Phase 2)

```
psx-inference/
├── psx_inference/
│   ├── main.py                 # FastAPI app
│   ├── models/
│   │   ├── lstm.py             # LSTM architecture definition
│   │   ├── xgboost_model.py
│   │   └── ensemble.py         # Stacking meta-model
│   ├── features/
│   │   └── pipeline.py         # Feature engineering (60-day window)
│   ├── training/
│   │   ├── train.py            # Training orchestration
│   │   └── evaluate.py         # Per-stock validation + threshold gating
│   └── routers/
│       └── predict.py          # POST /predict endpoint
├── models/                     # ONNX model files (gitignored)
│   └── .gitkeep
├── tests/
├── pyproject.toml
└── .env.example
```

## Model Acceptance Policy

Any stock where the best ensemble fails to achieve **≥ 53% accuracy** on the
held-out test set is marked `predictions_disabled = True` in the database.
The UI surfaces this explicitly — it never silently falls back to an unreliable model.
