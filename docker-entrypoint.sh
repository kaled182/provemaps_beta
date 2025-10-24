#!/usr/bin/env bash
# docker-entrypoint.sh — inicializações leves antes do comando final
# Objetivo:
#  - Esperar DB/Redis (se definidos) antes de iniciar web/celery/beat
#  - Opcionalmente rodar migrações/coleta de estáticos via flags
#
# Uso (exemplos no docker-compose.yml):
#   ENTRYPOINT ["/docker-entrypoint.sh"]
#   CMD ["gunicorn", "core.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
#
# Variáveis/flags de conveniência (todas opcionais):
#   WAIT_FOR_DB=true|false           # aguardar DB (default: true se DB_HOST setado)
#   WAIT_FOR_REDIS=true|false        # aguardar Redis (default: true se REDIS_URL setado)
#   INIT_MIGRATE=true|false          # rodar manage.py migrate antes de subir (default: false)
#   INIT_COLLECTSTATIC=true|false    # rodar manage.py collectstatic --noinput (default: false)
#   MIGRATE_TIMEOUT=300              # timeout do migrate (segundos)
#   COLLECTSTATIC_TIMEOUT=120        # timeout do collectstatic (segundos)

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
  log "=== Inicialização do Container ==="
  log "App: $(python -c "import django; print(django.get_version())" 2>/dev/null || echo "N/A")"
  log "Python: $(python --version 2>/dev/null || echo "N/A")"
  log "Settings: ${DJANGO_SETTINGS_MODULE:-Não definido}"
  log "DB: ${DB_HOST:-Não definido}:${DB_PORT:-N/A}"
  log "Redis: ${REDIS_URL:-Não definido}"
  log "Flags: WAIT_FOR_DB=${WAIT_FOR_DB}, WAIT_FOR_REDIS=${WAIT_FOR_REDIS}"
  log "Init: MIGRATE=${INIT_MIGRATE}, COLLECTSTATIC=${INIT_COLLECTSTATIC}"
  log "=================================="
}

wait_host_port() {
  local host="${1:-}" port="${2:-}" name="${3:-srv}" retries="${4:-120}"
  if [[ -z "$host" || -z "$port" ]]; then return 0; fi
  log "Aguardando ${name} em ${host}:${port} (timeout ~${retries}s)"
  
  for ((i=1; i<=retries; i++)); do
    if command -v nc >/dev/null 2>&1; then
      if nc -z -w 1 "$host" "$port" >/dev/null 2>&1; then 
        ok "${name} disponível após ${i}s"; return 0; 
      fi
    else
      # Python fallback robusto
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
        ok "${name} disponível após ${i}s"; return 0
      fi
    fi
    sleep 1
  done
  
  warn "Timeout ao aguardar ${name} após ${retries}s — seguindo assim mesmo"
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
    warn "REDIS_URL malformada: $rurl - usando padrões"
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
    log "Executando migrações (timeout ${MIGRATE_TIMEOUT}s)"
    if command -v timeout >/dev/null 2>&1; then
      timeout "${MIGRATE_TIMEOUT}" env PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-settings.dev}" \
        python manage.py migrate --noinput
    else
      run_manage migrate --noinput
    fi
    ok "Migrações aplicadas"
  fi
}

maybe_collectstatic() {
  if [[ "${INIT_COLLECTSTATIC}" == "true" ]]; then
    log "Executando collectstatic (timeout ${COLLECTSTATIC_TIMEOUT}s)"
    if command -v timeout >/dev/null 2>&1; then
      timeout "${COLLECTSTATIC_TIMEOUT}" env PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-settings.dev}" \
        python manage.py collectstatic --noinput
    else
      run_manage collectstatic --noinput
    fi
    ok "Collectstatic concluído"
  fi
}

setup_signal_handlers() {
  trap 'log "Recebido sinal de interrupção..."; exit 0' SIGINT SIGTERM
}

check_dependencies() {
  if [[ $# -eq 0 ]]; then
    err "Nenhum comando especificado para execução"
    return 1
  fi
  
  local main_cmd="$1"
  if ! command -v "$main_cmd" >/dev/null 2>&1; then
    err "Comando não encontrado: $main_cmd"
    return 1
  fi
  
  return 0
}

main() {
  setup_signal_handlers
  print_startup_info
  
  # Verifica dependências
  check_dependencies "$@" || exit 1
  
  # Aguarda serviços dependentes
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

  # Inicializações opcionais
  maybe_migrate
  maybe_collectstatic

  log "Iniciando processo: $*"
  exec "$@"
}

main "$@"
