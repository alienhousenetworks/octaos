#!/bin/bash
# Django-like wrapper for database migrations

if [ ! -d "venv" ]; then
    echo "Error: Virtual environment 'venv' not found."
    exit 1
fi

case "$1" in
  makemigrations)
    # Equivalent to Django's `python manage.py makemigrations`
    # It reads your SQLAlchemy models and automatically generates the alter/create/drop SQL
    MSG="${2:-auto_migration}"
    echo "Generating new database migrations for: $MSG"
    venv/bin/alembic revision --autogenerate -m "$MSG"
    ;;
    
  migrate)
    # Equivalent to Django's `python manage.py migrate`
    # It applies all pending migrations to the database
    echo "Applying pending migrations to the database..."
    venv/bin/alembic upgrade head
    ;;
    
  *)
    echo "Usage:"
    echo "  ./manage.sh makemigrations [optional_description_with_no_spaces]"
    echo "  ./manage.sh migrate"
    ;;
esac
