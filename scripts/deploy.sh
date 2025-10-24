#!/usr/bin/env bash
# scripts/deploy.sh — Deploy orquestrado para Django (mapsprovefiber)
# - Builda imagens
# - Sobe dependências (db/redis)
# - Executa migrações e collectstatic (com timeout por etapa)
# - Sobe web/celery/beat
# - Faz healthcheck em /healthz
# - Melhorias: validação de ambiente, backup preventivo, rollback automático, logs com timestamp,
#              verificação de recursos (disco), checagem de versão do compose, verificação final de serviços
#
# Uso:
#   ./scripts/deploy.sh [--compose docker-compose.yml] [--settings settings.prod] [--health http://HOST:8000/healthz] [--timeout 180]
#
# Variáveis (opcionais):
#   COMPOSE_FILE=./docker-compose.yml
#   DJANGO_SETTINGS_MODULE=settings.prod
#   HEALTHCHECK_URL=http://localhost:8000/healthz
#   HEALTHCHECK_TIMEOUT=180
#   MIGRATE_TIMEOUT=300
#   COLLECTSTATIC_TIMEOUT=120
#   SERVICE_WEB=web
#   SERVICE_WORKER=celery
#   SERVICE_BEAT=beat
#
# Requisitos:
#   - docker e docker compose v2
#   - alvo /healthz no Django (core.urls -> path("healthz", ...))

set -Eeuo pipefail

### ---- UI / LOG ----
NC=$'\e[0m'; RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; BLU=$'\e[34m'
ts() { date '+%Y-%m-%d %H:%M:%S'; }
log()   { echo "$(ts) ${BLU}[deploy]${NC} $*"; }
log_step(){ echo "$(ts) ┌─ ${BLU}[deploy]${NC} $*"; }
log_end(){ echo  "$(ts) └─ ${GRN}[concluído]${NC} $*"; }
ok()    { echo "$(ts) ${GRN}[ok]${NC} $*"; }
warn()  { echo "$(ts) ${YLW}[warn]${NC} $*"; }
err()   { echo "$(ts) ${RED}[err]${NC} $*" >&2; }
die()   { err "$*"; exit 1; }

### ---- METADADOS ----
SCRIPT_VERSION="1.1.0"
COMPOSE_MIN_VERSION="2.0.0"

### ---- DEFAULTS ----
COMPOSE_FILE="${COMPOSE_FILE:-./docker-compose.yml}"
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
Uso: $0 [opções]

Opções:
  --compose FILE          Caminho para docker-compose.yml (padrão: $COMPOSE_FILE)
  --settings MODULE       DJANGO_SETTINGS_MODULE (padrão: $DJANGO_SETTINGS_MODULE)
  --health URL            URL de healthcheck (padrão: $HEALTHCHECK_URL)
  --timeout SECONDS       Timeout do healthcheck (padrão: $HEALTHCHECK_TIMEOUT)
  -h, --help              Mostra esta ajuda

Ambiente:
  SERVICE_WEB, SERVICE_WORKER, SERVICE_BEAT para nomes dos serviços (compose).
Versões:
  script v${SCRIPT_VERSION} | compose mínimo recomendado ${COMPOSE_MIN_VERSION}
EOF
      exit 0;;
    *) die "Opção desconhecida: $1";;
  esac
done

### ---- HELPERS ----
compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

wait_for_url() {
  local url="$1" timeout="$2" t=0
  log "Aguardando health em: $url"
  until curl -fsS "$url" >/dev/null 2>&1; do
    sleep 2; t=$((t+2))
    if (( t >= timeout )); then
      return 1
    fi
  done
  return 0
}

### ---- VALIDAÇÕES E SEGURANÇA ----
check_compose_version() {
  local cv
  cv="$(docker compose version --short || echo "0")"
  if [[ "$(printf '%s\n' "$COMPOSE_MIN_VERSION" "$cv" | sort -V | head -n1)" != "$COMPOSE_MIN_VERSION" ]]; then
    warn "docker compose ($cv) pode ser inferior ao recomendado ($COMPOSE_MIN_VERSION)"
  else
    ok "docker compose versão $cv"
  fi
}

validate_environment() {
  log_step "Validando ambiente"
  command -v docker >/dev/null || die "docker não encontrado"
  docker compose version >/dev/null || die "docker compose v2 não encontrado"
  [[ -f "$COMPOSE_FILE" ]] || die "compose file não encontrado: $COMPOSE_FILE"

  local critical_vars=("DJANGO_SETTINGS_MODULE" "COMPOSE_FILE")
  for var in "${critical_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
      warn "Variável $var está vazia"
    fi
  done

  if ! compose config -q; then
    die "Compose file inválido: $COMPOSE_FILE"
  fi
  log_end "Ambiente validado"
}

check_disk_space() {
  log_step "Verificando espaço em disco"
  local available_kb min_kb
  available_kb=$(df / | awk 'NR==2 {print $4}')
  min_kb=$((1024 * 1024 * 2)) # 2GB
  if [[ "$available_kb" -lt "$min_kb" ]]; then
    warn "Espaço em disco baixo: ${available_kb}KB disponível"
    return 1
  fi
  log_end "Espaço em disco suficiente"
  return 0
}

# Backup preventivo: tenta MariaDB; se falhar, tenta PostgreSQL; caso não consiga, apenas avisa.
create_pre_deploy_backup() {
  log_step "Criando backup preventivo do banco (se disponível)"
  if ! compose ps db | grep -q "Up"; then
    warn "Serviço de banco não está rodando, pulando backup preventivo"
    return 0
  fi

  local tsf="backup_pre_deploy_$(date +%Y%m%d_%H%M%S)"
  local out_mysql="/tmp/${tsf}.sql"
  local out_pg="/tmp/${tsf}.pg.sql"

  # MariaDB/MySQL (recomendado para mapsprovefiber)
  if compose exec -T db sh -lc 'command -v mysqldump >/dev/null 2>&1'; then
    if compose exec -T db sh -lc 'mysqldump --version >/dev/null 2>&1'; then
      if compose exec -T db sh -lc 'mysqldump -uroot -p"$MARIADB_ROOT_PASSWORD" --all-databases' > "$out_mysql" 2>/dev/null; then
        log_end "Backup (MySQL/MariaDB) criado: $out_mysql"
        return 0
      fi
    fi
  fi

  # PostgreSQL (fallback)
  if compose exec -T db sh -lc 'command -v pg_dumpall >/dev/null 2>&1'; then
    if compose exec -T db sh -lc 'pg_dumpall -U postgres' > "$out_pg" 2>/dev/null; then
      log_end "Backup (PostgreSQL) criado: $out_pg"
      return 0
    fi
  fi

  warn "Não foi possível criar backup preventivo (sem erro fatal)"
  return 0
}

rollback() {
  err "Iniciando rollback..."
  compose down --timeout 30 || true
  ok "Rollback concluído - serviços parados"
  exit 1
}

setup_error_handling() {
  # Em qualquer erro ou sinal, dispara rollback
  trap rollback ERR SIGINT SIGTERM
}

check_services_health() {
  log_step "Verificando saúde dos serviços"
  local services=("$SERVICE_WEB" "$SERVICE_WORKER" "$SERVICE_BEAT")
  for service in "${services[@]}"; do
    if compose ps "$service" | grep -q "Up"; then
      ok "Serviço $service está rodando"
    else
      warn "Serviço $service não está rodando"
    fi
  done
  log_end "Verificação de serviços concluída"
}

### ---- RESUMO ----
log "Script v${SCRIPT_VERSION}"
log "Compose file: $COMPOSE_FILE"
log "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
log "Healthcheck: $HEALTHCHECK_URL (timeout ${HEALTHCHECK_TIMEOUT}s)"
log "Services: web=${SERVICE_WEB} worker=${SERVICE_WORKER} beat=${SERVICE_BEAT}"

### ---- FLUXO PRINCIPAL MELHORADO ----
setup_error_handling
check_compose_version
validate_environment
check_disk_space || warn "Espaço em disco pode ser insuficiente"
create_pre_deploy_backup

### ---- BUILD ----
log_step "Buildando imagens (pull + build)"
compose build --pull
log_end "Build concluído"

### ---- DEPENDÊNCIAS: DB/REDIS ----
log_step "Subindo dependências (db/redis) em background"
compose up -d db || true
compose up -d redis || true
log_end "Dependências tratadas"

### ---- MIGRAÇÕES ----
log_step "Executando migrações (timeout ${MIGRATE_TIMEOUT}s)"
compose run --rm \
  -e DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE" \
  "$SERVICE_WEB" timeout "$MIGRATE_TIMEOUT" python manage.py migrate --noinput
log_end "Migrações aplicadas"

### ---- COLLECTSTATIC ----
log_step "Executando collectstatic (timeout ${COLLECTSTATIC_TIMEOUT}s)"
compose run --rm \
  -e DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE" \
  "$SERVICE_WEB" timeout "$COLLECTSTATIC_TIMEOUT" python manage.py collectstatic --noinput
log_end "Collectstatic concluído"

### ---- SUBIR SERVIÇOS ----
log_step "Subindo serviços: $SERVICE_WEB $SERVICE_WORKER $SERVICE_BEAT"
compose up -d "$SERVICE_WEB" || die "falha ao subir $SERVICE_WEB"
compose up -d "$SERVICE_WORKER" || warn "worker não subiu (serviço opcional?)"
compose up -d "$SERVICE_BEAT" || warn "beat não subiu (serviço opcional?)"
log_end "Serviços em execução (subida inicial)"

### ---- HEALTHCHECK ----
if wait_for_url "$HEALTHCHECK_URL" "$HEALTHCHECK_TIMEOUT"; then
  ok "Aplicação saudável em: $HEALTHCHECK_URL"
else
  err "Healthcheck falhou após ${HEALTHCHECK_TIMEOUT}s."
  err "Logs recentes do serviço web:"
  compose logs --since=10m "$SERVICE_WEB" || true
  rollback
fi

### ---- VERIFICAÇÃO FINAL DE SERVIÇOS ----
check_services_health
ok "Deploy finalizado com sucesso."
