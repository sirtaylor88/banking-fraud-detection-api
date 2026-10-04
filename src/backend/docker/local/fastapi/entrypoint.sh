#!/bin/bash

# * errexit: exit immediately if any command returns a non-zero status,
# * preventing the script from silently continuing after a failure
set -o errexit

# * nounset: treat unset variables as an error — catches typos in variable names
set -o nounset

# * pipefail: a pipeline fails if any command in it fails, not just the last one
# * e.g. `failing_cmd | tee log.txt` will now propagate the failure
set -o pipefail

# * Inline Python script to wait for PostgreSQL to be ready before starting the app.
# * This prevents the app from crashing on startup when the DB container is still initialising.
# * The heredoc (<<END) passes the script body to the Python interpreter via stdin;
# * shell variable substitution (${POSTGRES_HOST} etc.) happens before Python sees the string.
python << END
import sys
import time
import psycopg

# Maximum time to wait for the database before giving up and exiting with an error
MAX_WAIT_SECONDS = 30
# How long to sleep between each connection attempt
RETRY_INTERVAL = 5
start_time = time.time()


def check_database() -> bool:
    """Attempt a single synchronous connection to PostgreSQL.

    Uses psycopg (sync) rather than asyncpg because this runs outside the
    FastAPI event loop, before the app process starts.

    Returns:
        bool: True if the connection succeeded, False otherwise.
    """
    try:
        conn = psycopg.connect(
            host="${POSTGRES_HOST}",
            port="${POSTGRES_PORT}",
            dbname="${POSTGRES_DB}",
            user="${POSTGRES_USER}",
            password="${POSTGRES_PASSWORD}"
        )
        # Close immediately — we only need to verify the DB is reachable
        conn.close()
        return True

    except psycopg.OperationalError as err:
        elapsed_time = int(time.time() - start_time)
        sys.stderr.write(f"Database connection failed after {elapsed_time} seconds: {err}\n")
        return False


# Polling loop: retry until the DB is ready or the timeout is exceeded
while True:
    if check_database():
        sys.stderr.write("Database is ready!\n")
        break

    if time.time() - start_time > MAX_WAIT_SECONDS:
        sys.stderr.write(
            "Database connection could not be established within the maximum wait time. Exiting.\n"
        )
        sys.exit(1)

    sys.stderr.write(f"Waiting for database to be ready... Retrying in {RETRY_INTERVAL} seconds.\n")
    time.sleep(RETRY_INTERVAL)
END

echo >&2 'POSTGRES is ready to accept connections!'

# * exec replaces this shell process with the container's CMD (e.g. fastapi run ...).
# * Using exec (rather than just calling "$@") ensures the app process receives
# * OS signals (SIGTERM, SIGINT) directly instead of them being swallowed by bash.
exec "$@"
