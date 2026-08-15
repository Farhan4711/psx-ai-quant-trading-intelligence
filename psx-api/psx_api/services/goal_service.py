"""CRUD + analysis for goals."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.goals.allocation import recommend
from psx_api.goals.tvm import analyze
from psx_api.models.goals import Goal
from psx_api.models.users import User
from psx_api.schemas.goals import (
    AllocationResponse,
    GoalAnalysisResponse,
    GoalCreate,
    GoalUpdate,
)
from psx_api.timezone import today_pkt


class GoalError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class GoalService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_user(self, user_id: str) -> list[Goal]:
        result = await self._db.execute(
            select(Goal).where(Goal.user_id == user_id).order_by(Goal.target_date)
        )
        return list(result.scalars().all())

    async def get(self, user_id: str, goal_id: str) -> Goal:
        result = await self._db.execute(
            select(Goal).where(Goal.id == goal_id, Goal.user_id == user_id)
        )
        goal = result.scalar_one_or_none()
        if not goal:
            raise GoalError("Goal not found.", status_code=404)
        return goal

    async def create(self, user_id: str, body: GoalCreate) -> Goal:
        goal = Goal(
            user_id=user_id,
            name=body.name,
            goal_type=body.goal_type,
            target_amount_pkr=body.target_amount_pkr,
            target_date=body.target_date,
            current_amount_pkr=body.current_amount_pkr,
            monthly_contribution_pkr=body.monthly_contribution_pkr,
            linked_portfolio_id=body.linked_portfolio_id,
            notes=body.notes,
        )
        self._db.add(goal)
        await self._db.flush()
        await self._db.refresh(goal)
        return goal

    async def update(self, user_id: str, goal_id: str, body: GoalUpdate) -> Goal:
        goal = await self.get(user_id, goal_id)
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(goal, field, value)
        await self._db.flush()
        return goal

    async def delete(self, user_id: str, goal_id: str) -> None:
        goal = await self.get(user_id, goal_id)
        await self._db.delete(goal)
        await self._db.flush()

    # ------------------------------------------------------------------

    @staticmethod
    def analyse(goal: Goal, user: User) -> GoalAnalysisResponse:
        result = analyze(
            target_amount_pkr=goal.target_amount_pkr,
            current_amount_pkr=goal.current_amount_pkr,
            monthly_contribution_pkr=goal.monthly_contribution_pkr,
            target_date=goal.target_date,
            today=today_pkt(),
        )
        # Allocation falls back to balanced when archetype is missing
        archetype = user.risk_archetype or "balanced_builder"
        alloc = recommend(archetype=archetype, months_remaining=result.months_remaining)
        return GoalAnalysisResponse(
            months_remaining=result.months_remaining,
            years_remaining=result.years_remaining,
            required_cagr=result.required_cagr,
            rating=result.rating,
            summary=result.summary,
            suggested_monthly_contribution_pkr=result.suggested_monthly_contribution_pkr,
            suggested_extension_months=result.suggested_extension_months,
            allocation=AllocationResponse(
                archetype=alloc.archetype,
                horizon_bucket=alloc.horizon_bucket,
                months=alloc.months,
                equity_pct=alloc.equity_pct,
                tbills_pct=alloc.tbills_pct,
                cash_pct=alloc.cash_pct,
                rationale=alloc.rationale,
            ),
        )
