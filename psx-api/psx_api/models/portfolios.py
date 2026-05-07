from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class TransactionType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    BONUS = "bonus"
    RIGHTS = "rights"


class Portfolio(Base):
    __tablename__ = "portfolios"

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
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="PKR")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_portfolios_user_name"),
    )

    def __repr__(self) -> str:
        return f"<Portfolio {self.user_id} {self.name}>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    portfolio_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Quantity is signed in the ledger (negative for sells); broker reports treat sells as positive.
    # We store the absolute quantity and rely on transaction_type to determine direction.
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price_per_share: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    brokerage_pkr: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default="0"
    )
    fed_pkr: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default="0"
    )
    cvt_pkr: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default="0"
    )
    cgt_pkr: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, server_default="0"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())

    def __repr__(self) -> str:
        return f"<Transaction {self.transaction_type} {self.symbol} qty={self.quantity}>"


class HoldingsSnapshot(Base):
    """Denormalised position rollup. Refreshed on every transaction commit."""

    __tablename__ = "holdings_snapshot"

    portfolio_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="RESTRICT"),
        primary_key=True,
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    avg_cost_pkr: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    total_invested_pkr: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    realized_pnl_pkr: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, server_default="0"
    )
    total_dividends_received_pkr: Mapped[Decimal] = mapped_column(
        Numeric(20, 2), nullable=False, server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<HoldingsSnapshot {self.portfolio_id} {self.symbol} qty={self.quantity}>"
