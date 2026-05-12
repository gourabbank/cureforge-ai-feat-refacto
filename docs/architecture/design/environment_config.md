# CureForge Environment & Configuration

## 2.1 Environment Variables

### Required Variables

| Variable        | Description                  | Default                 | Notes                                                     |
| --------------- | ---------------------------- | ----------------------- | --------------------------------------------------------- |
| MODEL_NAME      | LLM model to use via litellm | None (required)         | Format: `provider/model` e.g. `ollama/qwen3.5:397b-cloud` |
| LITELLM_API_KEY | Master key for litellm proxy | None (required)         | Set in .env, matches litellm config master_key            |
| REDIS_PASSWORD  | Redis authentication         | None (required in prod) | Used by compose.yml for redis --requirepass               |

### Optional Variables

| Variable         | Description                         | Default | Notes                                                  |
| ---------------- | ----------------------------------- | ------- | ------------------------------------------------------ |
| JINA_API_KEY     | Jina AI for markdown extraction     | None    | Used by get_markdown() in tools to fetch paper content |
| GROQ_API_KEY     | Groq API for groq/\* models         | None    | Optional - only if using Groq providers                |
| CEREBRAS_API_KEY | Cerebras API for cerebras/\* models | None    | Optional - only if using Cerebras providers            |
| GEMINI_API_KEY   | Google Gemini API                   | None    | Optional - only if using Gemini providers              |
| app_env          | Environment mode                    | dev     | Affects is_production property check                   |

### Inferred from app_env

```python
# settings.py:32-33
@property
def is_production(self) -> bool:
    return self.app_env.strip().lower() in ("production", "prod")
```

Setting `app_env=production` or `app_env=prod` enables production behavior (likely for logging/tracing).

## 2.2 Settings Properties

All defined in `app/src/utils/settings.py`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"

    # LLM Gateway
    litellm_base_url: str = "http://litellm:4000/v1"  # Docker Compose URL
    litellm_api_key: str = None
    jina_api_key: str = None
    model_name: str = None

    # Cache paths
    cache_prefix: str = "/app/.cache"
    input_prefix: str = "/app/.input"

    # Path configurations
    default_paths: dict[str, str] = {
        "agent_dbs": f"{cache_prefix}/agent_dbs",
        "logs": f"{cache_prefix}/logs",
        "simulations": f"{input_prefix}/simulations",
        "research": f"{input_prefix}/research",
        "playground": f"{cache_prefix}/playground",
    }

    # Output settings
    max_results_length: int = 10000  # truncation threshold

    # Redis
    redis_password: str = None
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
```

## 2.3 Path Configurations

The system creates directories under these mapped volumes:

| Internal Path | Docker Volume | Host Location  | Purpose                             |
| ------------- | ------------- | -------------- | ----------------------------------- |
| /app/.cache   | ./.cache      | project/.cache | Agent DBs, logs, playground outputs |
| /app/.input   | ./.input      | project/.input | Research data, simulations scripts  |

### What gets written where:

- **Agent DBs**: `.cache/agent_dbs/agent_{id}_memory.db` - SQLite checkpointer for each disease agent
- **Logs**: `.cache/logs/{YYYY-MM-DD}.log` and `.cache/logs/{YYYY-MM-DD}-error.log`
- **Playground**: `.cache/playground/{agent_id}/summaries/{phase}_{cycle}.md` - phase transition summaries
- **Temporary**: `.cache/playground/{agent_id}/{uuid}/content.txt` - large tool outputs

## 2.4 Docker Compose Dependencies

```yaml
# compose.yml dependencies (health checks)
cureforge:
    depends_on:
        redis:
            condition: service_healthy
        litellm:
            condition: service_healthy
```

**Startup sequence**:

1. Redis starts first, runs health check on ping
2. Litellm starts second, waits for redis, runs socket check on port 4000
3. Cureforge starts last only when both are healthy

**Failure behavior**:

- If redis is down: litellm proxy fails (rate limiting), cureforge health check fails, docker-compose up fails with non-zero exit
- If litellm is down: cureforge health checks fail, all LLM calls fail

## 2.5 litellm Configuration

Model list in `litellm/config.yml`:

### Local Models (Ollama)

- ollama/gemma4 -> host.docker.internal:11434
- ollama/gemma4:31b-cloud
- ollama/ministral-3:14b-cloud
- ollama/minimax-m2.7:cloud
- ollama/nemotron-3-super:cloud
- ollama/qwen3.5:397b-cloud

### External Providers

- groq/llama-3.1-8b-instant -> api.groq.com
- groq/openai/gpt-oss-120b -> api.groq.com
- cerebras/llama3.1-8b -> api.cerebras.ai
- gemini/gemini-2.5-flash -> api.google.com

All models have `supports_function_calling: true` set - critical for tool use.

## 2.6 Runtime Constraints

- **Python**: >=3.13 required (from pyproject.toml)
- **SQLite thread safety**: checkpointer uses `check_same_thread=False` for multi-threaded access in ThreadPoolExecutor
- **Max results length**: 10000 characters - beyond this, results written to file and path returned instead
- **LLM timeout**: 600 seconds (set in litellm config)
- **Rate limiting**: 30 RPM per model (set in litellm config)

## 2.7 Missing Environment Behavior

| Missing Variable                           | Behavior                                                  |
| ------------------------------------------ | --------------------------------------------------------- |
| MODEL_NAME                                 | Runtime error - get_settings().model_name is None         |
| LITELLM_API_KEY                            | All LLM calls fail with 401                               |
| REDIS_PASSWORD                             | Redis fails to authenticate, litellm rate limiting broken |
| JINA_API_KEY                               | get_markdown() uses unauthenticated request to jina.ai    |
| APP_ENV                                    | Defaults to "dev"                                         |
| External API keys (GROQ, CEREBRAS, GEMINI) | Those provider LLM calls fail                             |
