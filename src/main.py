"""Entry point: run the hallucination feedback pipeline on all examples."""

from __future__ import annotations

import argparse
import sys

from src.config import DEFAULT_LLM_PROVIDER, DEFAULT_MODEL, TEST_MODELS
from src.io_utils import load_examples, result_filename
from src.llm.base import LLMProvider
from src.llm.mock_provider import MockProvider
from src.llm.ollama_provider import (
    OllamaConnectionError,
    OllamaError,
    OllamaModelNotFoundError,
    OllamaProvider,
    OllamaTimeoutError,
)
from src.pipeline.runner import PipelineRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the GraphEval-style hallucination feedback pipeline."
    )
    parser.add_argument(
        "--provider",
        choices=["mock", "ollama"],
        default=DEFAULT_LLM_PROVIDER,
        help=f"LLM backend to use (default: {DEFAULT_LLM_PROVIDER})",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Ollama model tag (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--compare-models",
        action="store_true",
        help="Run all TEST_MODELS via Ollama and save per-model result files",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Do not fall back to mock when Ollama is unavailable",
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="Run all examples from data/examples.json (default behavior)",
    )
    return parser


def get_provider(
    name: str,
    *,
    model: str = DEFAULT_MODEL,
    fallback_to_mock: bool = True,
) -> LLMProvider:
    if name == "mock":
        return MockProvider()

    if name == "ollama":
        try:
            return OllamaProvider(model=model, verify_on_init=True)
        except OllamaError as exc:
            if fallback_to_mock:
                print(f"Warning: {exc}", file=sys.stderr)
                print("Falling back to mock provider.", file=sys.stderr)
                return MockProvider()
            raise

    raise ValueError(f"Unknown LLM provider: {name}")


def run_pipeline(
    provider: LLMProvider,
    *,
    model: str | None = None,
) -> None:
    runner = PipelineRunner(provider)
    examples = load_examples()
    label = model or type(provider).__name__
    print(f"Running pipeline on {len(examples)} example(s) with {label!r}")

    for example in examples:
        fname = result_filename(example.id, model) if model else None
        result = runner.run_and_save(example, filename=fname)
        runner.print_summary(result)
        if fname:
            print(f"Saved: results/{fname}")


def run_compare_models(*, fallback_to_mock: bool) -> None:
    examples = load_examples()
    print(f"Comparing {len(TEST_MODELS)} model(s) on {len(examples)} example(s)")

    for model in TEST_MODELS:
        print(f"\n========== model: {model} ==========")
        try:
            provider = OllamaProvider(model=model, verify_on_init=True)
        except OllamaError as exc:
            if fallback_to_mock:
                print(f"Warning: skipping {model}: {exc}", file=sys.stderr)
                continue
            raise

        runner = PipelineRunner(provider)
        for example in examples:
            fname = result_filename(example.id, model)
            try:
                result = runner.run_and_save(example, filename=fname)
            except (OllamaError, ValueError) as exc:
                print(f"Error on {example.id} with {model}: {exc}", file=sys.stderr)
                if not fallback_to_mock:
                    raise
                break
            else:
                runner.print_summary(result)
                print(f"Saved: results/{fname}")

    print("\nDone. Comparison results saved to results/")


def main() -> None:
    args = build_parser().parse_args()
    fallback_to_mock = not args.no_fallback

    if args.compare_models:
        if args.provider != "ollama":
            print("Note: --compare-models uses Ollama regardless of --provider.")
        run_compare_models(fallback_to_mock=fallback_to_mock)
        return

    provider = get_provider(
        args.provider,
        model=args.model,
        fallback_to_mock=fallback_to_mock,
    )
    model_suffix = args.model if args.provider == "ollama" else None
    if isinstance(provider, MockProvider) and args.provider == "ollama":
        model_suffix = None
    run_pipeline(provider, model=model_suffix)

    print("\nDone. Results saved to results/")


if __name__ == "__main__":
    try:
        main()
    except OllamaConnectionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except OllamaModelNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except OllamaTimeoutError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
