#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="$ROOT/.runtime/services"
API_PID_FILE="$RUNTIME_DIR/api.pid"
FRONTEND_PID_FILE="$RUNTIME_DIR/frontend.pid"
API_LOG="$RUNTIME_DIR/api.log"
FRONTEND_LOG="$RUNTIME_DIR/frontend.log"
API_URL="http://127.0.0.1:8000"
FRONTEND_URL="http://127.0.0.1:3000"
NEO4J_URI_DEFAULT="${NEO4J_URI:-bolt://127.0.0.1:7687}"
NEO4J_HOSTPORT="${NEO4J_URI_DEFAULT#*://}"
NEO4J_HOST="${NEO4J_HOSTPORT%%:*}"
NEO4J_PORT="${NEO4J_HOSTPORT##*:}"

mkdir -p "$RUNTIME_DIR"

die() {
  echo "Error: $*" >&2
  exit 1
}

require_repo() {
  [[ -d "$ROOT" ]] || die "Repository root not found: $ROOT"
  [[ -x "$ROOT/.venv/bin/uvicorn" ]] || die "Missing executable: $ROOT/.venv/bin/uvicorn"
  [[ -f "$ROOT/frontend/package.json" ]] || die "Missing file: $ROOT/frontend/package.json"
}

read_pid_file() {
  local pid_file=$1
  [[ -f "$pid_file" ]] || return 1
  local pid
  pid="$(tr -d '[:space:]' < "$pid_file")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  printf '%s\n' "$pid"
}

process_alive() {
  local pid=$1
  kill -0 "$pid" 2>/dev/null
}

pid_cwd() {
  local pid=$1
  python3 - "$pid" <<'PY' 2>/dev/null || true
import pathlib
import sys

print(pathlib.Path(f"/proc/{sys.argv[1]}/cwd").resolve())
PY
}

pid_cmdline() {
  local pid=$1
  tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true
}

pid_env_value() {
  local pid=$1 key=$2
  tr '\0' '\n' < "/proc/$pid/environ" 2>/dev/null | awk -F= -v key="$key" '$1 == key { sub(/^[^=]*=/, ""); print; exit }'
}

matches_api_pid() {
  local pid=$1
  local cwd cmd
  cwd="$(pid_cwd "$pid")"
  cmd="$(pid_cmdline "$pid")"
  [[ "$cwd" == "$ROOT" ]] || return 1
  [[ "$cmd" == *"api.server:app"* ]] || return 1
}

matches_frontend_pid() {
  local pid=$1
  local cwd cmd
  cwd="$(pid_cwd "$pid")"
  cmd="$(pid_cmdline "$pid")"
  [[ "$cwd" == "$ROOT/frontend" ]] || return 1
  [[ "$cmd" == *"next dev"* || "$cmd" == *"npm run dev"* || "$cmd" == *"next-server"* ]] || return 1
}

service_matches_pid() {
  local service=$1 pid=$2
  case "$service" in
    api) matches_api_pid "$pid" ;;
    frontend) matches_frontend_pid "$pid" ;;
    *) return 1 ;;
  esac
}

port_is_listening() {
  local port=$1
  ss -ltn "( sport = :$port )" | awk 'NR>1 { found=1 } END { exit found ? 0 : 1 }'
}

port_pids() {
  local port=$1
  fuser -n tcp "$port" 2>/dev/null | tr ' ' '\n' | awk 'NF' | sort -u
}

wait_for_port_free() {
  local port=$1
  for _ in $(seq 1 10); do
    if ! port_is_listening "$port"; then
      return 0
    fi
    sleep 1
  done
  return 1
}

stop_pid_gracefully() {
  local label=$1 pid=$2
  if ! process_alive "$pid"; then
    return 0
  fi

  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 10); do
    if ! process_alive "$pid"; then
      return 0
    fi
    sleep 1
  done

  kill -9 "$pid" 2>/dev/null || true
  for _ in $(seq 1 5); do
    if ! process_alive "$pid"; then
      return 0
    fi
    sleep 1
  done

  die "$label pid $pid did not stop"
}

stop_pid_file_service() {
  local service=$1 pid_file=$2
  local pid
  pid="$(read_pid_file "$pid_file" || true)"
  if [[ -z "${pid:-}" ]]; then
    rm -f "$pid_file"
    return 0
  fi

  if process_alive "$pid" && service_matches_pid "$service" "$pid"; then
    stop_pid_gracefully "$service" "$pid"
  fi

  rm -f "$pid_file"
}

stop_port_service() {
  local service=$1 port=$2
  local pid
  while read -r pid; do
    [[ -n "$pid" ]] || continue
    if process_alive "$pid" && service_matches_pid "$service" "$pid"; then
      stop_pid_gracefully "$service" "$pid"
    fi
  done < <(port_pids "$port")
}

resolve_service_pid() {
  local service=$1 pid_file=$2 port=$3
  local pid

  pid="$(read_pid_file "$pid_file" || true)"
  if [[ -n "${pid:-}" ]] && process_alive "$pid" && service_matches_pid "$service" "$pid"; then
    printf '%s\n' "$pid"
    return 0
  fi

  while read -r pid; do
    [[ -n "$pid" ]] || continue
    if process_alive "$pid" && service_matches_pid "$service" "$pid"; then
      printf '%s\n' "$pid" > "$pid_file"
      printf '%s\n' "$pid"
      return 0
    fi
  done < <(port_pids "$port")

  return 1
}

ensure_ports_free() {
  local ports=(8000 3000)
  local port
  for port in "${ports[@]}"; do
    if port_is_listening "$port"; then
      die "Port $port is still in use"
    fi
  done
}

stop_services() {
  stop_pid_file_service api "$API_PID_FILE"
  stop_pid_file_service frontend "$FRONTEND_PID_FILE"
  stop_port_service api 8000
  stop_port_service frontend 3000

  wait_for_port_free 8000 || die "Port 8000 did not become free"
  wait_for_port_free 3000 || die "Port 3000 did not become free"

  rm -f "$API_PID_FILE" "$FRONTEND_PID_FILE"
}

neo4j_status_summary() {
  local reachable="no"
  local docker_status="unavailable"

  if timeout 3 bash -lc ">/dev/tcp/$NEO4J_HOST/$NEO4J_PORT" 2>/dev/null; then
    reachable="yes"
  fi

  if command -v docker >/dev/null 2>&1; then
    docker_status="$(
      docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | awk '/grapheval-neo4j/ {print; found=1} END { if (!found) print "not-running-or-missing" }'
    )"
  fi

  printf 'Neo4j: reachable=%s, docker=%s\n' "$reachable" "$docker_status"
}

start_api() {
  local provider=$1
  : > "$API_LOG"
  (
    cd "$ROOT"
    nohup env \
      GRAPHEVAL_DEBUG_LOGS=true \
      NEO4J_ENABLED=true \
      DEFAULT_LLM_PROVIDER="$provider" \
      .venv/bin/uvicorn api.server:app \
        --host 127.0.0.1 \
        --port 8000 \
      > "$API_LOG" 2>&1 < /dev/null &
    printf '%s\n' "$!" > "$API_PID_FILE"
  )
}

start_frontend() {
  : > "$FRONTEND_LOG"
  (
    cd "$ROOT/frontend"
    rm -rf "$ROOT/frontend/.next"
    if command -v setsid >/dev/null 2>&1; then
      nohup setsid npm run dev -- \
        --hostname 127.0.0.1 \
        --port 3000 \
        > "$FRONTEND_LOG" 2>&1 < /dev/null &
    else
      nohup npm run dev -- \
        --hostname 127.0.0.1 \
        --port 3000 \
        > "$FRONTEND_LOG" 2>&1 < /dev/null &
    fi
    printf '%s\n' "$!" > "$FRONTEND_PID_FILE"
  )
}

print_failure_log() {
  local label=$1 log_file=$2
  echo "$label failed to start"
  if [[ -f "$log_file" ]]; then
    echo "Last 80 lines from $log_file:"
    tail -n 80 "$log_file"
  else
    echo "Log file not found: $log_file"
  fi
}

wait_for_http_ok() {
  local label=$1 url=$2 timeout_seconds=$3
  local code
  for _ in $(seq 1 "$timeout_seconds"); do
    code="$(timeout 5 curl -o /dev/null -w '%{http_code}' -sS "$url" 2>/dev/null || true)"
    if [[ "$code" == "200" ]]; then
      return 0
    fi
    sleep 1
  done
  return 1
}

verify_started_pid() {
  local service=$1 pid_file=$2 port=$3
  local pid
  pid="$(resolve_service_pid "$service" "$pid_file" "$port" || true)"
  [[ -n "${pid:-}" ]] || die "Missing PID file for $service"
  process_alive "$pid" || die "$service exited immediately"
  service_matches_pid "$service" "$pid" || die "$service PID does not match expected process"
}

start_services() {
  local provider=$1
  local startup_ok=0
  [[ "$provider" == "mock" || "$provider" == "ollama" ]] || die "Provider must be 'mock' or 'ollama'"
  trap 'if [[ "$startup_ok" -eq 0 ]]; then stop_services >/dev/null 2>&1 || true; fi' RETURN

  require_repo
  echo "$(neo4j_status_summary)"
  stop_services
  ensure_ports_free

  start_api "$provider"
  if ! wait_for_http_ok "API" "$API_URL/health" 60; then
    print_failure_log "API" "$API_LOG"
    stop_services
    exit 1
  fi
  verify_started_pid api "$API_PID_FILE" 8000

  start_frontend
  if ! wait_for_http_ok "Frontend" "$FRONTEND_URL" 60; then
    print_failure_log "Frontend" "$FRONTEND_LOG"
    stop_services
    exit 1
  fi
  verify_started_pid frontend "$FRONTEND_PID_FILE" 3000

  echo "API: running at $API_URL"
  echo "Frontend: running at $FRONTEND_URL"
  echo "Provider: $provider"
  echo "Logs: .runtime/services/"
  startup_ok=1
  trap - RETURN
}

status_services() {
  local api_pid frontend_pid api_alive frontend_alive api_port frontend_port api_health frontend_http neo4j provider

  api_pid="$(resolve_service_pid api "$API_PID_FILE" 8000 || true)"
  frontend_pid="$(resolve_service_pid frontend "$FRONTEND_PID_FILE" 3000 || true)"

  api_alive="no"
  frontend_alive="no"
  [[ -n "${api_pid:-}" ]] && process_alive "$api_pid" && matches_api_pid "$api_pid" && api_alive="yes"
  [[ -n "${frontend_pid:-}" ]] && process_alive "$frontend_pid" && matches_frontend_pid "$frontend_pid" && frontend_alive="yes"

  api_port="no"
  frontend_port="no"
  port_is_listening 8000 && api_port="yes"
  port_is_listening 3000 && frontend_port="yes"

  api_health="$(timeout 5 curl -fsS "$API_URL/health" 2>/dev/null || echo "unreachable")"
  frontend_http="$(timeout 5 curl -o /dev/null -w '%{http_code}' -sS "$FRONTEND_URL" 2>/dev/null || echo "unreachable")"
  neo4j="$(neo4j_status_summary)"
  provider="unknown"
  if [[ -n "${api_pid:-}" ]] && process_alive "$api_pid"; then
    provider="$(pid_env_value "$api_pid" "DEFAULT_LLM_PROVIDER" || true)"
    provider="${provider:-unknown}"
  elif [[ "$api_health" != "unreachable" ]]; then
    provider="$(
      timeout 5 curl -fsS "$API_URL/dependencies" 2>/dev/null | \
        python3 -c 'import json,sys; print(json.load(sys.stdin).get("config",{}).get("default_llm_provider","unknown"))' \
        2>/dev/null || echo "unknown"
    )"
  fi

  echo "API PID: ${api_pid:-missing} (alive: $api_alive)"
  echo "Frontend PID: ${frontend_pid:-missing} (alive: $frontend_alive)"
  echo "Port 8000 listening: $api_port"
  echo "Port 3000 listening: $frontend_port"
  echo "API health: $api_health"
  echo "Frontend HTTP: $frontend_http"
  echo "$neo4j"
  echo "Provider: $provider"
}

smoke_services() {
  local api_health frontend_http deps_status deps_json benchmarks_count

  api_health="$(timeout 5 curl -fsS "$API_URL/health")" || die "Smoke failed: API health endpoint unreachable"
  frontend_http="$(timeout 5 curl -o /dev/null -w '%{http_code}' -sS "$FRONTEND_URL")" || die "Smoke failed: frontend unreachable"
  [[ "$frontend_http" == "200" ]] || die "Smoke failed: frontend returned HTTP $frontend_http"

  deps_json="$(timeout 5 curl -fsS "$API_URL/dependencies")" || die "Smoke failed: dependencies endpoint unreachable"
  deps_status="$(
    python3 -c 'import json,sys; d=json.load(sys.stdin); neo=d.get("neo4j",{}); print("configured=%s, connected=%s, error=%s" % (neo.get("configured"), neo.get("connected"), neo.get("error")))' <<<"$deps_json"
  )"

  benchmarks_count="$(
    timeout 5 curl -fsS "$API_URL/benchmarks" | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))'
  )" || die "Smoke failed: benchmark catalog endpoint unreachable"

  echo "Smoke: PASS"
  echo "API health: $api_health"
  echo "Frontend HTTP: $frontend_http"
  echo "Neo4j via dependencies: $deps_status"
  echo "Benchmarks: $benchmarks_count"
}

show_logs() {
  echo "== API log =="
  if [[ -f "$API_LOG" ]]; then
    tail -n 100 "$API_LOG"
  else
    echo "Missing log: $API_LOG"
  fi
  echo
  echo "== Frontend log =="
  if [[ -f "$FRONTEND_LOG" ]]; then
    tail -n 100 "$FRONTEND_LOG"
  else
    echo "Missing log: $FRONTEND_LOG"
  fi
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/devctl.sh start mock
  ./scripts/devctl.sh start ollama
  ./scripts/devctl.sh stop
  ./scripts/devctl.sh restart mock
  ./scripts/devctl.sh restart ollama
  ./scripts/devctl.sh status
  ./scripts/devctl.sh smoke
  ./scripts/devctl.sh logs
EOF
}

main() {
  local command="${1:-}"
  local provider="${2:-}"

  case "$command" in
    start)
      [[ -n "$provider" ]] || die "Missing provider for start"
      start_services "$provider"
      ;;
    stop)
      require_repo
      stop_services
      echo "Stopped GraphEval dev services"
      ;;
    restart)
      [[ -n "$provider" ]] || die "Missing provider for restart"
      start_services "$provider"
      ;;
    status)
      require_repo
      status_services
      ;;
    smoke)
      require_repo
      smoke_services
      ;;
    logs)
      require_repo
      show_logs
      ;;
    *)
      usage
      [[ -z "$command" ]] && exit 1
      die "Unknown command: $command"
      ;;
  esac
}

main "$@"
