from langchain.agents import AgentState
from pydantic import Field


class ResearchAgentState(AgentState):
    """State for autonomous disease-focused research agents."""

    agent_id: str
    disease_name: str
    current_phase: str = "research"
    phase_history: list[str] = Field(default_factory=lambda: ["research"])

    phase_cycles: dict[str, int] = Field(default_factory=dict)

    transition_reason: str | None = None
    success_definition: str | None = None

    should_stop: bool = False
    cycle_count: int = 0

    # findings: list[str] = Field(default_factory=list)
    # hypothesis_bank: list[str] = Field(default_factory=list)
