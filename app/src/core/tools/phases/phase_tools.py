from app.src.core.tools.phases.control import stop_autonomous_run, transition_phase
from app.src.core.tools.phases.hypothesize_tools.tools import (
    hypothesize_propose_mechanism,
    hypothesize_rank_mechanism,
)
from app.src.core.tools.phases.research_tools.tools import (
    research_scan_literature,
)
from app.src.core.tools.phases.synthesize_tools.tools import (
    synthesize_define_next_steps,
    synthesize_generate_candidate_summary,
)
from app.src.core.tools.phases.test_tools.tools import (
    test_run_in_silico_trial,
    test_run_safety_screen,
)
from app.src.core.tools.base_tools import all_base_tools


PHASE_TOOLS = {
    "research": [
        research_scan_literature,
        transition_phase,
        *all_base_tools,
    ],
    "hypothesize": [
        hypothesize_propose_mechanism,
        hypothesize_rank_mechanism,
        transition_phase,
        *all_base_tools,
    ],
    "test": [
        test_run_in_silico_trial,
        test_run_safety_screen,
        transition_phase,
        *all_base_tools,
    ],
    "synthesize": [
        synthesize_generate_candidate_summary,
        synthesize_define_next_steps,
        stop_autonomous_run,
        transition_phase,
        *all_base_tools,
    ],
}


def get_all_phase_tools() -> list:
    """Return a de-duplicated list of all tools across phases."""
    tool_names = set()
    flattened_tools = []
    for phase_tools in PHASE_TOOLS.values():
        for tool_obj in phase_tools:
            if tool_obj.name in tool_names:
                continue
            tool_names.add(tool_obj.name)
            flattened_tools.append(tool_obj)
    return flattened_tools
