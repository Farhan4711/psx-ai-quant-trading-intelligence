"""CRUD service for portfolios."""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.portfolios import Portfolio
from psx_api.schemas.portfolios import PortfolioCreate, PortfolioUpdate


class PortfolioError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class PortfolioService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_user(self, user_id: str) -> list[Portfolio]:
        result = await self._db.execute(
            select(Portfolio)
            .where(Portfolio.user_id == user_id)
            .order_by(Portfolio.is_default.desc(), Portfolio.created_at)
        )
        return list(result.scalars().all())

    async def get(self, user_id: str, portfolio_id: str) -> Portfolio:
        result = await self._db.execute(
            select(Portfolio).where(
                Portfolio.id == portfolio_id, Portfolio.user_id == user_id
            )
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            raise PortfolioError("Portfolio not found.", status_code=404)
        return portfolio

    async def get_or_create_default(self, user_id: str) -> Portfolio:
        """Returns the user's default portfolio, creating one named 'Main' if none exists."""
        result = await self._db.execute(
            select(Portfolio).where(
                Portfolio.user_id == user_id, Portfolio.is_default.is_(True)
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        portfolio = Portfolio(
            user_id=user_id,
            name="Main",
            description="Default portfolio",
            base_currency="PKR",
            is_default=True,
        )
        self._db.add(portfolio)
        await self._db.flush()
        await self._db.refresh(portfolio)
        return portfolio

    async def create(self, user_id: str, body: PortfolioCreate) -> Portfolio:
        # If this portfolio is being set as default, unset any existing
        # default FIRST. Explicit flush() ensures the bulk UPDATE hits the
        # database before the new row's INSERT — otherwise the partial
        # unique index `uq_portfolios_user_default` could see two TRUE
        # rows in the flush batch and fail the IntegrityError check.
        if body.is_default:
            await self._db.execute(
                update(Portfolio)
                .where(Portfolio.user_id == user_id, Portfolio.is_default.is_(True))
                .values(is_default=False)
            )
            await self._db.flush()

        portfolio = Portfolio(
            user_id=user_id,
            name=body.name,
            description=body.description,
            base_currency=body.base_currency,
            is_default=body.is_default,
        )
        self._db.add(portfolio)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            raise PortfolioError(
                f"You already have a portfolio named '{body.name}'.",
                status_code=409,
            )
        await self._db.refresh(portfolio)
        return portfolio

    async def update(
        self, user_id: str, portfolio_id: str, body: PortfolioUpdate
    ) -> Portfolio:
        portfolio = await self.get(user_id, portfolio_id)

        if body.is_default is True and not portfolio.is_default:
            await self._db.execute(
                update(Portfolio)
                .where(Portfolio.user_id == user_id, Portfolio.is_default.is_(True))
                .values(is_default=False)
            )
            await self._db.flush()  # see create() — same unique-index ordering issue

        if body.name is not None:
            portfolio.name = body.name
        if body.description is not None:
            portfolio.description = body.description
        if body.is_default is not None:
            portfolio.is_default = body.is_default

        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            raise PortfolioError(
                f"You already have a portfolio named '{body.name}'.",
                status_code=409,
            )
        return portfolio

    async def delete(self, user_id: str, portfolio_id: str) -> None:
        portfolio = await self.get(user_id, portfolio_id)
        if portfolio.is_default:
            # Refuse to delete the default; user must promote another portfolio first
            raise PortfolioError(
                "Cannot delete the default portfolio. Set another portfolio as default first.",
                status_code=400,
            )
        await self._db.delete(portfolio)
        await self._db.flush()
