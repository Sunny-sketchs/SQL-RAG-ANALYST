from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.models import UsageLog
from src.app.config import settings


async def get_today_usage(session: AsyncSession, user_id: str) -> int:
    # Use offset-naive utcnow to align perfectly with TIMESTAMP WITHOUT TIME ZONE columns
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    stmt = select(func.coalesce(func.sum(UsageLog.tokens), 0)).where(
        UsageLog.user_id == user_id,
        UsageLog.created_at >= today_start,
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def check_budget(session: AsyncSession, user_id: str) -> bool:
    used = await get_today_usage(session, user_id)
    return used < settings.daily_token_limit


async def record_usage(session: AsyncSession, user_id: str, node: str, tokens: int) -> None:
    if tokens <= 0:
        return
    session.add(UsageLog(user_id=user_id, node=node, tokens=tokens))
    await session.commit()