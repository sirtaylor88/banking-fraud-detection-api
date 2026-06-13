# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package manager

This project uses `uv` (Python 3.12.13). All commands should be prefixed with `uv run`.

```bash
uv sync --all-groups   # Install all dependencies including dev
uv add <package>       # Add a runtime dependency
uv add --dev <package> # Add a dev dependency
```

## Running the app

```bash
uv run fastapi dev src/backend/app/main.py   # Development server with hot reload
uv run fastapi run src/backend/app/main.py   # Production server
```

## Linting and type checking

```bash
uv run ruff check .          # Lint (import sorting only)
uv run ruff format .         # Format
uv run pylint <files>        # Style/quality lint
uv run mypy .                # Type checking
uv run bandit -r cli/        # Security scan
```

## Testing

```bash
uv run pytest                                                        # Run all tests
uv run pytest tests/path/to/test_file.py::test_name                  # Run a single test
uv run pytest --cov=cli --cov-report=term-missing --cov-fail-under=100  # With coverage (100% required)
```

## Pre-commit hooks

Pre-commit runs ruff, ruff-format, pylint, mypy, pydocstyle (Google convention), bandit, sphinx-lint, and pytest with 100% coverage. Install hooks with:

```bash
uv run pre-commit install
```

## Architecture

The FastAPI application lives in `src/backend/app/`. The root `main.py` is a placeholder stub.

- **`src/backend/app/main.py`** — FastAPI app instance and route definitions
- **Database**: PostgreSQL via `asyncpg` (async driver) and `psycopg[pool]` (sync/pool), with `SQLModel` for ORM models and `Alembic` for migrations
- **Auth**: `argon2-cffi` for password hashing
- **Config**: `pydantic-settings` for environment-based configuration

Ruff is configured for import sorting only (`select = ["I"]`); pylint handles broader quality checks with `too-few-public-methods` and `duplicate-code` disabled.
