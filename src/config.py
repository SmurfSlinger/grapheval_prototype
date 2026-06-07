"""Project paths and runtime configuration."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

EXAMPLES_PATH = DATA_DIR / "examples.json"

PROMPT_ANSWER_GENERATION = PROMPTS_DIR / "answer_generation.txt"
PROMPT_TRIPLE_EXTRACTION = PROMPTS_DIR / "triple_extraction.txt"
PROMPT_TRIPLE_VERIFICATION = PROMPTS_DIR / "triple_verification.txt"
PROMPT_ANSWER_REVISION = PROMPTS_DIR / "answer_revision.txt"

# Default provider: "mock" runs without API keys
DEFAULT_LLM_PROVIDER = "mock"
