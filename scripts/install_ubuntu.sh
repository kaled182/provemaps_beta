#!/usr/bin/env bash
# install_ubuntu.sh — Instalação automática do ProVeMaps no Ubuntu/Debian
# Uso: sudo bash install_ubuntu.sh
# Testado em: Ubuntu 22.04 LTS / 24.04 LTS / Debian 12

set -Eeuo pipefail

# ─── Cores ────────────────────────────────────────────────────────────────────
NC=$'\e[0m'; BLU=$'\e[34m'; GRN=$'\e[32m'; YLW=$'\e[33m'; RED=$'\e[31m'; BLD=$'\e[1m'
log()  { echo -e "${BLU}[provemaps]${NC} $*"; }
ok()   { echo -e "${GRN}[ok]${NC} $*"; }
warn() { echo -e "${YLW}[aviso]${NC} $*"; }
err()  { echo -e "${RED}[erro]${NC} $*" >&2; exit 1; }
sep()  { echo -e "\n${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ─── Verificações iniciais ────────────────────────────────────────────────────
[[ "$EUID" -ne 0 ]] && err "Execute como root: sudo bash $0"
[[ "$(uname -s)" != "Linux" ]] && err "Este script é para Linux/Ubuntu."

# ─── Configuração ─────────────────────────────────────────────────────────────
REPO_URL="https://github.com/kaled182/provemaps_beta.git"
INSTALL_DIR="${INSTALL_DIR:-/opt/provemaps}"
REAL_USER="${SUDO_USER:-root}"

sep
echo -e "${BLD}  ProVeMaps — Instalação automática${NC}"
sep
echo ""
log "Diretório de instalação: ${INSTALL_DIR}"
log "Usuário do sistema:       ${REAL_USER}"
echo ""
read -r -p "Continuar? [S/n] " CONFIRM
[[ "${CONFIRM,,}" == "n" ]] && exit 0

# ─── 1. Instalar dependências de sistema ──────────────────────────────────────
sep
log "PASSO 1/5 — Instalando dependências (git, curl)..."

apt-get update -qq
apt-get install -y -qq git curl ca-certificates gnupg
ok "Dependências instaladas."

# ─── 2. Instalar Docker ───────────────────────────────────────────────────────
sep
log "PASSO 2/5 — Instalando Docker..."

if command -v docker &>/dev/null && docker compose version &>/dev/null; then
    ok "Docker já instalado: $(docker --version)"
else
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "${VERSION_CODENAME:-$(lsb_release -cs)}") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    ok "Docker instalado: $(docker --version)"
fi

systemctl enable docker --quiet
systemctl start docker
ok "Serviço Docker ativo."

if [[ "${REAL_USER}" != "root" ]]; then
    usermod -aG docker "${REAL_USER}" 2>/dev/null || true
    log "Usuário '${REAL_USER}' adicionado ao grupo docker (efetivo após relogin)."
fi

# ─── 3. Instalar Node.js 20 ───────────────────────────────────────────────────
sep
log "PASSO 3/5 — Instalando Node.js 20 LTS..."

if command -v node &>/dev/null && node --version | grep -q "^v20"; then
    ok "Node.js já instalado: $(node --version)"
else
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs
    ok "Node.js instalado: $(node --version)"
fi

# ─── 4. Clonar / atualizar repositório ───────────────────────────────────────
sep
log "PASSO 4/5 — Repositório..."

if [[ -d "${INSTALL_DIR}/.git" ]]; then
    log "Repositório já existe — atualizando..."
    git -C "${INSTALL_DIR}" fetch origin
    git -C "${INSTALL_DIR}" reset --hard origin/main
    ok "Código atualizado."
else
    mkdir -p "${INSTALL_DIR}"
    git clone "${REPO_URL}" "${INSTALL_DIR}"
    ok "Repositório clonado em ${INSTALL_DIR}"
fi

# Ajustar dono dos arquivos
[[ "${REAL_USER}" != "root" ]] && chown -R "${REAL_USER}:${REAL_USER}" "${INSTALL_DIR}"

# ─── 4b. Permissões e diretórios de dados ─────────────────────────────────────
sep
log "Configurando permissões e diretórios..."

chmod +x "${INSTALL_DIR}/docker/docker-entrypoint.sh"
find "${INSTALL_DIR}/scripts" -name "*.sh" -exec chmod +x {} \;

# Diretórios bind-mounted que precisam ter permissão de escrita pelo container
mkdir -p \
    "${INSTALL_DIR}/backend/staticfiles" \
    "${INSTALL_DIR}/backend/media" \
    "${INSTALL_DIR}/database" \
    "${INSTALL_DIR}/logs"

chmod -R 777 \
    "${INSTALL_DIR}/backend/media" \
    "${INSTALL_DIR}/database" \
    "${INSTALL_DIR}/logs"

chmod -R 777 "${INSTALL_DIR}/backend/staticfiles"

ok "Permissões configuradas."

# ─── 5. Build do frontend Vue 3 ──────────────────────────────────────────────
sep
log "PASSO 5/5 — Compilando frontend Vue 3..."

FRONTEND_DIR="${INSTALL_DIR}/frontend"
cd "${FRONTEND_DIR}"

if [[ "${REAL_USER}" != "root" ]]; then
    sudo -u "${REAL_USER}" npm install --prefer-offline --silent 2>/dev/null \
        || sudo -u "${REAL_USER}" npm install --silent
    sudo -u "${REAL_USER}" npm run build
else
    npm install --silent
    npm run build
fi

ok "Frontend compilado."

# ─── 6. Criar .env mínimo (se não existe) ────────────────────────────────────
sep
log "Arquivo .env..."

ENV_FILE="${INSTALL_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
    ok ".env já existe — mantendo configurações existentes."
else
    touch "${ENV_FILE}"
    [[ "${REAL_USER}" != "root" ]] && chown "${REAL_USER}:${REAL_USER}" "${ENV_FILE}"
    ok ".env criado (vazio). Configurações feitas pelo painel web após instalação."
fi

# ─── 7. Subir Docker Compose ─────────────────────────────────────────────────
sep
log "Iniciando serviços com Docker Compose..."

COMPOSE_FILE="${INSTALL_DIR}/docker/docker-compose.yml"

# Parar instalação anterior se existir
if docker compose -f "${COMPOSE_FILE}" ps -q 2>/dev/null | grep -q .; then
    log "Parando serviços anteriores..."
    docker compose -f "${COMPOSE_FILE}" down --remove-orphans 2>/dev/null || true
fi

docker compose -f "${COMPOSE_FILE}" up -d
ok "Serviços iniciados."

# ─── Aguardar aplicação ───────────────────────────────────────────────────────
sep
log "Aguardando aplicação iniciar (até 90 segundos)..."

READY=false
for i in $(seq 1 90); do
    if curl -sf "http://localhost:8100/healthz" > /dev/null 2>&1; then
        ok "Aplicação pronta após ${i}s!"
        READY=true
        break
    fi
    printf "."
    sleep 1
done
echo ""

if [[ "$READY" == false ]]; then
    warn "Timeout aguardando /healthz."
    warn "Verifique com: docker compose -f ${COMPOSE_FILE} logs -f web"
fi

# ─── Resumo final ────────────────────────────────────────────────────────────
sep
SERVER_IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GRN}${BLD}  Instalação concluída!${NC}"
echo ""
echo -e "  Acesso:       ${BLD}http://${SERVER_IP}:8100${NC}"
echo -e "  Configuração: ${BLD}http://${SERVER_IP}:8100/setup_app/first_time/${NC}"
echo ""
echo -e "  Comandos úteis:"
echo -e "    docker compose -f ${COMPOSE_FILE} ps"
echo -e "    docker compose -f ${COMPOSE_FILE} logs -f web"
echo -e "    docker compose -f ${COMPOSE_FILE} down"
echo ""
if [[ "${REAL_USER}" != "root" ]]; then
    warn "Faça logout e login novamente para usar Docker sem sudo."
fi
sep
