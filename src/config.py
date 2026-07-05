"""Project paths and runtime configuration."""

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_DIR = PROJECT_ROOT / "results"
PROMPTS_DIR = PROJECT_ROOT / "prompts"

EXAMPLES_PATH = DATA_DIR / "examples.json"

PROMPT_ANSWER_GENERATION = PROMPTS_DIR / "answer_generation.txt"
PROMPT_TRIPLE_EXTRACTION = PROMPTS_DIR / "triple_extraction.txt"
PROMPT_KG_CLAIM_EXTRACTION = PROMPTS_DIR / "kg_claim_extraction.txt"
PROMPT_TRIPLE_VERIFICATION = PROMPTS_DIR / "triple_verification.txt"
PROMPT_ANSWER_REVISION = PROMPTS_DIR / "answer_revision.txt"
PROMPT_SELF_CORRECTION = PROMPTS_DIR / "self_correction.txt"
PROMPT_CONTEXT_TRIPLE_EXTRACTION = PROMPTS_DIR / "context_triple_extraction.txt"
PROMPT_KG_ANSWER_GENERATION = PROMPTS_DIR / "kg_answer_generation.txt"
PROMPT_BACKTRACKING_REVISION = PROMPTS_DIR / "backtracking_revision.txt"

# LLM provider settings
DEFAULT_LLM_PROVIDER = "mock"

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "gemma4:e2b"
TEST_MODELS = ["gemma4:e2b", "gemma4:e4b", "gemma4:12b"]
OLLAMA_REQUEST_TIMEOUT = 120  # seconds per completion

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password123")
NEO4J_ENABLED = os.getenv("NEO4J_ENABLED", "false").lower() == "true"