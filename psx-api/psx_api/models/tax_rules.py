from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, Index, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class TaxRule(Base):
    """
    Capital Gains Tax bracket lookup table.

    Each row defines: for sells in [effective_from, effective_to] by filer/non-filer
    where the position was held [min_holding_days, max_holding_days] (max_holding_days
    NULL means unbounded), the CGT rate is `rate_pct` percent of realized gain.

    This table is the single source of truth for CGT rates — tax rates change
    every Federal Budget so we never hardcode them. Seeded with current SECP
    rules in the migration; admins update rows when the budget changes.
    """

    __tablename__ = "tax_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="cgt")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_filer: Mapped[bool] = mapped_column(Boolean, nullable=False)
    min_holding_days: Mapped[int] = mapped_column(nullable=False, server_default="0")
    max_holding_days: Mapped[int | None] = mapped_column(nullable=True)
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("rate_pct >= 0 AND rate_pct <= 100", name="ck_tax_rules_rate_range"),
        CheckConstraint("min_holding_days >= 0", name="ck_tax_rules_min_days"),
        CheckConstraint(
            "max_holding_days IS NULL OR max_holding_days >= min_holding_days",
            name="ck_tax_rules_holding_range",
        ),
        Index("ix_tax_rules_lookup", "rule_type", "effective_from", "is_filer"),
    )

    def __repr__(self) -> str:
        return (
            f"<TaxRule {self.effective_from}→{self.effective_to or '∞'} "
            f"filer={self.is_filer} {self.min_holding_days}–{self.max_holding_days} "
            f"rate={self.rate_pct}%>"
        )
