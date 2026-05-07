from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.ohlcv import OhlcvDaily
from psx_api.models.securities import Security
from psx_api.schemas.securities import (
    OhlcvListResponse,
    OhlcvResponse,
    SecuritiesListResponse,
    SecurityCreate,
    SecurityResponse,
)


class SecuritiesService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_securities(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        sector: str | None = None,
        kmi_only: bool = False,
        kse100_only: bool = False,
        search: str | None = None,
        active_only: bool = True,
    ) -> SecuritiesListResponse:
        query = select(Security)

        if active_only:
            query = query.where(Security.is_active.is_(True))
        if sector:
            query = query.where(Security.sector == sector)
        if kmi_only:
            query = query.where(Security.is_kmi_compliant.is_(True))
        if kse100_only:
            query = query.where(Security.is_kse100.is_(True))
        if search:
            pattern = f"%{search.upper()}%"
            query = query.where(
                Security.symbol.like(pattern) | Security.company_name.ilike(f"%{search}%")
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self._db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        query = query.order_by(Security.symbol).offset(offset).limit(page_size)
        result = await self._db.execute(query)
        items = result.scalars().all()

        return SecuritiesListResponse(
            items=[SecurityResponse.model_validate(s) for s in items],
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + len(items)) < total,
        )

    async def get_security(self, symbol: str) -> SecurityResponse | None:
        result = await self._db.execute(
            select(Security).where(Security.symbol == symbol.upper())
        )
        security = result.scalar_one_or_none()
        return SecurityResponse.model_validate(security) if security else None

    async def upsert_security(self, data: SecurityCreate) -> SecurityResponse:
        result = await self._db.execute(
            select(Security).where(Security.symbol == data.symbol)
        )
        existing = result.scalar_one_or_none()

        if existing:
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(existing, field, value)
            security = existing
        else:
            security = Security(**data.model_dump())
            self._db.add(security)

        await self._db.flush()
        await self._db.refresh(security)
        return SecurityResponse.model_validate(security)

    async def get_ohlcv(
        self,
        symbol: str,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 252,
        adjusted: bool = True,
    ) -> OhlcvListResponse:
        query = select(OhlcvDaily).where(OhlcvDaily.symbol == symbol.upper())

        if date_from:
            query = query.where(OhlcvDaily.date >= date_from)
        if date_to:
            query = query.where(OhlcvDaily.date <= date_to)

        query = query.order_by(OhlcvDaily.date.desc()).limit(limit)
        result = await self._db.execute(query)
        rows = result.scalars().all()

        return OhlcvListResponse(
            symbol=symbol.upper(),
            interval="daily",
            items=[OhlcvResponse.model_validate(r) for r in rows],
            total=len(rows),
        )

    async def list_sectors(self) -> list[str]:
        result = await self._db.execute(
            select(Security.sector)
            .where(Security.is_active.is_(True))
            .distinct()
            .order_by(Security.sector)
        )
        return list(result.scalars().all())
