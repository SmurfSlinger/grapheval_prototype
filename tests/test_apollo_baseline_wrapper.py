"""Focused tests for scripts/run_apollo_real_baseline.sh model resolution.

These tests exercise scripts/apollo_baseline_args.sh and the wrapper dry-run
path without requiring a real Ollama installation. They verify that the model
validated against Ollama is exactly the model passed to the benchmark runner.
"""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARGS_LIB = ROOT / "scripts" / "apollo_baseline_args.sh"
WRAPPER = ROOT / "scripts" / "run_apollo_real_baseline.sh"


def _run_resolve(
    *,
    cli_args: list[str] | None = None,
    env: dict[str, str] | None = None,
    dotenv: str | None = None,
    clear_model: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Source the shared helper and print resolved MODEL + forward args as JSON."""
    cli_args = cli_args or []
    work = Path(os.environ.get("TMPDIR", "/tmp")) / "apollo_wrapper_tests"
    work.mkdir(parents=True, exist_ok=True)

    dotenv_path = work / "dotenv.env"
    if dotenv is not None:
        dotenv_path.write_text(dotenv, encoding="utf-8")
    elif dotenv_path.exists():
        dotenv_path.unlink()

    quoted = " ".join(json.dumps(a) for a in cli_args)
    script = textwrap.dedent(
        f"""\
        set -euo pipefail
        source {json.dumps(str(ARGS_LIB))}
        apollo_baseline_parse_args {quoted} || exit $?
        apollo_baseline_capture_preexisting_model
        if [[ -f {json.dumps(str(dotenv_path))} ]]; then
          apollo_baseline_source_env_file {json.dumps(str(dotenv_path))}
        fi
        apollo_baseline_resolve_model || exit $?
        export MODEL
        export CLI_MODEL
        if ((${{#FORWARD_ARGS[@]}})); then
          FORWARD_JSON="$(printf '%s\\n' "${{FORWARD_ARGS[@]}}" | python3 -c 'import json,sys; print(json.dumps([line.rstrip("\\n") for line in sys.stdin]))')"
        else
          FORWARD_JSON='[]'
        fi
        export FORWARD_JSON
        python3 - <<'PY'
import json, os
print(json.dumps({{
    "model": os.environ["MODEL"],
    "forward_args": json.loads(os.environ["FORWARD_JSON"]),
    "cli_model": os.environ.get("CLI_MODEL", ""),
}}))
PY
        """
    )

    run_env = os.environ.copy()
    if clear_model:
        run_env.pop("MODEL", None)
    if env:
        run_env.update(env)

    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=run_env,
        cwd=str(ROOT),
        check=False,
    )


def _payload(proc: subprocess.CompletedProcess[str]) -> dict:
    assert proc.returncode == 0, f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def _run_wrapper_dry(
    cli_args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> dict:
    run_env = os.environ.copy()
    run_env.pop("MODEL", None)
    run_env["APOLLO_BASELINE_DRY_RUN"] = "1"
    if env:
        run_env.update(env)
    proc = subprocess.run(
        ["bash", str(WRAPPER), *cli_args],
        capture_output=True,
        text=True,
        env=run_env,
        cwd=str(ROOT),
        check=False,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r}\nstderr={proc.stderr!r}"
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_default_model_when_unset() -> None:
    data = _payload(_run_resolve())
    assert data["model"] == "gemma4:e2b"
    assert data["forward_args"] == []
    assert data["cli_model"] == ""


def test_model_from_environment() -> None:
    data = _payload(_run_resolve(env={"MODEL": "llama3:8b"}))
    assert data["model"] == "llama3:8b"
    assert data["cli_model"] == ""


def test_model_flag_space_form() -> None:
    data = _payload(_run_resolve(cli_args=["--model", "llama3:8b"]))
    assert data["model"] == "llama3:8b"
    assert data["cli_model"] == "llama3:8b"
    assert data["forward_args"] == []


def test_model_flag_equals_form() -> None:
    data = _payload(_run_resolve(cli_args=["--model=llama3:8b"]))
    assert data["model"] == "llama3:8b"
    assert data["cli_model"] == "llama3:8b"
    assert data["forward_args"] == []


def test_cli_model_overrides_environment() -> None:
    data = _payload(
        _run_resolve(
            cli_args=["--model", "llama3:8b"],
            env={"MODEL": "gemma4:e2b"},
        )
    )
    assert data["model"] == "llama3:8b"


def test_environment_overrides_dotenv() -> None:
    data = _payload(
        _run_resolve(
            env={"MODEL": "from-env:tag"},
            dotenv="MODEL=from-dotenv:tag\n",
        )
    )
    assert data["model"] == "from-env:tag"


def test_dotenv_used_when_env_unset() -> None:
    data = _payload(
        _run_resolve(
            dotenv="MODEL=from-dotenv:tag\nNUM_CTX=4096\n",
        )
    )
    assert data["model"] == "from-dotenv:tag"


def test_cli_overrides_dotenv_and_default() -> None:
    data = _payload(
        _run_resolve(
            cli_args=["--model=cli:tag"],
            dotenv="MODEL=from-dotenv:tag\n",
        )
    )
    assert data["model"] == "cli:tag"


def test_forward_args_preserve_non_model_flags() -> None:
    data = _payload(
        _run_resolve(
            cli_args=["--limit", "3", "--model", "llama3:8b", "--ids", "Q1"],
        )
    )
    assert data["model"] == "llama3:8b"
    assert data["forward_args"] == ["--limit", "3", "--ids", "Q1"]


def test_malformed_model_missing_value() -> None:
    proc = _run_resolve(cli_args=["--model"])
    assert proc.returncode == 2
    assert "requires a non-empty value" in proc.stderr


def test_malformed_model_empty_equals() -> None:
    proc = _run_resolve(cli_args=["--model="])
    assert proc.returncode == 2
    assert "requires a non-empty value" in proc.stderr


def test_malformed_model_value_looks_like_flag() -> None:
    proc = _run_resolve(cli_args=["--model", "--limit"])
    assert proc.returncode == 2
    assert "requires a non-empty value" in proc.stderr


def test_checked_model_matches_executed_model() -> None:
    """Resolved MODEL is used for both the Ollama check and the runner --model."""
    data = _run_wrapper_dry(["--model", "llama3:8b", "--limit", "1"])
    assert data["model"] == "llama3:8b"
    assert data["checked_model"] == data["executed_model"] == "llama3:8b"
    assert data["forward_args"] == ["--limit", "1"]
    assert "--model" not in data["forward_args"]


def test_wrapper_dry_run_equals_form_and_env_precedence() -> None:
    data = _run_wrapper_dry(
        ["--model=llama3:8b"],
        env={"MODEL": "gemma4:e2b"},
    )
    assert data["model"] == "llama3:8b"
    assert data["checked_model"] == data["executed_model"]


def test_wrapper_rejects_missing_model_before_ollama() -> None:
    """Malformed --model fails fast without needing Ollama."""
    env = os.environ.copy()
    env.pop("MODEL", None)
    proc = subprocess.run(
        ["bash", str(WRAPPER), "--model"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(ROOT),
        check=False,
    )
    assert proc.returncode == 2
    assert "requires a non-empty value" in proc.stderr
    assert "Verifying Ollama" not in proc.stdout
