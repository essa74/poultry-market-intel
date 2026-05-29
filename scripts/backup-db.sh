#!/usr/bin/env bash
set -euo pipefail

# Database backup script for Poultry Market Intel
# Usage: ./scripts/backup-db.sh [container_name] [db_user] [db_name]
#
# Defaults (matching docker-compose.prod.yml):
#   container: poultry-market-intel-db-1
#   db_user:   poultry
#   db_name:   poultry_market

BACKUP_DIR="${BACKUP_DIR:-./backups}"
CONTAINER="${1:-poultry-market-intel-db-1}"
DB_USER="${2:-poultry}"
DB_NAME="${3:-poultry_market}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
FILENAME="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "→ Backing up ${DB_NAME} from container ${CONTAINER} …"
docker exec "${CONTAINER}" pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${FILENAME}"

echo "✓ Backup saved: ${FILENAME} ($(du -h "${FILENAME}" | cut -f1))"

# Keep only last 14 daily backups
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -type f -mtime +14 -delete
