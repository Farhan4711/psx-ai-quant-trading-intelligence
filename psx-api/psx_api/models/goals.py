from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    goal_type: Mapped[str] = mapped_column(String(30), nullable=False)
    target_amount_pkr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_amount_pkr: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, server_default="0"
    )
    monthly_contribution_pkr: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, server_default="0"
    )
    linked_portfolio_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Goal {self.name} target={self.target_amount_pkr} by {self.target_date}>"
