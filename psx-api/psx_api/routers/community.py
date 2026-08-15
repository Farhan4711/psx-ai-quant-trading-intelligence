"""
Phase 4 community + lessons + benchmark + purification + notifications +
custom strategies endpoints. One file because each surface is small and
the auth dependency is the same.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.community import (
    BenchmarkPanel,
    LessonDetail,
    LessonSummary,
    NotificationResponse,
    PurificationReportResponse,
    QuizAttempt,
    QuizResult,
    StrategyCreate,
    StrategyResponse,
    StrategyUpdate,
    UnreadCount,
)
from psx_api.services.auth_service import AuthService
from psx_api.services.benchmark_service import BenchmarkService
from psx_api.services.custom_strategy_service import (
    CustomStrategyService,
    StrategyError,
)
from psx_api.services.lesson_service import LessonService
from psx_api.services.notification_service import NotificationService
from psx_api.services.purification_service import PurificationService
from psx_api.timezone import today_pkt

router = APIRouter(prefix="/api/v1", tags=["community"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


async def _current_user(
    db: DbDep,
    redis: RedisDep,
    psx_session: Annotated[str | None, Cookie()] = None,
) -> object:
    if not psx_session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    auth = AuthService(db, redis)
    user = await auth.get_session_user(psx_session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")
    return user


CurrentUser = Annotated[object, Depends(_current_user)]


# ── Benchmark (Step 61) ────────────────────────────────────────────────


@router.get("/benchmark/me", response_model=BenchmarkPanel)
async def my_benchmark(db: DbDep, current_user: CurrentUser) -> BenchmarkPanel:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = BenchmarkService(db)
    data = await service.panel(user)
    return BenchmarkPanel(**data)


# ── Custom strategies (Steps 62-63) ────────────────────────────────────


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_my_strategies(db: DbDep, current_user: CurrentUser) -> list[StrategyResponse]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = CustomStrategyService(db)
    items = await service.list_for_user(user.id)
    return [StrategyResponse.model_validate(s) for s in items]


@router.get("/strategies/public", response_model=list[StrategyResponse])
async def list_public_strategies(db: DbDep) -> list[StrategyResponse]:
    service = CustomStrategyService(db)
    items = await service.list_public()
    return [StrategyResponse.model_validate(s) for s in items]


@router.post(
    "/strategies",
    response_model=StrategyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_strategy(
    body: StrategyCreate, db: DbDep, current_user: CurrentUser
) -> StrategyResponse:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = CustomStrategyService(db)
    try:
        s = await service.create(user.id, body)
    except StrategyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return StrategyResponse.model_validate(s)


@router.patch("/strategies/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: str,
    body: StrategyUpdate,
    db: DbDep,
    current_user: CurrentUser,
) -> StrategyResponse:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = CustomStrategyService(db)
    try:
        s = await service.update(user.id, strategy_id, body)
    except StrategyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return StrategyResponse.model_validate(s)


@router.delete(
    "/strategies/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_strategy(strategy_id: str, db: DbDep, current_user: CurrentUser) -> None:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = CustomStrategyService(db)
    try:
        await service.delete(user.id, strategy_id)
    except StrategyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post(
    "/strategies/{strategy_id}/fork",
    response_model=StrategyResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fork_strategy(strategy_id: str, db: DbDep, current_user: CurrentUser) -> StrategyResponse:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = CustomStrategyService(db)
    try:
        s = await service.fork(user.id, strategy_id)
    except StrategyError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return StrategyResponse.model_validate(s)


# ── Notifications (Step 64) ─────────────────────────────────────────────


@router.get("/notifications", response_model=list[NotificationResponse])
async def list_notifications(
    db: DbDep, current_user: CurrentUser, limit: int = 50
) -> list[NotificationResponse]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = NotificationService(db)
    items = await service.list_for_user(user.id, limit=limit)
    return [NotificationResponse.model_validate(n) for n in items]


@router.get("/notifications/unread", response_model=UnreadCount)
async def unread_count(db: DbDep, current_user: CurrentUser) -> UnreadCount:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = NotificationService(db)
    return UnreadCount(unread=await service.unread_count(user.id))


@router.post(
    "/notifications/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def mark_read(notification_id: str, db: DbDep, current_user: CurrentUser) -> None:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = NotificationService(db)
    await service.mark_read(user.id, notification_id)


@router.post("/notifications/mark-all-read")
async def mark_all_read(db: DbDep, current_user: CurrentUser) -> dict[str, Any]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = NotificationService(db)
    n = await service.mark_all_read(user.id)
    return {"marked": n}


# ── Purification (Step 65) ──────────────────────────────────────────────


@router.get("/purification/report", response_model=PurificationReportResponse)
async def purification_report(
    db: DbDep,
    current_user: CurrentUser,
    fiscal_year: int | None = None,
) -> PurificationReportResponse:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = PurificationService(db)
    data = await service.report(user.id, fiscal_year=fiscal_year or today_pkt().year)
    return PurificationReportResponse(**data)


@router.post(
    "/purification/{fiscal_year}/{symbol}/mark-donated",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def mark_donated(
    fiscal_year: int,
    symbol: str,
    db: DbDep,
    current_user: CurrentUser,
    donated: bool = True,
) -> None:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = PurificationService(db)
    await service.mark_donated(user.id, fiscal_year, symbol.upper(), donated=donated)


# ── Lessons (Step 66) ───────────────────────────────────────────────────


@router.post("/lessons/seed")
async def seed_lessons(db: DbDep) -> dict[str, Any]:
    """One-shot seeder — idempotent. Mostly for the dev environment."""
    service = LessonService(db)
    inserted = await service.seed_curriculum()
    return {"inserted": inserted}


@router.get("/lessons", response_model=list[LessonSummary])
async def list_lessons(db: DbDep, current_user: CurrentUser) -> list[LessonSummary]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = LessonService(db)
    rows = await service.list_with_progress(user.id)
    return [LessonSummary(**r) for r in rows]


@router.get("/lessons/{slug}", response_model=LessonDetail)
async def get_lesson(slug: str, db: DbDep, current_user: CurrentUser) -> LessonDetail:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = LessonService(db)
    data = await service.get_with_progress(user.id, slug)
    if not data:
        raise HTTPException(status_code=404, detail="Lesson not found.")
    return LessonDetail(**data)


@router.post("/lessons/{slug}/quiz", response_model=QuizResult)
async def submit_quiz(
    slug: str,
    body: QuizAttempt,
    db: DbDep,
    current_user: CurrentUser,
) -> QuizResult:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = LessonService(db)
    result = await service.submit_quiz(user.id, slug, body.answers)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return QuizResult(**result)


# ── Settings (Step 59 opt-in) ───────────────────────────────────────────
# We extend /auth/me PATCH instead of adding a new route — the frontend
# already updates user fields through there. Just exposes share_anonymously
# and date_of_birth via the existing schema; see schemas/auth.py update.
