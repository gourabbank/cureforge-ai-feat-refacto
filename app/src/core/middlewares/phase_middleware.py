from typing import Callable

from langchain.agents.middleware import ModelRequest, ModelResponse, wrap_model_call

from app.src.core.phases import PHASES, PHASE_TRANSITIONS
from app.src.utils.logger import get_logger


logger = get_logger(__name__)


def create_phase_configuration_middleware(
    base_system_prompt: str,
    phase_instructions: dict[str, str],
    phase_tools: dict[str, list],
):
    """Create middleware that injects phase-specific instructions and tool scope."""

    @wrap_model_call
    def apply_phase_configuration(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        current_phase = request.state.get("current_phase")
        if current_phase not in PHASES:
            raise ValueError(
                f"Invalid current phase '{current_phase}'. Must be one of: {', '.join(PHASES)}"
            )

        allowed_next = ", ".join(PHASE_TRANSITIONS.get(current_phase, ()))
        phase_text = phase_instructions.get(current_phase, "")
        tools_for_phase = phase_tools.get(current_phase, [])
        tool_names = [tool.name for tool in tools_for_phase]
        tool_list = ", ".join(tool_names)

        scoped_prompt = (
            f"{base_system_prompt}\n\n"
            f"Current active phase: {current_phase}\n"
            f"Allowed next phases: {allowed_next}\n\n"
            f"Available tools for this phase: {tool_list}\n\n"
            f"Phase instructions:\n{phase_text}\n\n"
            "Transition policy:\n"
            "- Use transition_phase when you are ready to move phases.\n"
            "- Include rationale and measurable success definition.\n"
            "- Use only currently available tools.\n"
            "Tool-call formatting rule:\n"
            "- Tool names must be copied exactly from the available tools list.\n"
            "- Do not add extra punctuation characters to tool names (for example: }, ], )."
        )

        updated = request.override(system_prompt=scoped_prompt, tools=tools_for_phase)

        try:
            return handler(updated)
        except Exception as exc:
            message = str(exc)
            if "tool call validation failed" not in message:
                raise
            if "was not in request.tools" not in message:
                raise

            logger.warning(
                "Model returned an invalid tool name format; retrying once with stricter guidance."
            )

            retry_prompt = (
                f"{scoped_prompt}\n\n"
                "Retry instruction:\n"
                "- Call exactly one tool using an exact tool name from the available list.\n"
                "- Do not wrap tool names with symbols.\n"
                "- If unsure, call transition_phase with a rationale."
            )
            retry_request = request.override(
                system_prompt=retry_prompt,
                tools=tools_for_phase,
            )
            return handler(retry_request)

    return apply_phase_configuration
