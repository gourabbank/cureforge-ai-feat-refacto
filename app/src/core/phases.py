PHASES = (
    "research",
    "hypothesize",
    "test",
    "synthesize",
)


PHASE_TRANSITIONS = {
    "research": ("hypothesize",),
    "hypothesize": ("research", "test"),
    "test": ("research", "synthesize"),
    "synthesize": ("research",),
}


def is_valid_transition(current_phase: str, next_phase: str) -> bool:
    """Validate allowed phase transitions, including fallback loops."""
    return next_phase in PHASE_TRANSITIONS.get(current_phase, ())
