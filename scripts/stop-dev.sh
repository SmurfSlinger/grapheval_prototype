#!/usr/bin/env bash
# Stop tracked backend/frontend processes and the Neo4j dev container.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_DIR="$ROOT/scripts/.pids"
CONTAINER_NAME="grapheval-neo4j"

stop_tracked() {
  local label=$1 pid_file=$2
  if [[ ! -f "$pid_file" ]]; then
    echo "No PID file for $label ($pid_file)"
    return
  fi
  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    pkill -P "$pid" 2>/dev/null || true
    echo "Stopped $label (pid $pid)"
  else
    echo "$label not running (stale pid $pid)"
  fi
  rm -f "$pid_file"
}

echo "=== GraphEval prototype — dev shutdown ==="

stop_tracked "backend" "$PID_DIR/backend.pid"
stop_tracked "frontend" "$PID_DIR/frontend.pid"

if command -v docker &>/dev/null; then
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    if docker ps --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
      docker stop "$CONTAINER_NAME"
      echo "Stopped Neo4j container: $CONTAINER_NAME"
    else
      echo "Neo4j container '$CONTAINER_NAME' exists but is not running."
    fi
  else
    echo "Neo4j container '$CONTAINER_NAME' not found."
  fi
else
  echo "Docker not found — skipped Neo4j stop."
fi

echo "Done."
