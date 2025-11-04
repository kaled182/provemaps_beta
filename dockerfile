# ------------------------------------------------------------
# Dockerfile - multi-stage (slim) for Django (mapsprovefiber)
# - Optimized layers (wheel cache)
# - Lean and secure runtime (non-root, tz, ca-certs)
# - Compatible with docker-compose.yml (web/celery/beat)
# - Gunicorn + Uvicorn + Celery installed
# - HEALTHCHECK defined in docker-compose.yml (preferred)
# ------------------------------------------------------------

############################
# Stage 1: build Python dependency wheels
############################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dependencies required to compile native Python libraries (e.g. mysqlclient, pillow)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    default-libmysqlclient-dev \
    libpq-dev \
    pkg-config \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

WORKDIR /app

# Copy requirements first to make the best use of the build cache
COPY requirements.txt ./requirements.txt

# Build wheels for every requirement
RUN pip install --upgrade pip wheel && \
    pip wheel --no-deps --wheel-dir=/wheels -r requirements.txt


############################
# Stage 2: runtime
############################
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    TZ=UTC \
    DJANGO_SETTINGS_MODULE=settings.prod

# Minimal runtime plus useful utilities (without the build toolchain)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libmariadb3 \
    libpq5 \
    ca-certificates \
    curl \
    netcat-openbsd \
    tzdata \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean \
  && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Non-root user
ARG APP_USER=appuser
ARG APP_UID=1001
ARG APP_GID=1001
RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER}

WORKDIR /app

# Copy wheels and install dependencies
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN pip install --no-index --find-links=/wheels -r /app/requirements.txt && \
    # ensure server/worker binaries in runtime even if not pinned in requirements.txt
    pip install --no-cache-dir gunicorn uvicorn celery && \
    rm -rf /wheels /root/.cache

# Copy the application source
COPY . /app

# Permissions and writable directories
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/tmp && \
    chown -R ${APP_USER}:${APP_USER} /app && \
    chmod -R 755 /app

USER ${APP_USER}

# Application port (web)
EXPOSE 8000

# The final command is defined in docker-compose.yml:
#   web:    gunicorn core.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 3 --timeout 120 --max-requests 1000
#   celery: celery -A core.celery_app worker -Q default -l info
#   beat:   celery -A core.celery_app beat -l info --pidfile=/tmp/celerybeat.pid
#
# HEALTHCHECK remains in docker-compose.yml for environment specific overrides
