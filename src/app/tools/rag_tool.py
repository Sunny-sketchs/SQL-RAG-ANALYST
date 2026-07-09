import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.models import Chunk, Document
from src.app.llm.provider import get_embeddings
from src.app.config import settings

TOP_K = 5

# Embedding token usage isn't exposed via LangChain's aembed_query interface,
# so this is an estimate based on tiktoken's tokenizer, not exact API usage.
_encoding = tiktoken.encoding_for_model(settings.embedding_model)


def _estimate_tokens(text: str) -> int:
    return len(_encoding.encode(text))


async def run_rag_tool(query: str, session: AsyncSession) -> tuple[str, list[dict], int]:
    embeddings = get_embeddings()
    query_vector = await embeddings.aembed_query(query)
    tokens = _estimate_tokens(query)

    stmt = (
        select(Chunk, Document.filename)
        .join(Document, Chunk.document_id == Document.id)
        .order_by(Chunk.embedding.cosine_distance(query_vector))
        .limit(TOP_K)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        return "No relevant policy content found.", [], tokens

    context_parts = []
    sources = []
    for chunk, filename in rows:
        context_parts.append(f"[{filename}] {chunk.content}")
        sources.append({"filename": filename, "chunk_id": chunk.id})

    return "\n\n".join(context_parts), sources, tokens