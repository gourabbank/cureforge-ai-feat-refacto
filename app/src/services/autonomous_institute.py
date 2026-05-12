from concurrent.futures import ThreadPoolExecutor, as_completed

from app.src.core.agent import create_base_agent
from app.src.core.loop import run_autonomous_research_loop


class AutonomousResearchInstitute:
    """Run multiple independent disease agents in sync or async mode."""

    def __init__(
        self,
        model_name: str,
        max_workers: int = 4,
    ):
        self.model_name = model_name
        self.max_workers = max_workers

    def _run_one(self, disease_name: str, max_iterations: int) -> dict:
        agent_id = f"agent_{disease_name.lower().replace(' ', '_')}"
        agent = create_base_agent(
            id=agent_id,
            disease_name=disease_name,
            model_name=self.model_name,
        )
        return run_autonomous_research_loop(
            agent=agent,
            agent_id=agent_id,
            disease_name=disease_name,
            max_iterations=max_iterations,
        )

    def run_sync(self, disease_names: list[str], max_iterations: int = 3) -> dict:
        """Run all disease agents sequentially."""
        results = {}
        for disease_name in disease_names:
            results[disease_name] = self._run_one(
                disease_name=disease_name,
                max_iterations=max_iterations,
            )
        return results

    def run_async(self, disease_names: list[str], max_iterations: int = 3) -> dict:
        """Run all disease agents concurrently."""
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    self._run_one, disease_name, max_iterations
                ): disease_name
                for disease_name in disease_names
            }
            for future in as_completed(futures):
                disease_name = futures[future]
                results[disease_name] = future.result()

        return results
