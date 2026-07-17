#!/usr/bin/env bash
# Run the Apollo multi-hop real baseline benchmark on the user's local machine.
#
# Prerequisites (must be present before running this script):
#   1. Neo4j running locally  (see docs/LOCAL_NEO4J_RUN.md)
#   2. Ollama running locally (see docs/LOCAL_NEO4J_RUN.md)
#   3. Python dependencies installed (.venv or system)
#
# Usage:
#   ./scripts/run_apollo_real_baseline.sh [extra python runner args]
#
# The script passes all extra arguments through to run_multihop_benchmark.py.
# Example with a different model:
#   ./scripts/run_apollo_real_baseline.sh --model llama3:8b

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Find repository root
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# ---------------------------------------------------------------------------
# 2. Load .env when present (does NOT override existing env vars)
# ---------------------------------------------------------------------------
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
  echo "[env] Loaded .env from $ROOT/.env"
else
  echo "[env] No .env found; using environment variables as-is."
  echo "      Copy .env.example to .env and edit it before running."
fi

# ---------------------------------------------------------------------------
# 3. Configuration (override via .env or environment before running)
# ---------------------------------------------------------------------------
MODEL="${MODEL:-gemma4:e2b}"
NUM_CTX="${NUM_CTX:-32768}"
TIMEOUT_PER_QUESTION="${TIMEOUT_PER_QUESTION:-300}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-3}"
MAX_CONSECUTIVE_TIMEOUTS="${MAX_CONSECUTIVE_TIMEOUTS:-5}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

OUTPUT_JSON="$ROOT/results/apollo_multihop_real_report.json"
OUTPUT_MD="$ROOT/results/apollo_multihop_real_summary.md"
TEST_SET="$ROOT/data/test_sets/apollo_multihop_50.json"

# ---------------------------------------------------------------------------
# 4. Locate Python
# ---------------------------------------------------------------------------
PYTHON=""
for candidate in "$ROOT/.venv/bin/python" python3 python; do
  if command -v "$candidate" &>/dev/null || [[ -x "$candidate" ]]; then
    PYTHON="$candidate"
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "ERROR: Python not found. Install Python 3.10+ or create a .venv."
  exit 1
fi

echo "[python] Using: $PYTHON"

# ---------------------------------------------------------------------------
# 5. Verify Ollama is reachable
# ---------------------------------------------------------------------------
echo "[check] Verifying Ollama at $OLLAMA_BASE_URL ..."
if ! curl -sf "$OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1; then
  echo "ERROR: Ollama is not reachable at $OLLAMA_BASE_URL"
  echo "       Start Ollama and ensure it is listening, then re-run this script."
  exit 1
fi
echo "[check] Ollama is reachable."

# ---------------------------------------------------------------------------
# 6. Verify the requested model is installed
# ---------------------------------------------------------------------------
echo "[check] Verifying model '$MODEL' is installed in Ollama ..."
if ! curl -sf "$OLLAMA_BASE_URL/api/tags" | python3 -c "
import json, sys
tags = json.load(sys.stdin)
names = {m.get('name', '') for m in tags.get('models', [])}
model = '$MODEL'
# Require an exact installed tag match (gemma4:latest must not satisfy gemma4:e2b).
sys.exit(0 if model in names else 1)
" 2>/dev/null; then
  echo ""
  echo "WARNING: Model '$MODEL' does not appear to be installed in Ollama."
  echo "         An exact tag match is required (for example gemma4:latest does"
  echo "         NOT satisfy a request for gemma4:e2b)."
  echo "         To install it, run the following command (this may download several GB):"
  echo ""
  echo "             ollama pull $MODEL"
  echo ""
  echo "         Do NOT run this script automatically — download it manually first."
  echo "         Once the model is installed, re-run this script."
  exit 1
fi
echo "[check] Model '$MODEL' is available (exact tag match)."

# ---------------------------------------------------------------------------
# 7. Verify no active benchmark lock
# ---------------------------------------------------------------------------
LOCK_FILE="$ROOT/.runtime/benchmark.lock"
if [[ -f "$LOCK_FILE" ]]; then
  LOCKED_PID=$(python3 -c "import json; d=json.load(open('$LOCK_FILE')); print(d.get('pid','?'))" 2>/dev/null || echo "?")
  if [[ "$LOCKED_PID" != "?" ]] && kill -0 "$LOCKED_PID" 2>/dev/null; then
    echo "ERROR: Another benchmark run is active (pid $LOCKED_PID, lock file: $LOCK_FILE)."
    echo "       Stop that process or remove the lock file if it is stale."
    exit 1
  else
    echo "[check] Stale lock file found; the python runner will clean it up."
  fi
fi

# ---------------------------------------------------------------------------
# 8. Validate benchmark dataset
# ---------------------------------------------------------------------------
echo "[check] Validating benchmark dataset ..."
"$PYTHON" "$SCRIPT_DIR/run_multihop_benchmark.py" \
  --test-set "$TEST_SET" \
  --validate-only
echo "[check] Dataset is valid."

# ---------------------------------------------------------------------------
# 9. Run the benchmark
# ---------------------------------------------------------------------------
echo ""
echo "========================================================"
echo " Starting Apollo multi-hop REAL baseline"
echo "========================================================"
echo " Model:           $MODEL"
echo " num_ctx:         $NUM_CTX"
echo " Timeout/q:       ${TIMEOUT_PER_QUESTION}s"
echo " Cooldown:        ${COOLDOWN_SECONDS}s"
echo " Max consec. TO:  $MAX_CONSECUTIVE_TIMEOUTS"
echo " Output JSON:     $OUTPUT_JSON"
echo " Output Markdown: $OUTPUT_MD"
echo " Resume:          enabled (will skip completed questions)"
echo "========================================================"
echo ""

exec "$PYTHON" "$SCRIPT_DIR/run_multihop_benchmark.py" \
  --test-set "$TEST_SET" \
  --provider ollama \
  --model "$MODEL" \
  --num-ctx "$NUM_CTX" \
  --clear-neo4j \
  --timeout-per-question "$TIMEOUT_PER_QUESTION" \
  --continue-on-error \
  --resume \
  --cooldown-seconds "$COOLDOWN_SECONDS" \
  --max-consecutive-timeouts "$MAX_CONSECUTIVE_TIMEOUTS" \
  --output "$OUTPUT_JSON" \
  --summary "$OUTPUT_MD" \
  "$@"
