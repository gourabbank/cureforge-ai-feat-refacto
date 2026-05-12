from langchain.tools import ToolRuntime, tool

from app.src.core.state import ResearchAgentState
from app.src.core.tools.phases._shared import disease_name, plausibility


@tool
def hypothesize_propose_mechanism(
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Generate a candidate mechanism hypothesis for the disease.

    Use in hypothesize phase after reading research evidence.
    Pair with hypothesize_rank_mechanism to score confidence.

    Args: None.
    """
    disease = disease_name(runtime)
    return (
        f"Hypothesis candidate for {disease}: "
        f"targeting dysregulated signaling cluster could reduce disease activity."
    )


@tool
def hypothesize_rank_mechanism(
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Return confidence score for current hypothesis. Returns "Hypothesis rank score=X".

    Use after hypothesize_propose_mechanism to rank candidate.
    Higher score indicates stronger mechanism.

    Args: None.
    """
    return f"Hypothesis rank score={plausibility()} (higher is better)"
