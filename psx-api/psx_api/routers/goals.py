"""Goal CRUD + on-the-fly TVM analysis (Phase 2 Steps 35–36)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.schemas.goals import (
    GoalAnalysisResponse,
    GoalCreate,
    GoalResponse,
    GoalUpdate,
    GoalWithAnalysis,
)
from psx_api.services.auth_service import AuthService
from psx_api.services.goal_service import GoalError, GoalService

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])

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


def _with_analysis(goal_dict: dict[str, Any], analysis: GoalAnalysisResponse) -> GoalWithAnalysis:
    return GoalWithAnalysis(**goal_dict, analysis=analysis)


@router.get("", response_model=list[GoalWithAnalysis])
async def list_goals(db: DbDep, current_user: CurrentUser) -> list[GoalWithAnalysis]:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = GoalService(db)
    goals = await service.list_for_user(user.id)
    out: list[GoalWithAnalysis] = []
    for g in goals:
        analysis = service.analyse(g, user)
        out.append(_with_analysis(GoalResponse.model_validate(g).model_dump(), analysis))
    return out


@router.post("", response_model=GoalWithAnalysis, status_code=status.HTTP_201_CREATED)
async def create_goal(body: GoalCreate, db: DbDep, current_user: CurrentUser) -> GoalWithAnalysis:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = GoalService(db)
    try:
        goal = await service.create(user.id, body)
    except GoalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    analysis = service.analyse(goal, user)
    return _with_analysis(GoalResponse.model_validate(goal).model_dump(), analysis)


@router.get("/{goal_id}", response_model=GoalWithAnalysis)
async def get_goal(goal_id: str, db: DbDep, current_user: CurrentUser) -> GoalWithAnalysis:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = GoalService(db)
    try:
        goal = await service.get(user.id, goal_id)
    except GoalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    analysis = service.analyse(goal, user)
    return _with_analysis(GoalResponse.model_validate(goal).model_dump(), analysis)


@router.patch("/{goal_id}", response_model=GoalWithAnalysis)
async def update_goal(
    goal_id: str, body: GoalUpdate, db: DbDep, current_user: CurrentUser
) -> GoalWithAnalysis:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = GoalService(db)
    try:
        goal = await service.update(user.id, goal_id, body)
    except GoalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    analysis = service.analyse(goal, user)
    return _with_analysis(GoalResponse.model_validate(goal).model_dump(), analysis)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_goal(goal_id: str, db: DbDep, current_user: CurrentUser) -> None:
    from psx_api.models.users import User

    user: User = current_user  # type: ignore[assignment]
    service = GoalService(db)
    try:
        await service.delete(user.id, goal_id)
    except GoalError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
