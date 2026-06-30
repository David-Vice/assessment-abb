from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration shared across services and the worker."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SecretStr prevents the key leaking into logs/tracebacks; emptiness is
    # validated where the key is actually used (LLM/embeddings clients, P3).
    openai_api_key: SecretStr = SecretStr("")
    chat_model: str = "gpt-4o"
    aux_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-large"
    embedding_dim: int = 3072

    retrieval_candidates: int = 40
    retrieval_top_k: int = 6
    # Off by default: the reranker (torch) is an optional build extra, so the
    # default must not assume it is installed. Enable with INSTALL_RERANK + this.
    rerank_enabled: bool = False
    rerank_model: str = "BAAI/bge-reranker-v2-m3"
    context_token_budget: int = 8000
    chat_memory_enabled: bool = True

    database_url: str = "postgresql+psycopg://abb:abb@localhost:5432/abb_rag"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_per_minute: int = 60

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
