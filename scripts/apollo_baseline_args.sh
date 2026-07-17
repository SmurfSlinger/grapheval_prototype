#!/usr/bin/env bash
# Shared argument/model resolution for run_apollo_real_baseline.sh.
#
# Precedence for MODEL (highest to lowest):
#   1. CLI: --model VALUE or --model=VALUE
#   2. Pre-existing environment variable MODEL (set before the wrapper runs)
#   3. MODEL from .env (only applied when MODEL was not already set)
#   4. Default: gemma4:e2b
#
# This file is safe to source from tests. It does not talk to Ollama or run
# the benchmark.

# Parse wrapper argv. Sets:
#   CLI_MODEL          - model from --model / --model=... (empty if absent)
#   FORWARD_ARGS       - remaining args to pass through to the Python runner
# Exits 2 on malformed --model usage.
apollo_baseline_parse_args() {
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
      *)
        FORWARD_ARGS+=("$1")
        shift
        ;;
    esac
  done
  return 0
}

# Resolve MODEL after optional .env load.
#
# Inputs:
#   CLI_MODEL                  - from apollo_baseline_parse_args (may be empty)
#   APOLLO_ENV_MODEL_SET       - "1" if MODEL was set in the environment before .env
#   APOLLO_ENV_MODEL           - that pre-existing MODEL value (may be empty string)
#   MODEL                      - current MODEL after optional .env sourcing
#   APOLLO_DEFAULT_MODEL       - optional override of the default (tests)
#
# Output:
#   MODEL - the effective model tag that must be both validated and executed
apollo_baseline_resolve_model() {
  local default_model="${APOLLO_DEFAULT_MODEL:-gemma4:e2b}"

  if [[ -n "${CLI_MODEL}" ]]; then
    MODEL="$CLI_MODEL"
  elif [[ "${APOLLO_ENV_MODEL_SET:-0}" == "1" ]]; then
    MODEL="$APOLLO_ENV_MODEL"
  else
    MODEL="${MODEL:-$default_model}"
  fi

  if [[ -z "$MODEL" ]]; then
    echo "ERROR: resolved MODEL is empty" >&2
    return 2
  fi
  return 0
}

# Capture whether MODEL is already set in the environment (before sourcing .env).
# Sets APOLLO_ENV_MODEL_SET and APOLLO_ENV_MODEL.
apollo_baseline_capture_preexisting_model() {
  if [[ -n "${MODEL+x}" ]]; then
    APOLLO_ENV_MODEL_SET=1
    APOLLO_ENV_MODEL="$MODEL"
  else
    APOLLO_ENV_MODEL_SET=0
    APOLLO_ENV_MODEL=""
  fi
}

# Source a .env file without clobbering variables that are already set.
# Only assigns KEY=VALUE lines for keys that are currently unset.
# Normal unguarded `source .env` WOULD overwrite existing shell variables;
# this helper intentionally does not.
apollo_baseline_source_env_file() {
  local env_file="$1"
  local line key value

  [[ -f "$env_file" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    # Trim leading whitespace.
    line="${line#"${line%%[![:space:]]*}"}"
    [[ -z "$line" || "$line" == \#* ]] && continue

    # Support optional leading "export ".
    if [[ "$line" == export[[:space:]]* ]]; then
      line="${line#export}"
      line="${line#"${line%%[![:space:]]*}"}"
    fi

    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"

    # Strip optional surrounding single/double quotes.
    if [[ "$value" =~ ^\"(.*)\"$ ]]; then
      value="${BASH_REMATCH[1]}"
    elif [[ "$value" =~ ^\'(.*)\'$ ]]; then
      value="${BASH_REMATCH[1]}"
    fi

    # Only assign when the variable is currently unset.
    if [[ -z "${!key+x}" ]]; then
      printf -v "$key" '%s' "$value"
      export "$key"
    fi
  done < "$env_file"
}
