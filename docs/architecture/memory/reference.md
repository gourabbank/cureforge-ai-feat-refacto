# CureForge Critical Reference

**MUST BE FOLLOWED AT ALL TIMES**

## Development Commands

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # or use uv run

# Run demo
python app/main.py

# Run tests
pytest

# Run with coverage
pytest --cov=app

# Lint
ruff check .
ruff check --fix .
```

## Running with Docker

```bash
docker compose up
# Starts: cureforge, redis, litellm services
# Health checks: redis (10s interval), litellm (5s interval)
# Logs to stdout

# In separate terminal, run demo:
docker exec -it cureforge_app python app/main.py
```

## Environment Variables (Required)

```bash
# .env file
MODEL_NAME=ollama/qwen3.5:397b-cloud  # Required
LITELLM_API_KEY=sk-cureforge-internal  # Required
REDIS_PASSWORD=...  # Required
JINA_API_KEY=...  # Optional
GROQ_API_KEY=...  # Optional (for groq/* models)
CEREBRAS_API_KEY=...  # Optional (for cerebras/* models)
GEMINI_API_KEY=...  # Optional (for gemini/* models)
```

## Important File Locations

| What              | Location                                 |
| ----------------- | ---------------------------------------- |
| Entry point       | app/main.py                              |
| Agent creation    | app/src/core/agent.py                    |
| Research loop     | app/src/core/loop.py                     |
| Phase definitions | app/src/core/phases.py                   |
| Agent state       | app/src/core/state.py                    |
| Institute         | app/src/services/autonomous_institute.py |
| Settings          | app/src/utils/settings.py                |
| Logging           | app/src/utils/logger.py                  |
| Prompts           | app/prompts/prompts.py                   |
| litellm config    | litellm/config.yml                       |
| Docker compose    | compose.yml                              |

## Phase Pipeline

```
Research → Hypothesize → Test → Synthesize
                ↑                   │
                └────── Loop ───────┘
```

| Allowed From | Allowed To           |
| ------------ | -------------------- |
| research     | hypothesize          |
| hypothesize  | research, test       |
| test         | research, synthesize |
| synthesize   | research             |

## Key Constraints

1. **Python >=3.13** required
2. **Model must support function_calling** (all litellm models do)
3. **max_iterations >= 1** - raises ValueError otherwise
4. **max_results_length = 10000** - outputs longer than this go to file
5. **Phase tool names must match exactly** - no punctuation, no quotes
6. **LLM timeout = 600s** (litellm config)
7. **Rate limit = 30 RPM** per model

## Single Points of Failure

| Service             | Failure Impact                |
| ------------------- | ----------------------------- |
| litellm:4000        | All LLM calls fail            |
| redis               | Rate limiting broken          |
| Ollama (host:11434) | Local model calls fail        |
| .cache/agent_dbs/   | Agent state lost if disk full |

## Debugging

```bash
# View logs
tail -f .cache/logs/$(date +%Y-%m-%d).log

# View errors
cat .cache/logs/$(date +%Y-%m-%d)-error.log

# Check agent DB
sqlite3 .cache/agent_dbs/agent_alzheimer_memory.db ".tables"
sqlite3 .cache/agent_dbs/agent_alzheimer_memory.db "SELECT * FROM langgraph_checkpoints LIMIT 5"

# Check litellm health
curl http://localhost:4000/health

# Check redis
redis-cli -a "$REDIS_PASSWORD" ping
```

## Adding A New Tool

1. Add tool function in appropriate `phases/*_tools/tools.py`
2. Add to `PHASE_TOOLS` dict in `phase_tools.py` under correct phase
3. Add to `get_all_phase_tools()` if phase-scoped (automatic)
4. Add to base_system.md prompt if globally available

## Adding A New Model

1. Add to litellm/config.yml model_list
2. Set model_info.supports_function_calling: true
3. Update MODEL_NAME in .env
