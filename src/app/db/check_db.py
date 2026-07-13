import dotenv
import os
dotenv.load_dotenv(os.getenv("ENV_FILE", ".env"))

import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from src.app.config import settings


def check_sync_connection():
    print("--- Sync connection (used by scripts) ---")
    try:
        engine = create_engine(settings.sync_database_url)
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).scalar()
            print(f"Connected. Postgres version: {version.split(',')[0]}")

            db_name = conn.execute(text("SELECT current_database();")).scalar()
            print(f"Connected to database: {db_name}")
    except Exception as e:
        print(f"Sync connection failed: {e}")
        return False
    return True


async def check_async_connection():
    print("\n--- Async connection (used by FastAPI) ---")
    try:
        engine = create_async_engine(settings.database_url)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1;"))
            result.scalar()
            print("Async connection works.")
        await engine.dispose()
    except Exception as e:
        print(f"Async connection failed: {e}")
        return False
    return True


def check_extension():
    print("\n--- pgvector extension ---")
    try:
        engine = create_engine(settings.sync_database_url)
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector';")
            ).fetchone()
            if result:
                print("vector extension is installed.")
            else:
                print(" vector extension NOT installed yet (init_db.py will create it).")
    except Exception as e:
        print(f" Could not check extension: {e}")


def check_tables():
    print("\n--- Existing tables ---")
    try:
        engine = create_engine(settings.sync_database_url)
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
            ).fetchall()
            tables = [r[0] for r in rows]
            if tables:
                print(f"  Tables already exist: {tables}")
                print("   (init_db.py will SKIP creation if 'sales' or 'documents' are present)")
            else:
                print(" No tables yet — clean slate, init_db.py will create them.")
    except Exception as e:
        print(f" Could not list tables: {e}")


def check_env():
    print("--- .env sanity check ---")
    ok = True
    if not settings.database_url.startswith("postgresql+asyncpg://"):
        print(f" DATABASE_URL should start with 'postgresql+asyncpg://', got: {settings.database_url[:30]}...")
        ok = False
    else:
        print(" DATABASE_URL has correct asyncpg prefix.")

    if not settings.openai_api_key or not settings.openai_api_key.startswith("sk-"):
        print(" OPENAI_API_KEY missing or malformed.")
        ok = False
    else:
        print(" OPENAI_API_KEY looks present.")

    return ok


if __name__ == "__main__":
    print("=" * 50)
    from src.app.config import settings
    host = settings.database_url.split('@')[1].split('/')[0]
    print(f"🔌 Connecting to host: {host}")
    env_ok = check_env()
    print("=" * 50)

    if not env_ok:
        print("\nFix .env issues above before proceeding.")
    else:
        sync_ok = check_sync_connection()
        async_ok = asyncio.run(check_async_connection())
        check_extension()
        check_tables()

        print("\n" + "=" * 50)
        if sync_ok and async_ok:
            print(" All checks passed. Safe to run: python -m scripts.init_db")
        else:
            print(" Fix connection issues above before running init_db.py")