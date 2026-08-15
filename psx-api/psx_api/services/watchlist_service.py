from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.securities import Security
from psx_api.models.watchlist import WatchlistItem
from psx_api.schemas.securities import WatchlistItemResponse


class WatchlistError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class WatchlistService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_watchlist(self, user_id: str) -> list[WatchlistItemResponse]:
        result = await self._db.execute(
            select(WatchlistItem, Security)
            .join(Security, WatchlistItem.symbol == Security.symbol)
            .where(WatchlistItem.user_id == user_id)
            .order_by(WatchlistItem.sort_order, WatchlistItem.added_at)
        )
        rows = result.all()
        return [
            WatchlistItemResponse(
                symbol=item.symbol,
                company_name=sec.company_name,
                sector=sec.sector,
                is_kmi_compliant=sec.is_kmi_compliant,
                note=item.note,
                sort_order=item.sort_order,
                added_at=item.added_at,
            )
            for item, sec in rows
        ]

    async def add(
        self, user_id: str, symbol: str, note: str | None = None
    ) -> WatchlistItemResponse:
        sym = symbol.upper()

        # Verify security exists
        sec_result = await self._db.execute(select(Security).where(Security.symbol == sym))
        security = sec_result.scalar_one_or_none()
        if not security:
            raise WatchlistError(f"Security '{sym}' not found.", status_code=404)

        # Get current max sort_order for this user
        from sqlalchemy import func

        max_order_result = await self._db.execute(
            select(func.max(WatchlistItem.sort_order)).where(WatchlistItem.user_id == user_id)
        )
        max_order = max_order_result.scalar_one() or 0

        item = WatchlistItem(user_id=user_id, symbol=sym, note=note, sort_order=max_order + 1)
        self._db.add(item)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            raise WatchlistError(
                f"'{sym}' is already in your watchlist.", status_code=409
            ) from None

        await self._db.refresh(item)
        return WatchlistItemResponse(
            symbol=item.symbol,
            company_name=security.company_name,
            sector=security.sector,
            is_kmi_compliant=security.is_kmi_compliant,
            note=item.note,
            sort_order=item.sort_order,
            added_at=item.added_at,
        )

    async def remove(self, user_id: str, symbol: str) -> None:
        sym = symbol.upper()
        result = await self._db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.symbol == sym,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise WatchlistError(f"'{sym}' is not in your watchlist.", status_code=404)
        await self._db.delete(item)
        await self._db.flush()

    async def reorder(self, user_id: str, symbols: list[str]) -> list[WatchlistItemResponse]:
        normalised = [s.upper().strip() for s in symbols if s.strip()]
        result = await self._db.execute(
            select(WatchlistItem).where(WatchlistItem.user_id == user_id)
        )
        items = list(result.scalars().all())
        by_symbol = {i.symbol: i for i in items}

        # Validate every requested symbol belongs to the user
        unknown = [s for s in normalised if s not in by_symbol]
        if unknown:
            raise WatchlistError(
                f"Symbols not in watchlist: {', '.join(unknown)}",
                status_code=400,
            )

        for index, sym in enumerate(normalised, start=1):
            by_symbol[sym].sort_order = index

        # Anything not in the request keeps its existing relative order, pushed to the end
        next_order = len(normalised) + 1
        for item in sorted(items, key=lambda i: i.sort_order):
            if item.symbol not in normalised:
                item.sort_order = next_order
                next_order += 1

        await self._db.flush()
        return await self.get_watchlist(user_id)

    async def is_watching(self, user_id: str, symbol: str) -> bool:
        result = await self._db.execute(
            select(WatchlistItem).where(
                WatchlistItem.user_id == user_id,
                WatchlistItem.symbol == symbol.upper(),
            )
        )
        return result.scalar_one_or_none() is not None
