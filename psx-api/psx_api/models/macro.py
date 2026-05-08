from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class MacroIndicator(Base):
    """
    Daily macro series for chart overlays + the prediction feature pipeline.
    Composite PK on (date, indicator); whitelisted indicator names enforced
    via CHECK constraint at the DB level.
    """

    __tablename__ = "macro_indicators"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    indicator: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6), nullable=False)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Macro {self.indicator} {self.date}={self.value}>"
