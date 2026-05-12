import json
from time import perf_counter

from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage

from langgraph.types import Command

from app.src.utils.prompt_utils import truncate_error_message
from app.src.utils.logger import get_logger


logger = get_logger(__name__)


def _truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate text to max_length and append '...' if it exceeds the limit."""
    text_str = str(text)
    truncated = (
        f"{text_str[:max_length]}..." if len(text_str) > max_length else text_str
    )
    truncated = truncated.replace("\n", "").replace("\r", "")
    return truncated


def _extract_tool_info(request) -> tuple[str, str, str]:
    """Safely extract tool name, id, and arguments from request across middleware API variants."""
    tool_call = getattr(request, "tool_call", None)

    if isinstance(tool_call, dict):
        tool_name = tool_call.get("name", "unknown_tool")
        tool_id = tool_call.get("id", "unknown_id")
        args_dict = tool_call.get("args", {})
    else:
        tool_name = getattr(request, "name", "unknown_tool")
        tool_id = getattr(request, "id", getattr(request, "tool_call_id", "unknown_id"))
        args_dict = getattr(request, "args", getattr(request, "tool_input", {}))

    try:
        args_str = json.dumps(args_dict, ensure_ascii=False, default=str)
    except Exception:
        args_str = str(args_dict)

    return tool_name, tool_id, args_str


@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution errors with custom messages."""
    try:
        return handler(request)
    except Exception as e:
        _, tool_id, _ = _extract_tool_info(request)
        return ToolMessage(
            content=f"Tool error:\n\n({truncate_error_message(str(e))})",
            tool_call_id=tool_id,
        )


def create_tool_logger_middleware(agent_id: str):
    """Create tool logging middleware bound to a specific agent id."""
    log_prefix = f"[{agent_id}]"

    @wrap_tool_call
    def log_tool_calls_with_agent_id(request, handler):
        tool_name, tool_id, args_str = _extract_tool_info(request)

        logger.info(
            f"{log_prefix} Tool call started: {tool_name} [{_truncate_string(tool_id)}] | Args: {_truncate_string(args_str)}"
        )

        start = perf_counter()
        try:
            result = handler(request)
            duration_ms = (perf_counter() - start) * 1000

            if isinstance(result, ToolMessage):
                content_str = str(result.content)
            elif isinstance(result, Command):
                content_str = str(result.update)
            else:
                content_str = str(result)

            res_trunc = _truncate_string(content_str)

            if isinstance(result, ToolMessage) and content_str.startswith(
                ("Error:", "Tool error:")
            ):
                logger.warning(
                    f"{log_prefix} Tool call returned error message: {tool_name} [{_truncate_string(tool_id)}] "
                    f"({duration_ms:.2f} ms) | Args: {_truncate_string(args_str)} | Result: {res_trunc}"
                )
                return result

            logger.info(
                f"{log_prefix} Tool call completed: {tool_name} [{_truncate_string(tool_id)}] "
                f"({duration_ms:.2f} ms) | Args: {_truncate_string(args_str)} | Result: {res_trunc}"
            )
            return result

        except Exception as e:
            duration_ms = (perf_counter() - start) * 1000
            err_trunc = _truncate_string(str(e))

            logger.exception(
                f"{log_prefix} Tool call failed: {tool_name} [{_truncate_string(tool_id)}] "
                f"({duration_ms:.2f} ms) | Args: {_truncate_string(args_str)} | Error: {err_trunc}"
            )
            raise

    return log_tool_calls_with_agent_id
