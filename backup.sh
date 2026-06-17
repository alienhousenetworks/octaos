#!/bin/bash
# OctaOS Enterprise Backup & Disaster Recovery script
# Performs automated pg_dump backup and rotates old backups.

set -e

# Default configurations
BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/octaos_backup_${TIMESTAMP}.sql.gz"

# Database credentials (defaults from settings)
DB_HOST="${POSTGRES_SERVER:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-octaos}"
export PGPASSWORD="${POSTGRES_PASSWORD:-password}"

echo "=========================================================="
echo "OctaOS Backup Pipeline Initiated"
echo "Timestamp: $(date)"
echo "Target: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "=========================================================="

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

# Run pg_dump and pipe to gzip
echo "Creating pg_dump backup file..."
if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -F p | gzip > "${BACKUP_FILE}"; then
    echo "SUCCESS: Backup written successfully to ${BACKUP_FILE}"
    echo "Size: $(du -sh "${BACKUP_FILE}" | cut -f1)"
else
    echo "ERROR: pg_dump backup failed."
    exit 1
fi

# Rotate old backups
echo "Pruning backups older than ${KEEP_DAYS} days..."
find "${BACKUP_DIR}" -name "octaos_backup_*.sql.gz" -type f -mtime +"${KEEP_DAYS}" -delete
echo "Pruning completed."

echo "=========================================================="
echo "Backup Completed Successfully!"
echo "=========================================================="
echo ""
echo "----------------------------------------------------------"
echo "DISASTER RECOVERY / RESTORATION INSTRUCTIONS:"
echo "----------------------------------------------------------"
echo "To restore from a backup file, run the following commands:"
echo ""
echo "1. Drop and recreate database (WARNING: destructive!):"
echo "   dropdb -h <host> -p <port> -U <user> <db_name>"
echo "   createdb -h <host> -p <port> -U <user> <db_name>"
echo ""
echo "2. Decompress and restore schema/data:"
echo "   gunzip -c ${BACKUP_FILE} | psql -h <host> -p <port> -U <user> -d <db_name>"
echo "----------------------------------------------------------"
