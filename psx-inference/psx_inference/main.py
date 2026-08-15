from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from psx_inference.config import settings

logger = structlog.get_logger(__name__)


def _configure_sentry() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        traces_sample_rate=0.05,
        send_default_pii=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("psx-inference starting", environment=settings.environment)
    # Phase 12: pre-load every per-symbol ONNX bundle so the first
    # /predict call doesn't pay the cold-start cost. ModelRegistry is a
    # singleton so this also primes the same instance the routers use.
    from psx_inference.inference import ModelRegistry

    ModelRegistry.get().load()
    yield
    logger.info("psx-inference shutting down")


def create_app() -> FastAPI:
    _configure_sentry()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
    )

    app = FastAPI(
        title="PSX Inference Service",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    from psx_inference.routers import health, predict

    app.include_router(health.router)
    app.include_router(predict.router)

    return app


app = create_app()
