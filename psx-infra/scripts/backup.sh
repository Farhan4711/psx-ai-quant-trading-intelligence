#!/usr/bin/env bash
# PSX App — PostgreSQL backup to Cloudflare R2 (S3-compatible)
# Schedule via cron as the app user:
#   0 */6 * * * /opt/psx-app/psx-infra/scripts/backup.sh >> /var/log/psx-backup.log 2>&1
#
# Requires: docker, aws CLI (for S3-compatible upload)
# Install aws CLI: pip install awscli
# Configure: aws configure --profile psx-backup (use R2 credentials)

set -euo pipefail

CONTAINER="psx_postgres_prod"
DB_USER="${POSTGRES_USER:?POSTGRES_USER env var not set}"
DB_NAME="${DB_NAME:-psx_prod}"
BUCKET="${STORAGE_BUCKET_NAME:?STORAGE_BUCKET_NAME env var not set}"
ENDPOINT="${STORAGE_ENDPOINT_URL:?STORAGE_ENDPOINT_URL env var not set}"
BACKUP_DIR="/tmp/psx-backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/psx_${DB_NAME}_${TIMESTAMP}.sql.gz"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] BACKUP: $*"; }

mkdir -p "${BACKUP_DIR}"

log "Starting backup of ${DB_NAME}..."
docker exec "${CONTAINER}" \
    pg_dump -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-acl \
    | gzip > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -sh "${BACKUP_FILE}" | cut -f1)
log "Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

log "Uploading to R2: s3://${BUCKET}/backups/postgres/${TIMESTAMP}/"
aws s3 cp "${BACKUP_FILE}" \
    "s3://${BUCKET}/backups/postgres/psx_${DB_NAME}_${TIMESTAMP}.sql.gz" \
    --endpoint-url "${ENDPOINT}" \
    --profile psx-backup

log "Upload complete."

# Remove local file
rm -f "${BACKUP_FILE}"

# Remove R2 backups older than RETENTION_DAYS
log "Pruning backups older than ${RETENTION_DAYS} days from R2..."
CUTOFF=$(date -d "${RETENTION_DAYS} days ago" +%Y-%m-%dT%H:%M:%S 2>/dev/null \
    || date -v-"${RETENTION_DAYS}"d +%Y-%m-%dT%H:%M:%S)  # macOS fallback

aws s3 ls "s3://${BUCKET}/backups/postgres/" \
    --endpoint-url "${ENDPOINT}" \
    --profile psx-backup \
    | awk '{print $4}' \
    | while read -r obj; do
        obj_date=$(echo "${obj}" | grep -oE '[0-9]{8}' | head -1)
        if [[ -n "${obj_date}" ]] && [[ "${obj_date}" < "${CUTOFF:0:8}" ]]; then
            log "Pruning old backup: ${obj}"
            aws s3 rm "s3://${BUCKET}/backups/postgres/${obj}" \
                --endpoint-url "${ENDPOINT}" \
                --profile psx-backup
        fi
    done

log "Backup job complete."
