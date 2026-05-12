import time
from uuid import uuid4

from langgraph.graph.state import CompiledStateGraph

from app.src.utils.logger import get_logger
from app.src.utils.metrics import get_metrics


logger = get_logger(__name__)


def run_autonomous_research_loop(
    agent: CompiledStateGraph,
    agent_id: str,
    disease_name: str,
    max_iterations: int = 3,
    thread_id: str | None = None,
) -> dict:
    """Run an internal autonomous loop until stop signal or iteration cap."""
    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")

    m = get_metrics()
    resolved_thread_id = thread_id or str(uuid4())
    config = {"configurable": {"thread_id": resolved_thread_id}}
    loop_start = time.perf_counter()

    m.gauge("active_agents", value=(m.get_value("active_agents") or 0) + 1)

    try:
        try:
            agent.invoke(
                {
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"Begin autonomous cure research for {disease_name}. "
                                "Work through Research -> Hypothesize -> Test -> Synthesize. "
                                "Transition phases yourself when ready."
                            ),
                        }
                    ],
                    "agent_id": agent_id,
                    "disease_name": disease_name,
                    "current_phase": "research",
                    "phase_history": ["research"],
                    "phase_cycles": {"research": 0, "hypothesize": 0, "test": 0, "synthesize": 0},
                    "should_stop": False,
                    "cycle_count": 0,
                },
                config=config,
            )
        except Exception as e:
            m.increment("agent_errors_total")
            logger.error("Unahandled error during initial agent invocation: %s", str(e))

        iterations = 0
        while iterations < max_iterations:
            state_snapshot = agent.get_state(config)
            state = state_snapshot.values
            if state.get("should_stop", False):
                break

            iterations += 1
            m.increment("agent_iterations_total")
            current_phase = state.get("current_phase", "research")

            try:
                agent.invoke(
                    {
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    f"Continue autonomous work for {disease_name}. "
                                    f"Current phase is {current_phase}. "
                                    "Use your current phase tools. Transition if ready."
                                ),
                            }
                        ],
                        "cycle_count": iterations,
                    },
                    config=config,
                )
            except Exception as e:
                m.increment("agent_errors_total")
                logger.error(
                    "Unhandled error during agent invocation at iteration %d: %s",
                    iterations,
                    str(e),
                )

        final_state = agent.get_state(config).values
        final_state["_run_metadata"] = {
            "thread_id": resolved_thread_id,
            "iterations": iterations,
            "max_iterations": max_iterations,
            "stopped": final_state.get("should_stop", False),
        }
        return final_state

    except Exception as e:
        m.increment("agent_errors_total")
        return {
            "error": str(e),
            "_run_metadata": {
                "thread_id": resolved_thread_id,
                "iterations": max_iterations,
                "max_iterations": max_iterations,
                "stopped": True,
            },
        }
    finally:
        m.histogram("agent_runtime_seconds", value=time.perf_counter() - loop_start)
        m.gauge("active_agents", value=max(0, (m.get_value("active_agents") or 1) - 1))
        m.flush()