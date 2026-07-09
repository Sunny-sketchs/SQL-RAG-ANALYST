import re
import logging
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agent.prompts import SQL_GEN_PROMPT
from src.app.llm.provider import get_llm
from src.app.llm.token_utils import extract_tokens

logger = logging.getLogger(__name__)

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|truncate|grant|create)\b", re.I)


def _validate_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    if ";" in sql:
        raise ValueError("Multiple statements are not allowed.")
    if not sql.lower().startswith("select"):
        raise ValueError("Only SELECT statements are allowed.")
    if FORBIDDEN.search(sql):
        raise ValueError("Query contains a forbidden keyword.")
    if "limit" not in sql.lower():
        sql += " LIMIT 100"
    return sql


def _serialize_value(v):
    """Convert DB types that render awkwardly as raw Python repr (timedelta,
    Decimal) into plain, LLM-friendly values before they hit the synthesis
    prompt as text."""
    if isinstance(v, timedelta):
        return round(v.total_seconds() / 86400, 2)  # days, as a plain float
    if isinstance(v, Decimal):
        return float(v)
    return v


async def run_sql_tool(query: str, session: AsyncSession) -> tuple[str, int]:
    llm = get_llm()
    prompt = SQL_GEN_PROMPT.format(query=query)
    response = await llm.ainvoke(prompt)
    tokens = extract_tokens(response)

    logger.info("SQL_GEN input query: %s", query)
    logger.info("SQL_GEN raw LLM output: %s", response.content)

    try:
        sql = _validate_sql(response.content)
    except ValueError as e:
        logger.warning("SQL_GEN validation failed: %s | raw output: %s", e, response.content)
        return f"Could not run a safe SQL query: {e}", tokens

    logger.info("SQL_GEN validated SQL to execute: %s", sql)

    try:
        result = await session.execute(text(sql))
        rows = result.fetchall()
        columns = result.keys()
    except Exception as e:
        await session.rollback()
        logger.error("SQL execution failed: %s | SQL: %s", e, sql)
        return f"SQL execution failed: {e}", tokens

    if not rows:
        logger.info("SQL_GEN query returned no rows: %s", sql)
        return "Query returned no rows.", tokens

    formatted = [
        {col: _serialize_value(val) for col, val in zip(columns, row)}
        for row in rows
    ]
    logger.info("SQL_GEN result: %s", formatted)
    return str(formatted), tokens