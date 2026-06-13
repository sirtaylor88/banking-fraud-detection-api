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
uv run pylint src/           # Style/quality lint
uv run mypy .                # Type checking
uv run bandit -r src/        # Security scan
```

## Testing

```bash
uv run pytest                                                             # Run all tests
uv run pytest tests/path/to/test_file.py::test_name                      # Run a single test
uv run pytest --cov=src/backend --cov-report=term-missing                 # With coverage (100% required)
```

Test environment variables are set via `pytest-env` in `[tool.pytest.ini_options]` in `pyproject.toml` — do not add a `conftest.py` to set env vars.

## Pre-commit hooks

Pre-commit runs ruff, ruff-format, pylint, mypy, pydocstyle (Google convention), bandit, sphinx-lint, and pytest with 100% coverage. Install hooks with:

```bash
uv run pre-commit install
```

## Architecture

The FastAPI application lives in `src/backend/app/`.

- **`src/backend/app/main.py`** — FastAPI app instance; includes `api_router` with `API_V1_STR` prefix
- **`src/backend/app/api/main.py`** — aggregates all route routers into `api_router`
- **`src/backend/app/routes/`** — individual route modules (one `APIRouter` per file)
- **`src/backend/app/core/config.py`** — `Settings` (pydantic-settings); loaded from `src/.envs/.env.local`; all field defaults are intentionally empty — do not add fallback values
- **`src/backend/app/core/logging.py`** — loguru setup with `debug.log` (DEBUG/INFO) and `error.log` (ERROR+) sinks; use `get_logger()` throughout the app
- **Database**: PostgreSQL via `asyncpg` (async) and `psycopg[pool]` (sync/pool), with `SQLModel` for ORM and `Alembic` for migrations
- **Auth**: `argon2-cffi` for password hashing

## Environment variables

```bash
cp src/.envs/.env.example src/.envs/.env.local
```

`src/.envs/.env.local` is git-ignored. `src/.envs/.env.example` is committed and must be kept in sync with the `Settings` fields in `core/config.py`.

## Code style notes

- Ruff is configured for import sorting only (`select = ["I"]`); pylint handles broader quality checks with `too-few-public-methods` and `duplicate-code` disabled
- All public modules, packages, classes, and functions require docstrings (pydocstyle Google convention)
- Use `TYPE_CHECKING` guards for type-only imports to avoid runtime import errors
- Use `pathlib.Path` over `os.path` for filesystem operations
