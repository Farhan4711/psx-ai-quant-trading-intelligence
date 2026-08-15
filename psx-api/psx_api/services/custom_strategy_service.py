"""Custom strategy CRUD + backtest hookup (Phase 4 Steps 62-63)."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from psx_api.models.community import UserStrategy
from psx_api.schemas.community import StrategyCreate, StrategyUpdate
from psx_api.strategy_builder.parse import InvalidStrategyError, validate


class StrategyError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class CustomStrategyService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_for_user(self, user_id: str) -> list[UserStrategy]:
        return list(
            (
                await self._db.execute(
                    select(UserStrategy)
                    .where(UserStrategy.user_id == user_id)
                    .order_by(desc(UserStrategy.updated_at))
                )
            )
            .scalars()
            .all()
        )

    async def list_public(self, limit: int = 50) -> list[UserStrategy]:
        return list(
            (
                await self._db.execute(
                    select(UserStrategy)
                    .where(UserStrategy.is_public.is_(True))
                    .order_by(desc(UserStrategy.created_at))
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

    async def get(self, strategy_id: str) -> UserStrategy | None:
        return (
            await self._db.execute(select(UserStrategy).where(UserStrategy.id == strategy_id))
        ).scalar_one_or_none()

    async def create(self, user_id: str, body: StrategyCreate) -> UserStrategy:
        try:
            validate(body.rules)
        except InvalidStrategyError as exc:
            raise StrategyError(str(exc)) from exc

        s = UserStrategy(
            user_id=user_id,
            name=body.name,
            description=body.description,
            rules=body.rules,
            is_public=body.is_public,
        )
        self._db.add(s)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            raise StrategyError(
                f"You already have a strategy named '{body.name}'.",
                status_code=409,
            ) from None
        await self._db.refresh(s)
        return s

    async def update(self, user_id: str, strategy_id: str, body: StrategyUpdate) -> UserStrategy:
        s = await self.get(strategy_id)
        if not s or s.user_id != user_id:
            raise StrategyError("Strategy not found.", status_code=404)

        if body.rules is not None:
            try:
                validate(body.rules)
            except InvalidStrategyError as exc:
                raise StrategyError(str(exc)) from exc
            s.rules = body.rules
        if body.name is not None:
            s.name = body.name
        if body.description is not None:
            s.description = body.description
        if body.is_public is not None:
            s.is_public = body.is_public
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            raise StrategyError(
                f"You already have a strategy named '{body.name}'.",
                status_code=409,
            ) from None
        return s

    async def delete(self, user_id: str, strategy_id: str) -> None:
        s = await self.get(strategy_id)
        if not s or s.user_id != user_id:
            raise StrategyError("Strategy not found.", status_code=404)
        await self._db.delete(s)
        await self._db.flush()

    async def fork(self, user_id: str, strategy_id: str) -> UserStrategy:
        source = await self.get(strategy_id)
        if not source or not source.is_public:
            raise StrategyError("Strategy not available to fork.", status_code=404)

        s = UserStrategy(
            user_id=user_id,
            name=f"{source.name} (forked)",
            description=source.description,
            rules=source.rules,
            is_public=False,
            forked_from=source.id,
        )
        self._db.add(s)
        try:
            await self._db.flush()
        except IntegrityError:
            await self._db.rollback()
            raise StrategyError(
                "You've already forked this strategy. Rename your existing " "copy first.",
                status_code=409,
            ) from None
        await self._db.refresh(s)
        return s
