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
| Background tasks | [Celery](https://docs.celeryq.dev/) · [RabbitMQ](https://www.rabbitmq.com/) (broker) · [Redis](https://redis.io/) (result backend) |
| Periodic tasks | [celery-redbeat](https://github.com/sibson/redbeat) (schedule stored in Redis) |
| Task monitoring | [Flower](https://flower.readthedocs.io/) |
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
│   │   ├── celery_app.py  # Celery app (RabbitMQ broker, Redis backend, redbeat)
│   │   ├── config.py      # Settings loaded from .env.local
│   │   ├── constants.py   # Timeouts, retries, pool sizes and log settings
│   │   ├── db.py          # SQLAlchemy engine (pooled), async_session factory, init_db()
│   │   ├── health.py      # Health checker for PostgreSQL, Redis and Celery
│   │   └── logging.py     # Loguru setup and get_logger()
│   ├── logs/              # Runtime log files (git-ignored)
│   │   ├── debug.log      # DEBUG / INFO entries
│   │   └── error.log      # ERROR+ entries with backtrace
│   ├── routes/
│   │   └── home.py        # Home endpoint
│   └── main.py            # FastAPI app, lifespan (svcs + startup health checks), /health
└── docker/local/
    ├── fastapi/
    │   ├── Dockerfile     # Multi-stage image (uv + non-root user)
    │   ├── entrypoint.sh  # Waits for PostgreSQL, then exec CMD
    │   ├── start.sh       # Runs fastapi dev with hot-reload
    │   └── celery/        # Start scripts, restarted on code changes by watchfiles
    │       ├── worker/start.sh  # Celery worker
    │       ├── beat/start.sh    # Celery beat (redbeat scheduler)
    │       └── flower/start.sh  # Flower dashboard (basic auth)
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
| `MAIL_FROM` | Sender email address | `noreply@nextgen.local` |
| `MAIL_FROM_NAME` | Sender display name | `NextGen Bank` |
| `CELERY_FLOWER_USER` | Flower dashboard username (**required** — `flower` won't start without it) | `admin` |
| `CELERY_FLOWER_PASSWORD` | Flower dashboard password (**required**, no spaces) | `secret` |

These have defaults that match `docker-compose.local.yml`, so you can leave them empty when using Docker:

| Variable | Default |
| --- | --- |
| `SMTP_HOST` · `SMTP_PORT` · `MAILPIT_UI_PORT` | `mailpit` · `1025` · `8025` |
| `REDIS_HOST` · `REDIS_PORT` · `REDIS_DB` | `redis` · `6379` · `0` |
| `RABBITMQ_HOST` · `RABBITMQ_PORT` | `rabbitmq` · `5672` |
| `RABBITMQ_USER` · `RABBITMQ_PASSWORD` | `guest` · `guest` |

The Celery broker URL and the Redis URL (`settings.REDIS_URL`) are built from these values. Don't set them directly.

### 3 · Start the full stack

```bash
docker network create nextgen_local_nw                                                 # one-time setup
docker compose -f docker-compose.local.yml config                                      # verify env variable injection
docker compose -f docker-compose.local.yml up -d --build                               # start all services
docker compose -f docker-compose.local.yml up -d --build --force-recreate             # force recreate all containers
docker compose -f docker-compose.local.yml up -d --build --remove-orphans             # remove containers for removed services
docker compose -f docker-compose.local.yml up -d --build --force-recreate --remove-orphans  # full rebuild
docker compose -f docker-compose.local.yml up -d --build --renew-anon-volumes         # after changing dependencies
docker compose -f docker-compose.local.yml down                                        # stop
docker compose -f docker-compose.local.yml down -v                                     # stop and delete volumes
```

Services started:

| Service | URL |
| --- | --- |
| API (hot-reload) | `http://api.localhost` · home at `http://api.localhost{API_V1_STR}/home/` (`http://api.localhost/api/v1/home/`) · docs at `http://api.localhost{API_V1_STR}/docs` · health at `http://api.localhost/health` |
| Traefik dashboard | `http://localhost:8080` |
| Mailpit web UI | `http://localhost:8025` |
| Flower (Celery monitoring) | `http://flower.localhost` · log in with `CELERY_FLOWER_USER` / `CELERY_FLOWER_PASSWORD` |
| RabbitMQ management | `http://rabbitmq.localhost` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |
| RabbitMQ (AMQP) | `localhost:5672` |

Background services (no URL): `celeryworker` (consumes the `nextgen_tasks` queue) and `celerybeat` (sends periodic tasks, schedule stored in Redis).

The bare `http://api.localhost/` returns 404 because the app has no route at `/`. Use the `{API_V1_STR}` paths above.

#### Health checks

On startup the API checks the database connection (3 tries, with a longer wait after each failure). It then registers health checks for PostgreSQL, Redis and Celery and waits up to 90 seconds for all of them to pass. If they don't, startup fails with `Critical services failed to start!` and the API doesn't serve requests.

`GET /health` (no `{API_V1_STR}` prefix) returns the overall status and a status for each service. Results are cached for 25 seconds.

| Overall status | HTTP code |
| --- | --- |
| `healthy` | `200` |
| `degraded`: at least one service is failing | `206` |
| `unhealthy` | `503` |
| The health check itself raised an error | `500` |

Celery counts as healthy if a worker answers a ping. If no worker answers, it still counts as healthy as long as RabbitMQ is reachable, so the API can start before the worker. Traefik calls `/health` on the `api` service every 30 seconds (5 second timeout).

#### Hot reload

The project root is mounted at `/app` in `api` and in every Celery service, so code changes apply without rebuilding. `fastapi dev` reloads the API, and `watchfiles` restarts the worker, beat and Flower when a `.py` file changes.

The container keeps its own virtualenv in an anonymous volume at `/app/.venv`. That volume isn't refreshed by `--build`, so after adding or upgrading a dependency, run `up -d --build --renew-anon-volumes`.

Containers run as a non-root `fastapi` user that doesn't own the mounted files. Commands that write into the project, such as `alembic revision`, should be run on the host with `uv run`, not inside a container.

#### Troubleshooting

- **`*.localhost` URLs return 404 for every service.** Another program is probably using ports 80/8080, often a second Docker engine. Check with `sudo ss -ltnp 'sport = :80'`. On WSL with Docker Desktop, a native `dockerd` installed in the distro competes for the same ports, and `docker ps` can't see its containers. If you only use Docker Desktop, disable it with `sudo systemctl disable --now docker.service docker.socket containerd.service`, then restart Docker Desktop.
- **`api` exits with `Critical services failed to start!`.** PostgreSQL, Redis or RabbitMQ wasn't reachable within 90 seconds. Check `docker compose -f docker-compose.local.yml ps` and the container logs (or `error.log`) to see which check failed.
- **`flower` exits right after starting.** `CELERY_FLOWER_USER` or `CELERY_FLOWER_PASSWORD` is missing from `src/.envs/.env.local`.

---

## Development

### Linting & type checking

```bash
uv run ruff check .       # Import sorting
uv run ruff format .      # Formatting
uv run pylint src/        # Style / quality
uv run mypy .             # Type checking
uv run bandit -r src/     # Security scan
```

### Testing

```bash
uv run pytest                                                # All tests
uv run pytest tests/path/to/test_file.py::test_name         # Single test
uv run pytest --cov=src/backend --cov-report=term-missing   # With coverage
```

> 100% test coverage is required and enforced by pre-commit.

Tests mock every external service, so no running database, Redis or RabbitMQ is needed. Shared helpers live in `tests/helpers.py` (for example `async_cm()`, a mock async context manager). Use `pytest.mark.parametrize` for variants of the same scenario.

### Pre-commit hooks

```bash
uv run pre-commit install          # Install hooks
uv run pre-commit run --all-files  # Run manually
```

Hooks: `ruff` · `ruff-format` · `pylint` · `mypy` · `pydocstyle` (Google) · `bandit` · `sphinx-lint` · `pytest` (100% coverage)
