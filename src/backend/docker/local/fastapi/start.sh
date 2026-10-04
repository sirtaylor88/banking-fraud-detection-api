#!/bin/bash

# * errexit: exit immediately if any command returns a non-zero status
set -o errexit

# * nounset: treat unset variables as an error — catches typos in variable names
set -o nounset

# * pipefail: a pipeline fails if any command in it fails, not just the last one
set -o pipefail

# * exec replaces this shell process with the fastapi dev server so it receives
# * OS signals (SIGTERM, SIGINT) directly for clean shutdown.
# * --host 0.0.0.0: bind to all interfaces so the port is reachable from outside the container.
# * --port 8000: must match the EXPOSE directive and the docker-compose port mapping.
# * --reload: watch for file changes and restart automatically (local dev only).
exec fastapi dev src/backend/app/main.py --host 0.0.0.0 --port 8000 --reload
