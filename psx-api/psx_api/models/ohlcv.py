from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class OhlcvDaily(Base):
    """
    Daily OHLCV (Open/High/Low/Close/Volume) price data.
    Stored as a TimescaleDB hypertable partitioned by date.
    Primary key is composite (symbol, date) — no surrogate id.
    Both raw and adjusted prices are stored to support accurate backtesting.
    """

    __tablename__ = "ohlcv_daily"

    symbol: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("securities.symbol", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True, nullable=False)

    # Raw prices (as reported by exchange)
    open: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    value_pkr: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)

    # Split-and-dividend-adjusted close (computed by psx-ingest adjusted_prices task)
    # Never compute returns from raw close when corporate actions exist — use this.
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)

    def __repr__(self) -> str:
        return f"<OhlcvDaily {self.symbol} {self.date} close={self.close}>"
