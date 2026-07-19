import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.config import settings
from src.app.api.routes import router
from src.app.db.session import get_db


app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(router)


@app.api_route("/health", methods=["GET", "HEAD"], operation_id="check_system_health")
async def health(session: AsyncSession = Depends(get_db)):
    db_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "app": settings.app_name,
        "version": settings.app_version,
        "database": db_status,
    }