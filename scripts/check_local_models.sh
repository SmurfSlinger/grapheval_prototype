#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

base_url="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
default_model="${DEFAULT_MODEL:-gemma4:e4b}"
num_ctx="${OLLAMA_NUM_CTX:-not set}"

echo "GraphEval local model audit"
echo "OLLAMA_BASE_URL=$base_url"
echo "DEFAULT_MODEL=$default_model"
echo "OLLAMA_NUM_CTX=$num_ctx"

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama installed: no"
  echo "WARNING: Install Ollama before using the local provider."
  exit 1
fi

echo "Ollama installed: yes"
if ! timeout 5s ollama --version; then
  echo "WARNING: 'ollama --version' did not complete within 5 seconds."
fi

tags_json="$(curl --silent --show-error --connect-timeout 2 --max-time 5 \
  "${base_url%/}/api/tags" 2>/dev/null || true)"
if [[ -z "$tags_json" ]]; then
  echo "WARNING: Ollama is installed but /api/tags did not respond within 5 seconds."
  echo "Start it with: ollama serve"
  exit 1
fi

TAGS_JSON="$tags_json" DEFAULT_MODEL_AUDIT="$default_model" python3 - <<'PY'
import json
import os

try:
    data = json.loads(os.environ["TAGS_JSON"])
except (KeyError, json.JSONDecodeError) as exc:
    print(f"WARNING: Ollama /api/tags returned invalid JSON: {exc}")
    raise SystemExit(1)

names = [str(item.get("name", "")) for item in data.get("models", [])]
print("\nInstalled local models:")
if names:
    for name in names:
        print(name)
else:
    print("(none)")

gemma = [name for name in names if name.lower().split(":", 1)[0] == "gemma4"]
print("\nInstalled gemma4-related tags:")
if gemma:
    print("\n".join(gemma))
else:
    print("(none)")
    print(
        "WARNING: No gemma4 tag is installed. Example: "
        f"ollama pull {os.environ['DEFAULT_MODEL_AUDIT']}"
    )

configured = os.environ["DEFAULT_MODEL_AUDIT"]
if configured not in names:
    print(f"WARNING: Configured DEFAULT_MODEL '{configured}' is not listed locally.")
PY

echo
echo "Quantization/full-precision note:"
echo "This audit reports only locally visible tags. Use 'ollama show <tag>' to inspect"
echo "a model's details; do not assume a full-precision tag exists unless it is listed."
