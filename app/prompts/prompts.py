from pathlib import Path


prompts_dir = Path(__file__).parent / "markdown"


BASE_SYSTEM_PROMPT = ""
with open(prompts_dir / "base_system.md", "r") as f:
    BASE_SYSTEM_PROMPT = f.read()


RESEARCH_SYSTEM_PROMPT = ""
HYPOTHESIZE_SYSTEM_PROMPT = ""
TEST_SYSTEM_PROMPT = ""
SYNTHESIZE_SYSTEM_PROMPT = ""


with open(prompts_dir / "phases" / "research_system.md", "r") as f:
    RESEARCH_SYSTEM_PROMPT = f.read()
with open(prompts_dir / "phases" / "hypothesize_system.md", "r") as f:
    HYPOTHESIZE_SYSTEM_PROMPT = f.read()
with open(prompts_dir / "phases" / "test_system.md", "r") as f:
    TEST_SYSTEM_PROMPT = f.read()
with open(prompts_dir / "phases" / "synthesize_system.md", "r") as f:
    SYNTHESIZE_SYSTEM_PROMPT = f.read()


PHASE_INSTRUCTIONS = {
    "research": RESEARCH_SYSTEM_PROMPT,
    "hypothesize": HYPOTHESIZE_SYSTEM_PROMPT,
    "test": TEST_SYSTEM_PROMPT,
    "synthesize": SYNTHESIZE_SYSTEM_PROMPT,
}


CONTEXT_SUMMARY_PROMPT = ""
with open(prompts_dir / "context_summary.md", "r") as f:
    CONTEXT_SUMMARY_PROMPT = f.read()
