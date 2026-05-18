"""
Runtime inference — loads the ONNX bundles produced by the Colab
notebook and serves per-symbol predictions on CPU.

Disk layout expected (matches the notebook output exactly):

    models/onnx/
        training_report.csv
        HBL/
            xgb.onnx
            rf.onnx
            lstm.onnx
            meta.onnx
            manifest.json
        UBL/
            …

When this module is imported the first time we eagerly walk
`models/onnx/` and build an in-memory map symbol → InferenceBundle.
The HTTP layer (`psx_inference/routers/predict.py`) just looks up the
bundle and calls `predict()`.

Why eager-load?
- onnxruntime sessions are ~10-50ms to build per model, and we have up
  to 4 per symbol × 84 symbols. Doing it on every request makes the
  endpoint feel sluggish. Doing it once at startup adds ~10s to boot
  but the request path is single-digit ms.

Memory footprint
- A trained PSX bundle is ~150 KB on disk and ~3 MB in memory.
- 84 symbols × 3 MB = ~250 MB. Fits comfortably in a 1 GB container.
"""

from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────────


_DEFAULT_MODELS_DIR = (
    Path(__file__).resolve().parents[2] / "models" / "onnx"
)
"""`psx-inference/models/onnx/` relative to this file."""

# Has to match the order in `psx_api.predictions.features.FEATURE_NAMES`.
# We don't import the psx-api module to keep the inference service
# fully decoupled — the manifest.json that ships alongside each
# bundle is the source of truth at inference time.


# ── Data classes ─────────────────────────────────────────────────


@dataclass
class InferenceBundle:
    """All ONNX sessions for one symbol, plus the manifest metadata."""

    symbol: str
    sub_keys: list[str]      # e.g. ["xgb", "rf", "lstm"]
    feature_names: list[str]
    lstm_window: int
    sub_sessions: dict[str, Any] = field(default_factory=dict)
    meta_session: Any | None = None


@dataclass(frozen=True, slots=True)
class PredictionResult:
    """One row returned to the API client."""

    symbol: str
    prob_up: float
    confidence: str          # "low" | "medium" | "high"
    sub_probabilities: dict[str, float]
    predictions_disabled: bool
    reason: str | None
    model_version: str


# ── Loader ───────────────────────────────────────────────────────


class ModelRegistry:
    """Thread-safe lazy-singleton wrapping all the loaded bundles."""

    _instance: "ModelRegistry | None" = None
    _lock = threading.Lock()

    def __init__(self, models_dir: Path) -> None:
        self.models_dir = models_dir
        self._bundles: dict[str, InferenceBundle] = {}
        self._loaded = False

    @classmethod
    def get(cls, models_dir: Path | None = None) -> "ModelRegistry":
        # Double-checked locking — fast path is lock-free.
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(models_dir or _DEFAULT_MODELS_DIR)
        return cls._instance

    def load(self) -> None:
        """Walk the directory, build sessions. Safe to call multiple
        times; subsequent calls are no-ops."""
        if self._loaded:
            return
        if not self.models_dir.exists():
            logger.warning(
                "inference.no_models_dir",
                extra={"path": str(self.models_dir)},
            )
            self._loaded = True
            return

        # Lazy-import onnxruntime — keeps test environments without it
        # from blowing up at module import time.
        import onnxruntime as ort  # noqa: PLC0415

        sym_count = 0
        for sym_dir in sorted(self.models_dir.iterdir()):
            if not sym_dir.is_dir():
                continue
            manifest_path = sym_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text())
            except Exception as exc:
                logger.warning(
                    "inference.bad_manifest",
                    extra={"symbol": sym_dir.name, "error": str(exc)},
                )
                continue

            bundle = InferenceBundle(
                symbol=manifest["symbol"],
                sub_keys=list(manifest["sub_keys"]),
                feature_names=list(manifest["feature_names"]),
                lstm_window=int(manifest.get("lstm_window", 30)),
            )
            ok = True
            for key in bundle.sub_keys:
                model_path = sym_dir / f"{key}.onnx"
                if not model_path.exists():
                    logger.warning(
                        "inference.missing_sub_model",
                        extra={"symbol": bundle.symbol, "key": key},
                    )
                    ok = False
                    break
                bundle.sub_sessions[key] = ort.InferenceSession(
                    str(model_path), providers=["CPUExecutionProvider"]
                )

            if not ok:
                continue

            meta_path = sym_dir / "meta.onnx"
            if meta_path.exists():
                bundle.meta_session = ort.InferenceSession(
                    str(meta_path), providers=["CPUExecutionProvider"]
                )

            self._bundles[bundle.symbol] = bundle
            sym_count += 1

        self._loaded = True
        logger.info(
            "inference.loaded",
            extra={"symbols": sym_count, "path": str(self.models_dir)},
        )

    def get_bundle(self, symbol: str) -> InferenceBundle | None:
        if not self._loaded:
            self.load()
        return self._bundles.get(symbol.upper())

    def known_symbols(self) -> list[str]:
        if not self._loaded:
            self.load()
        return sorted(self._bundles)


# ── Inference math ───────────────────────────────────────────────


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _confidence_from_subs(probs: list[float]) -> str:
    """High when sub-models agree, low when they disagree.

    Variance-based mapping — mirrors the heuristic ensemble's contract
    so the UI's existing "confidence" chip keeps working unchanged.
    """
    if not probs:
        return "low"
    if len(probs) == 1:
        return "medium"
    mean = sum(probs) / len(probs)
    variance = sum((p - mean) ** 2 for p in probs) / len(probs)
    # σ < 0.05 → tight agreement → high; σ > 0.15 → noisy → low
    if variance < 0.0025:
        return "high"
    if variance > 0.0225:
        return "low"
    return "medium"


def predict(
    bundle: InferenceBundle,
    features: list[float],
    window: list[list[float]] | None = None,
) -> PredictionResult:
    """
    Run one prediction.

    Args:
        bundle: loaded by `ModelRegistry.get_bundle(symbol)`.
        features: single feature vector in the order specified by
                  bundle.feature_names. Used by xgb / rf / meta.
        window:   30×N matrix in the same feature order, for the LSTM.
                  If missing and the bundle has an LSTM, we backfill
                  with zeros and downgrade confidence.
    """
    sub_probs: dict[str, float] = {}

    x_flat = np.array([features], dtype=np.float32)

    for key in bundle.sub_keys:
        sess = bundle.sub_sessions[key]
        inp_name = sess.get_inputs()[0].name
        if key == "lstm":
            if window is None or len(window) < bundle.lstm_window:
                # No window provided — skip LSTM rather than fake it.
                continue
            arr = np.array([window[-bundle.lstm_window :]], dtype=np.float32)
            out = sess.run(None, {inp_name: arr})
            # PyTorch LSTM exports a logit; sigmoid it.
            sub_probs[key] = float(_sigmoid(float(out[0].squeeze())))
        else:
            out = sess.run(None, {inp_name: x_flat})
            # skl2onnx / onnxmltools both emit [labels, probabilities]
            # where probabilities[i] = [P(class0), P(class1)] — we want class 1.
            try:
                sub_probs[key] = float(out[1][0][1])
            except (IndexError, TypeError):
                # Some models emit a single probability tensor.
                sub_probs[key] = float(np.array(out[0]).squeeze())

    if not sub_probs:
        return PredictionResult(
            symbol=bundle.symbol,
            prob_up=0.5,
            confidence="low",
            sub_probabilities={},
            predictions_disabled=True,
            reason="no sub-models available at runtime",
            model_version="real-v1",
        )

    # Meta-model expects sub-probabilities in the order bundle.sub_keys.
    if bundle.meta_session is not None:
        meta_in = bundle.meta_session.get_inputs()[0].name
        meta_arr = np.array(
            [[sub_probs.get(k, sub_probs[next(iter(sub_probs))]) for k in bundle.sub_keys]],
            dtype=np.float32,
        )
        meta_out = bundle.meta_session.run(None, {meta_in: meta_arr})
        try:
            prob_up = float(meta_out[1][0][1])
        except (IndexError, TypeError):
            prob_up = float(np.array(meta_out[0]).squeeze())
    else:
        # No meta model trained — fall back to simple average.
        prob_up = sum(sub_probs.values()) / len(sub_probs)

    return PredictionResult(
        symbol=bundle.symbol,
        prob_up=round(prob_up, 4),
        confidence=_confidence_from_subs(list(sub_probs.values())),
        sub_probabilities={k: round(v, 4) for k, v in sub_probs.items()},
        predictions_disabled=False,
        reason=None,
        model_version="real-v1",
    )
