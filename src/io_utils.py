"""File I/O helpers for examples, prompts, and results."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import EXAMPLES_PATH, RESULTS_DIR
from src.models import Example, PipelineResult


def load_prompt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_examples(path: Path = EXAMPLES_PATH) -> list[Example]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        Example(
            id=item["id"],
            question=item["question"],
            context=item["context"],
            initial_answer=item.get("initial_answer"),
        )
        for item in raw
    ]


def save_result(result: PipelineResult, output_dir: Path = RESULTS_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{result.example_id}.json"
    payload: dict[str, Any] = result.to_dict()
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def parse_json_response(text: str) -> dict[str, Any]:
    """Extract and parse a JSON object from an LLM response."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return json.loads(text[start : end + 1])
