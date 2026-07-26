"""Optional per-run JSONL debug logs for GraphEval research debugging.

Enabled when GRAPHEVAL_DEBUG_LOGS=true. Writes to
.runtime/debug/<timestamp>_<run_id>_attempt_<n>.jsonl (unique per attempt).
Never logs credentials or secrets.
"""

from __future__ import annotations

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

DEBUG_DIR = PROJECT_ROOT / ".runtime" / "debug"
_SAFE_RUN_ID = re.compile(r"[^A-Za-z0-9._-]+")

_thread_state = threading.local()


def debug_logs_enabled() -> bool:
    env_enabled = os.getenv("GRAPHEVAL_DEBUG_LOGS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return env_enabled or bool(getattr(_thread_state, "force_enabled", False))


def debug_log_relative_path(filename_stem: str) -> str:
    safe = _sanitize_run_id(filename_stem)
    if safe.endswith(".jsonl"):
        return f".runtime/debug/{safe}"
    return f".runtime/debug/{safe}.jsonl"


def _unique_debug_filename(run_id: str, *, attempt: int | None = None) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe = _sanitize_run_id(run_id)
    if attempt is not None:
        attempt_part = f"attempt_{int(attempt)}"
    else:
        attempt_part = f"attempt_{uuid.uuid4().hex[:8]}"
    return f"{timestamp}_{safe}_{attempt_part}.jsonl"


def begin_debug_run(
    run_id: str,
    *,
    force: bool = False,
    attempt: int | None = None,
) -> str | None:
    """Start a unique debug log for a run. Returns relative path when active."""
    if force:
        _thread_state.force_enabled = True
    if not debug_logs_enabled():
        _thread_state.run_id = None
        _thread_state.path = None
        _thread_state.relative_path = None
        return None
    filename = _unique_debug_filename(run_id, attempt=attempt)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / filename
    # Open once to create the file even if no events are written later.
    path.touch(exist_ok=True)
    _thread_state.run_id = _sanitize_run_id(run_id)
    _thread_state.path = path
    _thread_state.relative_path = f".runtime/debug/{filename}"
    _thread_state.question_id = ""
    _thread_state.sub_question_id = ""
    _thread_state.attempt = attempt
    return _thread_state.relative_path


def set_debug_context(
    *,
    question_id: str | None = None,
    sub_question_id: str | int | None = None,
) -> None:
    if question_id is not None:
        _thread_state.question_id = str(question_id)
    if sub_question_id is not None:
        _thread_state.sub_question_id = str(sub_question_id)


def end_debug_run() -> None:
    # Preserve last path for error reporters after cleanup.
    _thread_state.last_relative_path = getattr(_thread_state, "relative_path", None)
    _thread_state.run_id = None
    _thread_state.path = None
    _thread_state.relative_path = None
    _thread_state.question_id = ""
    _thread_state.sub_question_id = ""
    _thread_state.force_enabled = False
    _thread_state.attempt = None


def current_debug_log_path() -> str | None:
    return getattr(_thread_state, "relative_path", None)


def last_debug_log_path() -> str | None:
    return getattr(_thread_state, "last_relative_path", None) or current_debug_log_path()


def log_debug_event(
    stage: str,
    event: str,
    data: dict[str, Any] | None = None,
    *,
    question_id: str | None = None,
    sub_question_id: str | int | None = None,
) -> None:
    if not debug_logs_enabled():
        return
    path: Path | None = getattr(_thread_state, "path", None)
    run_id = getattr(_thread_state, "run_id", None)
    if path is None or not run_id:
        return
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "attempt": getattr(_thread_state, "attempt", None),
        "debug_log_path": getattr(_thread_state, "relative_path", None),
        "question_id": question_id
        if question_id is not None
        else getattr(_thread_state, "question_id", ""),
        "sub_question_id": str(sub_question_id)
        if sub_question_id is not None
        else getattr(_thread_state, "sub_question_id", ""),
        "stage": stage,
        "event": event,
        "data": _redact(data or {}),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def write_raw_model_output_artifact(
    *,
    stage: str,
    raw_text: str,
    format_hint: str | None = None,
) -> str | None:
    """Persist full raw model output beside the JSONL when debug logging is on."""
    if not debug_logs_enabled():
        return None
    path: Path | None = getattr(_thread_state, "path", None)
    if path is None:
        return None
    stem = path.stem
    suffix = f"_{_sanitize_run_id(stage)}"
    artifact = path.with_name(f"{stem}{suffix}_raw.txt")
    artifact.write_text(raw_text, encoding="utf-8")
    relative = f".runtime/debug/{artifact.name}"
    log_debug_event(
        stage,
        "raw_model_output_artifact",
        {
            "raw_artifact_path": relative,
            "raw_chars": len(raw_text),
            "format_hint": format_hint,
        },
    )
    return relative


def _sanitize_run_id(run_id: str) -> str:
    cleaned = _SAFE_RUN_ID.sub("_", (run_id or "run").strip()) or "run"
    return cleaned[:180]


_SECRET_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "authorization",
    "neo4j_password",
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_l = str(key).lower()
            if any(fragment in key_l for fragment in _SECRET_KEY_FRAGMENTS):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value
