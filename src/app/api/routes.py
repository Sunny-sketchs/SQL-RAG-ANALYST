import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from openai import RateLimitError

from src.app.db.session import get_db
from src.app.agent.graph import build_graph
from src.app.api.schemas import AskRequest, AskResponse
from src.app.usage.tracker import check_budget, record_usage
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, session: AsyncSession = Depends(get_db)):
    try:
        allowed = await check_budget(session, request.user_id)
    except Exception:
        logger.exception("Usage budget check failed for user: %s", request.user_id)
        raise HTTPException(status_code=502, detail="Failed to check usage budget. Please try again.")

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Daily AI usage limit reached for this user. Try again tomorrow.",
        )

    try:
        graph = build_graph(session)
        result = await graph.ainvoke({"query": request.query, "user_id": request.user_id})
    except RateLimitError:
        logger.exception("LLM provider quota/rate limit exceeded")
        raise HTTPException(
            status_code=503,
            detail="The AI service is temporarily unavailable (quota exceeded). Please try again later.",
        )
    except Exception:
        logger.exception("Pipeline failed for query: %s", request.query)
        raise HTTPException(
            status_code=502,
            detail="Failed to process query. Please try again.",
        )

    answer = result.get("answer")
    if not answer:
        logger.warning("Pipeline returned no answer for query: %s", request.query)
        raise HTTPException(
            status_code=500,
            detail="No answer was generated for this query.",
        )

    tokens_used = result.get("tokens_used", 0)
    try:
        await record_usage(session, request.user_id, "total", tokens_used)
    except Exception:
        logger.exception("Failed to record usage for user: %s", request.user_id)

    return AskResponse(
        answer=answer,
        route=result.get("route", "unknown"),
        sources=result.get("sources", []),
        tokens_used=tokens_used,
    )


@router.get("/stats")
async def stats(session: AsyncSession = Depends(get_db)):
    result = await session.execute(text("""
        SELECT
            COUNT(*) AS total_orders,
            SUM(order_quantity) AS total_quantity,
            SUM(unit_price * order_quantity) AS total_revenue,
            COUNT(DISTINCT sales_channel) AS distinct_channels,
            MIN(order_date) AS earliest_order,
            MAX(order_date) AS latest_order
        FROM sales
    """))
    row = result.mappings().first()

    doc_result = await session.execute(text("SELECT COUNT(*) FROM documents"))
    doc_count = doc_result.scalar_one()

    return {
        "total_orders": row["total_orders"],
        "total_quantity": row["total_quantity"],
        "total_revenue": round(row["total_revenue"], 2) if row["total_revenue"] else 0,
        "distinct_channels": row["distinct_channels"],
        "earliest_order": str(row["earliest_order"])[:10] if row["earliest_order"] else None,
        "latest_order": str(row["latest_order"])[:10] if row["latest_order"] else None,
        "policy_documents": doc_count,
    }