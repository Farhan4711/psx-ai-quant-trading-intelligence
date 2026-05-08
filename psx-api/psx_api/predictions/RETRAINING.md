# Model Retraining Schedule (Phase 2 Step 46)

The Phase 2 v1 ships with a **heuristic placeholder ensemble**
(`psx_api/predictions/ensemble.py` → `MODEL_VERSION = "heuristic-v0.1.0"`).
Real LSTM + XGBoost + RandomForest training is documented here so the
infra is ready when training data + GPU/CPU budget land.

## When real models exist

### Daily reconciliation job
- **Trigger**: nightly cron at 23:00 PKT
- **Action**: for every prediction issued ≥1 horizon ago, look up the
  realised next-day close in `ohlcv_daily` and write
  `model_predictions.realised_direction` (1 if up, 0 if flat/down).
- **SQL sketch**:
  ```sql
  UPDATE model_predictions p
  SET realised_direction = CASE
    WHEN o2.close > o1.close THEN 1
    ELSE 0
  END
  FROM ohlcv_daily o1, ohlcv_daily o2
  WHERE p.symbol = o1.symbol
    AND o1.date = p.as_of_date
    AND o2.symbol = p.symbol
    AND o2.date = (SELECT MIN(date) FROM ohlcv_daily
                    WHERE symbol = p.symbol AND date > p.as_of_date)
    AND p.realised_direction IS NULL;
  ```

### Monthly retrain job
- **Trigger**: 1st of each month, 02:00 PKT
- **Steps**:
  1. Pull last 8 years of OHLCV + macro for top-50 by avg-daily-volume.
  2. Compute features (`psx_api/predictions/features.compute_features`).
  3. Train LSTM (Keras), XGBoost (xgboost), Random Forest (sklearn).
  4. Train logistic stacking layer on out-of-fold predictions.
  5. Evaluate on held-out 2024 test set: per-stock accuracy, F1, ROC.
  6. Bump model_version (e.g. `production-v1.4.0`).
  7. Export each base model + meta-model to ONNX.
  8. Upload to model bucket; update `model_versions` registry table
     (not yet created — add when training pipeline lands).

### Live-accuracy gate
- **Read in**: `PredictionService._live_accuracy_pct()` already wired —
  rolling 30-day reconciled accuracy per `(symbol, model_version)`.
- **Auto-disable threshold**: 53% (build-plan baseline). When a model
  drops below this on a given symbol, set
  `securities.predictions_disabled = TRUE` for that symbol (column not
  yet added — migrate when training lands) and Slack-alert.
- The Signal panel already handles `predictions_disabled: True` in the
  response, so no UI change needed when the gate fires.

## Why we ship the placeholder now

The placeholder lets us:
- Build + ship the **whole UI surface** (Signal panel, top features,
  confidence labels, disabled-state)
- Persist real prediction rows so when real models drop in, the
  `model_predictions` history is already 30+ days deep — live-accuracy
  gauges work on day 1
- Validate the API contract against the inference service's eventual
  ONNX runtime path
- Keep `MODEL_VERSION` strings versioned, so the cutover is just a
  single deploy + DB-bump, not a UI rewrite
