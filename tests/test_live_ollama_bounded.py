"""Bounded live Ollama integration tests. Enable with GRAPHEVAL_LIVE_OLLAMA=1."""

from __future__ import annotations

import json
import os
import urllib.request

import pytest

from src.config import DEFAULT_MODEL, OLLAMA_BASE_URL, OLLAMA_NUM_CTX
from src.llm.ollama_provider import OllamaProvider
from src.models import Example
from src.pipeline.decomposed_backtracking_runner import DecomposedBacktrackingRunner

pytestmark = pytest.mark.live_ollama

RACK_CONTEXT = (
    "System Alpha uses Service A. Service A depends on Database B. "
    "Database B runs on Host C. Host C is located in Rack R7."
)


def _live_enabled() -> bool:
    return os.getenv("GRAPHEVAL_LIVE_OLLAMA", "").strip().lower() in {"1", "true", "yes"}


def _require_ollama_model() -> str:
    if not _live_enabled():
        pytest.skip("Set GRAPHEVAL_LIVE_OLLAMA=1 to run live Ollama tests")
    model = os.getenv("DEFAULT_MODEL", DEFAULT_MODEL)
    try:
        with urllib.request.urlopen(
            f"{OLLAMA_BASE_URL.rstrip('/')}/api/tags", timeout=5
        ) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        pytest.fail(f"Ollama unreachable (no mock fallback): {exc}")
    names = [m.get("name") for m in payload.get("models", []) if isinstance(m, dict)]
    if model not in names:
        pytest.fail(f"Configured model not installed: {model}; have={names}")
    return model


def _apollo_question(hop: int) -> dict:
    path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "data",
        "test_sets",
        "apollo_multihop_50.json",
    )
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    questions = data["questions"] if isinstance(data, dict) else data
    for row in questions:
        if int(row.get("hop_count", 0)) == hop:
            return row
    pytest.fail(f"No Apollo question for hop={hop}")


@pytest.fixture
def ollama_provider():
    model = _require_ollama_model()
    os.environ["GRAPHEVAL_DEBUG_LOGS"] = "true"
    provider = OllamaProvider(model=model)
    assert provider.__class__.__name__ == "OllamaProvider"
    return provider


def test_live_apollo_hops_1_2_3(ollama_provider, monkeypatch):
    monkeypatch.setenv("NEO4J_ENABLED", os.getenv("NEO4J_ENABLED", "true"))
    from src.benchmarks import trusted_context

    results = []
    for hop in (1, 2, 3):
        q = _apollo_question(hop)
        context = trusted_context("apollo_multihop_50")
        runner = DecomposedBacktrackingRunner(
            ollama_provider,
            max_iterations_per_sub_question=1,
            answer_0_mode="generated_external_projected",
            clear_neo4j_before_run=True,
            neo4j_readback=os.getenv("NEO4J_ENABLED", "true").lower() == "true",
            require_neo4j=False,
        )
        result = runner.run_example(
            Example(id=q["id"], question=q["question"], context=context),
            attempt=1,
        )
        assert result.trace is not None
        assert result.trace.provider_class == "OllamaProvider"
        assert result.trace.model == ollama_provider.model
        assert result.debug_log_path
        results.append(
            {
                "id": q["id"],
                "hop": hop,
                "answer": result.combined_answer,
                "expected": q.get("expected_answer"),
                "anomalies": len(result.structured_triple_anomalies),
                "facts": len(result.base_kgc_facts),
                "debug_log_path": result.debug_log_path,
                "stop": [
                    sq.stop_reason.value if sq.stop_reason else None
                    for sq in result.sub_question_results
                ],
                "num_ctx": result.trace.configured_num_ctx or OLLAMA_NUM_CTX,
            }
        )
    # Persist a compact evidence blob for the final report without failing on model errors.
    out = os.path.join(
        os.path.dirname(__file__),
        "..",
        "results",
        "live_ollama_apollo_hops.json",
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    assert all(row["facts"] >= 0 for row in results)


def test_live_rack_r7_and_wrong_initial(ollama_provider, monkeypatch):
    monkeypatch.setenv("NEO4J_ENABLED", os.getenv("NEO4J_ENABLED", "true"))
    question = (
        "Which rack contains the host that runs the database depended on by the "
        "service used by System Alpha?"
    )
    runner = DecomposedBacktrackingRunner(
        ollama_provider,
        max_iterations_per_sub_question=2,
        answer_0_mode="preset_external_projected",
        clear_neo4j_before_run=True,
        neo4j_readback=False,
        require_neo4j=False,
    )
    result = runner.run_example(
        Example(
            id="live_rack_r7",
            question=question,
            context=RACK_CONTEXT,
            initial_answer="The host is in Rack R9.",
        ),
        attempt=1,
    )
    assert result.trace is not None
    assert result.trace.provider_class == "OllamaProvider"
    assert result.debug_log_path
    assert len(result.base_kgc_facts) >= 1
    out = os.path.join(
        os.path.dirname(__file__),
        "..",
        "results",
        "live_ollama_rack_r7.json",
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "answer": result.combined_answer,
                "facts": [f.__dict__ for f in result.base_kgc_facts],
                "anomalies": result.structured_triple_anomalies,
                "debug_log_path": result.debug_log_path,
                "model": result.trace.model,
                "num_ctx": result.trace.configured_num_ctx,
            },
            handle,
            indent=2,
            default=str,
        )
