"""Risk-profile questionnaire endpoints (Phase 2 Step 34)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.database import get_db
from psx_api.redis_client import get_redis
from psx_api.risk.profile import (
    ARCHETYPE_PROFILES,
    QUESTIONS,
    InvalidAnswers,
    evaluate,
)
from psx_api.schemas.risk import (
    Question as QuestionSchema,
    QuestionOption,
    QuestionnaireResponse,
    RiskProfileResult,
    SubmitAnswers,
)
from psx_api.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]  # type: ignore[type-arg]


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


@router.get("/questionnaire", response_model=QuestionnaireResponse)
async def get_questionnaire() -> QuestionnaireResponse:
    return QuestionnaireResponse(
        questions=[
            QuestionSchema(
                id=q.id,
                axis=q.axis,
                prompt=q.prompt,
                options=[QuestionOption(value=o.value, label=o.label) for o in q.options],
            )
            for q in QUESTIONS
        ]
    )


@router.get("/profile", response_model=RiskProfileResult | None)
async def get_profile(current_user: CurrentUser) -> RiskProfileResult | None:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]
    if user.risk_archetype is None:
        return None
    profile = ARCHETYPE_PROFILES[user.risk_archetype]
    return RiskProfileResult(
        archetype=user.risk_archetype,
        label=profile.label,
        description=profile.description,
        scores={
            "risk_tolerance": user.risk_tolerance_score or 0,
            "time_horizon": user.time_horizon_score or 0,
            "knowledge": user.knowledge_score or 0,
        },
        completed_at=user.risk_profile_completed_at,
    )


@router.post("/submit", response_model=RiskProfileResult)
async def submit_answers(
    body: SubmitAnswers, current_user: CurrentUser, db: DbDep
) -> RiskProfileResult:
    from psx_api.models.users import User
    user: User = current_user  # type: ignore[assignment]

    try:
        result = evaluate(body.answers)
    except InvalidAnswers as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )

    user.risk_archetype = result["archetype"]
    user.risk_tolerance_score = result["scores"]["risk_tolerance"]
    user.time_horizon_score = result["scores"]["time_horizon"]
    user.knowledge_score = result["scores"]["knowledge"]
    user.risk_profile_completed_at = datetime.now(timezone.utc)
    await db.flush()

    return RiskProfileResult(
        archetype=result["archetype"],
        label=result["label"],
        description=result["description"],
        scores=result["scores"],
        completed_at=user.risk_profile_completed_at,
    )
