# PSX DATA LICENSING NOTICE
# Current mode: EDUCATIONAL / NON-COMMERCIAL (ADR-000)
# Production / commercial use of PSX market data requires a license.
# Contact: marketdatarequest@psx.com.pk

"""
Seed the securities table from the static symbol list.
Run once after `alembic upgrade head`:

    python -m psx_ingest.seeds.seed_securities

Or via Celery task:

    celery -A psx_ingest.worker call psx_ingest.seeds.seed_securities.run_seed
"""

import asyncio
import sys

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from psx_ingest.config import settings
from psx_ingest.seeds.psx_symbols import PSX_SYMBOLS

logger = structlog.get_logger(__name__)


async def seed_securities(session: AsyncSession) -> dict[str, int]:
    inserted = 0
    updated = 0

    for symbol_data in PSX_SYMBOLS:
        # Check for existing row
        result = await session.execute(
            text("SELECT id FROM securities WHERE symbol = :symbol"),
            {"symbol": symbol_data["symbol"]},
        )
        existing = result.fetchone()

        if existing:
            await session.execute(
                text("""
                    UPDATE securities SET
                        company_name     = :company_name,
                        sector           = :sector,
                        is_kmi_compliant = :is_kmi_compliant,
                        is_kse100        = :is_kse100,
                        is_kse30         = :is_kse30,
                        updated_at       = NOW()
                    WHERE symbol = :symbol
                """),
                symbol_data,
            )
            updated += 1
        else:
            await session.execute(
                text("""
                    INSERT INTO securities
                        (symbol, company_name, sector, is_kmi_compliant, is_kse100, is_kse30, is_active, updated_at)
                    VALUES
                        (:symbol, :company_name, :sector, :is_kmi_compliant, :is_kse100, :is_kse30, true, NOW())
                """),
                symbol_data,
            )
            inserted += 1

    await session.commit()
    return {"inserted": inserted, "updated": updated}


async def _run() -> None:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        result = await seed_securities(session)

    await engine.dispose()
    logger.info(
        "Securities seed complete",
        inserted=result["inserted"],
        updated=result["updated"],
        total=len(PSX_SYMBOLS),
    )


if __name__ == "__main__":
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
    )
    asyncio.run(_run())
    sys.exit(0)
