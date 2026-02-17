#!/usr/bin/env bash
set -euo pipefail

# EKA – End-to-End reset & run (Docker)
#
# What it does:
#   1) docker compose down -v --remove-orphans
#   2) docker compose pull (base images)
#   3) docker compose build (api/ui/web)
#   4) docker compose up -d
#   5) waits for http://localhost:8000/health to be OK

NO_CACHE=0
SKIP_MODEL_PULL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-cache) NO_CACHE=1; shift ;;
    --skip-model-pull) SKIP_MODEL_PULL=1; shift ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_DIR="$REPO_ROOT/docker"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"

cd "$COMPOSE_DIR"

echo "==> Repo root: $REPO_ROOT"
echo "==> Compose:   $COMPOSE_FILE"

echo -e "\n==> [1/5] Stop + remove containers/volumes"
docker compose -f "$COMPOSE_FILE" down -v --remove-orphans

echo -e "\n==> [2/5] Pull base images"
docker compose -f "$COMPOSE_FILE" pull qdrant ollama ollama-init

echo -e "\n==> [3/5] Build local images (api/ui/web)"
if [[ $NO_CACHE -eq 1 ]]; then
  docker compose -f "$COMPOSE_FILE" build --no-cache --pull
else
  docker compose -f "$COMPOSE_FILE" build --pull
fi

echo -e "\n==> [4/5] Start stack"
docker compose -f "$COMPOSE_FILE" up -d

if [[ $SKIP_MODEL_PULL -eq 0 ]]; then
  echo -e "\n==> (Optional) Ensure Ollama models are present"
  set +e
  docker compose -f "$COMPOSE_FILE" exec -T ollama ollama pull llama3.1
  docker compose -f "$COMPOSE_FILE" exec -T ollama ollama pull nomic-embed-text
  set -e
fi

echo -e "\n==> [5/5] Wait for API health"
HEALTH_URL="http://localhost:8000/health"
OK=0
for i in $(seq 1 90); do
  if curl -fsS "$HEALTH_URL" | grep -q '"ok"'; then
    if curl -fsS "$HEALTH_URL" | grep -q '"ok":true'; then
      OK=1
      break
    fi
  fi
  sleep 1
done

if [[ $OK -ne 1 ]]; then
  echo "WARNING: API health check did not turn OK yet. Check logs: docker compose logs -f api" >&2
else
  echo -e "\n✅ System is up."
  echo "   Web UI:      http://localhost:3000"
  echo "   Streamlit:   http://localhost:8501"
  echo "   API Swagger: http://localhost:8000/docs"
  echo "   Qdrant:      http://localhost:6333/dashboard"
fi
