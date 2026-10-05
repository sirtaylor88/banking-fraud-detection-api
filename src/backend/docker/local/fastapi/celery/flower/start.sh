#!/bin/bash

# * errexit: exit immediately if any command returns a non-zero status
set -o errexit

# * nounset: treat unset variables as an error — catches typos in variable names
set -o nounset

# * pipefail: a pipeline fails if any command in it fails, not just the last one
set -o pipefail

# * exec replaces this shell process with the Flower monitoring tool so it receives
# * OS signals (SIGTERM, SIGINT) directly for clean shutdown.
# * `-A src.backend.app.core.celery_app`: the Celery app to monitor; the broker URL
# * comes from its configuration.
# * `flower`: start the Flower monitoring tool.
# * `--address=0.0.0.0`: bind to all interfaces so the port is reachable from outside
# * the container.
# * `--port=5555`: must match the EXPOSE directive and the docker-compose port mapping.
# * `--persistent=True --db=...`: keep task history in the nextgen_flower_data volume
# * across restarts.
# * `--basic-auth`: protect the dashboard with HTTP basic authentication.
FLOWER_CMD=(
    celery
    -A src.backend.app.core.celery_app
    flower
    --address=0.0.0.0
    --port=5555
    --persistent=True
    --db=/flower_data/flower.db
    "--basic-auth=${CELERY_FLOWER_USER}:${CELERY_FLOWER_PASSWORD}"
)

# * watchfiles restarts Flower when a Python file changes (local dev only).
# * `--filter python`: only react to changes in .py files.
# * `--ignore-paths`: comma-separated directories to skip.
# * The target must be a single command string, so the array is joined with spaces.
# * The last argument is the directory to watch for changes (the source code).
exec watchfiles \
    --filter python \
    --ignore-paths .venv,.git \
    "${FLOWER_CMD[*]}" \
    src
