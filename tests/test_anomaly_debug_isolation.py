"""Concurrent anomaly isolation and unique debug-log tests."""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor

from src.pipeline.debug_log import (
    begin_debug_run,
    end_debug_run,
    last_debug_log_path,
    log_debug_event,
    write_raw_model_output_artifact,
)
from src.pipeline.structured_output import (
    begin_anomaly_collection,
    end_anomaly_collection,
    get_last_parse_anomalies,
    get_run_parse_anomalies,
    parse_claims_response,
    parse_context_facts_response,
)


def _malformed_facts(marker: str) -> str:
    return json.dumps(
        {
            "triples": [
                {
                    "subject": f"Subject-{marker}",
                    "relation": "located_in",
                    "object": None,
                    "evidence": f"bad-{marker}",
                },
                {
                    "subject": f"Subject-{marker}",
                    "relation": "located_in",
                    "object": f"Rack-{marker}",
                    "evidence": f"ok-{marker}",
                },
            ]
        }
    )


def test_concurrent_parse_anomalies_are_isolated():
    barriers = threading.Barrier(2)
    results: dict[str, list[str]] = {}

    def worker(marker: str) -> None:
        begin_anomaly_collection()
        try:
            barriers.wait(timeout=5)
            facts = parse_context_facts_response(_malformed_facts(marker))
            barriers.wait(timeout=5)
            anomalies = get_run_parse_anomalies()
            results[marker] = [f"{a.subject}:{a.reason}" for a in anomalies]
            assert {f.object for f in facts} == {f"Rack-{marker}"}
            assert all(
                (a.subject or "").startswith(f"Subject-{marker}") for a in anomalies
            )
        finally:
            end_anomaly_collection()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, "A"), pool.submit(worker, "B")]
        for fut in futures:
            fut.result(timeout=10)

    assert results["A"]
    assert results["B"]
    assert all(item.startswith("Subject-A:") for item in results["A"])
    assert all(item.startswith("Subject-B:") for item in results["B"])


def test_claim_extraction_anomalies_accumulate_in_run_buffer():
    begin_anomaly_collection()
    try:
        claims = parse_claims_response(
            json.dumps(
                {
                    "triples": [
                        {
                            "subject": "Host C",
                            "relation": "located_in",
                            "object": {"name": "Rack R7"},
                            "source_sentence": "Host C is in Rack R7.",
                        },
                        {
                            "subject": "Host C",
                            "relation": "located_in",
                            "object": "Rack R7",
                            "source_sentence": "Host C is in Rack R7.",
                        },
                    ]
                }
            )
        )
        assert len(claims) == 1
        last = get_last_parse_anomalies()
        run = get_run_parse_anomalies()
        assert last
        assert len(run) >= len(last)
        assert any("unsupported" in a.reason for a in run)
    finally:
        end_anomaly_collection()
        assert get_run_parse_anomalies() == []


def test_repeated_run_id_gets_unique_debug_logs(monkeypatch, tmp_path):
    monkeypatch.setenv("GRAPHEVAL_DEBUG_LOGS", "true")
    from src.pipeline import debug_log as debug_mod

    monkeypatch.setattr(debug_mod, "DEBUG_DIR", tmp_path)

    paths = []
    for attempt in (1, 2):
        path = begin_debug_run("apollo_hop_011", attempt=attempt)
        assert path is not None
        log_debug_event("test", "ping", {"password": "secret-value", "ok": True})
        paths.append(path)
        end_debug_run()

    assert paths[0] != paths[1]
    assert "apollo_hop_011" in paths[0]
    assert "attempt_1" in paths[0]
    assert "attempt_2" in paths[1]
    for relative in paths:
        body = (tmp_path / relative.split("/")[-1]).read_text(encoding="utf-8")
        assert "secret-value" not in body
        assert "[REDACTED]" in body


def test_sanitized_run_id_and_exception_cleanup(monkeypatch, tmp_path):
    monkeypatch.setenv("GRAPHEVAL_DEBUG_LOGS", "true")
    from src.pipeline import debug_log as debug_mod

    monkeypatch.setattr(debug_mod, "DEBUG_DIR", tmp_path)
    begin_anomaly_collection()
    path = begin_debug_run("weird/id name?!", attempt=3)
    assert path is not None
    filename = path.rsplit("/", 1)[-1]
    assert "/" not in filename
    assert " " not in filename
    assert "?" not in filename
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        end_debug_run()
        end_anomaly_collection()
    assert last_debug_log_path() == path
    begin_anomaly_collection()
    try:
        assert get_run_parse_anomalies() == []
    finally:
        end_anomaly_collection()


def test_raw_model_output_artifact_written_when_debug_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("GRAPHEVAL_DEBUG_LOGS", "true")
    from src.pipeline import debug_log as debug_mod

    monkeypatch.setattr(debug_mod, "DEBUG_DIR", tmp_path)
    relative = begin_debug_run("raw_artifact_run", attempt=1)
    try:
        raw = (
            '{"triples": [{"subject": "Host C", "relation": "located_in", '
            '"object": "Rack R7"}]}'
        )
        artifact = write_raw_model_output_artifact(
            stage="claim_extraction",
            raw_text=raw,
            format_hint="claims",
        )
        assert artifact is not None
        assert artifact.endswith("_raw.txt")
        on_disk = tmp_path / artifact.rsplit("/", 1)[-1]
        assert on_disk.exists()
        assert on_disk.read_text(encoding="utf-8") == raw
        assert relative is not None
        log_body = (tmp_path / relative.rsplit("/", 1)[-1]).read_text(encoding="utf-8")
        assert "raw_artifact_path" in log_body
    finally:
        end_debug_run()
