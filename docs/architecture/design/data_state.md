# CureForge Data & State

## 4.1 State Structures

### ResearchAgentState (core/state.py)

Primary state schema that flows through the LangGraph agent. Extends langchain.agents.AgentState.

```python
class ResearchAgentState(AgentState):
    agent_id: str                              # Unique agent identifier
    disease_name: str                          # Target disease being researched
    current_phase: str = "research"            # Current phase in pipeline
    phase_history: list[str] = ["research"]    # Ordered list of visited phases
    phase_cycles: dict[str, int] = {}          # Count per phase: {"research": 0, "hypothesize": 0, ...}
    transition_reason: str | None = None       # Rationale from transition_phase tool
    success_definition: str | None = None      # Success criteria for next phase
    should_stop: bool = False                  # Flag to terminate loop
    cycle_count: int = 0                       # Current iteration number
```

Plus inherited from AgentState:

```python
messages: list[BaseMessage]  # Conversation history - user prompts, AI responses, tool messages
```

### AgentState Flow Example

Initial state (first invoke):

```python
{
    "messages": [{"role": "user", "content": "Begin autonomous cure research for alzheimer..."}],
    "agent_id": "agent_alzheimer",
    "disease_name": "alzheimer",
    "current_phase": "research",
    "phase_history": ["research"],
    "phase_cycles": {"research": 0, "hypothesize": 0, "test": 0, "synthesize": 0},
    "should_stop": False,
    "cycle_count": 0,
}
```

After transition to hypothesize:

```python
{
    "current_phase": "hypothesize",
    "phase_history": ["research", "hypothesize"],
    "phase_cycles": {"research": 1, "hypothesize": 0, "test": 0, "synthesize": 0},
    "transition_reason": "Found 5 relevant papers on tau protein aggregation",
    "success_definition": "Identified testable mechanism involving protein clearance",
}
```

### \_Run Metadata (appended on exit)

```python
{
    "_run_metadata": {
        "thread_id": "abc123...",      # SQLite thread ID for state persistence
        "iterations": 3,            # Actual iterations completed
        "max_iterations": 3,         # Requested max
        "stopped": True,            # Whether should_stop was set
    }
}
```

---

## 4.2 Input Data Structures

### run_demo() Input

```python
def run_demo(async_mode: bool = False, max_iterations: int = 50) -> dict:
# disease_names list passed to run_sync/run_async
disease_names: list[str] = ["alzheimer", "diabetes", "cancer"]
```

### disease_name normalization

In autonomous_institute.py:

```python
agent_id = f"agent_{disease_name.lower().replace(' ', '_')}"
```

| Input disease_name | Resulting agent_id    |
| ------------------ | --------------------- |
| "Alzheimer"        | agent_alzheimer       |
| "Type 2 Diabetes"  | agent_type_2_diabetes |
| "lung cancer"      | agent_lung_cancer     |

---

## 4.3 Tool Output Structures

### research_scan_literature Output

JSON array of arXiv entries:

```json
[
    {
        "title": "Paper title",
        "published": "2024-01-15T00:00:00Z",
        "updated": "2024-01-15T00:00:00Z",
        "summary": "Abstract text...",
        "authors": ["Author One", "Author Two"],
        "links": [{ "href": "http://arxiv.org/pdf/..." }]
    }
]
```

### transition_phase Output

Returns Command to update state:

```python
Command(
    update={
        "messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), ToolMessage(content=...)],
        "current_phase": "hypothesize",
        "phase_history": ["research", "hypothesize"],
        "transition_reason": "Found evidence...",
        "success_definition": "Testable hypothesis ready",
    }
)
```

### stop_autonomous_run Output

```python
Command(
    update={
        "messages": [ToolMessage(content="Autonomous run stop requested: ...")],
        "should_stop": True,
    },
    goto=END,
)
```

---

## 4.4 File Outputs

### Agent Database

Location: `.cache/agent_dbs/agent_{id}_memory.db`

Type: SQLite with langgraph-checkpoint-sqlite schema

Tables: langgraph_checkpoints, langgraph_checkpoint_writes, langgraph_checkpoints_meta (internal to LangGraph)

Access: check_same_thread=False enabled for ThreadPoolExecutor writes

### Log Files

Location: `.cache/logs/`

Naming: `{YYYY-MM-DD}.log` for standard logs, `{YYYY-MM-DD}-error.log` for full tracebacks

Format: `2026-04-24 - [LEVEL] => message`

### Phase Summaries

Location: `.cache/playground/{agent_id}/summaries/{phase}_{cycle}.md`

Example: `.cache/playground/agent_alzheimer/summaries/research_0.md`

Content: LLM-generated context summary at phase transition

### Large Tool Outputs

Location: `.cache/playground/{agent_id}/{uuid}/content.txt`

Created when tool output exceeds max_results_length (10000 characters)

---

## 4.5 Configuration Data Structures

### Settings (app/src/utils/settings.py)

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Environment
    app_env: str = "dev"

    # LLM Gateway
    litellm_base_url: str = "http://litellm:4000/v1"
    litellm_api_key: str = None
    jina_api_key: str = None
    model_name: str = None

    # Paths
    cache_prefix: str = "/app/.cache"
    input_prefix: str = "/app/.input"
    default_paths: dict[str, str] = {
        "agent_dbs": "/app/.cache/agent_dbs",
        "logs": "/app/.cache/logs",
        "simulations": "/app/.input/simulations",
        "research": "/app/.input/research",
        "playground": "/app/.cache/playground",
    }

    # Output limits
    max_results_length: int = 10000

    # Redis
    redis_password: str = None
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
```

### litellm Model List (litellm/config.yml)

```yaml
model_list:
    - model_name: ollama/gemma4
      litellm_params:
          model: ollama_chat/gemma4
          api_base: http://host.docker.internal:11434
          rpm: 30
      model_info:
          supports_function_calling: true
    # ... (10 models total)
```

---

## 4.6 Random/Deterministic Data

### Pseudo-random scores (\_shared.py)

Uses seeded Random for reproducibility:

```python
_RNG = Random(42)  # Fixed seed

def plausibility() -> float:
    return round(_RNG.uniform(0.51, 0.94), 2)  # Range: 0.51-0.94

def efficacy() -> float:
    return round(_RNG.uniform(0.35, 0.89), 2)  # Range: 0.35-0.89

def safety() -> float:
    return round(_RNG.uniform(0.62, 0.97), 2)  # Range: 0.62-0.97
```

Note: These are placeholder implementations returning deterministic pseudo-random values. Real implementations would integrate with simulation engines.

---

## 4.7 Redis Structures

### Used By

- litellm for rate limiting (router_settings.redis_host/port/password in config.yml)
- Not directly used by cureforge application code (fakeredis in test deps unused in main code)

### Redis URL Construction

```python
@property
def redis_url(self) -> str:
    if self.redis_password:
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
    return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
```

---

## 4.8 Data Flow Summary

```
User Input (main.py)
    │
    ├─► disease_names: ["alzheimer", ...]
    │
    ├─► max_iterations: int
    │
    └─► async_mode: bool
         │
         ▼
AutonomousResearchInstitute
    │
    ├─► create_base_agent(id, disease_name, model_name)
    │       │
    │       ├─► get_provider() ──► ChatOpenAI ──► litellm:4000
    │       │
    │       ├─► SqliteSaver ──► .cache/agent_dbs/agent_{id}.db
    │       │
    │       └─► LangGraph agent with middleware
    │
    ▼
run_autonomous_research_loop()
    │
    ├─► Initial invoke: "Begin autonomous cure research..."
    │       │
    │       ▼
    │   Phase: research
    │       │
    │       ├─► research_scan_literature ──► arXiv API
    │       │
    │       ├─► transition_phase ──► validates ──► current_phase: hypothesize
    │       │
    │       └─► summary saved: .cache/.../summaries/research_0.md
    │
    ├─► Continue invokes (iteration 1...n)
    │       │
    │       ▼
    │   Phase: hypothesize / test / synthesize
    │       │
    │       └─► (phase-specific tools)
    │
    ▼
Final State Dict
    │
    ├─► messages: list[BaseMessage]
    │
    ├─► current_phase: str
    │
    ├─► phase_history: list[str]
    │
    ├─► phase_cycles: dict[str, int]
    │
    └─► _run_metadata: dict
```
