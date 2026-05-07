#!/usr/bin/env bash
# PSX App — PostgreSQL restore from Cloudflare R2
# Usage: bash restore.sh <backup_filename> [target_db]
# Example: bash restore.sh psx_psx_prod_20260507_060000.sql.gz psx_prod
#
# WARNING: This DROPS and RECREATES the target database.
# Run only when you mean it. Confirm the backup filename first with:
#   aws s3 ls s3://<bucket>/backups/postgres/ --endpoint-url <url> --profile psx-backup

set -euo pipefail

BACKUP_FILE="${1:?Usage: $0 <backup_filename> [target_db]}"
TARGET_DB="${2:-psx_prod}"
CONTAINER="psx_postgres_prod"
DB_USER="${POSTGRES_USER:?POSTGRES_USER env var not set}"
BUCKET="${STORAGE_BUCKET_NAME:?STORAGE_BUCKET_NAME env var not set}"
ENDPOINT="${STORAGE_ENDPOINT_URL:?STORAGE_ENDPOINT_URL env var not set}"
LOCAL_PATH="/tmp/${BACKUP_FILE}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] RESTORE: $*"; }

log "========================================================"
log "  TARGET DATABASE : ${TARGET_DB}"
log "  BACKUP FILE     : ${BACKUP_FILE}"
log "  THIS WILL DROP AND RECREATE ${TARGET_DB}"
log "========================================================"

read -r -p "Type 'yes I am sure' to continue: " CONFIRM
if [[ "${CONFIRM}" != "yes I am sure" ]]; then
    log "Aborted."
    exit 0
fi

log "Downloading backup from R2..."
aws s3 cp \
    "s3://${BUCKET}/backups/postgres/${BACKUP_FILE}" \
    "${LOCAL_PATH}" \
    --endpoint-url "${ENDPOINT}" \
    --profile psx-backup

log "Download complete. File size: $(du -sh "${LOCAL_PATH}" | cut -f1)"

log "Stopping application containers to prevent writes during restore..."
docker stop psx_api_prod psx_worker_prod psx_beat_prod 2>/dev/null || true

log "Dropping and recreating database ${TARGET_DB}..."
docker exec "${CONTAINER}" psql -U "${DB_USER}" -c "DROP DATABASE IF EXISTS \"${TARGET_DB}\";"
docker exec "${CONTAINER}" psql -U "${DB_USER}" -c "CREATE DATABASE \"${TARGET_DB}\";"
docker exec "${CONTAINER}" psql -U "${DB_USER}" -d "${TARGET_DB}" -c "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"

log "Restoring data..."
gunzip -c "${LOCAL_PATH}" \
    | docker exec -i "${CONTAINER}" \
        psql -U "${DB_USER}" -d "${TARGET_DB}" --single-transaction

log "Restore complete."
rm -f "${LOCAL_PATH}"

log "Restarting application containers..."
docker start psx_api_prod psx_worker_prod psx_beat_prod

log "Waiting for API health check..."
sleep 10
if docker exec psx_api_prod curl -sf http://localhost:8000/health > /dev/null; then
    log "API healthy. Restore successful."
else
    log "WARNING: API health check failed after restore. Investigate immediately."
    exit 1
fi
