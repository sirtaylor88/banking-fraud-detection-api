"""Celery app configuration."""

from celery import Celery

from src.backend.app.core.config import settings

celery_app = Celery(
    "worker",  # must match the worker service name in docker-compose.yml
    broker=(
        f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"  # NOSONAR
        f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}//"
    ),
    backend=settings.REDIS_URL,
)
celery_app.conf.update(
    # * Serialization: accept JSON only, rejecting pickle payloads
    task_serializer="json",
    result_serializer="json",
    accept_content=["application/json"],
    # * Result backend
    result_backend_always_retry=True,  # retry on recoverable backend errors
    result_backend_max_retries=10,  # give up after 10 retries
    result_extended=True,  # store task name, args and kwargs with the result
    result_expires=60 * 60,  # delete stored results after 1 hour
    # * Task execution
    task_track_started=True,  # report a STARTED state while the task runs
    task_time_limit=5 * 60,  # kill the task after 5 minutes
    # * Raise SoftTimeLimitExceeded after 4 minutes so the task can clean up
    # * before the hard limit kills it
    task_soft_time_limit=4 * 60,
    task_acks_late=True,  # ack after the task finishes, not when it is received
    task_reject_on_worker_lost=True,  # requeue the task if its worker crashes
    # * Routing
    task_default_queue="nextgen_tasks",
    task_create_missing_queues=True,  # declare unknown queues on first use
    # * Monitoring events, consumed by Flower
    task_send_sent_event=True,  # emit an event when a task is published
    worker_send_task_events=True,  # emit events as workers process tasks
    # * Worker
    worker_prefetch_multiplier=1,  # reserve one task at a time per process
    # * Recycle a worker process after 1000 tasks or 500 MB of memory to
    # * contain memory leaks
    worker_max_tasks_per_child=1000,
    worker_max_memory_per_child=500_000,  # in kB
    # * Beat: store the redbeat schedule in Redis (defaults to the broker URL,
    # * which is RabbitMQ here)
    redbeat_redis_url=settings.REDIS_URL,
    # * Logging
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format=(
        "[%(asctime)s: %(levelname)s/%(processName)s]"
        "[%(task_name)s(%(task_id)s)] %(message)s"
    ),
)

celery_app.autodiscover_tasks(
    packages=["src.backend.app.core.emails"],  # packages to scan for tasks
    related_name="tasks",  # import the `tasks` submodule of each package
    force=True,  # import now instead of waiting for the worker to start
)
