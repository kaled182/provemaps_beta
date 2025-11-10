#!/usr/bin/env bash
# scripts/deploy.sh - Orchestrated deployment helper for MapsProveFiber
# - Builds Docker images
# - Starts dependencies (database/redis)
# - Runs migrations and collectstatic (with per-step timeouts)
# - Starts web/celery/beat services
# - Executes a /healthz check
# - Adds safeguards: environment validation, pre-deploy backup, automatic rollback, timestamped logs,
#   resource verification (disk), docker compose version check, final service verification
#
# Usage:
#   ./scripts/deploy.sh [--compose docker/docker-compose.yml] [--settings settings.prod] [--health http://HOST:8000/healthz] [--timeout 180]
#
# Optional environment overrides:
#   COMPOSE_FILE=docker/docker-compose.yml
#   DJANGO_SETTINGS_MODULE=settings.prod
#   HEALTHCHECK_URL=http://localhost:8000/healthz
#   HEALTHCHECK_TIMEOUT=180
#   MIGRATE_TIMEOUT=300
#   COLLECTSTATIC_TIMEOUT=120
#   SERVICE_WEB=web
#   SERVICE_WORKER=celery
#   SERVICE_BEAT=beat
#
# Requirements:
#   - docker and docker compose v2
#   - /healthz endpoint exposed by Django (core.urls -> path("healthz", ...))

set -Eeuo pipefail

### ---- UI / LOG ----
NC=$'\e[0m'; RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; BLU=$'\e[34m'
ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()   { echo "$(ts) ${BLU}[deploy]${NC} $*"; }
log_step(){ echo "$(ts) --> ${BLU}[deploy]${NC} $*"; }
log_end(){ echo  "$(ts) <-- ${GRN}[done]${NC} $*"; }
ok()    { echo "$(ts) ${GRN}[ok]${NC} $*"; }
warn()  { echo "$(ts) ${YLW}[warn]${NC} $*"; }
err()   { echo "$(ts) ${RED}[err]${NC} $*" >&2; }
die()   { err "$*"; exit 1; }

### ---- METADATA ----
SCRIPT_VERSION="1.1.0"
COMPOSE_MIN_VERSION="2.0.0"

### ---- DEFAULTS ----
COMPOSE_FILE="${COMPOSE_FILE:-docker/docker-compose.yml}"
DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-settings.prod}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-http://localhost:8000/healthz}"
HEALTHCHECK_TIMEOUT="${HEALTHCHECK_TIMEOUT:-180}"
MIGRATE_TIMEOUT="${MIGRATE_TIMEOUT:-300}"
COLLECTSTATIC_TIMEOUT="${COLLECTSTATIC_TIMEOUT:-120}"
SERVICE_WEB="${SERVICE_WEB:-web}"
SERVICE_WORKER="${SERVICE_WORKER:-celery}"
SERVICE_BEAT="${SERVICE_BEAT:-beat}"

### ---- ARGS ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose) COMPOSE_FILE="$2"; shift 2;;
    --settings) DJANGO_SETTINGS_MODULE="$2"; shift 2;;
    --health) HEALTHCHECK_URL="$2"; shift 2;;
    --timeout) HEALTHCHECK_TIMEOUT="$2"; shift 2;;
    -h|--help)
      cat <<EOF
Usage: $0 [options]

Options:
  --compose FILE          Path to docker/docker-compose.yml (default: $COMPOSE_FILE)
  --settings MODULE       DJANGO_SETTINGS_MODULE (default: $DJANGO_SETTINGS_MODULE)
  --health URL            Healthcheck URL (default: $HEALTHCHECK_URL)
  --timeout SECONDS       Healthcheck timeout (default: $HEALTHCHECK_TIMEOUT)
  -h, --help              Show this help message

Environment:
  SERVICE_WEB, SERVICE_WORKER, SERVICE_BEAT to override compose service names.
Versions:
  script v${SCRIPT_VERSION} | recommended minimum compose ${COMPOSE_MIN_VERSION}
EOF
      exit 0;;
    *) die "Unknown option: $1";;
  esac
done

### ---- HELPERS ----
compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

wait_for_url() {
  local url="$1" timeout="$2" t=0
  log "Waiting for health endpoint: $url"
  until curl -fsS "$url" >/dev/null 2>&1; do
    sleep 2; t=$((t+2))
    if (( t >= timeout )); then
      return 1
    fi
  done
  return 0
}

### ---- VALIDATION AND SAFETY ----
check_compose_version() {
  local cv
  cv="$(docker compose version --short || echo "0")"
  if [[ "$(printf '%s\n' "$COMPOSE_MIN_VERSION" "$cv" | sort -V | head -n1)" != "$COMPOSE_MIN_VERSION" ]]; then
    warn "docker compose ($cv) may be older than recommended ($COMPOSE_MIN_VERSION)"
  else
    ok "docker compose version $cv"
  fi
}

validate_environment() {
  log_step "Validating environment"
  command -v docker >/dev/null || die "docker binary not found"
  docker compose version >/dev/null || die "docker compose v2 not available"
  [[ -f "$COMPOSE_FILE" ]] || die "compose file not found: $COMPOSE_FILE"

  local critical_vars=("DJANGO_SETTINGS_MODULE" "COMPOSE_FILE")
  for var in "${critical_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
      warn "Environment variable $var is empty"
    fi
  done

  if ! compose config -q; then
    die "Invalid compose file: $COMPOSE_FILE"
  fi
  log_end "Environment verified"
}

check_disk_space() {
  log_step "Checking disk space"
  local available_kb min_kb
  available_kb=$(df / | awk 'NR==2 {print $4}')
  min_kb=$((1024 * 1024 * 2)) # 2GB
  if [[ "$available_kb" -lt "$min_kb" ]]; then
    warn "Low disk space: ${available_kb}KB available"
    return 1
  fi
  log_end "Disk space sufficient"
  return 0
}

# Preventive backup: try MariaDB first, then PostgreSQL; warn if both fail.
create_pre_deploy_backup() {
  log_step "Creating preventive database backup (when available)"
  if ! compose ps db | grep -q "Up"; then
    warn "Database service is not running, skipping preventive backup"
    return 0
  fi

  local tsf="backup_pre_deploy_$(date +%Y%m%d_%H%M%S)"
  local out_mysql="/tmp/${tsf}.sql"
  local out_pg="/tmp/${tsf}.pg.sql"

  # MariaDB/MySQL (default for MapsProveFiber)
  if compose exec -T db sh -lc 'command -v mysqldump >/dev/null 2>&1'; then
    if compose exec -T db sh -lc 'mysqldump --version >/dev/null 2>&1'; then
      if compose exec -T db sh -lc 'mysqldump -uroot -p"$MARIADB_ROOT_PASSWORD" --all-databases' > "$out_mysql" 2>/dev/null; then
        log_end "Backup (MySQL/MariaDB) created: $out_mysql"
        return 0
      fi
    fi
  fi

  # PostgreSQL (fallback)
  if compose exec -T db sh -lc 'command -v pg_dumpall >/dev/null 2>&1'; then
    if compose exec -T db sh -lc 'pg_dumpall -U postgres' > "$out_pg" 2>/dev/null; then
      log_end "Backup (PostgreSQL) created: $out_pg"
      return 0
    fi
  fi

  warn "Unable to create preventive backup (non-fatal)"
  return 0
}

rollback() {
  err "Starting rollback"
  compose down --timeout 30 || true
  ok "Rollback completed - services stopped"
  exit 1
}

setup_error_handling() {
  # Trigger rollback on any error or signal
  trap rollback ERR SIGINT SIGTERM
}

check_services_health() {
  log_step "Validating service health"
  local services=("$SERVICE_WEB" "$SERVICE_WORKER" "$SERVICE_BEAT")
  for service in "${services[@]}"; do
    if compose ps "$service" | grep -q "Up"; then
      ok "Service $service is running"
    else
      warn "Service $service is not running"
    fi
  done
  log_end "Service verification completed"
}

### ---- SUMMARY ----
log "Script v${SCRIPT_VERSION}"
log "Compose file: $COMPOSE_FILE"
log "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
log "Healthcheck: $HEALTHCHECK_URL (timeout ${HEALTHCHECK_TIMEOUT}s)"
log "Services: web=${SERVICE_WEB} worker=${SERVICE_WORKER} beat=${SERVICE_BEAT}"

### ---- MAIN EXECUTION FLOW ----
setup_error_handling
check_compose_version
validate_environment
check_disk_space || warn "Disk space may be insufficient"
create_pre_deploy_backup

### ---- BUILD ----
log_step "Building images (pull + build)"
compose build --pull
log_end "Build complete"

### ---- DEPENDENCIES: DB/REDIS ----
log_step "Starting dependencies (db/redis) in background"
compose up -d db || true
compose up -d redis || true
log_end "Dependencies ready"

### ---- MIGRATIONS ----
log_step "Running migrations (timeout ${MIGRATE_TIMEOUT}s)"
compose run --rm \
  -e DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE" \
  "$SERVICE_WEB" timeout "$MIGRATE_TIMEOUT" python manage.py migrate --noinput
log_end "Migrations applied"

### ---- COLLECTSTATIC ----
log_step "Executing collectstatic (timeout ${COLLECTSTATIC_TIMEOUT}s)"
compose run --rm \
  -e DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE" \
  "$SERVICE_WEB" timeout "$COLLECTSTATIC_TIMEOUT" python manage.py collectstatic --noinput
log_end "Collectstatic finished"

### ---- START SERVICES ----
log_step "Starting services: $SERVICE_WEB $SERVICE_WORKER $SERVICE_BEAT"
compose up -d "$SERVICE_WEB" || die "failed to start $SERVICE_WEB"
compose up -d "$SERVICE_WORKER" || warn "worker did not start (optional service?)"
compose up -d "$SERVICE_BEAT" || warn "beat did not start (optional service?)"
log_end "Services running (initial start)"

### ---- HEALTHCHECK ----
if wait_for_url "$HEALTHCHECK_URL" "$HEALTHCHECK_TIMEOUT"; then
  ok "Application healthy at: $HEALTHCHECK_URL"
else
  err "Healthcheck failed after ${HEALTHCHECK_TIMEOUT}s"
  err "Recent web service logs:"
  compose logs --since=10m "$SERVICE_WEB" || true
  rollback
fi

### ---- FINAL SERVICE VERIFICATION ----
check_services_health
ok "Deployment finished successfully"
