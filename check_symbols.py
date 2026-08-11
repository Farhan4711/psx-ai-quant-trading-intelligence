import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_db():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL not set!")
        return
    
    # Create engine directly
    engine = create_async_engine(db_url)
    
    try:
        async with engine.connect() as conn:
            # Query ohlcv_daily directly
            query = text("SELECT symbol, COUNT(*) FROM ohlcv_daily GROUP BY symbol")
            result = await conn.execute(query)
            
            print("\n📊 Symbols currently in Database:")
            print("-" * 35)
            found = False
            for row in result:
                found = True
                print(f"Symbol: {row[0]:<12} | Rows: {row[1]}")
            
            if not found:
                print("⚠️ Table is empty!")
            print("-" * 35)
    except Exception as e:
        print(f"❌ Error connecting to DB: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_db())
