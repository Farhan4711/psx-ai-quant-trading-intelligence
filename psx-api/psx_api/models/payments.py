"""
Payment intents — per-checkout audit row.

One row per "I clicked Pay" attempt. Survives across retries so we can
reconcile what the gateway says happened against what we recorded.
See migration 0015 for column-level commentary.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("subscription_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    billing_cycle: Mapped[str] = mapped_column(String(10), nullable=False, server_default="monthly")
    amount_pkr: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pending")
    merchant_txn_ref: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    gateway_txn_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    request_payload: Mapped[Any] = mapped_column(JSONB, nullable=False, server_default="{}")
    response_payload: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
