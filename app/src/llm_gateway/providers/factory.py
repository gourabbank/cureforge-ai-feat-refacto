from langchain_openai import ChatOpenAI
from app.src.utils.settings import get_settings


settings = get_settings()


def get_provider(id: str = None, model_name: str = None, temperature: float = 1):
    """Returns a provider instance based on the specified configuration."""
    resolved_model_name = model_name or settings.model_name

    return ChatOpenAI(
        model=resolved_model_name,
        temperature=temperature,
        api_key=settings.litellm_api_key,
        base_url=settings.litellm_base_url,
        default_headers={"X-Agent-ID": id} if id else None,
        max_retries=3,
    )
