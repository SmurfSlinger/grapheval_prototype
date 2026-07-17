"""NHS WannaCry dataset structure, hop semantics, provenance, and wrapper tests."""

from __future__ import annotations

import copy
import json
import os
import subprocess
from collections import Counter
from pathlib import Path

from scripts.build_nhs_wannacry_dataset import build_artifacts
from scripts.run_multihop_benchmark import (
    compute_shortest_directed_distance,
    entity_string_mentioned,
    validate_test_set,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "test_sets" / "nhs_wannacry_multihop_50.json"
AUDIT = ROOT / "data" / "test_sets" / "nhs_wannacry_multihop_50.audit.json"
AUDIT_MD = ROOT / "docs" / "NHS_WANNACRY_HOP_AUDIT.md"
APOLLO = ROOT / "data" / "test_sets" / "apollo_multihop_50.json"
MANIFEST = ROOT / "data" / "sources" / "nhs_wannacry" / "source_manifest.json"
WRAPPER = ROOT / "scripts" / "run_nhs_wannacry_real_baseline.sh"

CANONICAL_JSON = "results/nhs_wannacry_multihop_real_baseline.json"
CANONICAL_MD = "results/nhs_wannacry_multihop_real_baseline.md"


def _payload() -> dict:
    return json.loads(DATASET.read_text(encoding="utf-8"))


def _audit() -> dict:
    return json.loads(AUDIT.read_text(encoding="utf-8"))


def _triples(payload: dict) -> list[tuple[str, str, str]]:
    return [
        (fact["subject"], fact["relation"], fact["object"])
        for fact in payload["expected_graph_facts"]
    ]


def test_nhs_wannacry_validates_with_generalized_validator() -> None:
    payload = _payload()
    result = validate_test_set(payload)
    assert result["valid"], result["errors"]
    assert result["question_count"] == 50
    assert result["hop_distribution"] == {hop: 5 for hop in range(1, 11)}
    assert result["graph_metrics"]["shortcut_audit"]["shortcut_path_count"] == 0
    assert result["graph_metrics"]["shortcut_audit"]["final_subject_mention_count"] == 0
    assert payload["root_entity"] == "WannaCry attack on the NHS"


def test_apollo_still_validates_after_hop_semantics_extensions() -> None:
    payload = json.loads(APOLLO.read_text(encoding="utf-8"))
    result = validate_test_set(payload)
    assert result["valid"], result["errors"]
    assert payload["root_entity"] == "Apollo 11"
    assert result["graph_metrics"]["root_node"] == "Apollo 11"
    assert result["graph_metrics"]["shortcut_audit"] == {}


def test_nhs_question_anchors_paths_and_shortest_distances() -> None:
    payload = _payload()
    triples = _triples(payload)
    facts = set(triples)
    questions = payload["questions"]

    assert [question["id"] for question in questions] == [
        f"nhs_wannacry_h{hop:02d}_q{idx:02d}"
        for hop in range(1, 11)
        for idx in range(1, 6)
    ]
    assert Counter(question["hop_count"] for question in questions) == {
        hop: 5 for hop in range(1, 11)
    }

    for question in questions:
        path = [tuple(edge) for edge in question["expected_path"]]
        anchors = question["reasoning_anchor_entities"]
        assert anchors == [payload["root_entity"]]
        assert question["hop_semantics"] == "minimum_required_path"
        assert len(path) == question["hop_count"]
        assert path[0][0] in anchors
        assert all(edge in facts for edge in path)
        assert all(left[2] == right[0] for left, right in zip(path, path[1:]))
        assert question["expected_answer"] == path[-1][2]
        assert (
            compute_shortest_directed_distance(
                triples,
                anchors,
                question["expected_answer"],
            )
            == question["hop_count"]
        )


def test_nhs_no_late_entity_or_answer_shortcuts_in_questions() -> None:
    payload = _payload()
    for question in payload["questions"]:
        if question["hop_count"] <= 1:
            continue
        final_subject = question["expected_path"][-1][0]
        assert not entity_string_mentioned(question["question"], final_subject)
        assert not entity_string_mentioned(
            question["question"],
            question["expected_answer"],
        )
        assert question["shortcut_audit"]["direct_final_subject_mentioned"] is False


def test_nhs_audit_has_zero_unresolved_shortcuts() -> None:
    audit = _audit()
    assert audit["preliminary_shortcuts_before_rewrite"] == 15
    assert audit["shortcut_count"] == 0
    assert audit["unresolved_shortcuts"] == 0
    assert len(audit["questions"]) == 50
    assert all(not row["unresolved_shortcut"] for row in audit["questions"])
    assert all(row["manual_reviewed"] is True for row in audit["questions"])
    hop8_10 = [row for row in audit["questions"] if row["hop_count"] >= 8]
    assert len(hop8_10) == 15
    assert all(row["shortest_anchor_distance"] == row["hop_count"] for row in hop8_10)


def test_nhs_paths_have_no_repeated_nodes_or_duplicate_edges() -> None:
    payload = _payload()
    for question in payload["questions"]:
        path = question["expected_path"]
        nodes = [path[0][0], *[edge[2] for edge in path]]
        assert len(nodes) == len(set(nodes))
        assert len(path) == len({tuple(edge) for edge in path})


def test_nhs_relation_reuse_and_graph_metrics() -> None:
    payload = _payload()
    relations = Counter(fact["relation"] for fact in payload["expected_graph_facts"])
    graph_quality = payload["graph_quality"]
    assert 15 <= len(relations) <= 30
    assert sum(1 for count in relations.values() if count >= 2) > len(relations) // 2
    assert 6 <= graph_quality["root_out_degree"] <= 12
    assert graph_quality["entity_count"] >= 45
    assert graph_quality["edge_count"] >= 55
    assert graph_quality["connected_components"] == 1
    assert graph_quality["isolate_count"] == 0


def test_nhs_fact_provenance_and_manifest() -> None:
    payload = _payload()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    sources = manifest["sources"] if isinstance(manifest, dict) else manifest
    source_ids = {source["source_id"] for source in sources}
    fact_ids = set()
    for fact in payload["expected_graph_facts"]:
        assert fact["fact_id"] not in fact_ids
        fact_ids.add(fact["fact_id"])
        assert fact["fact_kind"] == "direct"
        assert fact["source_id"] in source_ids
        assert fact.get("page") not in (None, "") or fact.get("section")
        assert str(fact.get("evidence") or "").strip()


def test_trusted_context_is_clean_prose_without_scoring_markers() -> None:
    payload = _payload()
    ctx = payload["trusted_context"].lower()
    forbidden = [
        "expected_path",
        "expected_answer",
        "shortcut_audit",
        "reasoning_anchor_entities",
        "nw_f",
    ]
    for marker in forbidden:
        assert marker not in ctx


def test_example_construction_excludes_scoring_fields() -> None:
    from src.models import Example

    payload = _payload()
    question = payload["questions"][0]
    example = Example(
        id=question["id"],
        question=question["question"],
        context=payload["trusted_context"],
    )
    blob = json.dumps(example.__dict__)
    assert "expected_path" not in blob
    assert "expected_answer" not in blob
    assert "shortcut_audit" not in blob
    assert "reasoning_anchor_entities" not in blob


def test_malformed_provenance_fails_validation() -> None:
    payload = _payload()
    payload["expected_graph_facts"][0]["source_id"] = "not_a_real_source"
    result = validate_test_set(payload)
    assert result["valid"] is False
    assert any("unknown source_id" in error for error in result["errors"])


def test_noncontiguous_path_fails_validation() -> None:
    payload = _payload()
    question = next(item for item in payload["questions"] if item["hop_count"] >= 2)
    question["expected_path"][1][0] = "NOT_CONTIGUOUS"
    result = validate_test_set(payload)
    assert result["valid"] is False
    assert any("not contiguous" in error for error in result["errors"])


def test_malformed_shortcut_metadata_fails_validation() -> None:
    payload = _payload()
    question = next(item for item in payload["questions"] if item["hop_count"] == 8)
    question["shortcut_audit"]["manual_reviewed"] = False
    question["shortcut_audit"]["shortest_anchor_distance"] = 1
    result = validate_test_set(payload)
    assert result["valid"] is False
    assert any("manual_reviewed must be true" in error for error in result["errors"])
    assert any("shortest_anchor_distance mismatches" in error for error in result["errors"])


def test_shortened_anchor_distance_fails_validation() -> None:
    payload = _payload()
    question = next(item for item in payload["questions"] if item["hop_count"] == 10)
    payload["expected_graph_facts"].append(
        {
            "fact_id": "nw_shortcut_test",
            "subject": payload["root_entity"],
            "relation": "affected",
            "object": question["expected_answer"],
            "fact_kind": "direct",
            "source_id": "nao_wannacry_summary_2018",
            "page": 4,
            "section": "Synthetic validation fixture",
            "evidence": "Test-only edge used to verify shortcut validation.",
            "derivation_rule": None,
            "parent_fact_ids": [],
        }
    )
    result = validate_test_set(payload)
    assert result["valid"] is False
    assert any("shortest_anchor_distance 1 != hop_count 10" in error for error in result["errors"])


def test_inserting_final_subject_into_high_hop_question_fails_validation() -> None:
    payload = _payload()
    question = next(item for item in payload["questions"] if item["hop_count"] == 10)
    final_subject = question["expected_path"][-1][0]
    question["question"] = f"{question['question']} {final_subject}"
    question["shortcut_audit"]["direct_final_subject_mentioned"] = True
    result = validate_test_set(payload)
    assert result["valid"] is False
    assert any("mentions final-edge subject" in error for error in result["errors"])
    assert any("reports final-edge subject mention" in error for error in result["errors"])


def test_builder_output_matches_committed_dataset_and_audits() -> None:
    built_dataset, built_audit, built_markdown, _inventory, _metrics = build_artifacts()
    assert built_dataset == _payload()
    assert built_audit == _audit()
    assert built_markdown == AUDIT_MD.read_text(encoding="utf-8")


def test_validation_fixtures_do_not_mutate_original_payload() -> None:
    payload = _payload()
    clone = copy.deepcopy(payload)
    clone["questions"][0]["shortcut_audit"]["manual_reviewed"] = False
    assert payload["questions"][0]["shortcut_audit"]["manual_reviewed"] is True


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
    _proc, data = _run_wrapper_dry(["--model", "llama3:8b", "--limit", "2"])
    assert data is not None
    assert data["output_json_rel"] == CANONICAL_JSON
    assert data["output_md_rel"] == CANONICAL_MD
    assert data["checked_model"] == data["executed_model"] == "llama3:8b"
    assert data["forward_args"] == ["--limit", "2"]
    assert "--model" not in data["forward_args"]


def test_nhs_wrapper_rejects_protected_and_malformed_model() -> None:
    proc, _data = _run_wrapper_dry(["--output", "/tmp/x.json"], expect_ok=False)
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
