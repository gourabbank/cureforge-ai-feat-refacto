# CureForge Module Documentation

## 3.1 app/main.py - Entry Point

### Purpose

Single entry point for running the autonomous research system. Provides both sync and async execution modes.

### Functions

```python
def run_demo(async_mode: bool = False, max_iterations: int = 50) -> dict:
    """Run a demo autonomous institute session with seeded diseases."""
```

**Parameters**:

- `async_mode`: If True, runs agents concurrently via ThreadPoolExecutor; if False, runs sequentially
- `max_iterations`: Maximum number of agent-loop iterations per disease (default 50, demo uses 3)

**Returns**: Dict keyed by disease_name, valued by final agent state

**Usage**:

```python
# CLI: python app/main.py
output = run_demo(async_mode=False, max_iterations=3)

# API integration
institute = AutonomousResearchInstitute(model_name="ollama/qwen3.5:397b-cloud", max_workers=3)
results = institute.run_async(["alzheimer", "diabetes", "cancer"], max_iterations=10)
```

---

## 3.2 app/src/services/autonomous_institute.py

### Purpose

Orchestrates multiple independent disease research agents. Manages agent lifecycle and concurrency.

### Class: AutonomousResearchInstitute

```python
class AutonomousResearchInstitute:
    def __init__(self, model_name: str, max_workers: int = 4):
        self.model_name = model_name
        self.max_workers = max_workers

    def run_sync(self, disease_names: list[str], max_iterations: int = 3) -> dict
    def run_async(self, disease_names: list[str], max_iterations: int = 3) -> dict
```

**Key behavior**:

- Each disease gets its own agent instance via `create_base_agent()`
- Agent ID format: `agent_{disease_name.lower().replace(' ', '_')}`
- ThreadPoolExecutor with `max_workers` limit concurrent disease agents

---

## 3.3 app/src/core/agent.py

### Purpose

Creates individual phase-aware research agents with memory and middleware.

### Functions

```python
def create_base_agent(
    id: str,
    disease_name: str,
    model_name: str = None,
    tools: list = None,
    system_prompt: str = None,
    temperature: float = 1,
) -> CompiledStateGraph:
```

**Parameters**:

- `id`: Unique agent identifier (e.g., "agent_alzheimer")
- `disease_name`: Target disease for research
- `model_name`: Override settings.model_name
- `tools`: Override default tool list from get_all_phase_tools()
- `system_prompt`: Override BASE_SYSTEM_PROMPT
- `temperature`: LLM temperature (default 1)

**Returns**: CompiledStateGraph (LangGraph agent)

**What it does**:

1. Resolves model_name from settings if not provided
2. Gets LLM via `get_provider()` through litellm proxy
3. Creates SQLite checkpointer at `.cache/agent_dbs/agent_{id}_memory.db`
4. Composes agent with:
    - Base system prompt
    - Phase-specific tools
    - Middleware stack: phase_config -> tool_errors -> tool_logger
5. Returns compiled agent

**Side effects**:

- Creates `.cache/agent_dbs/` directory if missing
- Creates SQLite database file for checkpointer

---

## 3.4 app/src/core/loop.py

### Purpose

Executes the autonomous research loop - repeatedly invokes the agent until stop signal or iteration cap.

### Functions

```python
def run_autonomous_research_loop(
    agent: CompiledStateGraph,
    agent_id: str,
    disease_name: str,
    max_iterations: int = 3,
    thread_id: str | None = None,
) -> dict:
```

**Parameters**:

- `agent`: CompiledStateGraph from create_base_agent()
- `agent_id`: Agent identifier
- `disease_name`: Target disease
- `max_iterations`: Maximum iterations (must be >=1)
- `thread_id`: Optional thread ID for state persistence (auto-generated if None)

**Returns**: Dict with final state and `_run_metadata`

**Loop behavior**:

1. Initial invoke with "Begin autonomous cure research for {disease_name}..."
2. After each invoke, checks `state.should_stop` flag
3. Iterates up to max_iterations, invoking with "Continue autonomous work..."
4. Catches and logs errors per iteration
5. Returns final state with metadata: thread_id, iterations, max_iterations, stopped

**Edge cases**:

- If max_iterations < 1: raises ValueError
- On any exception: returns error dict with metadata, continues execution

---

## 3.5 app/src/core/phases.py

### Purpose

Defines phase constants and transition validation.

### Constants

```python
PHASES = ("research", "hypothesize", "test", "synthesize")

PHASE_TRANSITIONS = {
    "research": ("hypothesize",),
    "hypothesize": ("research", "test"),
    "test": ("research", "synthesize"),
    "synthesize": ("research",),
}
```

### Functions

```python
def is_valid_transition(current_phase: str, next_phase: str) -> bool:
    """Validate allowed phase transitions, including fallback loops."""
```

**Transition graph**:

```
Research -> Hypothesize -> Test -> Synthesize
                |                   |
                |___________________|
                         v
                      (loop back)
```

**Notes**:

- research can only go forward to hypothesize
- hypothesize can loop to research or advance to test
- test can loop to research or advance to synthesize
- synthesize goes back to research (new iteration cycle)

---

## 3.6 app/src/core/state.py

### Purpose

Defines the agent state schema that flows through the graph.

### Class: ResearchAgentState

```python
class ResearchAgentState(AgentState):
    agent_id: str
    disease_name: str
    current_phase: str = "research"
    phase_history: list[str] = Field(default_factory=lambda: ["research"])
    phase_cycles: dict[str, int] = Field(default_factory=dict)
    transition_reason: str | None = None
    success_definition: str | None = None
    should_stop: bool = False
    cycle_count: int = 0
```

**Notes**:

- Extends langchain.agents.AgentState (includes messages list)
- phase_history: tracks all phases visited in order
- phase_cycles: counts how many times each phase has been visited
- transition_reason: captures rationale when transitioning
- success_definition: captures measurable success for next phase
- should_stop: flag to terminate autonomous loop

---

## 3.7 app/src/core/tools/phases/control.py

### Purpose

Control tools that manage phase transitions and run termination.

### Tools

```python
@tool
def transition_phase(
    next_phase: str,
    rationale: str,
    success_definition: str,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> Command:
```

**Parameters**:

- next_phase: Target phase name (research, hypothesize, test, synthesize)
- rationale: Why this transition is justified
- success_definition: What success looks like in next phase

**Returns**: Command to update state, remove all messages, transition phase

**Validation**:

- Checks next_phase is valid PHASE name
- Checks transition is valid per PHASE_TRANSITIONS
- If invalid: returns ToolMessage with error, does not transition

**Side effects**:

- Increments phase_cycles[current_phase]
- Saves context summary to `.cache/playground/{agent_id}/summaries/{phase}_{cycle}.md`

---

```python
@tool
def stop_autonomous_run(
    reason: str,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> Command:
```

**Returns**: Command with should_stop=True, goto=END

---

## 3.8 app/src/core/tools/phases/phase_tools.py

### Purpose

Maps phases to available tools and provides deduplicated tool list.

### Constants

```python
PHASE_TOOLS = {
    "research": [research_scan_literature, transition_phase, *all_base_tools],
    "hypothesize": [hypothesize_propose_mechanism, hypothesize_rank_mechanism, transition_phase, *all_base_tools],
    "test": [test_run_in_silico_trial, test_run_safety_screen, transition_phase, *all_base_tools],
    "synthesize": [synthesize_generate_candidate_summary, synthesize_define_next_steps, stop_autonomous_run, transition_phase, *all_base_tools],
}
```

### Functions

```python
def get_all_phase_tools() -> list:
    """Return a de-duplicated list of all tools across phases."""
```

---

## 3.9 Phase-Specific Tools

### Research Phase

```python
@tool
def research_scan_literature(
    query: str,
    max_results: int,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    # Queries arXiv API, returns JSON list of papers
    # Uses send_results() to handle truncation
```

```python
@tool
def fetch_paper_from_link(
    link: str,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    # Fetches PDF via Jina AI markdown extraction
    # Uses get_markdown() helper
```

### Hypothesize Phase

```python
@tool
def hypothesize_propose_mechanism(runtime) -> str:
    # Returns placeholder hypothesis string

@tool
def hypothesize_rank_mechanism(runtime) -> str:
    # Returns placeholder plausibility score via _shared.plausibility()
```

### Test Phase

```python
@tool
def test_run_in_silico_trial(runtime) -> str:
    # Returns placeholder efficacy score

@tool
def test_run_safety_screen(runtime) -> str:
    # Returns placeholder safety score
```

### Synthesize Phase

```python
@tool
def synthesize_generate_candidate_summary(runtime) -> str:

@tool
def synthesize_define_next_steps(runtime) -> str:
```

---

## 3.10 app/src/core/tools/base_tools.py

### Base Tools (always available)

```python
@tool
def read_file(path, all=False, start=None, finish=None) -> str:

@tool
def write_file(path, content) -> str:

@tool
def modify_file(path, target, replacement, all_instances=False) -> str:

@tool
def get_file_length(path) -> int:

@tool
def list_dir(path) -> str:
```

---

## 3.11 app/src/core/middlewares/

### Phase Middleware (phase_middleware.py)

```python
def create_phase_configuration_middleware(
    base_system_prompt: str,
    phase_instructions: dict[str, str],
    phase_tools: dict[str, list],
) -> ModelMiddleware:
```

**What it does**:

- Reads current_phase from request.state
- Validates phase is in PHASES
- Injects phase-specific system prompt with:
    - Current phase name
    - Allowed next phases (from PHASE_TRANSITIONS)
    - Available tools for this phase
    - Phase instructions from prompts
    - Transition policy instructions
- Scopes tools to current phase only
- Has retry logic: if model returns invalid tool name format, retries once with stricter guidance

### Agent Middleware (agent_middleware.py)

```python
def handle_tool_errors(request, handler) -> ToolMessage:
    # Catches all tool exceptions, returns formatted error as ToolMessage

def create_tool_logger_middleware(agent_id) -> ToolMiddleware:
    # Logs tool invocations with timing, truncates args/results
    # Special handling for tool error results (logs as warning)
```

---

## 3.12 app/src/llm_gateway/

### Factory (providers/factory.py)

```python
def get_provider(id=None, model_name=None, temperature=1) -> ChatOpenAI:
    # Returns ChatOpenAI client pointed at litellm proxy
    # Uses settings.litellm_base_url, settings.litellm_api_key
    # Sets X-Agent-ID header if id provided
    # max_retries=3
```

### LLM (providers/llm.py)

```python
@lru_cache
def get_model() -> ChatOpenAI:
    # Cached default provider

def call_model(prompt: str) -> str:
    # Invokes model, returns stripped content
    # Used by get_context_summary() during phase transitions
```

---

## 3.13 app/src/utils/

### Settings (settings.py)

```python
@lru_cache
def get_settings() -> Settings:
    # Singleton settings instance
    # Loads from .env file
```

### Logger (logger.py)

```python
class Logger:
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        # Creates logger with console + file handlers
        # Install global exception hooks on first call
        # Writes to .cache/logs/{YYYY-MM-DD}.log
        # Full tracebacks to .cache/logs/{YYYY-MM-DD}-error.log
```

### Prompt Utils (prompt_utils.py)

```python
def truncate_error_message(error_message: str, max_length: int = 1000) -> str:
```

---

## 3.14 app/prompts/prompts.py

### Purpose

Loads prompt templates from markdown files.

```python
BASE_SYSTEM_PROMPT = ""  # from markdown/base_system.md
RESEARCH_SYSTEM_PROMPT = ""  # from markdown/phases/research_system.md
HYPOTHESIZE_SYSTEM_PROMPT = ""  # from markdown/phases/hypothesize_system.md
TEST_SYSTEM_PROMPT = ""  # from markdown/phases/test_system.md
SYNTHESIZE_SYSTEM_PROMPT = ""  # from markdown/phases/synthesize_system.md
CONTEXT_SUMMARY_PROMPT = ""  # from markdown/context_summary.md

PHASE_INSTRUCTIONS = {
    "research": RESEARCH_SYSTEM_PROMPT,
    "hypothesize": HYPOTHESIZE_SYSTEM_PROMPT,
    "test": TEST_SYSTEM_PROMPT,
    "synthesize": SYNTHESIZE_SYSTEM_PROMPT,
}
```
