import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from fastapi import FastAPI

from src.app.config import settings
from src.app.api.routes import router


app = FastAPI(title=settings.app_name, version=settings.app_version)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.app_version}