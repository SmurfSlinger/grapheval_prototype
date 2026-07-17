"""NHS WannaCry dataset structure, provenance, and wrapper tests."""

from __future__ import annotations

import json
import os
import subprocess
from collections import Counter
from pathlib import Path

from scripts.run_multihop_benchmark import validate_test_set

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "test_sets" / "nhs_wannacry_multihop_50.json"
APOLLO = ROOT / "data" / "test_sets" / "apollo_multihop_50.json"
MANIFEST = ROOT / "data" / "sources" / "nhs_wannacry" / "source_manifest.json"
WRAPPER = ROOT / "scripts" / "run_nhs_wannacry_real_baseline.sh"
ARGS_LIB = ROOT / "scripts" / "nhs_wannacry_baseline_args.sh"

CANONICAL_JSON = "results/nhs_wannacry_multihop_real_baseline.json"
CANONICAL_MD = "results/nhs_wannacry_multihop_real_baseline.md"


def _payload() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def test_nhs_wannacry_validates_with_generalized_validator() -> None:
    payload = _payload()
    result = validate_test_set(payload)
    assert result["valid"], result["errors"]
    assert result["question_count"] == 50
    assert result["hop_distribution"] == {hop: 5 for hop in range(1, 11)}
    metrics = result["graph_metrics"]
    assert metrics["node_count"] >= 45
    assert metrics["edge_count"] >= 55
    assert metrics["relation_count"] >= 15
    assert metrics["connected_components"] == 1
    assert metrics["isolated_entity_count"] == 0
    assert metrics["branches_reaching_10_hops"] >= 2
    assert payload["root_entity"] == "WannaCry attack on the NHS"


def test_apollo_still_validates_after_generalization() -> None:
    payload = json.loads(APOLLO.read_text(encoding="utf-8"))
    result = validate_test_set(payload)
    assert result["valid"], result["errors"]
    assert payload["root_entity"] == "Apollo 11"
    assert result["graph_metrics"]["root_node"] == "Apollo 11"


def test_nhs_question_ids_and_paths() -> None:
    payload = _payload()
    questions = payload["questions"]
    ids = [q["id"] for q in questions]
    assert len(set(ids)) == 50
    assert Counter(q["hop_count"] for q in questions) == {h: 5 for h in range(1, 11)}
    triples = {
        (f["subject"], f["relation"], f["object"])
        for f in payload["expected_graph_facts"]
    }
    for q in questions:
        assert q["id"].startswith("nhs_wannacry_h")
        path = [tuple(edge) for edge in q["expected_path"]]
        assert path[0][0] == payload["root_entity"]
        assert all(edge in triples for edge in path)
        assert all(a[2] == b[0] for a, b in zip(path, path[1:]))
        assert q["expected_answer"] == path[-1][2]


def test_nhs_fact_provenance_and_manifest() -> None:
    payload = _payload()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources = manifest["sources"] if isinstance(manifest, dict) else manifest
    source_ids = {s["source_id"] for s in sources}
    fact_ids = set()
    for fact in payload["expected_graph_facts"]:
        assert fact["fact_id"] not in fact_ids
        fact_ids.add(fact["fact_id"])
        if fact.get("fact_kind", "direct") == "direct":
            assert fact["source_id"] in source_ids
            assert fact.get("page") not in (None, "") or fact.get("section")
            assert str(fact.get("evidence") or "").strip()
        else:
            assert fact.get("parent_fact_ids")
            assert str(fact.get("derivation_rule") or "").strip()
            for parent in fact["parent_fact_ids"]:
                assert parent in fact_ids or any(
                    f["fact_id"] == parent for f in payload["expected_graph_facts"]
                )


def test_trusted_context_excludes_scoring_metadata_markers() -> None:
    payload = _payload()
    ctx = payload["trusted_context"].lower()
    assert "expected_path" not in ctx
    assert "expected_answer" not in ctx
    assert "nw_f" not in ctx


def test_malformed_provenance_fails_validation() -> None:
    payload = _payload()
    payload["expected_graph_facts"][0]["source_id"] = "not_a_real_source"
    result = validate_test_set(payload)
    assert result["valid"] is False
    assert any("unknown source_id" in err for err in result["errors"])


def test_noncontiguous_path_fails_validation() -> None:
    payload = _payload()
    q = next(item for item in payload["questions"] if item["hop_count"] >= 2)
    q["expected_path"][1][0] = "NOT_CONTIGUOUS"
    result = validate_test_set(payload)
    assert result["valid"] is False
    assert any("not contiguous" in err for err in result["errors"])


def test_example_construction_excludes_expected_fields() -> None:
    """Mirror runner isolation: only id/question/context reach inference."""
    from src.models import Example

    payload = _payload()
    question = payload["questions"][0]
    example = Example(
        id=question["id"],
        question=question["question"],
        context=payload["trusted_context"],
    )
    blob = json.dumps(example.__dict__)
    assert question["expected_answer"] not in blob
    assert "expected_path" not in blob


def _run_wrapper_dry(cli_args: list[str], *, expect_ok: bool = True):
    env = os.environ.copy()
    env.pop("MODEL", None)
    env["NHS_WANNACRY_BASELINE_DRY_RUN"] = "1"
    proc = subprocess.run(
        ["bash", str(WRAPPER), *cli_args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    if not expect_ok:
        return proc, None
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return proc, json.loads(proc.stdout.strip().splitlines()[-1])


def test_nhs_wrapper_canonical_paths_and_model_consistency() -> None:
    _, data = _run_wrapper_dry(["--model", "llama3:8b", "--limit", "2"])
    assert data is not None
    assert data["output_json_rel"] == CANONICAL_JSON
    assert data["output_md_rel"] == CANONICAL_MD
    assert data["checked_model"] == data["executed_model"] == "llama3:8b"
    assert data["forward_args"] == ["--limit", "2"]
    assert "--model" not in data["forward_args"]


def test_nhs_wrapper_rejects_protected_and_malformed_model() -> None:
    proc, _ = _run_wrapper_dry(["--output", "/tmp/x.json"], expect_ok=False)
    assert proc.returncode == 2
    assert "protected wrapper argument" in proc.stderr
    proc = subprocess.run(
        ["bash", str(WRAPPER), "--model"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert proc.returncode == 2
    assert "requires a non-empty value" in proc.stderr
