import sqlite3
from pathlib import Path

from langchain.agents import create_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from app.prompts.prompts import BASE_SYSTEM_PROMPT, PHASE_INSTRUCTIONS
from app.src.core.middlewares.agent_middleware import (
    create_tool_logger_middleware,
    handle_tool_errors,
)
from app.src.core.middlewares.phase_middleware import (
    create_phase_configuration_middleware,
)
from app.src.llm_gateway.providers.factory import get_provider
from app.src.core.state import ResearchAgentState
from app.src.core.tools.phases.phase_tools import PHASE_TOOLS, get_all_phase_tools
from app.src.utils.logger import get_logger
from app.src.utils.metrics import get_metrics
from app.src.utils.settings import get_settings


logger = get_logger(__name__)
settings = get_settings()


def create_base_agent(
    id: str,
    disease_name: str,
    model_name: str = None,
    tools: list = None,
    system_prompt: str = None,
    temperature: float = 1,
) -> CompiledStateGraph:
    """Create a phase-aware base research agent for a single disease."""
    resolved_model_name = model_name or settings.model_name

    llm = get_provider(
        id=id,
        model_name=resolved_model_name,
        temperature=temperature,
    )

    db_dir = Path(settings.default_paths["agent_dbs"])
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / f"agent_{id}_memory.db"

    sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
    checkpointer = SqliteSaver(sqlite_conn)

    base_prompt = system_prompt or BASE_SYSTEM_PROMPT
    all_tools = tools if tools is not None else get_all_phase_tools()

    phase_middleware = create_phase_configuration_middleware(
        base_system_prompt=base_prompt,
        phase_instructions=PHASE_INSTRUCTIONS,
        phase_tools=PHASE_TOOLS,
    )

    agent = create_agent(
        name=id,
        model=llm,
        tools=all_tools,
        system_prompt=base_prompt,
        state_schema=ResearchAgentState,
        checkpointer=checkpointer,
        middleware=[
            phase_middleware,
            handle_tool_errors,
            create_tool_logger_middleware(id),
        ],
    )

    get_metrics().increment("agent_created_total")
    logger.info(
        f"[{id}] Agent created for disease={disease_name} | model={resolved_model_name}"
    )
    return agent