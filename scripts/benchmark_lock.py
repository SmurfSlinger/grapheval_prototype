"""Exclusive benchmark process lock.

A single JSON lock file under .runtime/ (or a caller-supplied path) guards
against two concurrent benchmark runs on the same machine.

Usage::

    from scripts.benchmark_lock import BenchmarkLock

    lock = BenchmarkLock(lock_file, provider="ollama", model="gemma4:e2b",
                         output_path="results/report.json")
    lock.acquire()           # raises BenchmarkLockError if another run is live
    try:
        ...
    finally:
        lock.release()

Or as a context manager::

    with BenchmarkLock(...) as lock:
        ...

"""

from __future__ import annotations

import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class BenchmarkLockError(RuntimeError):
    """Raised when the lock is already held by a live process."""


class BenchmarkLock:
    """Exclusive single-runner lock backed by a JSON file."""

    def __init__(
        self,
        lock_file: Path | str | None = None,
        *,
        provider: str = "",
        model: str = "",
        output_path: str = "",
    ) -> None:
        if lock_file is None:
            root = Path(__file__).resolve().parents[1]
            runtime_dir = root / ".runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)
            lock_file = runtime_dir / "benchmark.lock"
        self.lock_file = Path(lock_file)
        self._provider = provider
        self._model = model
        self._output_path = output_path
        self._acquired = False

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Acquire the lock or raise BenchmarkLockError."""
        existing = self._read_lock()
        if existing is not None:
            pid = existing.get("pid")
            if pid is not None and _pid_is_alive(int(pid)):
                raise BenchmarkLockError(
                    f"Another benchmark run is active (pid {pid}, "
                    f"started {existing.get('timestamp', '?')}, "
                    f"lock file: {self.lock_file}).\n"
                    "Stop that process or remove the lock file if it is stale."
                )
            # Stale lock – previous run died without cleanup.
            self.lock_file.unlink(missing_ok=True)

        payload: dict[str, Any] = {
            "pid": os.getpid(),
            "hostname": platform.node(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": " ".join(sys.argv),
            "provider": self._provider,
            "model": self._model,
            "output_path": self._output_path,
        }
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.lock_file.write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )
        self._acquired = True

    def release(self) -> None:
        """Release the lock if this instance owns it."""
        if not self._acquired:
            return
        try:
            existing = self._read_lock()
            if existing is not None and existing.get("pid") == os.getpid():
                self.lock_file.unlink(missing_ok=True)
        except OSError:
            pass
        self._acquired = False

    def __enter__(self) -> "BenchmarkLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_lock(self) -> dict[str, Any] | None:
        if not self.lock_file.exists():
            return None
        try:
            return json.loads(self.lock_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None


def _pid_is_alive(pid: int) -> bool:
    """Return True if the given PID is still running."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but we cannot signal it (different owner).
        return True
    except OSError:
        return False
