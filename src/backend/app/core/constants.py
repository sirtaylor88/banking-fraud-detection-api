"""Application-wide constants."""

from datetime import timedelta
from pathlib import Path

# * Logging
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
    "{level: <8} | "
    "{name}:{function}:{line} - "
    "{message}"
)
LOG_ROTATION = "10 MB"  # start a new log file past this size
LOG_RETENTION = "30 days"  # delete rotated log files older than this

# * Database connection pool
DB_POOL_SIZE = 5  # connections kept open
DB_MAX_OVERFLOW = 10  # extra connections allowed above the pool size
DB_POOL_TIMEOUT = 30  # seconds to wait for a free connection
DB_POOL_RECYCLE = 30 * 60  # seconds before a connection is replaced

# * Database initialization: wait DB_INIT_RETRY_DELAY * attempt between tries
DB_INIT_MAX_RETRIES = 3
DB_INIT_RETRY_DELAY = 2  # seconds

# * Health checks
HEALTH_CHECK_TIMEOUT = 5.0  # default seconds allowed per check attempt
HEALTH_CHECK_RETRY_DELAY = 1.0  # default seconds between failed attempts
HEALTH_CHECK_MAX_RETRIES = 3  # default attempts before a service is unhealthy
HEALTH_CACHE_DURATION = timedelta(seconds=25)  # below Traefik's 30s poll interval
CELERY_BROKER_MAX_RETRIES = 3  # broker connection attempts when no worker answers
# * Delay in seconds between polls while waiting for services, indexed by
# * elapsed time in 10-second steps (the last value repeats)
HEALTH_WAIT_RETRY_INTERVALS = (1, 2, 5, 10, 15)

# * Startup
STARTUP_TIMEOUT = 90.0  # seconds to wait for all services to become healthy
