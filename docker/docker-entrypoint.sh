#!/usr/bin/env bash
# docker-entrypoint.sh - lightweight initialization before the main command
# Goals:
#  - Wait for DB/Redis (when configured) before starting web/celery/beat
#  - Optionally run migrations or collectstatic via flags
#
# Usage (see docker-compose.yml for examples):
#   ENTRYPOINT ["/docker-entrypoint.sh"]
#   CMD ["gunicorn", "core.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
#
# Convenience variables/flags (all optional):
#   WAIT_FOR_DB=true|false           # wait for DB (default: true when DB_HOST is set)
#   WAIT_FOR_REDIS=true|false        # wait for Redis (default: true when REDIS_URL is set)
#   INIT_MIGRATE=true|false          # run manage.py migrate before starting (default: false)
#   INIT_COLLECTSTATIC=true|false    # run manage.py collectstatic --noinput (default: false)
#   MIGRATE_TIMEOUT=300              # migrate timeout (seconds)
#   COLLECTSTATIC_TIMEOUT=120        # collectstatic timeout (seconds)

set -Eeuo pipefail

# ---- ui/log helpers ----
NC=$'\e[0m'; BLU=$'\e[34m'; GRN=$'\e[32m'; YLW=$'\e[33m'; RED=$'\e[31m'
ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()   { echo "$(ts) ${BLU}[entry]${NC} $*"; }
ok()    { echo "$(ts) ${GRN}[ok]${NC} $*"; }
warn()  { echo "$(ts) ${YLW}[warn]${NC} $*"; }
err()   { echo "$(ts) ${RED}[err]${NC} $*" >&2; }

# ---- defaults ----
WAIT_FOR_DB="${WAIT_FOR_DB:-}"
WAIT_FOR_REDIS="${WAIT_FOR_REDIS:-}"
INIT_MIGRATE="${INIT_MIGRATE:-false}"
INIT_COLLECTSTATIC="${INIT_COLLECTSTATIC:-false}"
INIT_ENSURE_SUPERUSER="${INIT_ENSURE_SUPERUSER:-false}"
INIT_APP_DATA="${INIT_APP_DATA:-false}"
MIGRATE_TIMEOUT="${MIGRATE_TIMEOUT:-300}"
COLLECTSTATIC_TIMEOUT="${COLLECTSTATIC_TIMEOUT:-120}"

# auto-enable waits if hints are set
if [[ -z "${WAIT_FOR_DB}" ]]; then
  if [[ -n "${DB_HOST:-}" && -n "${DB_PORT:-}" ]]; then WAIT_FOR_DB=true; else WAIT_FOR_DB=false; fi
fi
if [[ -z "${WAIT_FOR_REDIS}" ]]; then
  if [[ -n "${REDIS_URL:-}" ]]; then WAIT_FOR_REDIS=true; else WAIT_FOR_REDIS=false; fi
fi

print_startup_info() {
  log "=== Container Startup ==="
  log "App: $(python -c "import django; print(django.get_version())" 2>/dev/null || echo "N/A")"
  log "Python: $(python --version 2>/dev/null || echo "N/A")"
  log "Settings: ${DJANGO_SETTINGS_MODULE:-Not set}"
  log "DB: ${DB_HOST:-Not set}:${DB_PORT:-N/A}"
  log "Redis: ${REDIS_URL:-Not set}"
  log "Flags: WAIT_FOR_DB=${WAIT_FOR_DB}, WAIT_FOR_REDIS=${WAIT_FOR_REDIS}"
  log "Init: MIGRATE=${INIT_MIGRATE}, COLLECTSTATIC=${INIT_COLLECTSTATIC}, APP_DATA=${INIT_APP_DATA}"
  log "=================================="
}

wait_host_port() {
  local host="${1:-}" port="${2:-}" name="${3:-srv}" retries="${4:-120}"
  if [[ -z "$host" || -z "$port" ]]; then return 0; fi
  log "Waiting for ${name} at ${host}:${port} (timeout ~${retries}s)"
  
  for ((i=1; i<=retries; i++)); do
    if command -v nc >/dev/null 2>&1; then
      if nc -z -w 1 "$host" "$port" >/dev/null 2>&1; then 
        ok "${name} available after ${i}s"; return 0; 
      fi
    else
      # Robust Python fallback
      if python -c "
import socket, sys
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('$host', $port))
    sock.close()
    sys.exit(0 if result == 0 else 1)
except Exception:
    sys.exit(1)
" >/dev/null 2>&1; then
        ok "${name} available after ${i}s"; return 0
      fi
    fi
    sleep 1
  done
  
  warn "Timed out waiting for ${name} after ${retries}s - continuing"
  return 0
}

parse_redis_url() {
  local rurl="${1:-redis://redis:6379/1}"
  local without_proto="${rurl#*://}"
  local host_part="${without_proto%%:*}"
  local rhost="${host_part##*@}"
  local port_part="${without_proto#*:}"
  local rport="${port_part%%/*}"
  
  if [[ -z "$rhost" || -z "$rport" ]] || ! [[ "$rport" =~ ^[0-9]+$ ]]; then
    warn "Malformed REDIS_URL: $rurl - falling back to defaults"
    echo "redis 6379"
    return 1
  fi
  
  echo "$rhost $rport"
  return 0
}

run_manage() {
  local args=("$@")
  PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-settings.dev}" \
    python manage.py "${args[@]}"
}

maybe_migrate() {
  if [[ "${INIT_MIGRATE}" == "true" ]]; then
    log "Running migrations (timeout ${MIGRATE_TIMEOUT}s)"
    if command -v timeout >/dev/null 2>&1; then
      timeout "${MIGRATE_TIMEOUT}" env PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-settings.dev}" \
        python manage.py migrate --noinput
    else
      run_manage migrate --noinput
    fi
    ok "Migrations applied"
  fi
}

maybe_collectstatic() {
  if [[ "${INIT_COLLECTSTATIC}" == "true" ]]; then
    log "Running collectstatic (timeout ${COLLECTSTATIC_TIMEOUT}s)"
    # Ensure staticfiles is writable — bind mount ../backend:/app/backend means
    # files created on a previous run may be owned by a different UID on the host.
    local static_root="${DJANGO_STATIC_ROOT:-/app/backend/staticfiles}"
    if [[ -d "$static_root" ]]; then
      chmod -R a+w "$static_root" 2>/dev/null || warn "chmod on staticfiles failed (continuing)"
    fi
    if command -v timeout >/dev/null 2>&1; then
      timeout "${COLLECTSTATIC_TIMEOUT}" env PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-settings.dev}" \
        python manage.py collectstatic --noinput
    else
      run_manage collectstatic --noinput
    fi
    ok "Collectstatic completed"
  fi
}

maybe_ensure_superuser() {
  if [[ "${INIT_ENSURE_SUPERUSER:-false}" == "true" ]]; then
    log "Ensuring default superuser..."
    run_manage ensure_superuser
  fi
}

maybe_load_runtime_env() {
  # Se runtime.env existir, exporta variáveis DB_* para sobrescrever os
  # valores hardcoded do docker-compose. Isso garante que credenciais
  # alteradas via First-Time Setup persistam entre restarts do container.
  local runtime_env="/app/database/runtime.env"
  [[ -f "$runtime_env" ]] || return 0

  local key value
  while IFS='=' read -r key value; do
    # ignora comentários e linhas vazias
    [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
    [[ "$key" != *=* && -n "$value" ]] || true  # já separado pelo IFS
    # remove aspas duplas ou simples ao redor do valor
    value="${value%\"}"  ; value="${value#\"}"
    value="${value%\'}"  ; value="${value#\'}"
    case "$key" in
      DB_USER|DB_PASSWORD|DB_NAME|DB_HOST|DB_PORT)
        export "$key=$value"
        log "runtime.env: $key carregado"
        ;;
    esac
  done < "$runtime_env"
}

maybe_generate_fernet_key() {
  # Se FERNET_KEY não está definida, gera e tenta persistir em database/fernet.key
  # O valor é exportado para que gunicorn/celery herdem via exec
  if [[ -z "${FERNET_KEY:-}" ]]; then
    local key_file="/app/database/fernet.key"
    if [[ -f "$key_file" ]]; then
      export FERNET_KEY
      FERNET_KEY="$(cat "$key_file")"
      log "FERNET_KEY carregada de $key_file"
    else
      export FERNET_KEY
      FERNET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
      # Tenta persistir — falha silenciosa se sem permissão (não trava o boot)
      mkdir -p "$(dirname "$key_file")" 2>/dev/null || true
      if echo "$FERNET_KEY" > "$key_file" 2>/dev/null; then
        ok "FERNET_KEY gerada e salva em $key_file"
        warn "Para produção, defina FERNET_KEY no .env para garantir persistência"
      else
        warn "FERNET_KEY gerada (sessão apenas) — defina FERNET_KEY no .env para persistir entre reinicializações"
      fi
    fi
  fi
}

maybe_init_app_data() {
  # Only run for web/gunicorn workers, not celery/beat
  if [[ "${INIT_APP_DATA:-false}" == "true" ]]; then
    if [[ "$*" == *"celery"* ]]; then
      return 0
    fi
    log "Running init_app_data (superuser + periodic tasks)..."
    run_manage init_app_data
    ok "init_app_data completed"
  fi
}

setup_signal_handlers() {
  trap 'log "Received interrupt signal..."; exit 0' SIGINT SIGTERM
}

check_dependencies() {
  if [[ $# -eq 0 ]]; then
    err "No command specified for execution"
    return 1
  fi
  
  local main_cmd="$1"
  if ! command -v "$main_cmd" >/dev/null 2>&1; then
    err "Command not found: $main_cmd"
    return 1
  fi
  
  return 0
}

main() {
  setup_signal_handlers
  print_startup_info
  
  # Check dependencies
  check_dependencies "$@" || exit 1
  
  # Wait for dependent services
  if [[ "${WAIT_FOR_DB}" == "true" ]]; then
    wait_host_port "${DB_HOST:-}" "${DB_PORT:-}" "DB" 120
  fi
  
  if [[ "${WAIT_FOR_REDIS}" == "true" ]]; then
    local redis_info
    redis_info=$(parse_redis_url "${REDIS_URL:-}")
    if [[ $? -eq 0 ]]; then
      local rhost rport
      read -r rhost rport <<< "$redis_info"
      wait_host_port "$rhost" "$rport" "Redis" 120
    else
      wait_host_port "redis" "6379" "Redis" 120
    fi
  fi

  # Optional initialization steps
  maybe_load_runtime_env
  maybe_generate_fernet_key
  maybe_migrate
  maybe_collectstatic
  maybe_ensure_superuser
  maybe_init_app_data "$@"

  # Clean the Celery Beat PID file when the command invokes celery beat
  if [[ "$*" == *"celery"* && "$*" == *"beat"* ]]; then
    local pidfile="/tmp/celerybeat.pid"
    if [[ -f "$pidfile" ]]; then
      warn "Removing stale PID file: $pidfile"
      rm -f "$pidfile"
    fi
  fi

  log "Starting process: $*"
  exec "$@"
}

main "$@"
