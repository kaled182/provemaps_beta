#!/usr/bin/env bash
# scripts/backup.sh — Database + Redis backup for MapsProveFiber
#
# Backs up:
#   - PostgreSQL (pg_dump → compressed .sql.gz)
#   - Redis RDB snapshot (BGSAVE + copy data/dump.rdb)
#
# Retention: keeps the N most recent backups per type (default: 7)
#
# Usage:
#   ./scripts/backup.sh [OPTIONS]
#
# Options:
#   --output-dir  DIR      Backup destination (default: /backups or $BACKUP_DIR)
#   --retention   N        Keep N most recent backups (default: 7)
#   --compose     FILE     Compose file (default: docker/docker-compose.prod.yml)
#   --no-redis             Skip Redis backup
#   --no-postgres          Skip PostgreSQL backup
#   -h, --help             Show this message
#
# Environment variables (loaded from .env.production if present):
#   DB_NAME, DB_USER, DB_PASSWORD, REDIS_PASSWORD, BACKUP_DIR

set -Eeuo pipefail

NC=$'\e[0m'; RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; BLU=$'\e[34m'
ts()   { date '+%Y-%m-%d %H:%M:%S'; }
log()  { echo "$(ts) ${BLU}[backup]${NC} $*"; }
ok()   { echo "$(ts) ${GRN}[ok]${NC} $*"; }
warn() { echo "$(ts) ${YLW}[warn]${NC} $*"; }
err()  { echo "$(ts) ${RED}[err]${NC} $*" >&2; }
die()  { err "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env.production"

# ---- defaults ----
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/docker/docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION="${RETENTION:-7}"
DO_POSTGRES=true
DO_REDIS=true
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

# ---- parse args ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)  BACKUP_DIR="$2"; shift 2;;
    --retention)   RETENTION="$2"; shift 2;;
    --compose)     COMPOSE_FILE="$2"; shift 2;;
    --no-redis)    DO_REDIS=false; shift;;
    --no-postgres) DO_POSTGRES=false; shift;;
    -h|--help)
      sed -n '3,25p' "${BASH_SOURCE[0]}"
      exit 0;;
    *) die "Unknown option: $1";;
  esac
done

# Load env file
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a; source "${ENV_FILE}"; set +a
fi

DB_NAME="${DB_NAME:-mapsprovefiber}"
DB_USER="${DB_USER:-mapsprovefiber}"
DB_PASSWORD="${DB_PASSWORD:-}"
REDIS_PASSWORD="${REDIS_PASSWORD:-}"

compose() { docker compose -f "${COMPOSE_FILE}" "$@"; }

# =============================================================
# ensure_backup_dir
# =============================================================
ensure_backup_dir() {
  mkdir -p "${BACKUP_DIR}/postgres" "${BACKUP_DIR}/redis"
  ok "Backup directory: ${BACKUP_DIR}"
}

# =============================================================
# backup_postgres — pg_dump compressed
# =============================================================
backup_postgres() {
  if [[ "${DO_POSTGRES}" == "false" ]]; then
    warn "PostgreSQL backup skipped (--no-postgres)"
    return 0
  fi

  log "Starting PostgreSQL backup"
  if ! compose ps postgres 2>/dev/null | grep -qE "running|Up"; then
    warn "postgres container not running — skipping"
    return 0
  fi

  local out="${BACKUP_DIR}/postgres/pg_${DB_NAME}_${TIMESTAMP}.sql.gz"

  if PGPASSWORD="${DB_PASSWORD}" compose exec -T postgres \
       pg_dump -U "${DB_USER}" "${DB_NAME}" \
     | gzip -9 > "${out}"; then
    local size
    size=$(du -sh "${out}" | cut -f1)
    ok "PostgreSQL backup: ${out} (${size})"
  else
    err "pg_dump failed"
    rm -f "${out}"
    return 1
  fi
}

# =============================================================
# backup_redis — BGSAVE + copy dump.rdb
# =============================================================
backup_redis() {
  if [[ "${DO_REDIS}" == "false" ]]; then
    warn "Redis backup skipped (--no-redis)"
    return 0
  fi

  log "Starting Redis backup"
  if ! compose ps redis 2>/dev/null | grep -qE "running|Up"; then
    warn "redis container not running — skipping"
    return 0
  fi

  local out="${BACKUP_DIR}/redis/redis_${TIMESTAMP}.rdb"

  # Trigger a background save and wait for it to finish
  local auth_flag=""
  if [[ -n "${REDIS_PASSWORD}" ]]; then
    auth_flag="-a ${REDIS_PASSWORD}"
  fi

  # shellcheck disable=SC2086
  compose exec -T redis redis-cli ${auth_flag} BGSAVE >/dev/null
  sleep 2  # give redis time to save

  # Copy the RDB file from inside the container
  if docker cp "mapsprovefiber_redis:/data/dump.rdb" "${out}" 2>/dev/null; then
    local size
    size=$(du -sh "${out}" | cut -f1)
    ok "Redis backup: ${out} (${size})"
  else
    warn "Could not copy Redis dump.rdb (may not exist yet)"
  fi
}

# =============================================================
# apply_retention — delete oldest files, keep N
# =============================================================
apply_retention() {
  local dir="$1" keep="$2" label="$3"
  local count
  count=$(find "${dir}" -maxdepth 1 -type f | wc -l)
  if (( count > keep )); then
    local delete_n=$(( count - keep ))
    log "Removing ${delete_n} old ${label} backup(s) (keeping ${keep})"
    find "${dir}" -maxdepth 1 -type f -printf '%T+ %p\n' \
      | sort | head -n "${delete_n}" | awk '{print $2}' \
      | xargs rm -f
    ok "Retention applied for ${label}"
  fi
}

# =============================================================
# MAIN
# =============================================================
log "=== MapsProveFiber Backup ==="
log "Timestamp : ${TIMESTAMP}"
log "Output    : ${BACKUP_DIR}"
log "Retention : ${RETENTION} backups"

ensure_backup_dir
backup_postgres
backup_redis
apply_retention "${BACKUP_DIR}/postgres" "${RETENTION}" "postgres"
apply_retention "${BACKUP_DIR}/redis"    "${RETENTION}" "redis"

ok "=== Backup complete ==="
