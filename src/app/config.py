from functools import cached_property
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    gemini_api_key: str | None = None

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    daily_token_limit: int = 200_000
    llm_max_output_tokens: int = 1000

    log_level: str = "INFO"
    app_name: str = "SQL-RAG-Analyst"
    app_version: str = "1.0.0"
    ...

    # new for live test
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @cached_property
    def sync_database_url(self) -> str:
        """Sync variant (psycopg2) for offline scripts — psycopg2 uses
        sslmode=require, not asyncpg's ssl=require, so translate it."""
        url = self.database_url.replace("+asyncpg", "")
        url = url.replace("?ssl=require", "?sslmode=require")
        url = url.replace("&ssl=require", "&sslmode=require")
        return url

settings = Settings()