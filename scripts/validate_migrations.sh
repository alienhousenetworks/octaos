#!/bin/bash
# CI Migration Validation Script
# Verifies that database schema matches Alembic migration history and there are no unmigrated changes.

set -e

TEMP_DB="test_ci_migration.db"
echo "Creating temporary schema..."
SQLALCHEMY_DATABASE_URI="sqlite:///${TEMP_DB}" ./venv/bin/alembic upgrade head

echo "Checking schema synchronization..."
if SQLALCHEMY_DATABASE_URI="sqlite:///${TEMP_DB}" ./venv/bin/alembic check; then
    echo "SUCCESS: Database schema is in sync with migrations."
    rm -f "${TEMP_DB}"
    exit 0
else
    echo "ERROR: Database schema is out of sync. Please run 'alembic revision --autogenerate' to create a new migration."
    rm -f "${TEMP_DB}"
    exit 1
fi
