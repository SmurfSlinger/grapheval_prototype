"""Entry point: run the hallucination feedback pipeline on all examples."""

from __future__ import annotations

from src.config import DEFAULT_LLM_PROVIDER
from src.io_utils import load_examples
from src.llm.mock_provider import MockProvider
from src.pipeline.runner import PipelineRunner


def get_provider(name: str = DEFAULT_LLM_PROVIDER):
    if name == "mock":
        return MockProvider()
    raise ValueError(f"Unknown LLM provider: {name}")


def main() -> None:
    provider = get_provider()
    runner = PipelineRunner(provider)
    examples = load_examples()

    print(f"Running pipeline on {len(examples)} example(s) with provider={DEFAULT_LLM_PROVIDER!r}")

    for example in examples:
        result = runner.run_and_save(example)
        runner.print_summary(result)

    print("\nDone. Results saved to results/")


if __name__ == "__main__":
    main()
