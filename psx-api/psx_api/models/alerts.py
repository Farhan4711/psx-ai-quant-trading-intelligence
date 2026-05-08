from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class SuspiciousDay(Base):
    """One row per (symbol, alert_date) the pump/dump pipeline flagged."""

    __tablename__ = "suspicious_days"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alert_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    vol_spike: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_change_pct: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    anomaly_score: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    has_news_context: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("symbol", "alert_date", name="uq_suspicious_days_symbol_date"),
    )
