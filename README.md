# Banking Fraud Detection API

A full-featured banking application built with FastAPI, providing secure and efficient financial services with fraud detection capabilities.

## Tech stack

- **Runtime**: Python 3.12 · [uv](https://docs.astral.sh/uv/) package manager
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Database**: PostgreSQL via `asyncpg` (async) and `psycopg[pool]` (sync/pool)
- **ORM / Migrations**: [SQLModel](https://sqlmodel.tiangolo.com/) + [Alembic](https://alembic.sqlalchemy.org/)
- **Auth**: [argon2-cffi](https://argon2-cffi.readthedocs.io/) for password hashing
- **Config**: [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) (environment-based)
- **Logging**: [loguru](https://loguru.readthedocs.io/) with rotating file sinks

## Project structure

```
src/backend/app/
├── api/
│   └── main.py        # API router aggregator
├── core/
│   ├── config.py      # Settings loaded from .env.local
│   └── logging.py     # Loguru setup and get_logger()
├── logs/              # Runtime log files (git-ignored)
│   ├── debug.log      # DEBUG/INFO entries
│   └── error.log      # ERROR+ entries with backtrace
├── routes/
│   └── home.py        # Home endpoint
└── main.py            # FastAPI app instance
```

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- PostgreSQL

### Install dependencies

```bash
uv sync --all-groups
```

### Configure environment

```bash
cp src/.envs/.env.example src/.envs/.env.local
# Edit src/.envs/.env.local with your values
```

| Variable              | Description                        |
|-----------------------|------------------------------------|
| `PROJECT_NAME`        | Application name shown in API docs |
| `PROJECT_DESCRIPTION` | Description shown in API docs      |
| `API_V1_STR`          | API version prefix (e.g. `/api/v1`)|
| `SITE_NAME`           | Site display name                  |
| `ENVIRONMENT`         | `local` / `staging` / `production` |

### Run the development server

```bash
uv run fastapi dev src/backend/app/main.py
```

API docs are available at `{API_V1_STR}/docs` once the server is running.

## Development

### Linting and type checking

```bash
uv run ruff check .      # Import sorting lint
uv run ruff format .     # Format
uv run pylint src/       # Style/quality lint
uv run mypy .            # Type checking
```

### Testing

```bash
uv run pytest                                                           # All tests
uv run pytest tests/path/to/test_file.py::test_name                    # Single test
uv run pytest --cov=src/backend --cov-report=term-missing               # With coverage
```

100% test coverage is required (enforced by pre-commit).

### Pre-commit hooks

```bash
uv run pre-commit install   # Install hooks
uv run pre-commit run --all-files   # Run manually
```

Hooks run: `ruff`, `ruff-format`, `pylint`, `mypy`, `pydocstyle` (Google convention), `bandit`, `sphinx-lint`, and `pytest` with 100% coverage.
