#!/usr/bin/env bash
# Benchmark-neutral baseline wrapper helpers.
#
# Callers must set before sourcing (or rely on defaults after setting):
#   BASELINE_NAME
#   BASELINE_OUTPUT_JSON_REL
#   BASELINE_OUTPUT_MD_REL
#   BASELINE_TEST_SET_REL
#   BASELINE_WRAPPER_NAME   (script filename for error messages)
#
# Model precedence (highest to lowest):
#   1. CLI --model VALUE / --model=VALUE
#   2. Pre-existing MODEL environment variable
#   3. MODEL from .env when previously unset
#   4. Default gemma4:e4b (override with BASELINE_DEFAULT_MODEL)

benchmark_baseline_parse_args() {
  CLI_MODEL=""
  FORWARD_ARGS=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --model)
        if [[ $# -lt 2 || -z "${2}" || "${2}" == --* ]]; then
          echo "ERROR: --model requires a non-empty value (got: ${2:-<missing>})" >&2
          return 2
        fi
        CLI_MODEL="$2"
        shift 2
        ;;
      --model=*)
        CLI_MODEL="${1#--model=}"
        if [[ -z "$CLI_MODEL" ]]; then
          echo "ERROR: --model= requires a non-empty value" >&2
          return 2
        fi
        shift
        ;;
      --provider|--provider=*|\
      --test-set|--test-set=*|\
      --output|--output=*|\
      --summary|--summary=*)
        echo "ERROR: refusing to override protected wrapper argument: $1" >&2
        echo "       ${BASELINE_WRAPPER_NAME:-baseline wrapper} owns provider/test-set/output/summary." >&2
        echo "       Canonical checkpoint paths:" >&2
        echo "         ${BASELINE_OUTPUT_JSON_REL}" >&2
        echo "         ${BASELINE_OUTPUT_MD_REL}" >&2
        return 2
        ;;
      *)
        FORWARD_ARGS+=("$1")
        shift
        ;;
    esac
  done
  return 0
}

benchmark_baseline_resolve_model() {
  local default_model="${BASELINE_DEFAULT_MODEL:-gemma4:e4b}"

  if [[ -n "${CLI_MODEL}" ]]; then
    MODEL="$CLI_MODEL"
  elif [[ "${BASELINE_ENV_MODEL_SET:-0}" == "1" ]]; then
    MODEL="$BASELINE_ENV_MODEL"
  else
    MODEL="${MODEL:-$default_model}"
  fi

  if [[ -z "$MODEL" ]]; then
    echo "ERROR: resolved MODEL is empty" >&2
    return 2
  fi
  return 0
}

benchmark_baseline_capture_preexisting_model() {
  if [[ -n "${MODEL+x}" ]]; then
    BASELINE_ENV_MODEL_SET=1
    BASELINE_ENV_MODEL="$MODEL"
  else
    BASELINE_ENV_MODEL_SET=0
    BASELINE_ENV_MODEL=""
  fi
}

benchmark_baseline_source_env_file() {
  local env_file="$1"
  local line key value

  [[ -f "$env_file" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" == export[[:space:]]* ]]; then
      line="${line#export}"
      line="${line#"${line%%[![:space:]]*}"}"
    fi
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    if [[ "$value" =~ ^\"(.*)\"$ ]]; then
      value="${BASH_REMATCH[1]}"
    elif [[ "$value" =~ ^\'(.*)\'$ ]]; then
      value="${BASH_REMATCH[1]}"
    fi
    if [[ -z "${!key+x}" ]]; then
      printf -v "$key" '%s' "$value"
      export "$key"
    fi
  done < "$env_file"
}
