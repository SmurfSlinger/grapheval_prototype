#!/usr/bin/env bash
# Non-destructive master verification (no live Neo4j / Ollama requirements).
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

echo "==> compileall"
"$PYTHON" -m compileall -q src api scripts tests

echo "==> pytest (excluding live neo4j/ollama)"
"$PYTHON" -m pytest tests/ -q --tb=line \
  -k "not live_neo4j and not live_ollama"

echo "==> benchmark validate-only (apollo)"
"$PYTHON" scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/apollo_multihop_50.json \
  --validate-only

echo "==> benchmark validate-only (nhs wannacry)"
"$PYTHON" scripts/run_multihop_benchmark.py \
  --test-set data/test_sets/nhs_wannacry_multihop_50.json \
  --validate-only

if command -v node >/dev/null 2>&1 && [[ -d "$ROOT/frontend" ]]; then
  echo "==> frontend npm ci / build / lint"
  (
    cd "$ROOT/frontend"
    npm ci
    npm run build
    npm run lint
  )
else
  echo "==> frontend skipped (node not present)"
fi

echo "verify-master: OK"
