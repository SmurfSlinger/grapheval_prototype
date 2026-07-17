"""Exclusive benchmark process lock.

A single JSON lock file under .runtime/ (or a caller-supplied path) guards
against two concurrent benchmark runs on the same machine.

Acquisition is atomic via ``O_CREAT | O_EXCL`` exclusive file creation.
Malformed or unreadable lock files fail safely instead of being overwritten.

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
    """Raised when the lock cannot be acquired safely."""


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
        self._lock_fd: int | None = None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Acquire the lock or raise BenchmarkLockError.

        Uses exclusive file creation (``O_CREAT | O_EXCL``) so two processes
        cannot both believe they own the lock. Stale locks left by dead PIDs
        are removed only when ownership can be verified from readable JSON.
        """
        if self._acquired:
            return
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        payload = self._payload()
        encoded = (json.dumps(payload, indent=2) + "\n").encode("utf-8")

        # Retry once after reclaiming a verified-stale lock.
        for _ in range(2):
            try:
                fd = os.open(
                    self.lock_file,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                    0o644,
                )
            except FileExistsError:
                self._reclaim_or_raise()
                continue
            try:
                os.write(fd, encoded)
                os.fsync(fd)
            except OSError:
                os.close(fd)
                try:
                    os.unlink(self.lock_file)
                except OSError:
                    pass
                raise
            self._lock_fd = fd
            self._acquired = True
            return

        raise BenchmarkLockError(
            f"Could not acquire benchmark lock at {self.lock_file} after retry."
        )

    def release(self) -> None:
        """Release the lock if this instance owns it."""
        if not self._acquired:
            return
        try:
            if self._lock_fd is not None:
                try:
                    os.close(self._lock_fd)
                except OSError:
                    pass
                self._lock_fd = None
            existing = self._read_lock_strict()
            if existing.get("pid") == os.getpid():
                self.lock_file.unlink(missing_ok=True)
        except BenchmarkLockError:
            # Ownership cannot be verified; leave the file for manual review.
            pass
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

    def _payload(self) -> dict[str, Any]:
        return {
            "pid": os.getpid(),
            "hostname": platform.node(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": " ".join(sys.argv),
            "provider": self._provider,
            "model": self._model,
            "output_path": self._output_path,
        }

    def _read_lock_strict(self) -> dict[str, Any]:
        """Read and parse the lock file, failing safely on malformation."""
        try:
            raw = self.lock_file.read_text(encoding="utf-8")
        except OSError as exc:
            raise BenchmarkLockError(
                f"Benchmark lock file exists but cannot be read "
                f"({self.lock_file}): {exc}. "
                "Resolve ownership manually; refusing to overwrite."
            ) from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise BenchmarkLockError(
                f"Benchmark lock file is malformed JSON ({self.lock_file}): "
                f"{exc}. Resolve ownership manually; refusing to overwrite."
            ) from exc
        if not isinstance(data, dict):
            raise BenchmarkLockError(
                f"Benchmark lock file has unexpected shape ({self.lock_file}). "
                "Resolve ownership manually; refusing to overwrite."
            )
        return data

    def _reclaim_or_raise(self) -> None:
        existing = self._read_lock_strict()
        pid = existing.get("pid")
        try:
            pid_int = int(pid)
        except (TypeError, ValueError) as exc:
            raise BenchmarkLockError(
                f"Benchmark lock file has unverifiable pid "
                f"({self.lock_file}: pid={pid!r}). "
                "Resolve ownership manually; refusing to overwrite."
            ) from exc
        if _pid_is_alive(pid_int):
            raise BenchmarkLockError(
                f"Another benchmark run is active (pid {pid_int}, "
                f"started {existing.get('timestamp', '?')}, "
                f"lock file: {self.lock_file}).\n"
                "Stop that process or remove the lock file if it is stale."
            )
        # Verified stale: previous holder is dead.
        try:
            self.lock_file.unlink()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise BenchmarkLockError(
                f"Stale benchmark lock could not be removed "
                f"({self.lock_file}): {exc}."
            ) from exc


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
