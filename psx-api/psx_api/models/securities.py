from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from psx_api.models.base import Base


class Security(Base):
    __tablename__ = "securities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_kmi_compliant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_kse100: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_kse30: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    market_cap_pkr: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    shares_outstanding: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    listed_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    delisted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Security {self.symbol} — {self.company_name}>"
