"""
HTTP-level tests for POST /predict and GET /models.
ModelRegistry is monkeypatched so these don't need real ONNX files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest
from httpx import AsyncClient

from psx_inference.inference import InferenceBundle, ModelRegistry


@pytest.fixture(autouse=True)
def _reset_registry_singleton() -> Any:
    ModelRegistry._instance = None
    yield
    ModelRegistry._instance = None


def _fake_bundle() -> InferenceBundle:
    bundle = InferenceBundle(
        symbol="HBL",
        sub_keys=["xgb"],
        feature_names=["rsi_14", "macd"],
        lstm_window=3,
    )
    sess = MagicMock()
    sess.get_inputs.return_value = [MagicMock()]
    sess.get_inputs.return_value[0].name = "input"
    sess.run.return_value = [["1"], [[0.35, 0.65]]]
    bundle.sub_sessions["xgb"] = sess
    return bundle


@pytest.mark.asyncio
async def test_predict_returns_404_for_unknown_symbol(client: AsyncClient) -> None:
    registry = ModelRegistry(models_dir=Path("/nonexistent"))
    registry._loaded = True
    ModelRegistry._instance = registry

    response = await client.post("/predict", json={"symbol": "NOPE", "features": {"rsi_14": 55.0}})
    assert response.status_code == 404
    assert "NOPE" in response.json()["detail"]


@pytest.mark.asyncio
async def test_predict_returns_prediction_for_known_symbol(client: AsyncClient) -> None:
    registry = ModelRegistry(models_dir=Path("/nonexistent"))
    registry._loaded = True
    registry._bundles["HBL"] = _fake_bundle()
    ModelRegistry._instance = registry

    response = await client.post(
        "/predict",
        json={"symbol": "hbl", "features": {"rsi_14": 55.0, "macd": 0.2}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "HBL"
    assert data["predictions_disabled"] is False
    assert data["sub_probabilities"]["xgb"] == pytest.approx(0.65)
    assert data["model_version"] == "real-v1"


@pytest.mark.asyncio
async def test_predict_defaults_missing_features_to_zero(client: AsyncClient) -> None:
    """features dict may omit keys the manifest expects — they default to 0.0."""
    registry = ModelRegistry(models_dir=Path("/nonexistent"))
    registry._loaded = True
    registry._bundles["HBL"] = _fake_bundle()
    ModelRegistry._instance = registry

    response = await client.post("/predict", json={"symbol": "HBL", "features": {"rsi_14": 55.0}})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_predict_builds_window_matrix_for_lstm(client: AsyncClient) -> None:
    registry = ModelRegistry(models_dir=Path("/nonexistent"))
    registry._loaded = True
    bundle = _fake_bundle()
    bundle.sub_keys = ["xgb", "lstm"]
    lstm_sess = MagicMock()
    lstm_sess.get_inputs.return_value = [MagicMock()]
    lstm_sess.get_inputs.return_value[0].name = "input"
    lstm_sess.run.return_value = [np.array([[0.1]])]
    bundle.sub_sessions["lstm"] = lstm_sess
    registry._bundles["HBL"] = bundle
    ModelRegistry._instance = registry

    response = await client.post(
        "/predict",
        json={
            "symbol": "HBL",
            "features": {"rsi_14": 55.0, "macd": 0.2},
            "window": [{"rsi_14": 50.0, "macd": 0.1}] * 5,
        },
    )
    assert response.status_code == 200
    assert "lstm" in response.json()["sub_probabilities"]


@pytest.mark.asyncio
async def test_models_lists_loaded_symbols(client: AsyncClient) -> None:
    registry = ModelRegistry(models_dir=Path("/nonexistent"))
    registry._loaded = True
    registry._bundles["HBL"] = _fake_bundle()
    registry._bundles["ENGRO"] = _fake_bundle()
    ModelRegistry._instance = registry

    response = await client.get("/models")
    assert response.status_code == 200
    data = response.json()
    assert data["loaded_symbols"] == ["ENGRO", "HBL"]


@pytest.mark.asyncio
async def test_models_empty_when_nothing_loaded(client: AsyncClient) -> None:
    registry = ModelRegistry(models_dir=Path("/nonexistent"))
    registry._loaded = True
    ModelRegistry._instance = registry

    response = await client.get("/models")
    assert response.status_code == 200
    assert response.json()["loaded_symbols"] == []
