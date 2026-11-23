#!/usr/bin/env bash
# update.sh — Atualização automática do ProVeMaps no Ubuntu/Debian
# Uso: sudo bash update.sh
# Testado em: Ubuntu 22.04 LTS / 24.04 LTS / Debian 12
#
# O que faz (EV-0038 / EV-0039 / EV-0052):
#   1. git fetch + reset --hard origin/${UPDATE_BRANCH} — como o DONO do repositório, não como
#      root (ficheiros recriados pelo reset ficavam do root e o npm/git seguintes davam EACCES);
#   2. build das imagens web/celery/beat com GIT_SHA e APP_VERSION cozidos (o /healthz passa a
#      dizer o commit e a versão; é por eles que a Central de Evolução fecha itens);
#   3. up -d web celery beat nginx; 4. espera pelo /healthz e mostra o SHA no ar.
# O frontend NÃO é compilado no host: desde o EV-0052 o SPA vem da imagem (estágio
# frontend-builder do docker/dockerfile, com `npm ci`). HOST_FRONTEND_BUILD=true ainda compila
# no host (como o dono, com `npm ci`), só para desenvolvimento — não muda o que está no ar.
#
# Variáveis: INSTALL_DIR (/opt/provemaps), UPDATE_BRANCH (main), HOST_FRONTEND_BUILD (false),
#            ASSUME_YES (false — não pergunta).

set -Eeuo pipefail

# ─── Configurações Gerais ─────────────────────────────────────────────────────
INSTALL_DIR="${INSTALL_DIR:-/opt/provemaps}"
REAL_USER="${SUDO_USER:-root}"
UPDATE_BRANCH="${UPDATE_BRANCH:-main}"
HOST_FRONTEND_BUILD="${HOST_FRONTEND_BUILD:-false}"
ASSUME_YES="${ASSUME_YES:-false}"
LOG_FILE="/var/log/provemaps_update.log"
COMPOSE_FILE="${INSTALL_DIR}/docker/docker-compose.yml"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
VERSION_FILE="${INSTALL_DIR}/VERSION"

# Limpa/Cria o log
: > "$LOG_FILE"
[[ "${REAL_USER}" != "root" ]] && chown "${REAL_USER}:${REAL_USER}" "$LOG_FILE" 2>/dev/null || true

# ─── Cores e Funções Visuais ──────────────────────────────────────────────────
NC=$'\e[0m'; BLU=$'\e[34m'; GRN=$'\e[32m'; YLW=$'\e[33m'; RED=$'\e[31m'; BLD=$'\e[1m'
log()  { echo -e "${BLU}[provemaps]${NC} $*"; }
ok()   { echo -e "${GRN}[ok]${NC} $*"; }
warn() { echo -e "${YLW}[aviso]${NC} $*"; }
err()  { echo -e "${RED}[erro]${NC} $*\n${YLW}[!] Detalhes no log: ${LOG_FILE}${NC}" >&2; exit 1; }
sep()  { echo -e "\n${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    tput civis 2>/dev/null || true
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " ${BLU}%c${NC} Processando..." "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\r\033[K"
    done
    tput cnorm 2>/dev/null || true
    wait "$pid"
    return $?
}

# ─── Verificações iniciais ────────────────────────────────────────────────────
[[ "$EUID" -ne 0 ]] && err "Execute como root: sudo bash $0"
[[ "$(uname -s)" != "Linux" ]] && err "Este script é para Linux/Ubuntu."
[[ ! -d "${INSTALL_DIR}/.git" ]] && err "ProVeMaps não encontrado em ${INSTALL_DIR}. Use install_ubuntu.sh para instalar."

command -v docker  &>/dev/null || err "Docker não encontrado. Instale com: sudo bash ${INSTALL_DIR}/scripts/install_ubuntu.sh"
docker compose version &>/dev/null || err "docker compose não encontrado."
if [[ "${HOST_FRONTEND_BUILD}" == "true" ]]; then
    command -v node &>/dev/null || err "Node.js não encontrado (HOST_FRONTEND_BUILD=true). Instale com: sudo bash ${INSTALL_DIR}/scripts/install_ubuntu.sh"
fi

# EV-0038: git e npm correm como o DONO do repositório (quem fez o clone), não como root nem
# necessariamente como $SUDO_USER. Assim o reset não deixa ficheiros do root no meio da árvore,
# e o git não recusa o repositório por «dubious ownership».
REPO_OWNER="$(stat -c '%U' "${INSTALL_DIR}")"
as_owner() {
    if [[ "${REPO_OWNER}" == "root" ]]; then
        "$@"
    else
        local home
        home="$(getent passwd "${REPO_OWNER}" | cut -d: -f6)"
        runuser -u "${REPO_OWNER}" -- env HOME="${home:-/tmp}" "$@"
    fi
}

# Um `reset --hard origin/main` noutro ramo reescreveria esse ramo com o main: recusa-se.
BRANCH_ATUAL="$(as_owner git -C "${INSTALL_DIR}" rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
[[ "${BRANCH_ATUAL}" != "${UPDATE_BRANCH}" ]] && \
    err "O repositório está no ramo '${BRANCH_ATUAL}', não em '${UPDATE_BRANCH}'. Faça checkout de '${UPDATE_BRANCH}' ou use UPDATE_BRANCH=${BRANCH_ATUAL}."

# ─── Cabeçalho ───────────────────────────────────────────────────────────────
sep
echo -e "${BLD}  ProVeMaps — Atualização automática${NC}"
sep
echo ""

VERSION_ATUAL=$(cat "${VERSION_FILE}" 2>/dev/null | tr -d '[:space:]' || echo "desconhecida")
log "Versão instalada: ${BLD}v${VERSION_ATUAL}${NC}"
log "Diretório:        ${INSTALL_DIR} (dono: ${REPO_OWNER}, ramo: ${UPDATE_BRANCH})"
log "Log:              ${LOG_FILE}"
echo ""
if [[ "${ASSUME_YES}" != "true" ]]; then
    read -r -p "Continuar com a atualização? [S/n] " CONFIRM
    [[ "${CONFIRM,,}" == "n" ]] && exit 0
fi

# ─── PASSO 1: git pull ────────────────────────────────────────────────────────
sep
log "PASSO 1/4 — Obtendo código mais recente (git fetch + reset para origin/${UPDATE_BRANCH})..."

(
    as_owner git -C "${INSTALL_DIR}" fetch origin
    as_owner git -C "${INSTALL_DIR}" reset --hard "origin/${UPDATE_BRANCH}"
) >> "$LOG_FILE" 2>&1 &

spinner $! || err "Falha no git pull. Verifique: ${LOG_FILE}"

# Limpa bytecode obsoleto para evitar que .pyc antigos mascarem mudanças
find "${INSTALL_DIR}/backend" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

VERSION_NOVA=$(cat "${VERSION_FILE}" 2>/dev/null | tr -d '[:space:]' || echo "desconhecida")

if [[ "${VERSION_ATUAL}" == "${VERSION_NOVA}" ]]; then
    ok "Código atualizado — versão mantida: v${VERSION_NOVA}"
else
    ok "Código atualizado: v${VERSION_ATUAL} → ${GRN}v${VERSION_NOVA}${NC}"
fi

# Permissões dos diretórios montados nos containers. O `database/` guarda segredos
# (runtime.env, fernet.key — EV-0043): nunca 777, só dono e grupo (o mesmo que o entrypoint faz).
# backend/staticfiles já não é montado (volume static_data, EV-0052).
chmod -R 777 \
    "${INSTALL_DIR}/backend/media" \
    "${INSTALL_DIR}/logs" 2>/dev/null || true
chmod -R u+rwX,g+rwX,o-rwx "${INSTALL_DIR}/database" 2>/dev/null || true

find "${INSTALL_DIR}/scripts" -name "*.sh" -exec chmod +x {} \;

# ─── PASSO 2: Frontend no host (opcional) ───────────────────────────────────
# O SPA em produção vem da imagem (EV-0052). Só com HOST_FRONTEND_BUILD=true se compila aqui.
sep
if [[ "${HOST_FRONTEND_BUILD}" == "true" ]]; then
    log "PASSO 2/4 — Compilando frontend no host (HOST_FRONTEND_BUILD=true; não entra no ar)..."
    (
        cd "${FRONTEND_DIR}"
        as_owner npm ci
        as_owner npm run build
    ) >> "$LOG_FILE" 2>&1 &
    spinner $! || err "Falha na compilação do frontend. Verifique: ${LOG_FILE}"
    ok "Frontend compilado no host."
else
    log "PASSO 2/4 — Frontend: vem da imagem (estágio frontend-builder, npm ci) — nada a fazer no host."
fi

# ─── PASSO 3: Rebuild e restart dos containers ───────────────────────────────
# Reconstrói web + celery + beat (backend Python + SPA da imagem) com o commit e a versão
# cozidos (EV-0039): o /healthz passa a dizer git_sha/version e o `make evolucao-sync` fecha.
# O entrypoint do web copia o SPA da imagem para o volume static_data a cada arranque.
GIT_SHA="$(as_owner git -C "${INSTALL_DIR}" rev-parse HEAD)"
APP_VERSION="${VERSION_NOVA}"
export GIT_SHA APP_VERSION
echo "GIT_SHA=${GIT_SHA} APP_VERSION=${APP_VERSION}" >> "$LOG_FILE"

sep
log "PASSO 3/4 — Reconstruindo e reiniciando containers (web, celery, beat, nginx) — ${GIT_SHA:0:12}..."

(
    docker compose -f "${COMPOSE_FILE}" build web celery beat
    docker compose -f "${COMPOSE_FILE}" up -d web celery beat nginx
) >> "$LOG_FILE" 2>&1 &

spinner $! || err "Falha ao reconstruir containers. Verifique: ${LOG_FILE}"
ok "Containers atualizados e iniciados."

# ─── PASSO 4: Aguardar aplicação ─────────────────────────────────────────────
sep
log "PASSO 4/4 — Aguardando aplicação iniciar (health check)..."

(
    for _ in $(seq 1 90); do
        if curl -sf "http://localhost:8100/healthz" > /dev/null 2>&1; then
            exit 0
        fi
        sleep 1
    done
    exit 1
) &

# `if spinner` e não `spinner; if [[ $? ]]`: com `set -e` um timeout matava o script antes do aviso.
if spinner $!; then
    ok "Aplicação online e respondendo!"
    SHA_NO_AR="$(curl -s "http://localhost:8100/healthz" 2>/dev/null | sed -n 's/.*"git_sha" *: *"\([^"]*\)".*/\1/p')"
    if [[ "${SHA_NO_AR}" == "${GIT_SHA}" ]]; then
        ok "/healthz confirma o commit no ar: ${SHA_NO_AR:0:12}"
    else
        warn "/healthz diz git_sha='${SHA_NO_AR}', esperado ${GIT_SHA:0:12} — o container novo pode ainda não estar no ar."
    fi
else
    warn "Timeout ao aguardar /healthz — pode ainda estar inicializando."
    warn "Verifique com: docker compose -f ${COMPOSE_FILE} logs -f web"
fi

# ─── Resumo final ────────────────────────────────────────────────────────────
sep
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GRN}${BLD}  Atualização concluída!${NC}"
echo ""
[[ "${VERSION_ATUAL}" != "${VERSION_NOVA}" ]] && \
    echo -e "  Versão: ${YLW}v${VERSION_ATUAL}${NC} → ${GRN}${BLD}v${VERSION_NOVA}${NC}"
echo ""
echo -e "  Acesso:  ${BLD}http://${SERVER_IP}:8100${NC}"
echo ""
echo -e "  Comandos úteis:"
echo -e "    docker compose -f ${COMPOSE_FILE} ps"
echo -e "    docker compose -f ${COMPOSE_FILE} logs -f web"
echo -e "    tail -f ${LOG_FILE}  ${YLW}# log completo da atualização${NC}"
echo ""
sep
