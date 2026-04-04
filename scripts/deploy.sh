#!/usr/bin/env bash
# scripts/deploy.sh — Production deployment for MapsProveFiber
#
# Workflow:
#   1. Validate environment + secrets
#   2. Check disk space
#   3. Bootstrap SSL (first run only) OR renew certificate
#   4. Pre-deploy database backup
#   5. Build Docker images
#   6. Start DB + Redis
#   7. Run migrations + collectstatic + init_app_data
#   8. Start/recreate all services
#   9. Health check + rollback on failure
#
# Usage:
#   ./scripts/deploy.sh [OPTIONS]
#
# Options:
#   --profile    PROFILE   Compose profile to activate (default: minimal)
#   --compose    FILE      Path to compose file (default: docker/docker-compose.prod.yml)
#   --health     URL       Health check URL (default: https://$DOMAIN_NAME/healthz/)
#   --timeout    SECONDS   Health check timeout (default: 180)
#   --no-build             Skip image build (deploy with current images)
#   --no-certbot           Skip certbot SSL bootstrap/renewal
#   --init-data            Run init_app_data management command
#   -h, --help             Show this message
#
# Environment variables (loaded from .env.production if present):
#   DOMAIN_NAME, CERTBOT_EMAIL, COMPOSE_PROFILES, REDIS_PASSWORD,
#   SECRET_KEY, DB_PASSWORD, ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS

set -Eeuo pipefail

# ---- ui helpers ----
NC=$'\e[0m'; RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; BLU=$'\e[34m'
ts()       { date '+%Y-%m-%d %H:%M:%S'; }
log()      { echo "$(ts) ${BLU}[deploy]${NC} $*"; }
log_step() { echo "$(ts) --> ${BLU}$*${NC}"; }
log_end()  { echo "$(ts) <-- ${GRN}done:${NC} $*"; }
ok()       { echo "$(ts) ${GRN}[ok]${NC} $*"; }
warn()     { echo "$(ts) ${YLW}[warn]${NC} $*"; }
err()      { echo "$(ts) ${RED}[err]${NC} $*" >&2; }
die()      { err "$*"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---- defaults ----
COMPOSE_FILE="${COMPOSE_FILE:-${REPO_ROOT}/docker/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-${REPO_ROOT}/.env.production}"
PROFILE="${PROFILE:-${COMPOSE_PROFILES:-minimal}}"
HEALTHCHECK_TIMEOUT="${HEALTHCHECK_TIMEOUT:-180}"
DO_BUILD=true
DO_CERTBOT=true
DO_INIT_DATA=false

# ---- parse args ----
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)    PROFILE="$2"; shift 2;;
    --compose)    COMPOSE_FILE="$2"; shift 2;;
    --health)     HEALTHCHECK_URL="$2"; shift 2;;
    --timeout)    HEALTHCHECK_TIMEOUT="$2"; shift 2;;
    --no-build)   DO_BUILD=false; shift;;
    --no-certbot) DO_CERTBOT=false; shift;;
    --init-data)  DO_INIT_DATA=true; shift;;
    -h|--help)
      sed -n '3,30p' "${BASH_SOURCE[0]}"
      exit 0;;
    *) die "Unknown option: $1 (use --help)";;
  esac
done

# ---- load .env.production if exists ----
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a; source "${ENV_FILE}"; set +a
  ok "Loaded ${ENV_FILE}"
else
  warn ".env.production not found — relying on shell environment"
fi

DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
HEALTHCHECK_URL="${HEALTHCHECK_URL:-https://${DOMAIN_NAME}/healthz/}"

# ---- compose wrapper ----
compose() {
  docker compose -f "${COMPOSE_FILE}" --profile "${PROFILE}" "$@"
}

# =============================================================
# validate_environment — check required secrets + tools
# =============================================================
validate_environment() {
  log_step "Validating environment"
  command -v docker >/dev/null || die "docker not found"
  docker compose version >/dev/null 2>&1 || die "docker compose v2 not available"
  [[ -f "${COMPOSE_FILE}" ]] || die "Compose file not found: ${COMPOSE_FILE}"

  local required_vars=(
    SECRET_KEY DB_PASSWORD REDIS_PASSWORD
    ALLOWED_HOSTS CSRF_TRUSTED_ORIGINS
  )
  local missing=()
  for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
      missing+=("$var")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    die "Missing required env vars: ${missing[*]}
  Copy .env.production.example to .env.production and fill in the values."
  fi

  # Warn if still using placeholder values
  if [[ "${SECRET_KEY}" == *"change-me"* || "${SECRET_KEY}" == *"insecure"* ]]; then
    die "SECRET_KEY looks like a placeholder — set a real secret key"
  fi

  compose config -q 2>/dev/null || die "Compose config validation failed"
  log_end "Environment OK (profile: ${PROFILE})"
}

# =============================================================
# check_disk_space — require at least 3 GB free
# =============================================================
check_disk_space() {
  log_step "Checking disk space"
  local avail_kb min_kb
  avail_kb=$(df "${REPO_ROOT}" | awk 'NR==2{print $4}')
  min_kb=$((3 * 1024 * 1024))
  if [[ "${avail_kb}" -lt "${min_kb}" ]]; then
    warn "Low disk: ${avail_kb}KB free (recommended: ≥3GB)"
  else
    log_end "Disk OK (${avail_kb}KB free)"
  fi
}

# =============================================================
# bootstrap_ssl — obtain Let's Encrypt cert on first deploy
# =============================================================
bootstrap_ssl() {
  if [[ "${DO_CERTBOT}" == "false" ]]; then
    warn "Certbot skipped (--no-certbot)"
    return 0
  fi
  if [[ "${DOMAIN_NAME}" == "localhost" ]]; then
    warn "DOMAIN_NAME=localhost — skipping SSL bootstrap"
    return 0
  fi

  local cert_path="/etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem"
  if docker volume ls -q | grep -q "letsencrypt" && \
     docker run --rm -v letsencrypt:/etc/letsencrypt alpine test -f "${cert_path}" 2>/dev/null; then
    log "Certificate already exists — checking renewal"
    # Renewal handled by certbot container (runs every 12h automatically)
    return 0
  fi

  log_step "Obtaining SSL certificate for ${DOMAIN_NAME}"
  if [[ -z "${CERTBOT_EMAIL:-}" ]]; then
    warn "CERTBOT_EMAIL not set — certbot will register without email"
  fi

  # Temporarily serve HTTP using the bootstrap config
  local initial_conf="${REPO_ROOT}/docker/nginx/nginx.initial.conf"
  if [[ ! -f "${initial_conf}" ]]; then
    die "Missing ${initial_conf} — cannot bootstrap SSL"
  fi

  log "Starting nginx with HTTP-only bootstrap config"
  docker compose -f "${COMPOSE_FILE}" run --rm \
    -v "${initial_conf}:/etc/nginx/nginx.conf:ro" \
    -p "80:80" \
    --entrypoint "nginx -g 'daemon off;'" \
    nginx &
  local nginx_pid=$!
  sleep 3

  docker run --rm \
    -v letsencrypt:/etc/letsencrypt \
    -v certbot_webroot:/var/www/certbot \
    certbot/certbot certonly \
      --webroot \
      --webroot-path /var/www/certbot \
      --email "${CERTBOT_EMAIL:-}" \
      --agree-tos \
      --no-eff-email \
      -d "${DOMAIN_NAME}" \
      && ok "Certificate obtained for ${DOMAIN_NAME}" \
      || { kill "${nginx_pid}" 2>/dev/null || true; die "certbot failed"; }

  kill "${nginx_pid}" 2>/dev/null || true
  log_end "SSL bootstrap complete"
}

# =============================================================
# pre_deploy_backup — pg_dump into /tmp
# =============================================================
pre_deploy_backup() {
  log_step "Pre-deploy database backup"
  if ! compose ps postgres 2>/dev/null | grep -q "running\|Up"; then
    warn "postgres not running — skipping backup"
    return 0
  fi

  local tsf out
  tsf="$(date +%Y%m%d_%H%M%S)"
  out="/tmp/backup_pre_deploy_${tsf}.sql"

  if compose exec -T postgres \
       pg_dump -U "${DB_USER:-mapsprovefiber}" "${DB_NAME:-mapsprovefiber}" \
       > "${out}" 2>/dev/null; then
    ok "Backup saved: ${out}"
  else
    warn "pg_dump failed — continuing without backup"
  fi
}

# =============================================================
# rollback — stop everything on error
# =============================================================
rollback() {
  err "Deployment failed — stopping services"
  compose down --timeout 30 || true
  err "Rollback complete"
  exit 1
}

# =============================================================
# wait_for_url — poll until URL returns 2xx
# =============================================================
wait_for_url() {
  local url="$1" timeout="$2" elapsed=0
  log "Waiting for: ${url} (timeout ${timeout}s)"
  until curl -fsS --max-time 5 "${url}" >/dev/null 2>&1; do
    sleep 3; elapsed=$((elapsed + 3))
    if (( elapsed >= timeout )); then
      return 1
    fi
    printf "."
  done
  echo ""
  return 0
}

# =============================================================
# MAIN
# =============================================================
trap rollback ERR SIGINT SIGTERM

log "=== MapsProveFiber Deploy ==="
log "Compose : ${COMPOSE_FILE}"
log "Profile : ${PROFILE}"
log "Domain  : ${DOMAIN_NAME}"

validate_environment
check_disk_space
bootstrap_ssl
pre_deploy_backup

# Build
if [[ "${DO_BUILD}" == "true" ]]; then
  log_step "Building images"
  compose build --pull
  log_end "Build done"
fi

# Start infrastructure
log_step "Starting postgres + redis"
compose up -d postgres redis
log "Waiting 10s for services to initialize..."
sleep 10
log_end "Infrastructure up"

# Migrations + collectstatic
log_step "Migrations"
compose run --rm \
  -e INIT_MIGRATE=true \
  -e INIT_COLLECTSTATIC=false \
  web python manage.py migrate --noinput
log_end "Migrations applied"

log_step "Collectstatic"
compose run --rm web python manage.py collectstatic --noinput
log_end "Collectstatic done"

# Optional init_app_data
if [[ "${DO_INIT_DATA}" == "true" ]]; then
  log_step "Running init_app_data"
  compose run --rm web python manage.py init_app_data
  log_end "App data initialized"
fi

# Start all services
log_step "Starting all services (profile: ${PROFILE})"
compose up -d --remove-orphans
log_end "Services started"

# Health check
if wait_for_url "${HEALTHCHECK_URL}" "${HEALTHCHECK_TIMEOUT}"; then
  ok "Application healthy: ${HEALTHCHECK_URL}"
else
  err "Health check failed after ${HEALTHCHECK_TIMEOUT}s"
  err "=== Recent web logs ==="
  compose logs --tail=50 web || true
  rollback
fi

# Final status
log_step "Service status"
compose ps
ok "=== Deployment complete ==="
