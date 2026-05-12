from pathlib import Path

from langchain_core.messages import RemoveMessage
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.graph import END
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.types import Command

from app.src.core.phases import PHASES, PHASE_TRANSITIONS, is_valid_transition
from app.src.core.state import ResearchAgentState
from app.src.utils.logger import get_logger
from app.src.core.tools.phases._shared import (
    convert_history_to_markdown,
    get_context_summary,
)
from app.src.utils.settings import get_settings


settings = get_settings()
logger = get_logger(__name__)


@tool
def transition_phase(
    next_phase: str,
    rationale: str,
    success_definition: str,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> Command:
    """Transition to next phase in pipeline. Returns Command to update state.

    Use when evidence supports moving forward or looping back.
    Not valid for invalid phase names or disallowed transitions (see phases.py).

    Args:
        next_phase: Target phase name: research, hypothesize, test, or synthesize (str).
        rationale: Why this transition is justified (str).
        success_definition: What success looks like in next phase (str).
    """
    agent_id = runtime.state.get("agent_id", "unknown_agent")
    current_phase = runtime.state.get("current_phase", "research")
    normalized_next = next_phase.strip().lower()

    if normalized_next not in PHASES:
        content = f"Invalid phase '{next_phase}'. Supported phases: {', '.join(PHASES)}"
        return Command(
            update={
                "messages": [
                    ToolMessage(content=content, tool_call_id=runtime.tool_call_id)
                ]
            }
        )

    if not is_valid_transition(current_phase, normalized_next):
        allowed = ", ".join(PHASE_TRANSITIONS.get(current_phase, ()))
        content = (
            f"Transition denied: {current_phase} -> {normalized_next}. "
            f"Allowed next phases: {allowed}"
        )
        return Command(
            update={
                "messages": [
                    ToolMessage(content=content, tool_call_id=runtime.tool_call_id)
                ]
            }
        )

    history = list(runtime.state.get("phase_history", []))
    history.append(normalized_next)

    # summarize context
    full_context_markdown = convert_history_to_markdown(runtime)

    # tmp_path = Path(settings.default_paths["playground"]) / agent_id / "tmp"
    # tmp_path.mkdir(parents=True, exist_ok=True)
    # with open(tmp_path / f"context.md", "a") as f:
    #     f.write(full_context_markdown + "\n\n---\n\n")

    summary_instruction = ""
    try:
        context_summary = get_context_summary(full_context_markdown)
        summary_path = (
            Path(settings.default_paths["playground"]) / agent_id / "summaries"
        )
        summary_path.mkdir(parents=True, exist_ok=True)

        if "phase_cycles" not in runtime.state:
            runtime.state["phase_cycles"] = {
                "research": 0,
                "hypothesize": 0,
                "test": 0,
                "synthesize": 0,
            }

        current_phase_cycle = runtime.state.get("phase_cycles", {}).get(
            current_phase, 0
        )

        runtime.state["phase_cycles"][current_phase] += 1

        summary_file_path = summary_path / f"{current_phase}_{current_phase_cycle}.md"
        summary_file_path.touch(exist_ok=True)

        with open(summary_file_path, "w") as f:
            f.write(context_summary)

        summary_instruction = (
            f"Context from previous phase summarized and saved to {summary_file_path}."
        )
    except Exception as e:
        logger.warning(
            f'[{agent_id}] Failed to summarize context from phase "{current_phase}" to "{normalized_next}": {e}'
        )
        import traceback

        traceback.print_exc()
        summary_instruction = "Context from previous phase truncated, please refer to the saved artifacts for details."

    content = (
        f"{summary_instruction} "
        f"Phase transition approved: {current_phase} -> {normalized_next}. "
        f"Rationale: {rationale}"
    )

    # logger.info(content)  # explicitly log the transition event

    return Command(
        update={
            "messages": [
                RemoveMessage(id=REMOVE_ALL_MESSAGES),
                ToolMessage(content=content, tool_call_id=runtime.tool_call_id),
            ],
            "current_phase": normalized_next,
            "phase_history": history,
            "transition_reason": rationale,
            "success_definition": success_definition,
        }
    )


@tool
def stop_autonomous_run(
    reason: str,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> Command:
    """End the current autonomous run. Returns Command reaching END.

    Use when task is complete, deadlocked, or user-interrupted.

    Args:
        reason: Why the run is stopping (str).
    """
    agent_id = runtime.state.get("agent_id", "unknown_agent")
    logger.info(f"[{agent_id}] stop_autonomous_run called")

    return Command(
        update={
            "messages": [
                ToolMessage(
                    content=f"Autonomous run stop requested: {reason}",
                    tool_call_id=runtime.tool_call_id,
                )
            ],
            "should_stop": True,
        },
        goto=END,
    )
