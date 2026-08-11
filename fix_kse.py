import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def fix_registration():
    db_url = os.getenv("DATABASE_URL")
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        # Register the KSE100 index so the database accepts its prices
        await conn.execute(text(
            "INSERT INTO securities (symbol, name, sector) "
            "VALUES ('KSE100', 'KSE 100 Index', 'Index') "
            "ON CONFLICT (symbol) DO NOTHING"
        ))
        await conn.commit()
        print("✅ KSE100 successfully registered in securities table.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(fix_registration())
