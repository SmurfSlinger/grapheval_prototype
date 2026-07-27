"""Immutable per-attempt execution identity for pipeline runs.

Every pipeline attempt (API request, benchmark question, custom run, built-in
example) receives a unique ``execution_id`` generated once at the execution
boundary and reused throughout that attempt. The execution ID is distinct from
the example ID, benchmark ID, benchmark question ID, run label, and debug-log
label: repeated executions of the same question always receive different
execution IDs.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

_SAFE_LABEL = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_label(label: str) -> str:
    cleaned = _SAFE_LABEL.sub("_", (label or "run").strip()) or "run"
    return cleaned[:120]


def new_execution_id(label: str) -> str:
    """Build a unique execution ID such as ``apollo_hop_011__20260727T031500Z__a1b2c3d4``.

    The label (usually the example/question ID) is only a readability prefix;
    uniqueness comes from the timestamp plus random suffix, so repeated
    executions of the same question never collide.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{_sanitize_label(label)}__{timestamp}__{suffix}"


@dataclass(frozen=True)
class ExecutionScope:
    """Identity threaded through one pipeline attempt and its Neo4j writes."""

    execution_id: str
    example_id: str
    benchmark_id: str | None = None
    question_id: str | None = None

    @classmethod
    def begin(
        cls,
        example_id: str,
        *,
        benchmark_id: str | None = None,
        question_id: str | None = None,
        execution_id: str | None = None,
    ) -> "ExecutionScope":
        return cls(
            execution_id=execution_id or new_execution_id(example_id),
            example_id=example_id,
            benchmark_id=benchmark_id,
            question_id=question_id,
        )

    def to_dict(self) -> dict[str, str | None]:
        return {
            "execution_id": self.execution_id,
            "example_id": self.example_id,
            "benchmark_id": self.benchmark_id,
            "question_id": self.question_id,
        }
