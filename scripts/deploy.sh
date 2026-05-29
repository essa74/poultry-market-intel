#!/usr/bin/env bash
set -euo pipefail

# Poultry Market Intel — production deploy script
# Usage: ./scripts/deploy.sh [--no-cache]

COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

if [ ! -f "${ENV_FILE}" ]; then
  echo "ERROR: ${ENV_FILE} not found. Copy .env.production.example to ${ENV_FILE} and fill in secrets."
  exit 1
fi

echo "→ Pulling latest images …"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull

echo "→ Building services …"
if [ "${1:-}" = "--no-cache" ]; then
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" build --no-cache
else
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" build
fi

echo "→ Running database migrations …"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" run --rm backend alembic upgrade head

echo "→ Starting all services …"
docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d

echo "→ Cleaning up old images …"
docker image prune -f

echo "✓ Deployment complete."
echo "  Backend health: curl http://localhost:8000/health"
echo "  Web:            http://localhost:3000"
