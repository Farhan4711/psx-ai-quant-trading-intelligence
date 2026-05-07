from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from psx_api.config import settings

logger = structlog.get_logger(__name__)


def _configure_sentry() -> None:
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        integrations=[StarletteIntegration(), FastApiIntegration()],
        # Only sample 10% of transactions in production to keep costs down
        traces_sample_rate=0.1 if settings.is_production else 1.0,
        send_default_pii=False,
    )


def _configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            structlog.stdlib._NAME_TO_LEVEL.get(settings.log_level.upper(), 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("psx-api starting", environment=settings.environment)
    yield
    from psx_api.redis_client import close_redis
    await close_redis()
    logger.info("psx-api shutting down")


def create_app() -> FastAPI:
    _configure_sentry()
    _configure_logging()

    app = FastAPI(
        title="PSX AI Trading Intelligence API",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    from psx_api.routers import auth, health, securities, watchlist
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(securities.router)
    app.include_router(watchlist.router)

    return app


app = create_app()
