from src.app.agent.state import AgentState
from src.app.agent.prompts import SYNTHESIS_PROMPT
from src.app.llm.provider import get_llm
from src.app.llm.token_utils import extract_tokens


async def synthesis_node(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = SYNTHESIS_PROMPT.format(
        query=state["query"],
        sql_context=state.get("sql_result") or "N/A",
        rag_context=state.get("rag_result") or "N/A",
    )
    response = await llm.ainvoke(prompt)

    tokens = extract_tokens(response)
    return {
        **state,
        "answer": response.content,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }