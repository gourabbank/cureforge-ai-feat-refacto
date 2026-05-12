from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """CureForge AI centralized settings management."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"

    litellm_base_url: str = "http://litellm:4000/v1"
    litellm_api_key: str = None
    jina_api_key: str = None

    model_name: str = None

    cache_prefix: str = "/app/.cache"
    input_prefix: str = "/app/.input"

    default_paths: dict[str, str] = {
        "agent_dbs": f"{cache_prefix}/agent_dbs",
        "logs": f"{cache_prefix}/logs",
        "simulations": f"{input_prefix}/simulations",
        "research": f"{input_prefix}/research",
        "playground": f"{cache_prefix}/playground",
    }

    max_results_length: int = 10000

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in ("production", "prod")

    redis_password: str = None
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings():
    return Settings()
