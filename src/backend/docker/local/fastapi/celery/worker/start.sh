#!/bin/bash

# * errexit: exit immediately if any command returns a non-zero status
set -o errexit

# * nounset: treat unset variables as an error — catches typos in variable names
set -o nounset

# * pipefail: a pipeline fails if any command in it fails, not just the last one
set -o pipefail

# * exec replaces this shell process with watchfiles so it receives OS signals
# * (SIGTERM, SIGINT) directly for clean shutdown.
# * watchfiles restarts the Celery worker when a Python file changes (local dev only).
# * `--filter python`: only react to changes in .py files.
# * `-A src.backend.app.core.celery_app`: specify the Celery app to use.
# * `worker`: start a Celery worker process; it consumes from `task_default_queue`.
# * `-l INFO`: set the logging level to INFO for more detailed output.
# * The last argument is the directory to watch for changes (the source code).
exec watchfiles \
    --filter python \
    celery.__main__.main \
    --args '-A src.backend.app.core.celery_app worker -l INFO' \
    src
