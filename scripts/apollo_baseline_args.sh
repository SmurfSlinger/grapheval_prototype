#!/usr/bin/env bash
# Apollo-compatible aliases over the shared baseline helpers.

BASELINE_NAME="${BASELINE_NAME:-Apollo}"
BASELINE_OUTPUT_JSON_REL="${BASELINE_OUTPUT_JSON_REL:-results/apollo_multihop_real_baseline.json}"
BASELINE_OUTPUT_MD_REL="${BASELINE_OUTPUT_MD_REL:-results/apollo_multihop_real_baseline.md}"
BASELINE_TEST_SET_REL="${BASELINE_TEST_SET_REL:-data/test_sets/apollo_multihop_50.json}"
BASELINE_WRAPPER_NAME="${BASELINE_WRAPPER_NAME:-run_apollo_real_baseline.sh}"
BASELINE_DEFAULT_MODEL="${BASELINE_DEFAULT_MODEL:-${APOLLO_DEFAULT_MODEL:-gemma4:e2b}}"

APOLLO_BASELINE_OUTPUT_JSON_REL="$BASELINE_OUTPUT_JSON_REL"
APOLLO_BASELINE_OUTPUT_MD_REL="$BASELINE_OUTPUT_MD_REL"
APOLLO_BASELINE_TEST_SET_REL="$BASELINE_TEST_SET_REL"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=benchmark_baseline_args.sh
source "$SCRIPT_DIR/benchmark_baseline_args.sh"

apollo_baseline_parse_args() { benchmark_baseline_parse_args "$@"; }

apollo_baseline_capture_preexisting_model() {
  benchmark_baseline_capture_preexisting_model
  APOLLO_ENV_MODEL_SET="${BASELINE_ENV_MODEL_SET}"
  APOLLO_ENV_MODEL="${BASELINE_ENV_MODEL}"
}

apollo_baseline_resolve_model() {
  BASELINE_DEFAULT_MODEL="${APOLLO_DEFAULT_MODEL:-${BASELINE_DEFAULT_MODEL:-gemma4:e2b}}"
  if [[ "${APOLLO_ENV_MODEL_SET:-0}" == "1" ]]; then
    BASELINE_ENV_MODEL_SET=1
    BASELINE_ENV_MODEL="${APOLLO_ENV_MODEL:-}"
  fi
  benchmark_baseline_resolve_model
}

apollo_baseline_source_env_file() { benchmark_baseline_source_env_file "$@"; }
