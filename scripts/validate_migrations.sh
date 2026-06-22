#!/bin/bash
# CI Migration Validation Script
# Verifies that database schema matches Alembic migration history and there are no unmigrated changes.

set -e

# Resolve repo root (one level up from scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"  # repo root is one level above scripts/
VENV_DIR="$APP_DIR/venv"

# Alembic must run from repo root so it finds alembic.ini
cd "$APP_DIR"

TEMP_DB="test_ci_migration.db"
echo "Creating temporary schema..."
SQLALCHEMY_DATABASE_URI="sqlite:///${TEMP_DB}" "$VENV_DIR/bin/alembic" upgrade head

echo "Checking schema synchronization..."
if SQLALCHEMY_DATABASE_URI="sqlite:///${TEMP_DB}" "$VENV_DIR/bin/alembic" check; then
    echo "SUCCESS: Database schema is in sync with migrations."
    rm -f "${TEMP_DB}"
    exit 0
else
    echo "ERROR: Database schema is out of sync. Please run 'alembic revision --autogenerate' to create a new migration."
    rm -f "${TEMP_DB}"
    exit 1
fi
