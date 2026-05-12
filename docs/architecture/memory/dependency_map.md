# CureForge Dependency Map

## Module Dependencies

```
app/
├── main.py
│   └── imports: AutonomousResearchInstitute, get_settings
│
├── prompts/
│   └── prompts.py
│       └── imports: pathlib.Path (reads markdown/)
│
└── src/
    ├── core/
    │   ├── agent.py
    │   │   └── imports:
    │   │       ├── langchain.agents (create_agent)
    │   │       ├── langgraph (CompiledStateGraph, SqliteSaver)
    │   │       ├── app.prompts.prompts
    │   │       ├── app.src.core.middlewares
    │   │       ├── app.src.llm_gateway.providers.factory
    │   │       ├── app.src.core.state
    │   │       ├── app.src.core.tools.phases.phase_tools
    │   │       ├── app.src.utils.logger
    │   │       └── app.src.utils.settings
    │   │
    │   ├── loop.py
    │   │   └── imports:
    │   │       ├── uuid
    │   │       ├── langgraph (CompiledStateGraph)
    │   │       └── app.src.utils.logger
    │   │
    │   ├── phases.py
    │   │   └── exports: PHASES, PHASE_TRANSITIONS, is_valid_transition
    │   │
    │   ├── state.py
    │   │   └── imports: langchain.agents.AgentState, pydantic.Field
    │   │
    │   ├── middlewares/
    │   │   ├── agent_middleware.py
    │   │   │   └── imports: json, time, langchain, app.src.utils
    │   │   │
    │   │   └── phase_middleware.py
    │   │       └── imports: typing, langchain, app.src.core.phases, app.src.utils.logger
    │   │
    │   └── tools/
    │       ├── base_tools.py
    │       │   └── imports: langchain_core.tools, os
    │       │
    │       ├── phases/
    │       │   ├── control.py
    │       │   │   └── imports:
    │       │   │       ├── pathlib
    │       │   │       ├── langchain.messages, langchain.tools
    │       │   │       ├── langgraph (Command, END, REMOVE_ALL_MESSAGES)
    │       │   │       ├── app.src.core.phases
    │       │   │       ├── app.src.core.state
    │       │   │       ├── app.src.utils.logger
    │       │   │       ├── app.src.core.tools.phases._shared
    │       │   │       └── app.src.utils.settings
    │       │   │
    │       │   ├── phase_tools.py
    │       │   │   └── imports: all phase tool modules
    │       │   │
    │       │   ├── research_tools/tools.py
    │       │   │   └── imports: json, langchain.tools, app.src.core.state, _shared, feedparser
    │       │   │
    │       │   ├── hypothesize_tools/tools.py
    │       │   │   └── imports: langchain.tools, app.src.core.state, _shared
    │       │   │
    │       │   ├── test_tools/tools.py
    │       │   │   └── imports: langchain.tools, app.src.core.state, _shared
    │       │   │
    │       │   ├── synthesize_tools/tools.py
    │       │   │   └── imports: langchain.tools, app.src.core.state, _shared
    │       │   │
    │       │   └── _shared.py
    │       │       └── imports:
    │       │           ├── uuid
    │       │           ├── requests
    │       │           ├── datetime
    │       │           ├── random
    │       │           ├── pathlib
    │       │           ├── langchain.tools
    │       │           ├── app.src.core.state
    │       │           ├── app.src.llm_gateway.providers.llm
    │       │           ├── app.prompts.prompts
    │       │           ├── app.src.utils.logger
    │       │           └── app.src.utils.settings
    │       │
    │       └── external_apis/
    │           └── (empty __init__.py)
    │
    ├── llm_gateway/
    │   ├── __init__.py (empty)
    │   │
    │   └── providers/
    │       ├── __init__.py (empty)
    │       │
    │       ├── factory.py
    │       │   └── imports: langchain_openai.ChatOpenAI, app.src.utils.settings
    │       │
    │       └── llm.py
    │           └── imports: functools, app.src.llm_gateway.providers.factory, app.src.utils.logger
    │
    ├── services/
    │   └── autonomous_institute.py
    │       └── imports: concurrent.futures, app.src.core.agent, app.src.core.loop
    │
    └── utils/
        ├── settings.py
        │   └── imports: functools, pydantic_settings
        │
        ├── logger.py
        │   └── imports: logging, sys, threading, traceback, uuid, pathlib, datetime, os
        │
        └── prompt_utils.py
            └── (no imports)
```

## External Service Dependencies

| Service   | URL                        | Used By                  | Purpose           |
| --------- | -------------------------- | ------------------------ | ----------------- |
| litellm   | litellm:4000               | get_provider()           | LLM proxy gateway |
| redis     | redis:6379                 | litellm config           | Rate limiting     |
| arXiv API | export.arxiv.org           | research_scan_literature | Paper search      |
| Jina AI   | r.jina.ai                  | get_markdown()           | PDF to markdown   |
| Ollama    | host.docker.internal:11434 | litellm config           | Local models      |

## File System Dependencies

| Path                          | Created By          | Used By                  |
| ----------------------------- | ------------------- | ------------------------ |
| .cache/agent_dbs/             | create_base_agent() | SqliteSaver checkpointer |
| .cache/logs/                  | Logger.get_logger() | All logging              |
| .cache/playground/{agent_id}/ | tool outputs        | send_results()           |
| .input/                       | Docker volume       | External input           |

## Dependency Graph

```
main.py
    │
    ├── AutonomousResearchInstitute
    │   │
    │   ├── create_base_agent()
    │   │   │
    │   │   ├── get_provider() → ChatOpenAI → litellm:4000
    │   │   │
    │   │   ├── SqliteSaver → .cache/agent_dbs/*.db
    │   │   │
    │   │   ├── PHASE_TOOLS
    │   │   │   │
    │   │   │   ├── base_tools.py
    │   │   │   │
    │   │   │   ├── phase_tools.py → control.py
    │   │   │   │
    │   │   │   └── research_tools/ → hypothesize/ → test/ → synthesize/
    │   │   │
    │   │   ├── prompts.py → *.md files
    │   │   │
    │   │   ├── middlewares/
    │   │   │   │
    │   │   │   ├── phase_middleware.py
    │   │   │   │
    │   │   │   └── agent_middleware.py
    │   │   │
    │   │   └── settings.py
    │   │
    │   └── run_autonomous_research_loop()
    │       │
    │       └── agent.invoke()
    │           │
    │           ├── LLM (litellm → external provider)
    │           │
    │           └── Tool calls
    │               │
    │               ├── arXiv API
    │               │
    │               ├── Jina AI
    │               │
    │               ├── file I/O
    │               │
    │               └── _shared.py → call_model()
    │                   │
    │                   └── get_provider() → litellm
```

## Critical Dependency Chains

### LLM calls

```
get_settings() [singleton]
    ↓
get_provider() → ChatOpenAI [cached by factory]
    ↓
litellm:4000 [Docker service]
    ↓
[external: Ollama/Groq/Cerebras/Gemini]
```

### Agent state persistence

```
create_base_agent()
    ↓
SqliteSaver(sqlite3.connect(...))
    ↓
.cache/agent_dbs/agent_{id}_memory.db
    ↓
[disk I/O]
```

### Tool execution

```
agent.invoke()
    ↓
phase_middleware (scopes tools)
    ↓
Tool validation (tool name format)
    ↓
handle_tool_errors (catches exceptions)
    ↓
log_tool_calls_with_agent_id (logs)
    ↓
Tool function executes
    ↓
[SIDE EFFECTS: file I/O, HTTP calls, state updates]
```

### Phase transition

```
transition_phase tool
    ↓
is_valid_transition() [validates]
    ↓
convert_history_to_markdown()
    ↓
get_context_summary() → call_model()
    ↓
get_provider() → litellm → LLM
    ↓
summary → file (.cache/playground/.../summaries/)
    ↓
Command(update=...)
    ↓
[removes messages, updates phase]
```
