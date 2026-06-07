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

# LLM provider settings
DEFAULT_LLM_PROVIDER = "mock"

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e2b"
TEST_MODELS = ["gemma4:e2b", "gemma4:e4b", "gemma4:12b"]
OLLAMA_REQUEST_TIMEOUT = 120  # seconds per completion
