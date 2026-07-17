"""API coverage for UI benchmark listing and single-question runs."""

from __future__ import annotations

from src.models import (
    DecomposedBacktrackingResult,
    DecomposedBacktrackingTrace,
    SubQuestion,
    SubQuestionResult,
    SubQuestionStopReason,
)


def _fake_result(example) -> DecomposedBacktrackingResult:
    return DecomposedBacktrackingResult(
        example_id=example.id,
        original_question=example.question,
        context=example.context,
        sub_questions=[SubQuestion(id=1, question=example.question)],
        sub_question_results=[
            SubQuestionResult(
                sub_question_id=1,
                question=example.question,
                initial_answer="synthetic answer",
                final_answer="synthetic answer",
                stop_reason=SubQuestionStopReason.RESOLVED,
                iteration_count=1,
            )
        ],
        combined_answer="synthetic answer",
        trace=DecomposedBacktrackingTrace(
            mode="decomposed_kgc_backtracking",
            answer_0_mode="generated_external_projected",
        ),
    )


def test_benchmarks_list_both_suites_with_hop_distribution():
    from fastapi.testclient import TestClient

    from api.server import app

    client = TestClient(app)
    response = client.get("/benchmarks")
    assert response.status_code == 200
    rows = response.json()
    ids = {row["id"] for row in rows}
    assert ids == {"apollo_multihop_50", "nhs_wannacry_multihop_50"}
    for row in rows:
        assert row["question_count"] == 50
        assert row["hop_distribution"] == {str(hop): 5 for hop in range(1, 11)}
        assert "expected_answer" not in row
        assert "expected_path" not in row
        assert "trusted_context" not in row


def test_benchmark_question_listing_excludes_scoring_fields():
    from fastapi.testclient import TestClient

    from api.server import app

    client = TestClient(app)
    for benchmark_id in ("apollo_multihop_50", "nhs_wannacry_multihop_50"):
        response = client.get(f"/benchmarks/{benchmark_id}/questions")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 50
        for row in rows:
            assert set(row.keys()) == {"id", "hop_count", "question"}
            assert "expected_answer" not in row
            assert "expected_path" not in row
            assert "required_relations" not in row
            assert "shortcut_audit" not in row


def test_benchmark_question_listing_hop_filter():
    from fastapi.testclient import TestClient

    from api.server import app

    client = TestClient(app)
    response = client.get("/benchmarks/apollo_multihop_50/questions", params={"hop": 7})
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 5
    assert all(row["hop_count"] == 7 for row in rows)


def test_invalid_benchmark_and_question_ids_are_rejected():
    from fastapi.testclient import TestClient

    from api.server import app

    client = TestClient(app)
    assert client.get("/benchmarks/not_a_suite/questions").status_code == 404
    assert (
        client.post(
            "/run-benchmark-question",
            json={
                "benchmark_id": "not_a_suite",
                "question_id": "apollo_hop_001",
                "provider": "mock",
            },
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/run-benchmark-question",
            json={
                "benchmark_id": "apollo_multihop_50",
                "question_id": "missing_question",
                "provider": "mock",
            },
        ).status_code
        == 404
    )


def test_run_benchmark_question_uses_context_and_excludes_scoring_from_example(
    monkeypatch,
):
    from fastapi.testclient import TestClient

    import api.server as server
    from api.server import app
    from src.benchmarks import get_question, trusted_context

    captured: dict = {}

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            captured["runner_kwargs"] = kwargs

        def run_example(self, example):
            captured["example"] = example
            return _fake_result(example)

    monkeypatch.setattr(server, "_make_decomposed_backtracking_runner", FakeRunner)

    client = TestClient(app)
    question = get_question("apollo_multihop_50", "apollo_hop_001")
    context = trusted_context("apollo_multihop_50")
    response = client.post(
        "/run-benchmark-question",
        json={
            "benchmark_id": "apollo_multihop_50",
            "question_id": "apollo_hop_001",
            "provider": "mock",
            "model": "gemma4:e2b",
            "clear_neo4j_before_run": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    example = captured["example"]
    assert example.id == "apollo_hop_001"
    assert example.question == question["question"]
    assert example.context == context
    assert example.initial_answer is None
    assert question["expected_answer"] not in example.question
    assert "expected_path" not in example.__dict__
    assert getattr(example, "expected_answer", None) in (None, "")
    assert getattr(example, "expected_path", None) in (None, [], ())
    assert body["benchmark"]["question_id"] == "apollo_hop_001"
    assert body["benchmark"]["hop_count"] == 1
    assert body["benchmark"]["expected_answer"] == question["expected_answer"]
    assert "result" in body
    assert body["result"]["original_question"] == question["question"]
    assert body["result"]["context"] == context


def test_run_benchmark_question_does_not_send_expected_fields_to_provider(
    monkeypatch,
):
    from fastapi.testclient import TestClient

    import api.server as server
    from api.server import app

    captured: dict = {}

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            captured["runner_kwargs"] = kwargs

        def run_example(self, example):
            captured["example"] = example
            captured["example_keys"] = sorted(example.__dict__.keys())
            return _fake_result(example)

    monkeypatch.setattr(server, "_make_decomposed_backtracking_runner", FakeRunner)
    client = TestClient(app)
    response = client.post(
        "/run-benchmark-question",
        json={
            "benchmark_id": "nhs_wannacry_multihop_50",
            "question_id": "nhs_wannacry_h01_q01",
            "provider": "mock",
        },
    )
    assert response.status_code == 200, response.text
    example = captured["example"]
    assert set(captured["example_keys"]) == {
        "id",
        "question",
        "context",
        "initial_answer",
    }
    assert example.initial_answer is None
    assert not hasattr(example, "expected_answer") or example.__dict__.get(
        "expected_answer"
    ) in (None, "")
    assert "expected_path" not in example.__dict__
    assert "expected_answer" not in example.__dict__
    assert captured["runner_kwargs"]["answer_0_mode"] == "generated_external_projected"
    # Post-run scoring may reveal the expected answer only in the response payload.
    assert "expected_answer" in response.json()["benchmark"]
    assert "expected_path" not in response.json()["benchmark"]
    assert "expected_path" not in response.json()["result"]
    assert "expected_answer" not in response.json()["result"]


def test_existing_custom_and_builtin_decomposed_endpoints_still_work(monkeypatch):
    from fastapi.testclient import TestClient

    import api.server as server
    from api.server import app
    from src.models import Example

    seen: list[str] = []

    class FakeRunner:
        def __init__(self, *args, **kwargs):
            pass

        def run_example(self, example):
            seen.append(example.id)
            return _fake_result(example)

    monkeypatch.setattr(server, "_make_decomposed_backtracking_runner", FakeRunner)
    monkeypatch.setattr(
        server,
        "load_examples",
        lambda: [
            Example(
                id="builtin_demo",
                question="What is the answer?",
                context="The answer is 42.",
                initial_answer="Maybe 7.",
            )
        ],
    )

    client = TestClient(app)
    builtin = client.post(
        "/run-decomposed-kgc-backtracking",
        json={
            "example_id": "builtin_demo",
            "provider": "mock",
            "model": "gemma4:e2b",
        },
    )
    assert builtin.status_code == 200, builtin.text

    custom = client.post(
        "/run-decomposed-kgc-backtracking-custom",
        json={
            "run_id": "custom_ui_check",
            "question": "Which rack?",
            "context": "Host C is in Rack R7.",
            "provider": "mock",
            "clear_neo4j_before_run": True,
        },
    )
    assert custom.status_code == 200, custom.text
    assert seen == ["builtin_demo", "custom_ui_check"]
