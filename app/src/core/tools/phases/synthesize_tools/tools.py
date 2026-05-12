from langchain.tools import ToolRuntime, tool

from app.src.core.state import ResearchAgentState
from app.src.core.tools.phases._shared import disease_name, plausibility


@tool
def synthesize_generate_candidate_summary(
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Generate summary for candidate intervention. Returns summary string.

    Use in synthesize phase after test_run_in_silico_trial and test_run_safety_screen.
    Provides benefit-risk estimate.

    Args: None.
    """
    disease = disease_name(runtime)
    return (
        f"Synthesis summary for {disease}: prioritized intervention path with "
        f"benefit-risk estimate={plausibility()}"
    )


@tool
def synthesize_define_next_steps(
    runtime: ToolRuntime[None, ResearchAgentState],
) -> str:
    """Return next-step recommendations. Returns string with action items.

    Use after synthesize_generate_candidate_summary to close cycle.
    Typically: replicate in expanded cohort or design wet-lab protocol.

    Args: None.
    """
    return "Next steps: replicate in expanded simulation cohort and design wet-lab protocol."
