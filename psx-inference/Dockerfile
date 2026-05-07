FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN pip install uv==0.5.4
COPY pyproject.toml ./
# Install only inference deps (no torch/scikit-learn training stack)
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python -e "." --no-dev

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --chown=appuser:appgroup psx_inference/ ./psx_inference/
# Model directory — populated by CI/CD from object storage on deploy
RUN mkdir -p models && chown appuser:appgroup models

USER appuser

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"

CMD ["uvicorn", "psx_inference.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
