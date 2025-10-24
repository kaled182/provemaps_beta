# ------------------------------------------------------------
# Dockerfile — multi-stage (slim) para Django (mapsprovefiber)
# - Camadas otimizadas (cache de wheels)
# - Runtime enxuto e seguro (não-root, tz, ca-certs)
# - Compatível com docker-compose.yml (web/celery/beat)
# - Gunicorn + Uvicorn + Celery instalados
# - HEALTHCHECK fica no docker-compose.yml (preferível)
# ------------------------------------------------------------

############################
# Stage 1: build de dependências (wheels)
############################
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Dependências para compilar libs Python nativas (ex.: mysqlclient, pillow)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    default-libmysqlclient-dev \
    libpq-dev \
    pkg-config \
  && rm -rf /var/lib/apt/lists/* \
  && apt-get clean

WORKDIR /app

# Copia primeiro o requirements para aproveitar cache de camadas
COPY requirements.txt ./requirements.txt

# Gera wheels para todas as dependências do requirements
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

# Runtime mínimo + utilitários úteis (sem toolchain de build)
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

# Usuário não-root
ARG APP_USER=appuser
ARG APP_UID=1001
ARG APP_GID=1001
RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -m -u ${APP_UID} -g ${APP_GID} -s /bin/bash ${APP_USER}

WORKDIR /app

# Copia wheels e instala dependências
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN pip install --no-index --find-links=/wheels -r /app/requirements.txt && \
    # garante servidores/worker em runtime mesmo se não estiverem no requirements.txt
    pip install --no-cache-dir gunicorn uvicorn celery && \
    rm -rf /wheels /root/.cache

# Copia a aplicação
COPY . /app

# Permissões e diretórios de trabalho
RUN mkdir -p /app/logs /app/media /app/staticfiles /app/tmp && \
    chown -R ${APP_USER}:${APP_USER} /app && \
    chmod -R 755 /app

USER ${APP_USER}

# Porta de aplicação (web)
EXPOSE 8000

# O comando final é definido no docker-compose.yml:
#   web:    gunicorn core.asgi:application -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --workers 3 --timeout 120 --max-requests 1000
#   celery: celery -A core.celery_app worker -Q default -l info
#   beat:   celery -A core.celery_app beat -l info --pidfile=/tmp/celerybeat.pid
#
# HEALTHCHECK permanece no docker-compose.yml (mais flexível por ambiente)
