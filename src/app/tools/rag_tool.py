import logging
import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.db.models import Chunk, Document
from src.app.llm.provider import get_embeddings
from src.app.config import settings

logger = logging.getLogger(__name__)

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

    logger.info("RAG_GEN input query: %s", query)

    stmt = (
        select(Chunk, Document.filename)
        .join(Document, Chunk.document_id == Document.id)
        .order_by(Chunk.embedding.cosine_distance(query_vector))
        .limit(TOP_K)
    )
    result = await session.execute(stmt)
    rows = result.all()

    if not rows:
        logger.info("RAG_GEN: no chunks retrieved for query: %s", query)
        return "No relevant policy content found.", [], tokens

    context_parts = []
    sources = []
    for chunk, filename in rows:
        preview = chunk.content[:80].replace("\n", " ")
        logger.info("RAG_GEN retrieved chunk: filename=%s chunk_id=%s preview=%r", filename, chunk.id, preview)
        context_parts.append(f"[{filename}] {chunk.content}")
        sources.append({"filename": filename, "chunk_id": chunk.id})

    logger.info("RAG_GEN retrieved %d chunk(s) total", len(rows))
    return "\n\n".join(context_parts), sources, tokens