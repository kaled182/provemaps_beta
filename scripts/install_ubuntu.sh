#!/usr/bin/env bash
# install_ubuntu.sh — Instalação automática do ProVeMaps no Ubuntu
# Uso: sudo bash install_ubuntu.sh
# Testado em: Ubuntu 22.04 LTS / 24.04 LTS

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
REAL_USER="${SUDO_USER:-$USER}"

sep
echo -e "${BLD}  ProVeMaps — Instalação automática${NC}"
sep
echo ""
log "Diretório de instalação: ${INSTALL_DIR}"
log "Usuário do sistema:       ${REAL_USER}"
echo ""
read -r -p "Continuar? [S/n] " CONFIRM
[[ "${CONFIRM,,}" == "n" ]] && exit 0

# ─── 1. Instalar Docker ───────────────────────────────────────────────────────
sep
log "PASSO 1/5 — Instalando Docker..."

if command -v docker &>/dev/null; then
    ok "Docker já instalado: $(docker --version)"
else
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg

    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

    ok "Docker instalado: $(docker --version)"
fi

# Garantir que o serviço está rodando
systemctl enable docker --quiet
systemctl start docker
ok "Serviço Docker ativo."

# Adicionar usuário real ao grupo docker
if [[ "${REAL_USER}" != "root" ]]; then
    usermod -aG docker "${REAL_USER}" 2>/dev/null || true
    log "Usuário '${REAL_USER}' adicionado ao grupo docker."
fi

# ─── 2. Instalar Node.js ──────────────────────────────────────────────────────
sep
log "PASSO 2/5 — Instalando Node.js 20 LTS..."

if command -v node &>/dev/null && [[ "$(node --version)" == v20* ]]; then
    ok "Node.js já instalado: $(node --version)"
else
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
    apt-get install -y -qq nodejs
    ok "Node.js instalado: $(node --version)"
fi

# ─── 3. Clonar repositório ───────────────────────────────────────────────────
sep
log "PASSO 3/5 — Clonando repositório..."

if [[ -d "${INSTALL_DIR}/.git" ]]; then
    ok "Repositório já existe em ${INSTALL_DIR}. Atualizando..."
    git -C "${INSTALL_DIR}" pull
else
    mkdir -p "${INSTALL_DIR}"
    git clone "${REPO_URL}" "${INSTALL_DIR}"
    chown -R "${REAL_USER}:${REAL_USER}" "${INSTALL_DIR}"
    ok "Repositório clonado em ${INSTALL_DIR}"
fi

# ─── 4. Criar arquivo .env ───────────────────────────────────────────────────
sep
log "PASSO 4/5 — Configurando variáveis de ambiente..."

ENV_FILE="${INSTALL_DIR}/.env"
ENV_EXAMPLE="${INSTALL_DIR}/.env.example"

if [[ -f "${ENV_FILE}" ]]; then
    ok ".env já existe — mantendo configurações existentes."
else
    cp "${ENV_EXAMPLE}" "${ENV_FILE}"
    chown "${REAL_USER}:${REAL_USER}" "${ENV_FILE}"
    ok ".env criado a partir do .env.example"

    warn "IMPORTANTE: Edite ${ENV_FILE} com suas configurações antes de usar em produção."
    warn "Variáveis principais:"
    warn "  SECRET_KEY      — gere com: python3 -c \"import secrets; print(secrets.token_urlsafe(60))\""
    warn "  FERNET_KEY      — gere com: python3 -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
    warn "  ZABBIX_API_URL  — URL da sua instância Zabbix"
    warn "  GOOGLE_MAPS_API_KEY — chave do Google Maps"
    echo ""
    read -r -p "Deseja editar o .env agora? [s/N] " EDIT_ENV
    if [[ "${EDIT_ENV,,}" == "s" ]]; then
        EDITOR="${EDITOR:-nano}"
        "${EDITOR}" "${ENV_FILE}"
    fi
fi

# ─── 5. Build do frontend ────────────────────────────────────────────────────
sep
log "PASSO 5/5 — Compilando frontend Vue 3..."

FRONTEND_DIR="${INSTALL_DIR}/frontend"

cd "${FRONTEND_DIR}"
sudo -u "${REAL_USER}" npm install --silent
sudo -u "${REAL_USER}" npm run build
ok "Frontend compilado."

# ─── 6. Subir Docker Compose ─────────────────────────────────────────────────
sep
log "PASSO 6/6 — Iniciando serviços com Docker Compose..."

cd "${INSTALL_DIR}/docker"
docker compose up -d

ok "Serviços iniciados."

# ─── Aguardar aplicação ficar pronta ─────────────────────────────────────────
sep
log "Aguardando aplicação iniciar (pode levar até 60 segundos)..."

for i in $(seq 1 60); do
    if curl -sf http://localhost:8100/healthz > /dev/null 2>&1; then
        ok "Aplicação pronta após ${i}s!"
        break
    fi
    sleep 1
    if [[ $i -eq 60 ]]; then
        warn "Timeout aguardando /healthz. Verifique com: docker compose logs -f web"
    fi
done

# ─── Resumo final ────────────────────────────────────────────────────────────
sep
echo ""
echo -e "${GRN}${BLD}  Instalação concluída!${NC}"
echo ""
echo -e "  Acesso:       ${BLD}http://$(hostname -I | awk '{print $1}'):8100${NC}"
echo -e "  Admin:        ${BLD}http://$(hostname -I | awk '{print $1}'):8100/admin${NC}"
echo -e "  Usuário:      admin"
echo -e "  Senha padrão: admin123  ${YLW}← Troque imediatamente!${NC}"
echo ""
echo -e "  Configuração: ${BLD}http://$(hostname -I | awk '{print $1}'):8100/setup_app/${NC}"
echo ""
echo -e "  Comandos úteis:"
echo -e "    cd ${INSTALL_DIR}/docker"
echo -e "    docker compose ps          # status dos serviços"
echo -e "    docker compose logs -f web # logs da aplicação"
echo -e "    docker compose down        # parar tudo"
echo ""
if [[ "${REAL_USER}" != "root" ]]; then
    warn "Faça logout e login novamente para usar Docker sem sudo."
fi
sep
