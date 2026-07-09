from src.app.agent.state import AgentState
from src.app.agent.prompts import ROUTER_PROMPT
from src.app.llm.provider import get_llm
from src.app.llm.token_utils import extract_tokens

VALID_ROUTES = {"sql", "rag", "hybrid"}


async def router_node(state: AgentState) -> AgentState:
    llm = get_llm()
    prompt = ROUTER_PROMPT.format(query=state["query"])
    response = await llm.ainvoke(prompt)

    route = response.content.strip().lower()
    if route not in VALID_ROUTES:
        route = "hybrid"

    tokens = extract_tokens(response)
    return {
        **state,
        "route": route,
        "tokens_used": state.get("tokens_used", 0) + tokens,
    }