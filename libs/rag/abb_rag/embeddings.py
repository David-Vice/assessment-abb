from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from abb_rag.exceptions import ExternalServiceError
from abb_rag.log import get_logger
from abb_rag.settings import get_settings

logger = get_logger(__name__)

# LangChain's OpenAIEmbeddings batches, retries (max_retries), and asserts the
# response shape — honoring the LangChain stack decision. Retrieval itself is
# custom hybrid SQL, so LangChain is used only where it earns its keep.
EMBED_MAX_RETRIES = 5
# OpenAI caps each embeddings request at 300k tokens summed across inputs (and
# 2048 inputs). Chunks are <=1024 tokens, so 256/request stays <=262k tokens —
# safely under both caps. The default chunk_size of 1000 would overflow at scale.
EMBED_BATCH_SIZE = 256


@lru_cache
def get_embeddings_client() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key.get_secret_value(),
        max_retries=EMBED_MAX_RETRIES,
        chunk_size=EMBED_BATCH_SIZE,
    )


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts; asserts count + dimension on the way out."""

    if not texts:
        return []
    logger.info("embedding", model=get_settings().embedding_model, count=len(texts))
    try:
        vectors = await get_embeddings_client().aembed_documents(texts)
    except Exception as error:
        raise ExternalServiceError(f"embedding request failed: {error}") from error

    if len(vectors) != len(texts):
        raise ExternalServiceError(
            f"embedding count {len(vectors)} does not match input count {len(texts)}"
        )
    expected = get_settings().embedding_dim
    if vectors and len(vectors[0]) != expected:
        raise ExternalServiceError(
            f"embedding dimension {len(vectors[0])} does not match expected {expected}"
        )
    return vectors


async def embed_query(text: str) -> list[float]:
    return (await embed_texts([text]))[0]
