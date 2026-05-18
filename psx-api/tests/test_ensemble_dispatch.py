"""
Tests for the inference-service dispatch in `psx_api.predictions.ensemble`.

We don't ship trained models in CI, so the bulk of the test surface
is *fallback behaviour*: the API must keep working when the inference
service is unconfigured / unreachable / slow / 404ing.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from psx_api.predictions import ensemble


_SAMPLE_FEATURES = {
    "log_return_1d": 0.01,
    "log_return_5d": 0.02,
    "log_return_10d": 0.04,
    "rsi_14": 55.0,
    "momentum_10": 0.03,
    "disparity_5": 0.01,
    "disparity_10": 0.02,
    "williams_r_14": -40.0,
    "macd_histogram": 0.1,
    "bollinger_pct_b": 0.55,
    "volume_z_20": 0.3,
    "kse100_return_pct": 0.5,
}


def _set_inference_url(monkeypatch: pytest.MonkeyPatch, url: str | None) -> None:
    monkeypatch.setattr(
        "psx_api.predictions.ensemble.settings.inference_service_url",
        url or "",
    )


# ── Fallback: no URL configured ───────────────────────────────────


def test_no_url_uses_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_inference_url(monkeypatch, None)
    result = ensemble.predict(_SAMPLE_FEATURES, symbol="HBL")
    assert result.model_version == ensemble.MODEL_VERSION
    assert 0.0 <= result.probability_up <= 1.0
    assert set(result.sub_model_probabilities) == {"lstm", "xgboost", "random_forest"}


def test_no_symbol_uses_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_inference_url(monkeypatch, "http://localhost:8001")
    result = ensemble.predict(_SAMPLE_FEATURES)
    # No symbol means we never even try the remote — heuristic guaranteed.
    assert result.model_version == ensemble.MODEL_VERSION


# ── Fallback: service unreachable / timeout ──────────────────────


def test_unreachable_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_inference_url(monkeypatch, "http://localhost:8001")

    def boom(*a: object, **kw: object) -> None:
        raise httpx.ConnectError("connection refused")

    with patch("psx_api.predictions.ensemble.httpx.post", side_effect=boom):
        result = ensemble.predict(_SAMPLE_FEATURES, symbol="HBL")
    assert result.model_version == ensemble.MODEL_VERSION


def test_404_falls_back_silently(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_inference_url(monkeypatch, "http://localhost:8001")
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 404
    fake_response.text = '{"detail": "no model for FOO"}'
    with patch("psx_api.predictions.ensemble.httpx.post", return_value=fake_response):
        result = ensemble.predict(_SAMPLE_FEATURES, symbol="FOO")
    assert result.model_version == ensemble.MODEL_VERSION


def test_5xx_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_inference_url(monkeypatch, "http://localhost:8001")
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 500
    fake_response.text = "internal error"
    with patch("psx_api.predictions.ensemble.httpx.post", return_value=fake_response):
        result = ensemble.predict(_SAMPLE_FEATURES, symbol="HBL")
    assert result.model_version == ensemble.MODEL_VERSION


# ── Success path: real models return a structured response ────────


def test_success_returns_real_version(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_inference_url(monkeypatch, "http://localhost:8001")
    fake_response = MagicMock(spec=httpx.Response)
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "symbol": "HBL",
        "prob_up": 0.62,
        "confidence": "high",
        "sub_probabilities": {"xgb": 0.61, "rf": 0.64, "lstm": 0.60},
        "predictions_disabled": False,
        "reason": None,
        "model_version": "real-v1",
    }
    with patch("psx_api.predictions.ensemble.httpx.post", return_value=fake_response):
        result = ensemble.predict(_SAMPLE_FEATURES, symbol="HBL")
    assert result.model_version == "real-v1"
    assert result.probability_up == 0.62
    assert result.confidence == "high"
    # Sub-prob keys come straight from the service (xgb/rf/lstm), not
    # the heuristic's lstm/xgboost/random_forest. UI handles either set.
    assert set(result.sub_model_probabilities) == {"xgb", "rf", "lstm"}


def test_predictions_disabled_surfaces() -> None:
    """When the trained model failed its quality gate, the service
    returns predictions_disabled=True and we propagate that without
    falling back to the heuristic (which would silently 'enable'
    a symbol the quality gate said to disable)."""
    with patch(
        "psx_api.predictions.ensemble.settings.inference_service_url",
        "http://localhost:8001",
    ):
        fake_response = MagicMock(spec=httpx.Response)
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "symbol": "WEAK",
            "prob_up": 0.5,
            "confidence": "low",
            "sub_probabilities": {},
            "predictions_disabled": True,
            "reason": "auc<0.53",
            "model_version": "real-v1",
        }
        with patch(
            "psx_api.predictions.ensemble.httpx.post",
            return_value=fake_response,
        ):
            result = ensemble.predict(_SAMPLE_FEATURES, symbol="WEAK")
    assert result.model_version == "real-v1"
    assert result.probability_up == 0.5
    assert result.confidence == "low"
