from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base

# Valid action types — kept here as constants so they're reused in validation
ACTION_TYPE_DIVIDEND_CASH = "dividend_cash"
ACTION_TYPE_DIVIDEND_STOCK = "dividend_stock"
ACTION_TYPE_BONUS = "bonus"
ACTION_TYPE_RIGHTS = "rights"
ACTION_TYPE_AGM = "agm"
ACTION_TYPE_SPLIT = "split"

VALID_ACTION_TYPES = frozenset(
    {
        ACTION_TYPE_DIVIDEND_CASH,
        ACTION_TYPE_DIVIDEND_STOCK,
        ACTION_TYPE_BONUS,
        ACTION_TYPE_RIGHTS,
        ACTION_TYPE_AGM,
        ACTION_TYPE_SPLIT,
    }
)


class CorporateAction(Base):
    __tablename__ = "corporate_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    announcement_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    ex_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Per-share amount (for cash dividends, rights price)
    amount_per_share: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # For bonus/rights: ratio_numerator shares for every ratio_denominator held
    ratio_numerator: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ratio_denominator: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_announcement: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<CorporateAction {self.symbol} {self.action_type} {self.announcement_date}>"
