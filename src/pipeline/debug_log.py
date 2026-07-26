"""Optional per-run JSONL debug logs for GraphEval research debugging.

Enabled when GRAPHEVAL_DEBUG_LOGS=true. Writes to .runtime/debug/<run_id>.jsonl.
Never logs credentials or secrets.
"""

from __future__ import annotations

import json
import os
import re
import threading
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


def debug_log_relative_path(run_id: str) -> str:
    safe = _sanitize_run_id(run_id)
    return f".runtime/debug/{safe}.jsonl"


def begin_debug_run(run_id: str, *, force: bool = False) -> str | None:
    """Start a debug log for a run. Returns relative path when logging is active."""
    if force:
        _thread_state.force_enabled = True
    if not debug_logs_enabled():
        _thread_state.run_id = None
        _thread_state.path = None
        return None
    safe = _sanitize_run_id(run_id)
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / f"{safe}.jsonl"
    _thread_state.run_id = safe
    _thread_state.path = path
    _thread_state.question_id = ""
    _thread_state.sub_question_id = ""
    return debug_log_relative_path(safe)


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
    _thread_state.run_id = None
    _thread_state.path = None
    _thread_state.question_id = ""
    _thread_state.sub_question_id = ""
    _thread_state.force_enabled = False


def current_debug_log_path() -> str | None:
    path = getattr(_thread_state, "path", None)
    run_id = getattr(_thread_state, "run_id", None)
    if path is None or run_id is None:
        return None
    return debug_log_relative_path(str(run_id))


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
