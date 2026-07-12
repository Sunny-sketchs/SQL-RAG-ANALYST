from functools import lru_cache
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.app.config import settings


def get_llm(provider: str | None = None):
    """Factory for the chat/generation model. Swappable via LLM_PROVIDER."""
    provider = provider or settings.llm_provider

    if provider == "openai":
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
            max_tokens=settings.llm_max_output_tokens,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set but llm_provider=gemini")
        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",  # gemini-1.5-flash was retired; this is current stable as of mid-2026
            google_api_key=settings.gemini_api_key,
            temperature=0,
            max_tokens=settings.llm_max_output_tokens,
        )

    raise ValueError(f"Unknown llm_provider: {provider}")


@lru_cache
def get_embeddings():
    """Embeddings are intentionally NOT swappable — see models.py note on Vector(1536)."""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )