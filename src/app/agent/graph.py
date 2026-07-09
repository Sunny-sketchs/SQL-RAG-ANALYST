from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.agent.state import AgentState
from src.app.agent.router_node import router_node
from src.app.agent.synthesis_node import synthesis_node
from src.app.tools.sql_tool import run_sql_tool
from src.app.tools.rag_tool import run_rag_tool


def build_graph(session: AsyncSession):
    async def sql_node(state: AgentState) -> AgentState:
        result, tokens = await run_sql_tool(state["query"], session)
        return {
            **state,
            "sql_result": result,
            "tokens_used": state.get("tokens_used", 0) + tokens,
        }

    async def rag_node(state: AgentState) -> AgentState:
        result, sources, tokens = await run_rag_tool(state["query"], session)
        return {
            **state,
            "rag_result": result,
            "sources": sources,
            "tokens_used": state.get("tokens_used", 0) + tokens,
        }

    async def hybrid_node(state: AgentState) -> AgentState:
        state = await sql_node(state)
        state = await rag_node(state)
        return state

    def route_selector(state: AgentState) -> str:
        return state["route"]

    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("sql", sql_node)
    graph.add_node("rag", rag_node)
    graph.add_node("hybrid", hybrid_node)
    graph.add_node("synthesis", synthesis_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges(
        "router",
        route_selector,
        {"sql": "sql", "rag": "rag", "hybrid": "hybrid"},
    )
    graph.add_edge("sql", "synthesis")
    graph.add_edge("rag", "synthesis")
    graph.add_edge("hybrid", "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()