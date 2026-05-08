from datetime import datetime

from pydantic import BaseModel, Field


class QuestionOption(BaseModel):
    value: str
    label: str


class Question(BaseModel):
    id: str
    axis: str
    prompt: str
    options: list[QuestionOption]


class QuestionnaireResponse(BaseModel):
    questions: list[Question]


class SubmitAnswers(BaseModel):
    # question_id → option.value
    answers: dict[str, str] = Field(..., min_length=1)


class RiskProfileResult(BaseModel):
    archetype: str
    label: str
    description: str
    scores: dict[str, int]
    completed_at: datetime | None = None
