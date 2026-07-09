from typing import TypedDict, Literal


class AgentState(TypedDict, total=False):
    query: str
    user_id: str
    route: Literal["sql", "rag", "hybrid"]
    sql_result: str | None
    rag_result: str | None
    sources: list[dict]
    answer: str
    tokens_used: int