"""Ensure baseline wrappers do not interpolate model/path into Python source."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_apollo_and_nhs_wrappers_pass_model_via_env() -> None:
    for name in (
        "scripts/run_apollo_real_baseline.sh",
        "scripts/run_nhs_wannacry_real_baseline.sh",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "model = '$MODEL'" not in text
        assert "MODEL=\"$MODEL\" python3 -c" in text
        assert "os.environ['MODEL']" in text
        assert "open('$LOCK_FILE')" not in text
        assert "LOCK_FILE=\"$LOCK_FILE\" python3 -c" in text
        assert "os.environ['LOCK_FILE']" in text


def test_debug_log_path_helper() -> None:
    from src.pipeline.debug_log import debug_log_relative_path

    assert debug_log_relative_path("apollo_hop_001") == (
        ".runtime/debug/apollo_hop_001.jsonl"
    )
