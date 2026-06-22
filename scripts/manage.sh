#!/bin/bash
# Django-like wrapper for database migrations
# Can be run from the repo root OR from the scripts/ subdirectory.

# Resolve the repo root (one level up if this script lives in scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"  # repo root is one level above scripts/

VENV_DIR="$APP_DIR/venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Error: Virtual environment not found at $VENV_DIR"
    exit 1
fi

# Alembic must be run from the repo root so it finds alembic.ini
cd "$APP_DIR"

case "$1" in
  makemigrations)
    # Equivalent to Django's `python manage.py makemigrations`
    # It reads your SQLAlchemy models and automatically generates the alter/create/drop SQL
    MSG="${2:-auto_migration}"
    echo "Generating new database migrations for: $MSG"
    "$VENV_DIR/bin/alembic" revision --autogenerate -m "$MSG"
    ;;
    
  migrate)
    # Equivalent to Django's `python manage.py migrate`
    # It applies all pending migrations to the database
    echo "Applying pending migrations to the database..."
    "$VENV_DIR/bin/alembic" upgrade head
    ;;
    
  *)
    echo "Usage:"
    echo "  bash scripts/manage.sh makemigrations [optional_description_with_no_spaces]"
    echo "  bash scripts/manage.sh migrate"
    ;;
esac
