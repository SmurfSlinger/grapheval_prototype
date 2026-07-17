#!/usr/bin/env bash
# NHS WannaCry aliases over the shared baseline helpers.

BASELINE_NAME="NHS WannaCry"
BASELINE_OUTPUT_JSON_REL="results/nhs_wannacry_multihop_real_baseline.json"
BASELINE_OUTPUT_MD_REL="results/nhs_wannacry_multihop_real_baseline.md"
BASELINE_TEST_SET_REL="data/test_sets/nhs_wannacry_multihop_50.json"
BASELINE_WRAPPER_NAME="run_nhs_wannacry_real_baseline.sh"
BASELINE_DEFAULT_MODEL="${BASELINE_DEFAULT_MODEL:-gemma4:e2b}"

NHS_WANNACRY_BASELINE_OUTPUT_JSON_REL="$BASELINE_OUTPUT_JSON_REL"
NHS_WANNACRY_BASELINE_OUTPUT_MD_REL="$BASELINE_OUTPUT_MD_REL"
NHS_WANNACRY_BASELINE_TEST_SET_REL="$BASELINE_TEST_SET_REL"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=benchmark_baseline_args.sh
source "$SCRIPT_DIR/benchmark_baseline_args.sh"

nhs_wannacry_baseline_parse_args() { benchmark_baseline_parse_args "$@"; }
nhs_wannacry_baseline_resolve_model() { benchmark_baseline_resolve_model; }
nhs_wannacry_baseline_capture_preexisting_model() { benchmark_baseline_capture_preexisting_model; }
nhs_wannacry_baseline_source_env_file() { benchmark_baseline_source_env_file "$@"; }
