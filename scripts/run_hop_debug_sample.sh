#!/usr/bin/env bash
# Bounded 1/2/3-hop Apollo debug sample for GraphEval research.
# Does not pass expected answers into inference.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODEL="${MODEL:-gemma4:e4b}"
NUM_CTX="${NUM_CTX:-32768}"
TIMEOUT_PER_QUESTION="${TIMEOUT_PER_QUESTION:-300}"
PROVIDER="${PROVIDER:-ollama}"
TEST_SET="data/test_sets/apollo_multihop_50.json"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/run_hop_debug_sample.sh [--model TAG] [--num-ctx N] [--timeout-per-question SECONDS]

Runs one Apollo question at hop 1, hop 2, and hop 3.
Enables GRAPHEVAL_DEBUG_LOGS and clears Neo4j between questions.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --num-ctx)
      NUM_CTX="$2"
      shift 2
      ;;
    --timeout-per-question)
      TIMEOUT_PER_QUESTION="$2"
      shift 2
      ;;
    --provider)
      PROVIDER="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="results/hop_debug/${STAMP}"
mkdir -p "$OUT_DIR"

export GRAPHEVAL_DEBUG_LOGS=true
export OLLAMA_NUM_CTX="$NUM_CTX"

CLEAR_NEO4J_ARGS=(--clear-neo4j)
if ! python3 - <<'PY'
import os
from neo4j import GraphDatabase

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "password123")
try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    driver.close()
except Exception:
    raise SystemExit(1)
PY
then
  echo "[warn] Neo4j is unavailable; continuing without --clear-neo4j / Neo4j readback."
  CLEAR_NEO4J_ARGS=()
fi

QUESTION_IDS=(
  "apollo_hop_001"  # hop 1
  "apollo_hop_006"  # hop 2
  "apollo_hop_011"  # hop 3
)

echo "Hop debug sample"
echo "  model=$MODEL"
echo "  num_ctx=$NUM_CTX"
echo "  timeout_per_question=$TIMEOUT_PER_QUESTION"
echo "  provider=$PROVIDER"
echo "  output=$OUT_DIR"
echo

SUMMARY_JSON="$OUT_DIR/summary.json"
python3 - <<'PY' >"$SUMMARY_JSON"
import json
print(json.dumps({"runs": []}, indent=2))
PY

for QID in "${QUESTION_IDS[@]}"; do
  echo "============================================================"
  echo "Running $QID"
  echo "============================================================"
  OUT_JSON="$OUT_DIR/${QID}.json"
  OUT_MD="$OUT_DIR/${QID}.md"
  set +e
  python3 scripts/run_multihop_benchmark.py \
    --test-set "$TEST_SET" \
    --provider "$PROVIDER" \
    --model "$MODEL" \
    --num-ctx "$NUM_CTX" \
    --ids "$QID" \
    --timeout-per-question "$TIMEOUT_PER_QUESTION" \
    --continue-on-error \
    "${CLEAR_NEO4J_ARGS[@]}" \
    --output "$OUT_JSON" \
    --summary "$OUT_MD"
  STATUS=$?
  set -e

  python3 - <<PY
import json
from pathlib import Path

out_dir = Path("$OUT_DIR")
qid = "$QID"
status = $STATUS
summary_path = out_dir / "summary.json"
row = {
    "question_id": qid,
    "exit_status": status,
    "result_json": str(out_dir / f"{qid}.json"),
    "result_md": str(out_dir / f"{qid}.md"),
}
result_path = out_dir / f"{qid}.json"
if result_path.exists():
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    rows = payload.get("rows") or payload.get("results") or []
    if rows:
        r = rows[0]
        row.update({
            "hop_count": r.get("hop_count"),
            "model": r.get("model"),
            "num_ctx": r.get("configured_num_ctx") or r.get("num_ctx"),
            "runtime_seconds": r.get("runtime_seconds") or r.get("elapsed_seconds"),
            "final_answer": r.get("predicted_answer") or r.get("combined_answer"),
            "exact_match": r.get("exact_match"),
            "contains_expected": r.get("contains_expected_answer"),
            "pipeline_resolved": r.get("resolved_by_pipeline"),
            "stop_reason": r.get("final_stop_reason") or r.get("failure_category"),
            "fact_count": r.get("fact_count") or r.get("fact_edges_written"),
            "claim_count": r.get("claim_count") or r.get("claim_edges_written"),
            "debug_log_path": r.get("debug_log_path"),
            "structured_triple_anomaly_count": r.get("structured_triple_anomaly_count"),
            "error": r.get("error"),
        })
summary = json.loads(summary_path.read_text(encoding="utf-8"))
summary.setdefault("runs", []).append(row)
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(row, indent=2))
PY

  echo
  echo "Debug logs under .runtime/debug/ (if enabled):"
  ls -1 .runtime/debug 2>/dev/null | tail -n 20 || true
  echo
done

echo "Wrote hop-debug sample to $OUT_DIR"
echo "Summary: $SUMMARY_JSON"
cat "$SUMMARY_JSON"
