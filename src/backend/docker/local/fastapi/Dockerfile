ARG PYTHONVERSION=3.12.15
# * Pin uv version to ensure reproducible builds across environments
ARG UVVERSION=0.7.19

FROM python:${PYTHONVERSION}-slim-bookworm AS python

# * Materialise the uv image as a named stage so COPY --from can reference it by name.
# * COPY --from does not support variable expansion (e.g. --from=image:${ARG} fails),
# * but FROM does — this is the official Docker workaround for pinned external images.
FROM ghcr.io/astral-sh/uv:${UVVERSION} AS uv-binary

# * Stage 1: Copy the uv binary from the named uv stage into the Python base
FROM python AS uv-install-stage

COPY --from=uv-binary /uv /usr/local/bin/uv

# * UV_COMPILE_BYTECODE: pre-compile .pyc files at install time for faster container startup
# * UV_LINK_MODE=copy: use file copies instead of hardlinks to work correctly across Docker layers
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# * Stage 2: Install runtime dependencies into an isolated virtualenv
FROM uv-install-stage AS python-build-stage

WORKDIR /app

# * libpq-dev is required to compile asyncpg and psycopg native extensions during uv sync.
# * No purge/autoremove here: this stage is discarded after build — only .venv is copied
# * to the run stage, so build-stage image size has no impact on the final image.
# * rm -rf /var/lib/apt/lists/* removes the apt cache to keep intermediate layers lean.
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# * Copy only the lockfile and manifest first to maximise layer cache reuse:
# * dependency layers are only rebuilt when pyproject.toml or uv.lock change
COPY pyproject.toml uv.lock ./

# * --frozen: fail if uv.lock is out of sync with pyproject.toml (no silent drift)
# * --no-install-project: skip installing the project itself, only install its dependencies
# * --no-dev: exclude dev dependencies from the runtime image
RUN uv sync --frozen --no-install-project --no-dev

# * Stage 3: Lean runtime image — no uv, no build tools, only the app and its venv
FROM python AS python-run-stage

ARG APP_HOME=/app
ARG APP_USER=fastapi
ARG APP_GROUP=fastapi

WORKDIR ${APP_HOME}

# * Merge apt install, user creation into one layer to reduce image size.
# * Logs directory is intentionally NOT created here — it must be created after
# * COPY to avoid COPY overwriting the parent directory ownership (see below).
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    sudo git bash-completion nano ssh \
    gettext \
    # * libpq-dev is required at runtime for asyncpg and psycopg native extensions
    libpq-dev \
    # * Cleanup build dependencies and remove apt cache to reduce image size
    && apt-get purge -y --autoremove -o APT::AutoRemove::RecommendsImportant=false \
    && rm -rf /var/lib/apt/lists/* \
    # * Create a non-root user to run the application for security reasons
    && groupadd -r ${APP_GROUP} \
    && useradd -r -g ${APP_GROUP} -d ${APP_HOME} -m ${APP_USER}

# * Copy only the pre-built virtualenv from the build stage, not uv or build deps.
# * --chown ensures the app user owns the venv — without this it lands as root-owned
# * and the non-root process cannot write .pyc files or cache entries into it.
COPY --chown=${APP_USER}:${APP_GROUP} --from=python-build-stage /app/.venv ${APP_HOME}/.venv

# * Prepend the virtualenv bin directory so Python resolves packages from it
ENV PATH="${APP_HOME}/.venv/bin:$PATH"

# * Copy entrypoint and start scripts as root so they cannot be tampered with by the app user,
# * then make them executable. Ownership stays with root intentionally (Sonarqube S6504).
COPY ./src/backend/docker/local/fastapi/entrypoint.sh /entrypoint.sh
COPY ./src/backend/docker/local/fastapi/start.sh /start.sh

# * Copy the beat, celery and flower start scripts as root so they cannot be tampered with by the app user,
# * then make them executable. Ownership stays with root intentionally (Sonarqube S6504).
COPY ./src/backend/docker/local/fastapi/celery/beat/start.sh /start-celerybeat.sh
COPY ./src/backend/docker/local/fastapi/celery/worker/start.sh /start-celeryworker.sh
COPY ./src/backend/docker/local/fastapi/celery/flower/start.sh /start-flower.sh

# * Ensure scripts have Unix line endings and are executable
RUN sed -i 's/\r$//g' /entrypoint.sh /start.sh /start-celerybeat.sh /start-celeryworker.sh /start-flower.sh && \
    chmod +x /entrypoint.sh /start.sh /start-celerybeat.sh /start-celeryworker.sh /start-flower.sh

# * Copy the application code into the image and set ownership to the app user
COPY --chown=${APP_USER}:${APP_GROUP} . ${APP_HOME}

# * Create the logs directory AFTER the final COPY so Docker does not reset its ownership.
# * COPY recreates intermediate directories (src/backend/app/) as root — any mkdir done
# * before COPY would have its parent ownership overwritten. Running mkdir here guarantees
# * the app user can write log files at runtime.
# * /flower_data holds the Flower database, outside APP_HOME so the source bind mount
# * does not hide it. The nextgen_flower_data named volume is seeded from it on first
# * use, inheriting the app user ownership so Flower can write its database.
RUN mkdir -p ${APP_HOME}/src/backend/app/logs /flower_data && \
    chmod 755 ${APP_HOME}/src/backend/app/logs && \
    chown -R ${APP_USER}:${APP_GROUP} ${APP_HOME}/src/backend/app/logs /flower_data

# * Switch to non-root user before starting the process
USER ${APP_USER}

ENTRYPOINT ["/entrypoint.sh"]

EXPOSE 8000

CMD ["fastapi", "run", "src/backend/app/main.py", "--host", "0.0.0.0", "--port", "8000"]
