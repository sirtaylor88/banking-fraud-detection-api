# Banking Fraud Detection API

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![uv](https://img.shields.io/badge/uv-package%20manager-DE5FE9?logo=uv&logoColor=white)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-FAB040?logo=pre-commit&logoColor=white)](https://pre-commit.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> A full-featured banking application built with FastAPI — secure, async, and production-ready.

---

## Tech stack

| Layer | Technology |
|---|---|
| Runtime | Python 3.12 · [uv](https://docs.astral.sh/uv/) |
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | PostgreSQL · [asyncpg](https://magicstack.github.io/asyncpg/) · [psycopg\[pool\]](https://www.psycopg.org/) |
| ORM / Migrations | [SQLModel](https://sqlmodel.tiangolo.com/) · [Alembic](https://alembic.sqlalchemy.org/) |
| Auth | [argon2-cffi](https://argon2-cffi.readthedocs.io/) |
| Config | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Logging | [loguru](https://loguru.readthedocs.io/) |

---

## Project structure

```
src/backend/app/
├── api/
│   └── main.py        # API router aggregator
├── core/
│   ├── config.py      # Settings loaded from .env.local
│   └── logging.py     # Loguru setup and get_logger()
├── logs/              # Runtime log files (git-ignored)
│   ├── debug.log      # DEBUG / INFO entries
│   └── error.log      # ERROR+ entries with backtrace
├── routes/
│   └── home.py        # Home endpoint
└── main.py            # FastAPI app instance
```

---

## Getting started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Docker & Docker Compose

### 1 · Install dependencies

```bash
uv sync --all-groups
```

### 2 · Configure environment

```bash
cp src/.envs/.env.example src/.envs/.env.local
```

Fill in `src/.envs/.env.local`:

| Variable | Description | Example |
|---|---|---|
| `PROJECT_NAME` | Application name shown in API docs | `NextGen Bank` |
| `PROJECT_DESCRIPTION` | Description shown in API docs | `Banking API` |
| `API_V1_STR` | API version prefix | `/api/v1` |
| `SITE_NAME` | Site display name | `NextGen Bank` |
| `ENVIRONMENT` | Runtime environment | `local` · `staging` · `production` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `secret` |
| `POSTGRES_DB` | Database name | `fraud_db` |
| `POSTGRES_HOST` | Hostname (service name in Compose) | `postgres-db` |
| `POSTGRES_PORT` | Database port | `5432` |
| `POSTGRES_SCHEMA` | Schema name (no hyphens) | `public` |
| `DATABASE_URL` | Assembled async DSN (auto-composed) | _(leave as-is)_ |

### 3 · Start the database

```bash
docker network create nextgen_local_nw                   # one-time setup
docker compose -f docker-compose.local.yml config        # verify env variable injection
docker compose -f docker-compose.local.yml up -d         # start PostgreSQL
docker compose -f docker-compose.local.yml down          # stop
docker compose -f docker-compose.local.yml down -v       # stop and delete volume
```

### 4 · Run the development server

```bash
uv run fastapi dev src/backend/app/main.py
```

Once running, API docs are at `{API_V1_STR}/docs`.

---

## Development

### Linting & type checking

```bash
uv run ruff check .       # Import sorting
uv run ruff format .      # Formatting
uv run pylint src/        # Style / quality
uv run mypy .             # Type checking
```

### Testing

```bash
uv run pytest                                                # All tests
uv run pytest tests/path/to/test_file.py::test_name         # Single test
uv run pytest --cov=src/backend --cov-report=term-missing   # With coverage
```

> 100% test coverage is required and enforced by pre-commit.

### Pre-commit hooks

```bash
uv run pre-commit install          # Install hooks
uv run pre-commit run --all-files  # Run manually
```

Hooks: `ruff` · `ruff-format` · `pylint` · `mypy` · `pydocstyle` (Google) · `bandit` · `sphinx-lint` · `pytest` (100% coverage)
