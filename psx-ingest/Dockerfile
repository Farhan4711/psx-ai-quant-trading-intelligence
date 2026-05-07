FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
RUN pip install uv==0.5.4
COPY pyproject.toml ./
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
COPY --chown=appuser:appgroup psx_ingest/ ./psx_ingest/

USER appuser

# Default: run the Celery worker. Override CMD in docker-compose for beat scheduler.
CMD ["celery", "-A", "psx_ingest.worker", "worker", "--loglevel=info", "--concurrency=2"]
