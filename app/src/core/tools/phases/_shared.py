import uuid
import requests
from datetime import datetime
from random import Random
from pathlib import Path

import requests
from langchain.tools import ToolRuntime

from app.src.core.state import ResearchAgentState
from app.src.llm_gateway.providers.llm import call_model
from app.prompts.prompts import CONTEXT_SUMMARY_PROMPT
from app.src.utils.logger import get_logger
from app.src.utils.settings import get_settings


settings = get_settings()
logger = get_logger(__name__)
_RNG = Random(42)


def disease_name(runtime: ToolRuntime[None, ResearchAgentState]) -> str:
    """Return the active disease name from state."""
    return runtime.state.get("disease_name", "unknown disease")


def plausibility() -> float:
    """Return a deterministic pseudo-random plausibility score."""
    return round(_RNG.uniform(0.51, 0.94), 2)


def efficacy() -> float:
    """Return a deterministic pseudo-random efficacy score."""
    return round(_RNG.uniform(0.35, 0.89), 2)


def safety() -> float:
    """Return a deterministic pseudo-random safety score."""
    return round(_RNG.uniform(0.62, 0.97), 2)


def timestamp_utc() -> str:
    """Return an ISO8601 UTC timestamp string."""
    return f"{datetime.now(datetime.timezone.utc)}Z"


def send_results(
    results: str,
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Send results or save them to a file, depending on the length."""
    try:
        agent_id = runtime.state.get("agent_id", "unknown_agent")
        results_dir = Path(settings.default_paths["playground"]) / agent_id
        results_dir.mkdir(parents=True, exist_ok=True)
        if len(results) <= settings.max_results_length:
            return results
        else:
            tmp_path = results_dir / f"{str(uuid.uuid4())[:4]}" / "content.txt"
            tmp_path.parent.mkdir(parents=True, exist_ok=True)
            with open(tmp_path, "w") as f:
                f.write(results)
            return (
                f"Output saved to `{tmp_path}`. Content length: {len(results)} characters, "
                "Make sure to retrieve it in chunks if it's too large to read at once."
            )
    except Exception as e:
        return f"Error saving results, please try again. Details: {str(e)}"


def get_markdown(link: str, runtime: ToolRuntime[None, ResearchAgentState]) -> str:
    """Fetch markdown content from a URL."""
    jina_url = "https://r.jina.ai/"
    url = f"{jina_url}{link}"
    headers = {"Authorization": f"Bearer {settings.jina_api_key}"}
    try:
        response = requests.get(url, headers=headers).text
    except Exception as e:
        response = (
            f"Error fetching markdown content, please try again. Details: {str(e)}"
        )
    return send_results(response, runtime)


def convert_history_to_markdown(runtime: ToolRuntime[None, ResearchAgentState]) -> str:
    """
    Convert the list of BaseMessage objects in state['messages'] into a markdown string.
    Each message is rendered as a blockquote with its type and content.
    """
    messages = runtime.state.get("messages", [])
    if not messages:
        return "_No messages in history._"

    lines = ["## Conversation History\n"]
    for msg in messages:
        if hasattr(msg, "type"):
            msg_type = msg.type
        elif isinstance(msg, dict) and "type" in msg:
            msg_type = msg["type"]
        else:
            msg_type = "message"

        if hasattr(msg, "content"):
            content = msg.content
        elif isinstance(msg, dict) and "content" in msg:
            content = msg["content"]
        else:
            content = str(msg)

        if not isinstance(content, str):
            content = str(content)

        content = content.strip()
        if not content:
            continue

        lines.append(f"> **{msg_type}**: {content}\n")

    return "\n".join(lines)


def get_context_summary(full_context_markdown: str) -> str:
    """Use the LLM to summarize the context for better decision making."""
    full_prompt = f"{CONTEXT_SUMMARY_PROMPT}\n\n{full_context_markdown}"
    logger.info("Generating context summary for phase transition...")
    summary = call_model(full_prompt)
    return summary
