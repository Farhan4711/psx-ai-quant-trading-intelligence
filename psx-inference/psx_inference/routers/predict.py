"""
POST /predict — the runtime endpoint psx-api hits.

Request shape mirrors what `psx_api.services.prediction_service`
already builds for the heuristic ensemble:
  - features: dict of feature_name → float (matching FEATURE_NAMES)
  - window:   optional 30×N matrix for the LSTM (oldest → newest)

Response is the `PredictionResult` from `psx_inference.inference`
serialized to JSON.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from psx_inference.inference import ModelRegistry, predict

router = APIRouter(tags=["predict"])


class PredictRequest(BaseModel):
    symbol: str = Field(..., examples=["HBL"])
    features: dict[str, float] = Field(
        ...,
        description=(
            "Feature dict in the order specified by the symbol's "
            "manifest.json — extra/missing keys are tolerated, "
            "missing ones default to 0.0."
        ),
    )
    window: list[dict[str, float]] | None = Field(
        default=None,
        description=(
            "Optional last-N feature rows (oldest → newest) for the "
            "LSTM. If omitted, the LSTM sub-model is skipped."
        ),
    )


class PredictResponse(BaseModel):
    symbol: str
    prob_up: float
    confidence: str
    sub_probabilities: dict[str, float]
    predictions_disabled: bool
    reason: str | None
    model_version: str


@router.post("/predict", response_model=PredictResponse)
def post_predict(payload: PredictRequest) -> PredictResponse:
    registry = ModelRegistry.get()
    bundle = registry.get_bundle(payload.symbol)
    if bundle is None:
        # Caller can use this to flip to the heuristic fallback.
        raise HTTPException(
            status_code=404,
            detail=(
                f"No trained model for {payload.symbol!r}. "
                f"Known: {len(registry.known_symbols())} symbols."
            ),
        )

    # Align features → fixed-length vector in bundle's order, defaulting to 0.
    vec = [float(payload.features.get(name, 0.0)) for name in bundle.feature_names]

    window: list[list[float]] | None = None
    if payload.window:
        window = [
            [float(row.get(name, 0.0)) for name in bundle.feature_names] for row in payload.window
        ]

    result = predict(bundle, vec, window=window)
    return PredictResponse(
        symbol=result.symbol,
        prob_up=result.prob_up,
        confidence=result.confidence,
        sub_probabilities=result.sub_probabilities,
        predictions_disabled=result.predictions_disabled,
        reason=result.reason,
        model_version=result.model_version,
    )


@router.get("/models")
def list_models() -> dict[str, Any]:
    """Diagnostic — which symbols have models loaded right now."""
    registry = ModelRegistry.get()
    return {
        "loaded_symbols": registry.known_symbols(),
        "models_dir": str(registry.models_dir),
    }
