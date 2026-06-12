#!/usr/bin/env bash
# Start Neo4j + FastAPI backend + Next.js frontend for local demos.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PID_DIR="$ROOT/scripts/.pids"
mkdir -p "$PID_DIR"

CONTAINER_NAME="grapheval-neo4j"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

export NEO4J_ENABLED=true
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password123

port_in_use() {
  (echo >/dev/tcp/127.0.0.1/"$1") &>/dev/null
}

stop_tracked_processes() {
  local label=$1 pid_file=$2
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      # Kill child processes (e.g. uvicorn reloader, next dev)
      pkill -P "$pid" 2>/dev/null || true
      echo "Stopped $label (pid $pid)"
    fi
    rm -f "$pid_file"
  fi
}

cleanup() {
  echo ""
  echo "Shutting down backend and frontend..."
  stop_tracked_processes "backend" "$BACKEND_PID_FILE"
  stop_tracked_processes "frontend" "$FRONTEND_PID_FILE"
  echo "Neo4j container left running (stop with: scripts/stop-dev.sh)"
  exit 0
}

trap cleanup SIGINT SIGTERM

echo "=== GraphEval prototype — dev startup ==="
echo "Project root: $ROOT"
echo ""

if ! command -v docker &>/dev/null; then
  echo "Error: Docker is not installed or not in PATH."
  echo "Install Docker or start Neo4j, backend, and frontend manually (see README)."
  exit 1
fi

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Error: Do not run this script with sudo."
  echo ""
  echo "Running as root uses a different Python (/usr/sbin/python) without pip or your"
  echo "user-installed packages, which causes 'No module named pip' errors."
  echo ""
  echo "Fix Docker access for your normal user instead:"
  echo "  sudo usermod -aG docker \"\$USER\""
  echo "  newgrp docker    # or log out and back in"
  echo "  ./scripts/start-dev.sh"
  exit 1
fi

if ! docker info &>/dev/null; then
  echo "Error: Cannot access the Docker daemon (permission denied)."
  echo ""
  echo "Add your user to the docker group, then start a new login session:"
  echo "  sudo usermod -aG docker \"\$USER\""
  echo "  newgrp docker    # or log out and back in"
  echo ""
  echo "Do NOT run this script with sudo."
  exit 1
fi

if port_in_use 8000; then
  echo "Warning: Port 8000 is already in use."
  echo "         The FastAPI backend may fail to start. Stop the other process or change the port."
fi

if port_in_use 7474 || port_in_use 7687; then
  echo "Note: Port 7474 or 7687 is already in use."
  echo "      Neo4j may already be running — will try to use container '$CONTAINER_NAME'."
fi

# --- Neo4j ---
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
  echo "Starting existing Neo4j container: $CONTAINER_NAME"
  docker start "$CONTAINER_NAME"
else
  echo "Creating Neo4j container: $CONTAINER_NAME"
  docker run -d \
    --name "$CONTAINER_NAME" \
    -p 7474:7474 -p 7687:7687 \
    -e NEO4J_AUTH=neo4j/password123 \
    neo4j:latest
fi

echo "Waiting for Neo4j (http://localhost:7474)..."
neo4j_ready=false
for _ in $(seq 1 45); do
  if curl -sf http://localhost:7474 >/dev/null 2>&1; then
    neo4j_ready=true
    break
  fi
  sleep 1
done

if [[ "$neo4j_ready" == true ]]; then
  echo "Neo4j is ready."
else
  echo "Warning: Neo4j did not respond within 45s."
  echo "         Backend will start anyway; graph storage may warn until Neo4j is up."
fi

# --- Python dependencies (project .venv — avoids sudo/root Python issues) ---
PYTHON=""
for cmd in python3 python; do
  if command -v "$cmd" &>/dev/null; then
    PYTHON=$cmd
    break
  fi
done

if [[ -z "$PYTHON" ]]; then
  echo "Error: python3 not found. Install Python 3.10+."
  exit 1
fi

VENV_DIR="$ROOT/.venv"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  echo "Creating Python virtual environment at .venv ..."
  if ! "$PYTHON" -m venv "$VENV_DIR"; then
    echo "Error: failed to create .venv (is python3-venv installed?)"
    echo "  Fedora: sudo dnf install python3-venv python3-pip"
    exit 1
  fi
fi
PYTHON="$VENV_DIR/bin/python"

if ! "$PYTHON" -m pip --version &>/dev/null; then
  echo "Error: pip is not available in .venv."
  echo "  Try: rm -rf .venv && ./scripts/start-dev.sh"
  exit 1
fi

if ! "$PYTHON" -c "import fastapi, neo4j, uvicorn" 2>/dev/null; then
  echo "Installing Python dependencies into .venv ..."
  if ! "$PYTHON" -m pip install -r requirements.txt; then
    echo "Error: pip install failed."
    echo "  Run manually: .venv/bin/pip install -r requirements.txt"
    exit 1
  fi
else
  echo "Python dependencies OK (.venv)."
fi

# --- Frontend dependencies ---
if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  if ! command -v npm &>/dev/null; then
    echo "Error: npm not found. Install Node.js 18+."
    exit 1
  fi
  (cd frontend && npm install)
else
  echo "Frontend dependencies OK."
fi

# --- Backend ---
echo "Starting FastAPI backend on http://localhost:8000 ..."
"$PYTHON" -m uvicorn api.server:app --reload --port 8000 &
echo $! >"$BACKEND_PID_FILE"
sleep 1

if ! port_in_use 8000; then
  echo "Warning: Backend does not appear to be listening on port 8000 yet."
fi

# --- Frontend ---
if ! command -v npm &>/dev/null; then
  echo "Error: npm not found. Install Node.js 18+."
  cleanup
  exit 1
fi

echo "Starting Next.js frontend ..."
( cd frontend && npm run dev ) &
echo $! >"$FRONTEND_PID_FILE"

echo ""
echo "============================================"
echo " GraphEval dev stack is running"
echo "============================================"
echo " Frontend:      http://localhost:3000"
echo "                (Next.js uses 3001 if 3000 is busy)"
echo " Backend:       http://localhost:8000/health"
echo " API docs:      http://localhost:8000/docs"
echo " Neo4j Browser: http://localhost:7474"
echo "                login: neo4j / password123"
echo ""
echo " Neo4j storage: ENABLED (verifier unchanged — storage only)"
echo " Press Ctrl+C to stop backend + frontend"
echo " Stop Neo4j:     scripts/stop-dev.sh"
echo "============================================"
echo ""

# Wait for background jobs; Ctrl+C runs cleanup via trap
wait
