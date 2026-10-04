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
| --- | --- |
| Runtime | Python 3.12 · [uv](https://docs.astral.sh/uv/) |
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | PostgreSQL · [asyncpg](https://magicstack.github.io/asyncpg/) · [psycopg\[pool\]](https://www.psycopg.org/) |
| ORM / Migrations | [SQLModel](https://sqlmodel.tiangolo.com/) · [Alembic](https://alembic.sqlalchemy.org/) |
| Auth | [argon2-cffi](https://argon2-cffi.readthedocs.io/) |
| Config | [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) |
| Logging | [loguru](https://loguru.readthedocs.io/) |
| Service registry | [svcs](https://svcs.hynek.me/) |
| Reverse proxy | [Traefik v3.6.2+](https://doc.traefik.io/traefik/) ¹ |
| Mail (local) | [Mailpit](https://mailpit.axllent.org/) |

> ¹ Traefik v3.6.2+ is required for compatibility with Docker Engine 29+. Earlier versions bundle a Docker SDK that defaults to API v1.24, which Docker Engine 29 rejects (minimum is 1.40), breaking container discovery.

---

## Project structure

```text
src/backend/
├── app/
│   ├── api/
│   │   └── main.py        # API router aggregator
│   ├── core/
│   │   ├── config.py      # Settings loaded from .env.local
│   │   ├── db.py          # SQLAlchemy engine and async_session factory
│   │   └── logging.py     # Loguru setup and get_logger()
│   ├── logs/              # Runtime log files (git-ignored)
│   │   ├── debug.log      # DEBUG / INFO entries
│   │   └── error.log      # ERROR+ entries with backtrace
│   ├── routes/
│   │   └── home.py        # Home endpoint
│   └── main.py            # FastAPI app instance + svcs lifespan
└── docker/local/
    ├── fastapi/
    │   ├── Dockerfile     # Multi-stage image (uv + non-root user)
    │   ├── entrypoint.sh  # Waits for PostgreSQL, then exec CMD
    │   └── start.sh       # Runs fastapi dev with hot-reload
    ├── postgres/
    │   └── Dockerfile     # postgres:17.5-bullseye base
    └── traefik/
        └── traefik.yml    # Traefik static configuration
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
| --- | --- | --- |
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

### 3 · Start the full stack

```bash
docker network create nextgen_local_nw                                                 # one-time setup
docker compose -f docker-compose.local.yml config                                      # verify env variable injection
docker compose -f docker-compose.local.yml up -d --build                               # start all services
docker compose -f docker-compose.local.yml up -d --build --force-recreate             # force recreate all containers
docker compose -f docker-compose.local.yml up -d --build --remove-orphans             # remove containers for removed services
docker compose -f docker-compose.local.yml up -d --build --force-recreate --remove-orphans  # full rebuild
docker compose -f docker-compose.local.yml down                                        # stop
docker compose -f docker-compose.local.yml down -v                                     # stop and delete volumes
```

Services started:

| Service | URL |
| --- | --- |
| API (hot-reload) | `http://api.localhost` · home at `http://api.localhost{API_V1_STR}/home/` (`http://api.localhost/api/v1/home/`) · docs at `http://api.localhost{API_V1_STR}/docs` |
| Traefik dashboard | `http://localhost:8080` |
| Mailpit web UI | `http://localhost:8025` |
| PostgreSQL | `localhost:5432` |

The `api` service mounts the project root for hot-reload — code changes are reflected immediately without rebuilding.

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
