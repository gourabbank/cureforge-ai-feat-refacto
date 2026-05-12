# CureForge Inferred Rules & Implicit Contracts

## 5.1 Behaviors Enforced By Code

### Phase Transition Validation

The system enforces strict phase transition rules via is_valid_transition():

```python
PHASE_TRANSITIONS = {
    "research": ("hypothesize",),         # Only forward
    "hypothesize": ("research", "test"),  # Backward or forward
    "test": ("research", "synthesize"),   # Backward or forward
    "synthesize": ("research",),          # Only backward (restart)
}
```

**Implicit rule**: No direct transitions like research -> test, research -> synthesize, hypothesize -> synthesize. Must follow the graph.

### Tool Scope Enforcement

Phase middleware scopes available tools to current phase only. Tools from other phases raise errors if called.

**Implicit rule**: Each phase only has access to its defined tools. Tools from future phases are unavailable.

### Phase Instruction Injection

Every LLM call gets phase-specific instructions prepended to system prompt via phase_middleware.

### Tool Name Formatting

Phase middleware has retry logic for invalid tool name format (e.g., tool names with extra punctuation):

```python
# If model returns invalid tool name format, retries once with:
"- Call exactly one tool using an exact tool name from the available list.\n"
"- Do not wrap tool names with symbols.\n"
```

**Implicit rule**: Tool names must match exactly, no quotes, brackets, or punctuation.

---

## 5.2 Ordering Dependencies

### Agent Creation Must Precede Loop

create_base_agent() must be called before run_autonomous_research_loop(). Agent instance is stateful.

### Initial Phase Is Always "research"

The system always starts at "research" phase. This is hardcoded in loop.py:

```python
"current_phase": "research"  # initial state
```

### Phase History Is Append-Only

phase_history is appended on each transition, never modified or reordered.

```python
history.append(normalized_next)  # control.py:70
```

### Message History Cleared On Transition

transition_phase explicitly removes all previous messages:

```python
"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES), ...]
```

Reason: Prevent context window pollution from accumulated messages.

---

## 5.3 Timing Assumptions

### Loop Iteration Timing

Each iteration in run_autonomous_research_loop():

1. Checks should_stop after invoke
2. Then invokes again if not stopped

This means iteration count = number of invokes AFTER initial invoke.

Example: max_iterations=3 means:

- Invoke 1 (initial): "Begin..."
- Invoke 2: "Continue..." (iteration 1)
- Invoke 3: "Continue..." (iteration 2)
- Invoke 4: "Continue..." (iteration 3)
- Check should_stop, exit

So number of user prompts = 3 + initial = 4 invokes for 3 iterations.

### Thread ID Persistence

thread_id (SQLite thread) persists state across invokes. If None, generated via uuid4().

### Max Results Length Threshold

If tool output exceeds `settings.max_results_length` (10000 chars), redirects to file:

```python
if len(results) <= settings.max_results_length:
    return results
else:
    # Write to file, return path reference
```

---

## 5.4 Format Expectations

### Agent ID Format

Agent IDs must be URL-safe lowercase with underscores:

```python
agent_id = f"agent_{disease_name.lower().replace(' ', '_')}"
```

- Input: "Alzheimer Disease" -> agent_alzheimer_disease
- Input: "COVID-19" -> agent_covid-19 (dash preserved from lower())

### Database Path Format

SQLite DBs stored at:

```
.cache/agent_dbs/agent_{id}_memory.db
```

### Log File Naming

Logs use ISO date format: `{YYYY-MM-DD}.log`

---

## 5.5 Fallback Chains

### Provider Resolution

Model name resolution (agent.py:36):

```python
resolved_model_name = model_name or settings.model_name
```

- First checks function parameter
- Falls back to settings.model_name
- Must not be None otherwise ChatOpenAI fails

### Settings Singleton

get_settings() is cached via @lru_cache - one Settings instance per process.

### LLM Provider Caching

get_model() in llm.py uses @lru_cache - one ChatOpenAI instance for context summarization.

### Large Output Handling

Two-step fallback:

1. If content <= max_results_length: return inline
2. Else: write to file, return path

Error handling: If write fails, return inline error message.

---

## 5.6 Failure Behavior

### Tool Error Handling

handle_tool_errors middleware catches all tool exceptions:

```python
try:
    return handler(request)
except Exception as e:
    return ToolMessage(content=f"Tool error:\n({truncate_error_message(str(e))})")
```

Does not re-raise - returns error as ToolMessage to agent.

### Loop Error Handling

Errors in loop iteration are caught and logged, loop continues:

```python
try:
    agent.invoke(...)
except Exception as e:
    logger.error("Unhandled error during agent invocation...")
    # Continue to next iteration or exit
```

### Partial State On Error

If loop encounters error returns dict with error key:

```python
return {
    "error": str(e),
    "_run_metadata": {...}
}
```

### Database Creation Behavior

If agent_dbs directory missing, created on first agent:

```python
db_dir.mkdir(parents=True, exist_ok=True)
```

---

## 5.7 Error Logging

### Uncaught Exceptions

Global exception hooks in Logger class:

- sys.excepthook for main thread
- threading.excepthook for background threads

Logs go to both stdout and `.cache/logs/{YYYY-MM-DD}-error.log`.

### Error ID Generation

Every uncaught exception gets error_id = uuid4().hex[:12]:

```python
error_id = uuid4().hex[:12]
# Example: abc123def456
```

Used to correlate console output with full traceback file.

---

## 5.8 Implicit Contracts For Developers

### Model Must Support Function Calling

All litellm models marked with:

```yaml
model_info:
    supports_function_calling: true
```

**Implicit**: Using a model that doesn't support function calling will cause tool calls to fail.

### Thread Safety

SQLite checkpointer has check_same_thread=False:

```python
sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
```

**Implicit**: Safe for ThreadPoolExecutor in run_async mode.

### Redis Must Be Available

compose.yml shows cureforge depends on redis healthcheck.

**Implicit**: Without redis, litellm cannot manage rate limits.

### Tool Names Are Unique

get_all_phase_tools() deduplicates by tool.name:

```python
if tool_obj.name in tool_names:
    continue
tool_names.add(tool_obj.name)
```

**Implicit**: Adding a tool with duplicate name is ignored.

### No Authentication On First LLM Call

litellm uses master_key as auth:

```yaml
litellm_settings:
    master_key: os.environ/LITELLM_API_KEY
```

**Implicit**: No per-request auth tokens needed - all requests authenticated via master_key.

### State Schema Is Strict

ResearchAgentState has no extra fields allowed (pydantic with no extra config):

**Implicit**: Any unknown field in state will raise validation error.

---

## 5.9 What Code Does Not Say

### Why Four Phases?

The system uses research/hypothesize/test/synthesize pipeline but codebase provides no documentation of why these specific phases or if they're configurable.

### Why Seeded Random 42?

`_RNG = Random(42)` in \_shared.py - fixed seed ensures reproducibility but no comment explaining the choice.

### Why Message Removal?

`RemoveMessage(id=REMOVE_ALL_MESSAGES)` clears history on transition - likely to prevent context window issues but not explicitly documented.

### Why Phase Summaries?

Context summaries saved to `.cache/playground/{agent_id}/summaries/` - appears to capture decision context but not documented what happens with them.

### Why No Input Validation?

disease_name from user input becomes agent_id without sanitization (beyond lower() and space replacement). Special characters in agent_id could cause path issues.

### Why Jina Unauthenticated Fallback?

get_markdown() passes Jina auth header but catches exception and retries without auth:

```python
headers = {"Authorization": f"Bearer {settings.jina_api_key}"}
response = requests.get(url, headers=headers).text
except Exception:
    # Falls back
    response = requests.get(url).text
```

Not documented why unauthenticated fallback exists.
