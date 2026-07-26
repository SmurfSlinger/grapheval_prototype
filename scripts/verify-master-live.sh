#!/usr/bin/env bash
# Live master verification: requires docker Neo4j + Ollama model. Never mock-falls-back.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

PYTHON="${ROOT}/.venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

REPORT_DIR="$ROOT/results"
mkdir -p "$REPORT_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="$REPORT_DIR/verify-master-live_${STAMP}.txt"

exec > >(tee "$REPORT") 2>&1

fail() {
  echo "verify-master-live: FAIL — $*" >&2
  exit 1
}

echo "verify-master-live report: $REPORT"
echo "timestamp_utc=$STAMP"
echo "DEFAULT_MODEL=${DEFAULT_MODEL:-unset}"
echo "OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
echo "NEO4J_URI=${NEO4J_URI:-bolt://localhost:7687}"

command -v docker >/dev/null 2>&1 || fail "docker is required"
command -v ollama >/dev/null 2>&1 || fail "ollama is required"

echo "==> checking Ollama tags / configured model"
"$ROOT/scripts/check_local_models.sh" || fail "local model audit failed"

MODEL="${DEFAULT_MODEL:-gemma4:e4b}"
export DEFAULT_MODEL="$MODEL"
OLLAMA_BASE="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
OLLAMA_BASE="${OLLAMA_BASE%/}"
TAGS_JSON="$(curl --silent --show-error --connect-timeout 2 --max-time 5 \
  "${OLLAMA_BASE}/api/tags" 2>/dev/null || true)"
[[ -n "$TAGS_JSON" ]] || fail "Ollama /api/tags did not respond"
echo "$TAGS_JSON" | "$PYTHON" -c "
import json, os, sys
data = json.load(sys.stdin)
names = {str(item.get('name','')) for item in data.get('models', [])}
model = os.environ.get('DEFAULT_MODEL', '')
if model not in names:
    raise SystemExit(f'configured model {model!r} not installed')
print(f'model_ok={model}')
" || fail "required Ollama model missing"

echo "==> checking Neo4j Bolt"
export NEO4J_ENABLED=true
"$PYTHON" - <<'PY' || fail "Neo4j connectivity check failed"
from src.storage.neo4j_store import neo4j_status
status = neo4j_status(required_for_this_route=True)
print(status)
if not status.get("connected"):
    raise SystemExit(status.get("error") or "neo4j not connected")
PY

echo "==> live Neo4j pytest"
export GRAPHEVAL_LIVE_NEO4J=1
"$PYTHON" -m pytest tests/test_neo4j_live_integration.py -q --tb=short \
  || fail "live Neo4j tests failed"

echo "==> bounded live Ollama pytest (no mock fallback)"
export GRAPHEVAL_LIVE_OLLAMA=1
"$PYTHON" -m pytest tests/test_live_ollama_bounded.py -q --tb=short \
  || fail "live Ollama tests failed"

echo "verify-master-live: OK"
echo "report_written=$REPORT"
