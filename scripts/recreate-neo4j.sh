#!/usr/bin/env bash
# Recreate the GraphEval development Neo4j container from the pinned image.
#
# Usage:
#   ./scripts/recreate-neo4j.sh --yes [--fresh-data]
#
#   --yes         Required confirmation flag; the script refuses to run without it.
#   --fresh-data  Also remove the GraphEval development data volume so the new
#                 container starts with an empty database.
#
# The script only ever touches the configured GraphEval container and volume.
# It never prints the Neo4j password.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

NEO4J_IMAGE="${NEO4J_IMAGE:-neo4j:5.26.0}"
NEO4J_CONTAINER="${NEO4J_CONTAINER:-grapheval-neo4j}"
NEO4J_VOLUME="${NEO4J_VOLUME:-grapheval-neo4j-data}"
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-password123}"
NEO4J_DATABASE="${NEO4J_DATABASE:-neo4j}"

# Derive host ports from the configured URI so config stays authoritative.
BOLT_PORT="$(sed -E 's|^.*:([0-9]+)/?$|\1|' <<<"$NEO4J_URI")"
[[ "$BOLT_PORT" =~ ^[0-9]+$ ]] || BOLT_PORT=7687
HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"

CONFIRMED=false
FRESH_DATA=false
for arg in "$@"; do
  case "$arg" in
    --yes) CONFIRMED=true ;;
    --fresh-data) FRESH_DATA=true ;;
    *)
      echo "Unknown argument: $arg" >&2
      echo "Usage: $0 --yes [--fresh-data]" >&2
      exit 2
      ;;
  esac
done

if [[ "$CONFIRMED" != true ]]; then
  echo "Refusing to recreate Neo4j without explicit confirmation." >&2
  echo "Re-run with: $0 --yes [--fresh-data]" >&2
  exit 2
fi

fail() {
  echo "recreate-neo4j: FAIL — $*" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker is required"
docker info >/dev/null 2>&1 || fail "Cannot access the Docker daemon"

echo "=== GraphEval Neo4j recreation ==="
echo "image:     $NEO4J_IMAGE"
echo "container: $NEO4J_CONTAINER"
echo "volume:    $NEO4J_VOLUME (fresh-data: $FRESH_DATA)"
echo "bolt:      localhost:$BOLT_PORT"
echo "http:      localhost:$HTTP_PORT"
echo "user:      $NEO4J_USER"
echo "database:  $NEO4J_DATABASE"
echo "(password not printed)"
echo ""

if docker ps -a --format '{{.Names}}' | grep -qx "$NEO4J_CONTAINER"; then
  echo "Stopping and removing container: $NEO4J_CONTAINER"
  docker stop "$NEO4J_CONTAINER" >/dev/null 2>&1 || true
  docker rm "$NEO4J_CONTAINER" >/dev/null
else
  echo "Container $NEO4J_CONTAINER does not exist yet."
fi

if [[ "$FRESH_DATA" == true ]]; then
  if docker volume ls --format '{{.Name}}' | grep -qx "$NEO4J_VOLUME"; then
    echo "Removing development data volume: $NEO4J_VOLUME"
    docker volume rm "$NEO4J_VOLUME" >/dev/null
  else
    echo "Volume $NEO4J_VOLUME does not exist yet."
  fi
fi

echo "Pulling pinned image: $NEO4J_IMAGE"
docker pull "$NEO4J_IMAGE" >/dev/null || fail "Could not pull $NEO4J_IMAGE"

echo "Creating named volume: $NEO4J_VOLUME"
docker volume create "$NEO4J_VOLUME" >/dev/null

echo "Starting container: $NEO4J_CONTAINER"
docker run -d \
  --name "$NEO4J_CONTAINER" \
  -p "$HTTP_PORT:7474" -p "$BOLT_PORT:7687" \
  -v "$NEO4J_VOLUME:/data" \
  -e "NEO4J_AUTH=${NEO4J_USER}/${NEO4J_PASSWORD}" \
  "$NEO4J_IMAGE" >/dev/null

echo "Waiting for Neo4j Bolt authentication (cypher-shell)..."
neo4j_ready=false
for _ in $(seq 1 90); do
  if docker exec "$NEO4J_CONTAINER" cypher-shell \
      -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -d "$NEO4J_DATABASE" \
      "RETURN 1;" >/dev/null 2>&1; then
    neo4j_ready=true
    break
  fi
  sleep 1
done
[[ "$neo4j_ready" == true ]] || fail "Neo4j Bolt authentication did not succeed within 90s"
echo "Neo4j Bolt is ready (authenticated)."

echo "Installing GraphEval constraints/indexes..."
run_cypher() {
  docker exec -i "$NEO4J_CONTAINER" cypher-shell \
    -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" -d "$NEO4J_DATABASE" "$1"
}

# Execution-scoped entity uniqueness (composite). If the edition rejects the
# composite uniqueness constraint, fall back to a composite index and report it.
if run_cypher "CREATE CONSTRAINT grapheval_entity_per_execution IF NOT EXISTS FOR (e:Entity) REQUIRE (e.execution_id, e.name) IS UNIQUE;" >/dev/null 2>&1; then
  echo "  constraint grapheval_entity_per_execution: OK"
else
  echo "  composite uniqueness constraint unsupported; creating composite index instead"
  run_cypher "CREATE INDEX grapheval_entity_per_execution_idx IF NOT EXISTS FOR (e:Entity) ON (e.execution_id, e.name);" >/dev/null
  echo "  index grapheval_entity_per_execution_idx: OK"
fi
run_cypher "CREATE INDEX grapheval_fact_execution_idx IF NOT EXISTS FOR ()-[f:FACT]-() ON (f.execution_id);" >/dev/null
echo "  index grapheval_fact_execution_idx: OK"
run_cypher "CREATE INDEX grapheval_claim_execution_idx IF NOT EXISTS FOR ()-[c:CLAIM]-() ON (c.execution_id);" >/dev/null
echo "  index grapheval_claim_execution_idx: OK"

echo ""
echo "Constraints/indexes now present:"
run_cypher "SHOW CONSTRAINTS YIELD name, type, entityType, labelsOrTypes, properties RETURN name, type, entityType, labelsOrTypes, properties;" || true
run_cypher "SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties WHERE name STARTS WITH 'grapheval' RETURN name, type, entityType, labelsOrTypes, properties;" || true

IMAGE_ID="$(docker image inspect --format '{{.Id}}' "$NEO4J_IMAGE")"
IMAGE_DIGEST="$(docker image inspect --format '{{join .RepoDigests ", "}}' "$NEO4J_IMAGE")"
echo ""
echo "=== recreate-neo4j: PASS ==="
echo "image tag:    $NEO4J_IMAGE"
echo "image id:     $IMAGE_ID"
echo "repo digest:  ${IMAGE_DIGEST:-<none — locally built or never pushed>}"
echo "container:    $NEO4J_CONTAINER"
echo "volume:       $NEO4J_VOLUME"
