#!/usr/bin/env bash
# update.sh — Atualização automática do ProVeMaps no Ubuntu/Debian
# Uso: sudo bash update.sh
# Testado em: Ubuntu 22.04 LTS / 24.04 LTS / Debian 12

set -Eeuo pipefail

# ─── Configurações Gerais ─────────────────────────────────────────────────────
INSTALL_DIR="${INSTALL_DIR:-/opt/provemaps}"
REAL_USER="${SUDO_USER:-root}"
LOG_FILE="/var/log/provemaps_update.log"
COMPOSE_FILE="${INSTALL_DIR}/docker/docker-compose.yml"
FRONTEND_DIR="${INSTALL_DIR}/frontend"
VERSION_FILE="${INSTALL_DIR}/VERSION"

# Limpa/Cria o log
> "$LOG_FILE"
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
command -v node    &>/dev/null || err "Node.js não encontrado. Instale com: sudo bash ${INSTALL_DIR}/scripts/install_ubuntu.sh"
docker compose version &>/dev/null || err "docker compose não encontrado."

# ─── Cabeçalho ───────────────────────────────────────────────────────────────
sep
echo -e "${BLD}  ProVeMaps — Atualização automática${NC}"
sep
echo ""

VERSION_ATUAL=$(cat "${VERSION_FILE}" 2>/dev/null | tr -d '[:space:]' || echo "desconhecida")
log "Versão instalada: ${BLD}v${VERSION_ATUAL}${NC}"
log "Diretório:        ${INSTALL_DIR}"
log "Log:              ${LOG_FILE}"
echo ""
read -r -p "Continuar com a atualização? [S/n] " CONFIRM
[[ "${CONFIRM,,}" == "n" ]] && exit 0

# ─── PASSO 1: git pull ────────────────────────────────────────────────────────
sep
log "PASSO 1/4 — Obtendo código mais recente (git pull)..."

(
    git -C "${INSTALL_DIR}" fetch origin
    git -C "${INSTALL_DIR}" reset --hard origin/main
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

# Garante permissões nos diretórios bind-mounted
chmod -R 777 \
    "${INSTALL_DIR}/backend/staticfiles" \
    "${INSTALL_DIR}/backend/media" \
    "${INSTALL_DIR}/database" \
    "${INSTALL_DIR}/logs" 2>/dev/null || true

find "${INSTALL_DIR}/scripts" -name "*.sh" -exec chmod +x {} \;

# ─── PASSO 2: Build do frontend ───────────────────────────────────────────────
sep
log "PASSO 2/4 — Compilando frontend Vue 3..."

(
    cd "${FRONTEND_DIR}"
    if [[ "${REAL_USER}" != "root" ]]; then
        sudo -u "${REAL_USER}" npm install --prefer-offline 2>/dev/null \
            || sudo -u "${REAL_USER}" npm install
        sudo -u "${REAL_USER}" npm run build
    else
        npm install --prefer-offline 2>/dev/null || npm install
        npm run build
    fi
) >> "$LOG_FILE" 2>&1 &

spinner $! || err "Falha na compilação do frontend. Verifique: ${LOG_FILE}"
ok "Frontend compilado com sucesso."

# ─── PASSO 3: Rebuild e restart dos containers ───────────────────────────────
# Sempre reconstruir web + celery + beat para garantir que o backend Python
# e os static files baked na imagem estejam atualizados.
sep
log "PASSO 3/4 — Reconstruindo e reiniciando containers (web, celery, beat)..."

(
    docker compose -f "${COMPOSE_FILE}" build web celery beat
    docker compose -f "${COMPOSE_FILE}" up -d web celery beat
) >> "$LOG_FILE" 2>&1 &

spinner $! || err "Falha ao reconstruir containers. Verifique: ${LOG_FILE}"
ok "Containers atualizados e iniciados."

# ─── PASSO 4: Aguardar aplicação ─────────────────────────────────────────────
sep
log "PASSO 4/4 — Aguardando aplicação iniciar (health check)..."

(
    for i in $(seq 1 90); do
        if curl -sf "http://localhost:8100/healthz" > /dev/null 2>&1; then
            exit 0
        fi
        sleep 1
    done
    exit 1
) &

spinner $!
if [[ $? -eq 0 ]]; then
    ok "Aplicação online e respondendo!"
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
