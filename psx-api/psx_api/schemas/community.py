from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Benchmark ──────────────────────────────────────────────────────────


class BenchmarkPanel(BaseModel):
    available: bool
    bucket_label: str | None = None
    sample_count: int = 0
    user_ytd_return_pct: float | None = None
    median_ytd_return_pct: float | None = None
    percentile_rank: int | None = None
    user_top_sector: str | None = None
    user_top_sector_pct: float | None = None
    peer_top_sector: str | None = None
    peer_top_sector_pct: float | None = None
    peer_top_holdings: list[dict[str, Any]] = []
    message: str | None = None


# ── Custom strategy ────────────────────────────────────────────────────


class StrategyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    rules: dict[str, Any]
    is_public: bool = False


class StrategyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    rules: dict[str, Any] | None = None
    is_public: bool | None = None


class StrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    name: str
    description: str | None
    rules: dict[str, Any]
    is_public: bool
    forked_from: str | None
    created_at: datetime
    updated_at: datetime


# ── Notifications ──────────────────────────────────────────────────────


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    title: str
    body: str
    link_path: str | None
    read_at: datetime | None
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int


# ── Purification ───────────────────────────────────────────────────────


class PurificationLineResponse(BaseModel):
    symbol: str
    dividends_pkr: Decimal
    purification_pct: Decimal
    purification_amount_pkr: Decimal
    marked_donated: bool = False


class PurificationReportResponse(BaseModel):
    fiscal_year: int
    total_dividends_pkr: Decimal
    total_purification_pkr: Decimal
    purification_pct: Decimal
    lines: list[PurificationLineResponse]


# ── Lessons ────────────────────────────────────────────────────────────


class LessonSummary(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    difficulty: int
    started: bool = False
    completed: bool = False
    quiz_score: int | None = None


class LessonDetail(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    difficulty: int
    body_md: str
    quiz: list[dict[str, Any]]
    progress: dict[str, Any] | None = None


class QuizAttempt(BaseModel):
    answers: list[int] = Field(..., min_length=1, max_length=20)


class QuizResult(BaseModel):
    score: int
    completed: bool
    correct_indices: list[int]
