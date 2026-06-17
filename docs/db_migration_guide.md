# Database Migration Guide

OctaOS uses **Alembic** for managing database schema migrations. Schema creation and modification are no longer performed during application startup. Instead, schema changes are explicitly generated as migration files and applied using command-line commands.

---

## 1. Quick Start

Ensure the virtual environment is active and you are in the project root:

```bash
source venv/bin/activate
```

### Apply Migrations (New Database)
To apply all migrations to a clean database:

```bash
alembic upgrade head
```

### Transitioning an Existing Database
If you are deploying this version on a database instance that **already has existing tables** (such as a production, staging, or active local development database), running `alembic upgrade head` directly will fail because the tables already exist.

To transition an existing database, stamp the database version as the current `head` revision without running the DDL statements:

```bash
alembic stamp head
```

---

## 2. Generating New Migrations

When you add or update SQLAlchemy models in `app/models/`, follow these steps to generate a migration script.

1. **Write or modify models** under the `app/models/` directory.
2. **Import any new model** inside `alembic/env.py` to ensure it is registered on `Base.metadata`.
3. **Autogenerate a revision script**:
   ```bash
   alembic revision --autogenerate -m "describe your changes"
   ```
4. **Verify the generated file** inside `alembic/versions/`. Review the `upgrade()` and `downgrade()` functions. If you are using SQLite, make sure your table modifications are wrapped in batch mode (`op.batch_alter_table`).
5. **Apply the migration**:
   ```bash
   alembic upgrade head
   ```

---

## 3. Configuration Details

- **`alembic.ini`**: Main configuration file. It specifies the path of the scripts (`script_location = alembic`) and sets up basic logging formatters.
- **`alembic/env.py`**: The migration runner. It dynamically loads the database connection string from the application settings (`settings.SQLALCHEMY_DATABASE_URI`). It loads `.env` variables automatically.
- **SQLite Compatibility**: When running against SQLite databases (e.g. during testing or development), `render_as_batch=True` is enabled in `env.py`. This ensures that Alembic handles table alterations properly even on database engines with limited alter capabilities.
