from functools import lru_cache

from app.src.llm_gateway.providers.factory import get_provider
from app.src.utils.logger import get_logger


logger = get_logger(__name__)


@lru_cache
def get_model():
    return get_provider(id="default")


def call_model(prompt: str) -> str:
    """Call the LLM provider with the given prompt and return the response."""
    model = get_model()
    try:
        logger.info("Default LLM call started")
        response = model.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        logger.warning(f"Default LLM call failed: {e}")
        raise
