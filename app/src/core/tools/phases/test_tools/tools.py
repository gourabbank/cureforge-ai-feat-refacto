from langchain.tools import ToolRuntime, tool

from app.src.core.state import ResearchAgentState
from app.src.core.tools.phases._shared import (
    disease_name,
    efficacy,
    plausibility,
    safety,
)


@tool
def test_run_in_silico_trial(
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Run simulated efficacy test for hypothesis. Returns "efficacy=X, confidence=Y".

    Use in test phase after hypothesize_rank_mechanism.
    Pair with test_run_safety_screen for full evaluation.

    Args: None.
    """
    disease = disease_name(runtime)
    return (
        f"In-silico trial for {disease}: efficacy={efficacy()}, "
        f"confidence={plausibility()}"
    )


@tool
def test_run_safety_screen(
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Run simulated safety screen for hypothesis. Returns "Safety screen complete: safety_index=X".

    Use in test phase to assess safety profile.
    Pair with test_run_in_silico_trial for full evaluation.

    Args: None.
    """
    return f"Safety screen complete: safety_index={safety()}"
