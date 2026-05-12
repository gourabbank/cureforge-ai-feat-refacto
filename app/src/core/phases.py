import time

from app.src.utils.metrics import get_metrics


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


def record_phase_transition(current_phase: str, next_phase: str):
    """Call this whenever a phase transition occurs."""
    get_metrics().increment(
        "phase_transitions_total",
        {"phase_from": current_phase, "phase_to": next_phase},
    )


class PhaseTimer:
    """Context manager to time a phase and record histogram."""
    def __init__(self, phase: str):
        self.phase = phase
        self._start = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *_):
        get_metrics().histogram(
            "phase_duration_seconds",
            {"phase": self.phase},
            time.perf_counter() - self._start,
        )