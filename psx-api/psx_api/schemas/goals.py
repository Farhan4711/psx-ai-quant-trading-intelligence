from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


GoalTypeLiteral = Literal[
    "retirement",
    "hajj",
    "education",
    "home",
    "marriage",
    "emergency_fund",
    "custom",
]

RatingLiteral = Literal["feasible", "stretch", "aggressive", "unrealistic", "already_funded"]


class GoalBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    goal_type: GoalTypeLiteral
    target_amount_pkr: Decimal = Field(..., gt=0, decimal_places=2)
    target_date: date
    current_amount_pkr: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    monthly_contribution_pkr: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)
    linked_portfolio_id: str | None = None
    notes: str | None = None


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    target_amount_pkr: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    target_date: date | None = None
    current_amount_pkr: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    monthly_contribution_pkr: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    linked_portfolio_id: str | None = None
    notes: str | None = None


class GoalResponse(GoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class AllocationResponse(BaseModel):
    archetype: str
    horizon_bucket: str
    months: int
    equity_pct: int
    tbills_pct: int
    cash_pct: int
    rationale: str


class GoalAnalysisResponse(BaseModel):
    months_remaining: int
    years_remaining: float
    required_cagr: Decimal | None
    rating: RatingLiteral
    summary: str
    suggested_monthly_contribution_pkr: Decimal | None
    suggested_extension_months: int | None
    allocation: AllocationResponse


class GoalWithAnalysis(GoalResponse):
    analysis: GoalAnalysisResponse
