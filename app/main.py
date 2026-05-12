from app.src.services.autonomous_institute import AutonomousResearchInstitute
from app.src.utils.settings import get_settings


def run_demo(async_mode: bool = False, max_iterations: int = 50) -> dict:
    """Run a demo autonomous institute session with seeded diseases."""
    settings = get_settings()
    model_name = settings.model_name

    institute = AutonomousResearchInstitute(
        model_name=model_name,
        max_workers=3,
    )
    seeded_diseases = ["alzheimer", "diabetes", "cancer"]

    if async_mode:
        return institute.run_async(seeded_diseases, max_iterations=max_iterations)
    return institute.run_sync(seeded_diseases, max_iterations=max_iterations)


if __name__ == "__main__":
    output = run_demo(async_mode=False, max_iterations=3)
    print({disease: state.get("current_phase") for disease, state in output.items()})
