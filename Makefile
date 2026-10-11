# * Build the app image with your UID/GID so containers can write to the mounted project
# * (docker-compose.local.yml passes them as build args; see README "Hot reload").
export APP_UID := $(shell id -u)
export APP_GID := $(shell id -g)

build:
	docker compose -f docker-compose.local.yml up --build -d --remove-orphans

up:
	docker compose -f docker-compose.local.yml up -d

down-v:
	docker compose -f docker-compose.local.yml down -v

down:
	docker compose -f docker-compose.local.yml down

# * Delete app logs and Flower task history (not cleared by down -v). The app services are
# * stopped first because they keep these files open; run `make up` to start them again.
clean-data:
	docker compose -f docker-compose.local.yml stop api celeryworker celerybeat flower
	rm -rf src/backend/app/logs .flower

nextgen-config:
	docker compose -f docker-compose.local.yml config

# * The container has no ruff, so Alembic's post-write hook is skipped there: sort and format on the host.
makemigrations:
	docker compose -f docker-compose.local.yml exec -it api alembic revision --autogenerate -m "$(name)"
	uv run ruff check --fix --quiet migrations && uv run ruff format --quiet migrations

migrate:
	docker compose -f docker-compose.local.yml exec -it api alembic upgrade head

history:
	docker compose -f docker-compose.local.yml exec -it api alembic history

current-migration:
	docker compose -f docker-compose.local.yml exec -it api alembic current

downgrade:
	docker compose -f docker-compose.local.yml exec -it api alembic downgrade $(version)

inspect-network:
	docker network inspect nextgen_local_nw

psql:
	docker compose -f docker-compose.local.yml exec -it postgres-db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'
