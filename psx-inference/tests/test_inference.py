"""
Unit tests for psx_inference.inference — the real-model ONNX prediction
path. onnxruntime.InferenceSession is mocked throughout; we're testing
the wrapping logic (session selection, meta-model combination, LSTM
windowing, error handling), not onnxruntime itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from psx_inference.inference import (
    InferenceBundle,
    ModelRegistry,
    _confidence_from_subs,
    _sigmoid,
    predict,
)


@pytest.fixture(autouse=True)
def _reset_registry_singleton() -> Any:
    """ModelRegistry.get() caches a singleton on the class — reset it
    between tests so state doesn't leak."""
    ModelRegistry._instance = None
    yield
    ModelRegistry._instance = None


def _mock_session(output: list[Any]) -> MagicMock:
    """A stand-in for onnxruntime.InferenceSession: get_inputs()[0].name
    plus a run() that returns a fixed output."""
    sess = MagicMock()
    sess.get_inputs.return_value = [MagicMock(name="input")]
    sess.get_inputs.return_value[0].name = "input"
    sess.run.return_value = output
    return sess


def _bundle(sub_keys: list[str], *, with_meta: bool = False) -> InferenceBundle:
    b = InferenceBundle(
        symbol="ENGRO",
        sub_keys=sub_keys,
        feature_names=["rsi_14", "macd"],
        lstm_window=3,
    )
    for key in sub_keys:
        if key == "lstm":
            # LSTM exports a raw logit, shape (1, 1) so .squeeze() -> scalar
            b.sub_sessions[key] = _mock_session([np.array([[0.4]])])
        else:
            # skl2onnx style: [labels, probabilities[N][2]]
            b.sub_sessions[key] = _mock_session([["1"], [[0.3, 0.7]]])
    if with_meta:
        b.meta_session = _mock_session([["1"], [[0.2, 0.8]]])
    return b


# ── _sigmoid ─────────────────────────────────────────────────────


def test_sigmoid_zero_is_half() -> None:
    assert _sigmoid(0.0) == pytest.approx(0.5)


def test_sigmoid_large_positive_approaches_one() -> None:
    assert _sigmoid(10.0) == pytest.approx(1.0, abs=1e-3)


def test_sigmoid_large_negative_approaches_zero() -> None:
    assert _sigmoid(-10.0) == pytest.approx(0.0, abs=1e-3)


# ── _confidence_from_subs ────────────────────────────────────────


def test_confidence_empty_is_low() -> None:
    assert _confidence_from_subs([]) == "low"


def test_confidence_single_value_is_medium() -> None:
    assert _confidence_from_subs([0.7]) == "medium"


def test_confidence_tight_agreement_is_high() -> None:
    assert _confidence_from_subs([0.70, 0.71, 0.69]) == "high"


def test_confidence_wide_disagreement_is_low() -> None:
    assert _confidence_from_subs([0.1, 0.9]) == "low"


def test_confidence_moderate_disagreement_is_medium() -> None:
    assert _confidence_from_subs([0.5, 0.65]) == "medium"


# ── predict() ────────────────────────────────────────────────────


def test_predict_two_output_shape_picks_class_one_probability() -> None:
    bundle = _bundle(["xgb"])
    result = predict(bundle, features=[50.0, 0.1])
    assert result.sub_probabilities["xgb"] == pytest.approx(0.7)
    assert result.predictions_disabled is False
    assert result.model_version == "real-v1"


def test_predict_falls_back_to_single_tensor_output() -> None:
    bundle = _bundle([])
    bundle.sub_keys = ["xgb"]
    # A session whose output can't be indexed as [1][0][1] -> falls back
    # to float(np.array(out[0]).squeeze())
    sess = MagicMock()
    sess.get_inputs.return_value = [MagicMock()]
    sess.get_inputs.return_value[0].name = "input"
    sess.run.return_value = [0.65]
    bundle.sub_sessions["xgb"] = sess

    result = predict(bundle, features=[50.0, 0.1])
    assert result.sub_probabilities["xgb"] == pytest.approx(0.65)


def test_predict_lstm_skipped_without_window() -> None:
    bundle = _bundle(["lstm"])
    result = predict(bundle, features=[50.0, 0.1], window=None)
    assert "lstm" not in result.sub_probabilities
    # No other sub-models and lstm was skipped -> nothing produced
    assert result.predictions_disabled is True


def test_predict_lstm_skipped_when_window_shorter_than_required() -> None:
    bundle = _bundle(["lstm", "xgb"])
    short_window = [[1.0, 2.0]] * 2  # bundle.lstm_window is 3
    result = predict(bundle, features=[50.0, 0.1], window=short_window)
    assert "lstm" not in result.sub_probabilities
    assert "xgb" in result.sub_probabilities


def test_predict_lstm_included_with_sufficient_window() -> None:
    bundle = _bundle(["lstm", "xgb"])
    window = [[1.0, 2.0]] * 5  # >= lstm_window (3)
    result = predict(bundle, features=[50.0, 0.1], window=window)
    assert "lstm" in result.sub_probabilities
    # sigmoid(0.4) via the mocked raw logit output
    assert result.sub_probabilities["lstm"] == pytest.approx(round(_sigmoid(0.4), 4))


def test_predict_no_sub_models_returns_disabled() -> None:
    bundle = InferenceBundle(symbol="ENGRO", sub_keys=[], feature_names=["rsi_14"], lstm_window=3)
    result = predict(bundle, features=[50.0])
    assert result.predictions_disabled is True
    assert result.prob_up == 0.5
    assert result.confidence == "low"
    assert result.reason is not None


def test_predict_uses_meta_session_when_present() -> None:
    bundle = _bundle(["xgb", "rf"], with_meta=True)
    result = predict(bundle, features=[50.0, 0.1])
    # meta_session mock returns class-1 probability 0.8
    assert result.prob_up == pytest.approx(0.8)


def test_predict_meta_session_falls_back_to_single_tensor_output() -> None:
    bundle = _bundle(["xgb", "rf"])
    meta_sess = MagicMock()
    meta_sess.get_inputs.return_value = [MagicMock()]
    meta_sess.get_inputs.return_value[0].name = "input"
    meta_sess.run.return_value = [np.array(0.55)]  # can't be indexed as [1][0][1]
    bundle.meta_session = meta_sess

    result = predict(bundle, features=[50.0, 0.1])
    assert result.prob_up == pytest.approx(0.55)


def test_predict_averages_subs_when_no_meta_session() -> None:
    bundle = _bundle(["xgb", "rf"], with_meta=False)
    result = predict(bundle, features=[50.0, 0.1])
    # Both sub-sessions mocked to return 0.7 -> average is 0.7
    assert result.prob_up == pytest.approx(0.7)


def test_predict_rounds_probabilities() -> None:
    bundle = _bundle(["xgb"])
    result = predict(bundle, features=[50.0, 0.1])
    assert result.sub_probabilities["xgb"] == round(result.sub_probabilities["xgb"], 4)
    assert result.prob_up == round(result.prob_up, 4)


# ── ModelRegistry ────────────────────────────────────────────────


def test_get_returns_the_same_instance(tmp_path: Path) -> None:
    a = ModelRegistry.get(tmp_path)
    b = ModelRegistry.get(tmp_path)
    assert a is b


def test_load_on_missing_dir_marks_loaded_with_no_bundles(tmp_path: Path) -> None:
    registry = ModelRegistry(tmp_path / "does-not-exist")
    registry.load()
    assert registry._loaded is True
    assert registry.known_symbols() == []


def test_load_skips_non_directory_entries(tmp_path: Path) -> None:
    (tmp_path / "stray.txt").write_text("not a symbol dir")
    registry = ModelRegistry(tmp_path)
    registry.load()
    assert registry.known_symbols() == []


def test_load_skips_symbol_dir_without_manifest(tmp_path: Path) -> None:
    (tmp_path / "HBL").mkdir()
    registry = ModelRegistry(tmp_path)
    registry.load()
    assert registry.known_symbols() == []


def test_load_skips_symbol_dir_with_invalid_manifest_json(tmp_path: Path) -> None:
    sym_dir = tmp_path / "HBL"
    sym_dir.mkdir()
    (sym_dir / "manifest.json").write_text("{not valid json")
    registry = ModelRegistry(tmp_path)
    registry.load()
    assert registry.known_symbols() == []


def _write_manifest(sym_dir: Path, symbol: str, sub_keys: list[str]) -> None:
    sym_dir.mkdir()
    (sym_dir / "manifest.json").write_text(
        json.dumps(
            {
                "symbol": symbol,
                "sub_keys": sub_keys,
                "feature_names": ["rsi_14", "macd"],
                "lstm_window": 30,
            }
        )
    )


def test_load_skips_symbol_missing_a_sub_model_file(tmp_path: Path) -> None:
    sym_dir = tmp_path / "HBL"
    _write_manifest(sym_dir, "HBL", ["xgb", "rf"])
    (sym_dir / "xgb.onnx").write_bytes(b"")
    # rf.onnx deliberately missing
    registry = ModelRegistry(tmp_path)
    with patch("onnxruntime.InferenceSession", return_value=MagicMock()):
        registry.load()
    assert registry.known_symbols() == []


def test_load_builds_bundle_with_sub_sessions_and_meta(tmp_path: Path) -> None:
    sym_dir = tmp_path / "HBL"
    _write_manifest(sym_dir, "HBL", ["xgb", "rf"])
    (sym_dir / "xgb.onnx").write_bytes(b"")
    (sym_dir / "rf.onnx").write_bytes(b"")
    (sym_dir / "meta.onnx").write_bytes(b"")

    registry = ModelRegistry(tmp_path)
    with patch("onnxruntime.InferenceSession", return_value=MagicMock()) as mock_session:
        registry.load()

    assert registry.known_symbols() == ["HBL"]
    bundle = registry.get_bundle("hbl")  # case-insensitive lookup
    assert bundle is not None
    assert set(bundle.sub_sessions) == {"xgb", "rf"}
    assert bundle.meta_session is not None
    # xgb.onnx, rf.onnx, meta.onnx -> 3 sessions built
    assert mock_session.call_count == 3


def test_load_without_meta_onnx_leaves_meta_session_none(tmp_path: Path) -> None:
    sym_dir = tmp_path / "HBL"
    _write_manifest(sym_dir, "HBL", ["xgb"])
    (sym_dir / "xgb.onnx").write_bytes(b"")

    registry = ModelRegistry(tmp_path)
    with patch("onnxruntime.InferenceSession", return_value=MagicMock()):
        registry.load()

    bundle = registry.get_bundle("HBL")
    assert bundle is not None
    assert bundle.meta_session is None


def test_load_is_idempotent(tmp_path: Path) -> None:
    sym_dir = tmp_path / "HBL"
    _write_manifest(sym_dir, "HBL", ["xgb"])
    (sym_dir / "xgb.onnx").write_bytes(b"")

    registry = ModelRegistry(tmp_path)
    with patch("onnxruntime.InferenceSession", return_value=MagicMock()) as mock_session:
        registry.load()
        registry.load()  # second call should be a no-op

    assert mock_session.call_count == 1


def test_get_bundle_returns_none_for_unknown_symbol(tmp_path: Path) -> None:
    registry = ModelRegistry(tmp_path)
    assert registry.get_bundle("NOPE") is None


def test_known_symbols_triggers_lazy_load_when_not_loaded(tmp_path: Path) -> None:
    sym_dir = tmp_path / "HBL"
    _write_manifest(sym_dir, "HBL", ["xgb"])
    (sym_dir / "xgb.onnx").write_bytes(b"")

    registry = ModelRegistry(tmp_path)
    assert registry._loaded is False
    with patch("onnxruntime.InferenceSession", return_value=MagicMock()):
        symbols = registry.known_symbols()  # should trigger load() itself

    assert symbols == ["HBL"]
    assert registry._loaded is True


def test_known_symbols_is_sorted(tmp_path: Path) -> None:
    for sym in ("UBL", "HBL", "ENGRO"):
        _write_manifest(tmp_path / sym, sym, ["xgb"])
        (tmp_path / sym / "xgb.onnx").write_bytes(b"")

    registry = ModelRegistry(tmp_path)
    with patch("onnxruntime.InferenceSession", return_value=MagicMock()):
        registry.load()

    assert registry.known_symbols() == ["ENGRO", "HBL", "UBL"]
