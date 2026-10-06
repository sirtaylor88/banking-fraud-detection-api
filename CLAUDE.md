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

## Docker

```bash
docker network create nextgen_local_nw                                                      # one-time: create external network
docker compose -f docker-compose.local.yml config                                           # verify env variable injection
docker compose -f docker-compose.local.yml up -d --build                                    # start all services
docker compose -f docker-compose.local.yml up -d --build --force-recreate                  # force recreate all containers
docker compose -f docker-compose.local.yml up -d --build --remove-orphans                  # remove containers for removed services
docker compose -f docker-compose.local.yml up -d --build --force-recreate --remove-orphans # full rebuild
docker compose -f docker-compose.local.yml up -d --build --renew-anon-volumes              # after changing dependencies (refresh the /app/.venv volume)
docker compose -f docker-compose.local.yml down                                             # stop
docker compose -f docker-compose.local.yml down -v                                          # stop and delete all volumes
```

Services: `api` (FastAPI + hot-reload via `start.sh`), `postgres-db`, `traefik` (reverse proxy), `mailpit` (local email), `redis` (Celery result backend + redbeat schedule), `rabbitmq` (Celery broker), `celeryworker`, `celerybeat` (redbeat scheduler), `flower` (Celery monitoring). The Celery services reuse the `api` image via a YAML anchor; their start scripts live in `src/backend/docker/local/fastapi/celery/{worker,beat,flower}/start.sh` and restart on code changes via `watchfiles`.

The source is bind-mounted at `/app` (the image WORKDIR) with an anonymous volume over `/app/.venv`, so the container keeps its own virtualenv. Containers run as the non-root `fastapi` user, which does not own the bind-mounted files — run commands that write to the project (e.g. `alembic revision`) on the host with `uv run`, not via `docker compose exec`.

Compose gotchas:

- Services built from `<<: *api` inherit its Traefik `labels`; non-HTTP services must set `labels: []`, otherwise Traefik load-balances `api.localhost` onto them. Overriding a list key (`volumes`, `labels`) replaces the whole list — YAML anchors cannot be spliced into lists.
- The RabbitMQ healthcheck uses `rabbitmq-diagnostics check_port_connectivity`; `ping` passes before the AMQP listener accepts connections.
- Traefik routes appear only after containers are running/healthy, so a 404 right after `up` can be transient. A persistent 404 on every `*.localhost` host with routes visible inside the container (`docker compose exec traefik wget -qO- localhost:8080/api/http/routers`) means another process owns host ports 80/8080 — on this machine that was a native `dockerd` in WSL competing with Docker Desktop.

URLs: API → `http://api.localhost{API_V1_STR}/home/` (docs at `{API_V1_STR}/docs`; `/` is 404) | Traefik dashboard → `http://localhost:8080` | Mailpit → `http://localhost:8025` | RabbitMQ management → `http://rabbitmq.localhost` | Flower → `http://flower.localhost` (basic auth)

The external network (`nextgen_local_nw`) must be created before the first `up`. Named volumes: `nextgen_local_db` (PostgreSQL), `nextgen_mailpit_data` (Mailpit), `nextgen_local_logs` (app logs — seeded from image layer to preserve non-root ownership), `nextgen_redis_data` (Redis), `nextgen_rabbitmq_data` (RabbitMQ), `nextgen_flower_data` (Flower database).

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

Test conventions:

- Tests mock every external service (database, Redis, Celery); none need running services. Shared helpers go in `tests/helpers.py` (e.g. `async_cm()` for async context manager mocks)
- Use `pytest.mark.parametrize` for variants of the same scenario. Pass mock kwargs (`{"side_effect": ...}`) rather than mock instances, which would be shared across cases
- Name fixtures as `@pytest.fixture(name="x")` on `def fixture_x()`, and use `@pytest.mark.usefixtures(...)` when the value is unused. The pylint pre-commit hook lints staged test files, so this avoids `redefined-outer-name` / `unused-argument`
- Build exceptions and mocks before a `pytest.raises` block so it contains only one call that can raise

## Pre-commit hooks

Pre-commit runs ruff, ruff-format, pylint, mypy, pydocstyle (Google convention), bandit, sphinx-lint, and pytest with 100% coverage. Install hooks with:

```bash
uv run pre-commit install
```

## Architecture

The FastAPI application lives in `src/backend/app/`.

- **`src/backend/app/main.py`** — FastAPI app instance. On startup the lifespan registers the `AsyncSession` factory with svcs, runs `init_db()`, registers the database/Redis/Celery health checks and awaits `health_checker.wait_for_services()` inside `asyncio.timeout(STARTUP_TIMEOUT)` (90s, from `core/constants.py`; a timeout becomes `RuntimeError`). On shutdown or failed startup, `shutdown()` clears the health checker, closes the registry and disposes the engine. Exposes `GET /health` at the root, not under `API_V1_STR` (200 healthy / 206 degraded / 503 unhealthy / 500 check error; Traefik polls it), and includes `api_router` with the `API_V1_STR` prefix
- **`src/backend/app/api/main.py`** — aggregates all route routers into `api_router`
- **`src/backend/app/routes/`** — individual route modules (one `APIRouter` per file)
- **`src/backend/app/core/config.py`** — `Settings` (pydantic-settings); loaded from `src/.envs/.env.local`. App-specific fields (project/API/site names, `DATABASE_URL`, mail sender) default to empty — do not add fallback values. Infrastructure fields (SMTP, Redis, RabbitMQ) may default to their local Docker Compose values (service name as host, standard port, local dev credentials), and every such default must have `Field` constraints (`min_length=1` for strings, `ge=1, le=65535` for ports). Derived URLs are `@computed_field` properties (e.g. `REDIS_URL`)
- **`src/backend/app/core/celery_app.py`** — `celery_app`: RabbitMQ broker (AMQP URL built from `RABBITMQ_*`), Redis result backend (`settings.REDIS_URL`), JSON-only serialization, default queue `nextgen_tasks`. Periodic tasks use `celery-redbeat` (`redbeat_redis_url`; beat runs with `-S redbeat.RedBeatScheduler`). Tasks are autodiscovered from the `tasks` submodule of the packages listed in `autodiscover_tasks` (currently `src.backend.app.core.emails`, not created yet). Use only lowercase Celery 5 setting names. Retry options (`max_retries`, `default_retry_delay`) are per-task decorator arguments, not `conf` settings
- **`src/backend/app/core/db.py`** — SQLAlchemy `engine` (`AsyncAdaptedQueuePool`, `pool_pre_ping`) and `async_session` factory; `db_session_factory` (the svcs factory) rolls back on error and logs rollback/close failures without hiding the original error; `init_db()` runs `SELECT 1` with 3 tries and a longer wait after each failure. Session lifecycle is managed by svcs, not by standalone helpers
- **`src/backend/app/core/health.py`** — `HealthCheck` and the module-level `health_checker`. Services are registered with `add_service(name, check, *, timeout, retry_delay, max_retries, depends_on)`; dependencies must be registered first. `check_service_health` retries and returns a `ServiceStatus`; a service with an unhealthy dependency is `DEGRADED`. `check_all_services` runs every check at once and caches the result for 25s. `wait_for_services()` polls with back-off until all are healthy and never times out on its own; callers bound it with `asyncio.timeout()`. Async functions take no `timeout` parameter: apply timeouts at the call site with `asyncio.timeout()`. Built-in checks: `check_database`, `check_redis`, `check_celery` (healthy with no workers if the broker is reachable)
- **`src/backend/app/core/constants.py`** — app-wide constants grouped by area (logging, DB pool, DB init retries, health checks, startup timeout), each with a unit comment. Put new tuning values (timeouts, retry counts, intervals, sizes) here instead of hard-coding them, and import them by name (`from src.backend.app.core.constants import STARTUP_TIMEOUT`). In tests, patch a constant where it is used (`src.backend.app.main.STARTUP_TIMEOUT`), not in `constants`. Celery `conf` values stay in `celery_app.py`, commented inline
- **`src/backend/app/core/logging.py`** — loguru setup with `debug.log` (DEBUG/INFO) and `error.log` (ERROR+) sinks; use `get_logger()` throughout the app
- **Service registry**: `svcs` — `AsyncSession` is registered at startup via `app.state.svcs_registry`; routes resolve it with `svcs.Container(request.app.state.svcs_registry).aget(AsyncSession)`
- **Database**: PostgreSQL via `asyncpg` (async) and `psycopg[pool]` (sync/pool), with `SQLModel` for ORM and `Alembic` for migrations
- **Auth**: `argon2-cffi` for password hashing
- **Imports**: absolute from the repo root with the `src.` prefix (`from src.backend.app.core.config import settings`); Celery `-A` paths use the same form (`src.backend.app.core.celery_app`)

## Environment variables

```bash
cp src/.envs/.env.example src/.envs/.env.local
```

`src/.envs/.env.local` is git-ignored. `src/.envs/.env.example` is committed and must be kept in sync with the `Settings` fields in `core/config.py`.

Key vars: `PROJECT_NAME`, `API_V1_STR`, `ENVIRONMENT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST` (= service name in Compose), `POSTGRES_PORT`, `POSTGRES_SCHEMA`, `DATABASE_URL` (assembled from the POSTGRES_* vars), `MAIL_FROM`, `MAIL_FROM_NAME`, `CELERY_FLOWER_USER` / `CELERY_FLOWER_PASSWORD` (read only by `celery/flower/start.sh`, not by `Settings`; required because the script runs with `nounset`). `SMTP_*`, `REDIS_*` and `RABBITMQ_*` default to the Compose values and may be left empty (`env_ignore_empty=True`). Tests get Redis/RabbitMQ values from pytest-env, pointing at `localhost`.

## Code style notes

- Ruff is configured for import sorting only (`select = ["I"]`); pylint handles broader quality checks with `too-few-public-methods` and `duplicate-code` disabled
- All public modules, packages, classes, and functions require docstrings (pydocstyle Google convention)
- Use `TYPE_CHECKING` guards for type-only imports to avoid runtime import errors
- Use `pathlib.Path` over `os.path` for filesystem operations
