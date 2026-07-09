import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000/ask"
STATS_URL = "http://127.0.0.1:8000/stats"
HEALTH_URL = "http://127.0.0.1:8000/health"

st.set_page_config(page_title="SQL-RAG-Analyst", page_icon="📊", layout="centered")

ROUTE_COLORS = {"sql": "#2563eb", "rag": "#16a34a", "hybrid": "#9333ea"}


def route_badge(route: str) -> str:
    color = ROUTE_COLORS.get(route, "#6b7280")
    return f"""<span style="background-color:{color}; color:white; padding:2px 10px;
    border-radius:12px; font-size:0.75rem; font-weight:600;">{route.upper()}</span>"""


def token_badge(tokens: int) -> str:
    if not tokens:
        return ""
    return f"""<span style="color:#6b7280; font-size:0.75rem; margin-left:8px; font-weight:500;">🪙 {tokens:,} tokens</span>"""


st.title("📊 SQL-RAG-Analyst")
st.caption("Ask questions about sales data, company policy, or both.")


@st.cache_data(ttl=60)
def fetch_stats():
    resp = requests.get(STATS_URL, timeout=5)
    resp.raise_for_status()
    return resp.json()


# --- Stats bar ---
try:
    stats = fetch_stats()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Orders", f"{stats['total_orders']:,}")
    c2.metric("Total Revenue", f"${stats['total_revenue']:,.0f}")
    c3.metric("Sales Channels", stats["distinct_channels"])
    c4.metric("Policy Docs", stats["policy_documents"])
    st.caption(f"Data range: {stats['earliest_order']} → {stats['latest_order']}")
    st.divider()
except (requests.exceptions.RequestException, KeyError, ValueError):
    st.warning("Stats unavailable — is the backend running?")

if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar: user settings, examples + health ---
with st.sidebar:
    st.subheader("User Settings")
    # Store user_id in session state via the text input
    st.text_input(
        "User ID",
        value="guest-user",
        key="user_id",
        help="Used to track daily token budget."
    )
    st.divider()

    st.subheader("Example questions")

    with st.expander("📈 SQL — sales data", expanded=True):
        for i, ex in enumerate([
            "What is the total order quantity across all sales?",
            "What sales channel had the most orders?",
        ]):
            if st.button(ex, use_container_width=True, key=f"sql_{i}"):
                st.session_state.pending_query = ex

    with st.expander("📄 Policy — company documents"):
        for i, ex in enumerate([
            "What discount level requires regional manager sign-off?",
            "What is the monthly remote work stipend?",
        ]):
            if st.button(ex, use_container_width=True, key=f"rag_{i}"):
                st.session_state.pending_query = ex

    with st.expander("🔀 Hybrid — data + policy"):
        for i, ex in enumerate([
            "Does a 25% discount comply with commission policy, and how many orders exceed that in our data?",
        ]):
            if st.button(ex, use_container_width=True, key=f"hybrid_{i}"):
                st.session_state.pending_query = ex

    st.divider()
    st.subheader("Backend status")
    try:
        health = requests.get(HEALTH_URL, timeout=3)
        if health.status_code == 200:
            st.success("API reachable")
        else:
            st.warning(f"API returned {health.status_code}")
    except requests.exceptions.RequestException:
        st.error("API not reachable — is uvicorn running?")


def render_sources(sources):
    if sources:
        with st.expander(f"Sources ({len(sources)})"):
            for src in sources:
                st.markdown(f"- **{src.get('filename', 'unknown')}** (chunk {src.get('chunk_id', '?')})")


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("route"):
            meta_html = route_badge(msg["route"]) + token_badge(msg.get("tokens_used", 0))
            st.markdown(meta_html, unsafe_allow_html=True)
            render_sources(msg.get("sources"))


def ask_backend(query: str, user_id: str):
    try:
        resp = requests.post(API_URL, json={"query": query, "user_id": user_id}, timeout=60)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.HTTPError as e:
        try:
            detail = resp.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, f"Request failed: {detail}"
    except requests.exceptions.RequestException as e:
        return None, f"Could not reach the API: {e}"


def handle_query(query: str):
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            data, error = ask_backend(query, st.session_state.user_id)

        if error:
            st.error(error)
            st.session_state.messages.append({"role": "assistant", "content": error})
        else:
            answer = data.get("answer", "")
            route = data.get("route", "")
            sources = data.get("sources", [])
            tokens = data.get("tokens_used", 0)

            st.markdown(answer)

            meta_html = route_badge(route) + token_badge(tokens)
            st.markdown(meta_html, unsafe_allow_html=True)

            render_sources(sources)

            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "route": route,
                "sources": sources,
                "tokens_used": tokens
            })


if "pending_query" in st.session_state:
    handle_query(st.session_state.pop("pending_query"))

if user_query := st.chat_input("Ask about sales data or company policy..."):
    handle_query(user_query)