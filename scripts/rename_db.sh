#!/usr/bin/env bash
# =============================================================================
#  OctaOS – One-Time Database Rename Script
#  Run this ONCE on your VPS before running updatedeploy.sh
#  Usage: sudo bash rename_db.sh
# =============================================================================

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo -e "\033[0;31m[ERROR]\033[0m Please run as root: sudo bash rename_db.sh"
  exit 1
fi

echo "Stopping OctaOS services to close database connections..."
systemctl stop octaos-api octaos-worker octaos-beat octaos-frontend 2>/dev/null || true

echo "Terminating active connections to 'nexusos' database..."
su - postgres -c "psql -c \"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = 'nexusos' AND pid <> pg_backend_pid();\"" 2>/dev/null || true

echo "Renaming PostgreSQL database from 'nexusos' to 'octaos'..."
su - postgres -c "psql -c \"ALTER DATABASE nexusos RENAME TO octaos;\"" || {
  echo -e "\033[1;33m[WARN]\033[0m Database rename failed. It might already be named 'octaos' or does not exist."
}

echo -e "\033[0;32m[OK]\033[0m Database rename step complete."
echo "You can now safely run: sudo bash updatedeploy.sh"
