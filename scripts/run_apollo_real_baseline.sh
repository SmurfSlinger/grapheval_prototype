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
# Model selection precedence (highest to lowest):
#   1. CLI: --model VALUE or --model=VALUE
#   2. Pre-existing environment variable MODEL
#   3. MODEL from .env (applied only when MODEL was not already set)
#   4. Default: gemma4:e4b
#
# Canonical checkpoint paths (resume requires these exact files):
#   results/apollo_multihop_real_baseline.json
#   results/apollo_multihop_real_baseline.md
#
# Protected (rejected): --provider, --test-set, --output, --summary
# Forwardable tuning examples: --limit, --ids, --start-at, --stop-after-minutes,
#   --retry-errors, --rerun-completed, timeout/cooldown/num-ctx controls
#
# The model validated against Ollama is exactly the model passed to the runner.
# Example:
#   ./scripts/run_apollo_real_baseline.sh --model llama3:8b

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Find repository root and load shared arg helpers
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

# shellcheck source=apollo_baseline_args.sh
source "$SCRIPT_DIR/apollo_baseline_args.sh"

# ---------------------------------------------------------------------------
# 2. Parse CLI --model before any availability checks
# ---------------------------------------------------------------------------
apollo_baseline_parse_args "$@" || exit $?

# ---------------------------------------------------------------------------
# 3. Load .env without overriding pre-existing environment variables
# ---------------------------------------------------------------------------
apollo_baseline_capture_preexisting_model
if [[ -f "$ROOT/.env" ]]; then
  apollo_baseline_source_env_file "$ROOT/.env"
  echo "[env] Loaded unset keys from $ROOT/.env (existing env vars preserved)"
else
  echo "[env] No .env found; using environment variables as-is."
  echo "      Copy .env.example to .env and edit it before running."
fi

# ---------------------------------------------------------------------------
# 4. Resolve effective model, then apply remaining configuration defaults
# ---------------------------------------------------------------------------
apollo_baseline_resolve_model || exit $?

NUM_CTX="${NUM_CTX:-32768}"
TIMEOUT_PER_QUESTION="${TIMEOUT_PER_QUESTION:-300}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-3}"
MAX_CONSECUTIVE_TIMEOUTS="${MAX_CONSECUTIVE_TIMEOUTS:-5}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

OUTPUT_JSON="$ROOT/$APOLLO_BASELINE_OUTPUT_JSON_REL"
OUTPUT_MD="$ROOT/$APOLLO_BASELINE_OUTPUT_MD_REL"
TEST_SET="$ROOT/$APOLLO_BASELINE_TEST_SET_REL"

# ---------------------------------------------------------------------------
# 5. Locate Python
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
echo "[model] Effective model: $MODEL"

# Optional dry-run for tests: resolve model/args without contacting Ollama.
# The validated model and the runner --model value are the same resolved MODEL.
if [[ "${APOLLO_BASELINE_DRY_RUN:-0}" == "1" ]]; then
  export MODEL
  export OUTPUT_JSON OUTPUT_MD TEST_SET
  export OUTPUT_JSON_REL="$APOLLO_BASELINE_OUTPUT_JSON_REL"
  export OUTPUT_MD_REL="$APOLLO_BASELINE_OUTPUT_MD_REL"
  export TEST_SET_REL="$APOLLO_BASELINE_TEST_SET_REL"
  if ((${#FORWARD_ARGS[@]})); then
    FORWARD_JSON="$(printf '%s\n' "${FORWARD_ARGS[@]}" | python3 -c 'import json,sys; print(json.dumps([line.rstrip("\n") for line in sys.stdin]))')"
  else
    FORWARD_JSON='[]'
  fi
  export FORWARD_JSON
  python3 - <<'PY'
import json, os
model = os.environ["MODEL"]
forward = json.loads(os.environ["FORWARD_JSON"])
print(json.dumps({
    "model": model,
    "checked_model": model,
    "executed_model": model,
    "forward_args": forward,
    "provider": "ollama",
    "resume": True,
    "output_json": os.environ["OUTPUT_JSON"],
    "output_md": os.environ["OUTPUT_MD"],
    "test_set": os.environ["TEST_SET"],
    "output_json_rel": os.environ["OUTPUT_JSON_REL"],
    "output_md_rel": os.environ["OUTPUT_MD_REL"],
    "test_set_rel": os.environ["TEST_SET_REL"],
}))
PY
  exit 0
fi

# ---------------------------------------------------------------------------
# 6. Verify Ollama is reachable
# ---------------------------------------------------------------------------
echo "[check] Verifying Ollama at $OLLAMA_BASE_URL ..."
if ! curl -sf "$OLLAMA_BASE_URL/api/tags" >/dev/null 2>&1; then
  echo "ERROR: Ollama is not reachable at $OLLAMA_BASE_URL"
  echo "       Start Ollama and ensure it is listening, then re-run this script."
  exit 1
fi
echo "[check] Ollama is reachable."

# ---------------------------------------------------------------------------
# 7. Verify the resolved model is installed (exact tag match)
# ---------------------------------------------------------------------------
echo "[check] Verifying model '$MODEL' is installed in Ollama ..."
if ! curl -sf "$OLLAMA_BASE_URL/api/tags" | MODEL="$MODEL" python3 -c "
import json, os, sys
tags = json.load(sys.stdin)
names = {m.get('name', '') for m in tags.get('models', [])}
model = os.environ['MODEL']
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
# 8. Verify no active benchmark lock
# ---------------------------------------------------------------------------
LOCK_FILE="$ROOT/.runtime/benchmark.lock"
if [[ -f "$LOCK_FILE" ]]; then
  LOCKED_PID=$(LOCK_FILE="$LOCK_FILE" python3 -c "import json, os; d=json.load(open(os.environ['LOCK_FILE'])); print(d.get('pid','?'))" 2>/dev/null || echo "?")
  if [[ "$LOCKED_PID" != "?" ]] && kill -0 "$LOCKED_PID" 2>/dev/null; then
    echo "ERROR: Another benchmark run is active (pid $LOCKED_PID, lock file: $LOCK_FILE)."
    echo "       Stop that process or remove the lock file if it is stale."
    exit 1
  else
    echo "[check] Stale lock file found; the python runner will clean it up."
  fi
fi

# ---------------------------------------------------------------------------
# 9. Validate benchmark dataset
# ---------------------------------------------------------------------------
echo "[check] Validating benchmark dataset ..."
"$PYTHON" "$SCRIPT_DIR/run_multihop_benchmark.py" \
  --test-set "$TEST_SET" \
  --validate-only
echo "[check] Dataset is valid."

# ---------------------------------------------------------------------------
# 10. Run the benchmark with the same resolved model
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
  "${FORWARD_ARGS[@]+"${FORWARD_ARGS[@]}"}"
