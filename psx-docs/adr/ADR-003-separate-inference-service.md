# ADR-003: Why the Inference Service is a Separate Microservice

**Date:** 2026-05-07
**Status:** Accepted

---

## Context

The ML prediction pipeline needs to serve predictions from trained LSTM, XGBoost, and ensemble models. The question is whether this lives inside `psx-api` or as a separate service.

## Decision

The inference service (`psx-inference`) is a **separate FastAPI microservice** called by `psx-api` over HTTP (or a message queue in a later phase).

## Rationale

**Deployment independence:**
Model retraining and redeployment takes 2–10 seconds of load time (loading ONNX files into memory, warming up the runtime). If inference lives inside `psx-api`, every model update causes a brief API outage or requires a careful rolling restart. With a separate service, `psx-api` stays up while `psx-inference` restarts.

**Dependency isolation:**
`psx-api` needs zero ML dependencies at runtime — no PyTorch, no scikit-learn, no heavy `numpy` loading on startup. `psx-inference` can carry the full ML stack without making `psx-api`'s Docker image 3× larger.

**Independent scaling:**
During market hours, prediction requests spike. `psx-inference` can be scaled horizontally on GPU instances without scaling the database-connected `psx-api`.

**GPU isolation:**
The inference container can run on a GPU instance (Hetzner GPU cloud) while `psx-api` runs on a standard CPU instance — important for cost efficiency.

## Consequences

- `psx-api` calls `psx-inference` via an internal HTTP endpoint (not exposed publicly)
- `psx-inference` has no direct database access — `psx-api` fetches features from the DB and passes them in the request, OR `psx-inference` reads from a Redis feature cache populated by the ingest workers
- The inference service URL is configured in `psx-api` via environment variable: `INFERENCE_SERVICE_URL`
- A circuit breaker in `psx-api` handles the case where `psx-inference` is down — it returns a graceful "predictions temporarily unavailable" response rather than a 500
- In Phase 0–1, the inference service can be a stub (Phase 2 activates it fully); `psx-api` can be developed without it running
