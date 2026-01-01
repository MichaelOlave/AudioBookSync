# Repository Guidelines

## Project Structure & Module Organization

Source code lives in `src/` (core config/logging, infrastructure utilities, operations workflows, database integration, and future integrations). Tests mirror this layout under `tests/`, using `test_*.py` files. Top‑level helpers such as `database/migrate.py` and `scripts/migrate_csv_to_db.py` contain operational utilities; documentation lives in `docs/`.

## Build, Test, and Development Commands

Use `make help` to discover common tasks. Typical flows:
- Setup: `make install` (runtime deps) or `make install-dev` then `make setup` for local folders.
- Run app: `make run` for normal execution, `make run-dev` for debug mode.
- Tests: `make test` (all), `make test-unit`, `make test-async`, `make test-db`, or `make coverage` / `make coverage-html`.
- Quality: `make lint`, `make format`, `make format-check`, `make type-check`, or `make qa` / `make check` for full suites.

## Coding Style & Naming Conventions

This is a Python 3.9+ codebase using 4‑space indentation and Black + isort formatting (`make format`). Linting uses Flake8 with a 100‑character line limit; type checking uses mypy. Prefer descriptive module and function names (e.g., `sync_library`, `download_audiobook_batch`) and keep files grouped by domain (core, infrastructure, operations, database).

## Testing Guidelines

Tests use pytest with markers for `unit`, `asyncio`, `integration`, and `db` (see `pytest.ini`). Name test files `test_*.py`, classes `Test*`, and functions `test_*`. Run focused suites with `make test-unit` or `pytest tests/core/test_config.py -k "test_env_override"` when iterating. New features and bug fixes should include or update tests and keep coverage from regressing.

## Commit & Pull Request Guidelines

Follow the existing history: short, imperative commit subjects (e.g., “Add PostgreSQL schema”, “Refine sync workflow”). For pull requests, include a concise summary, testing instructions (`make test`, `make coverage`), and any operational notes (database migrations, new env vars). Link related issues and, when behavior changes, describe user‑visible impact and rollback considerations.

## Security & Configuration Tips

Store secrets and connection strings (such as `DATABASE_URL` or Audible credentials) only in your local `.env` or environment, never in Git. When touching database or filesystem paths (e.g., `audiobooks/`, `logs/`), prefer configuration via `src/core/config` to keep environments reproducible.

