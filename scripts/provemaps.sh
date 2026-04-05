#!/usr/bin/env bash
# provemaps.sh — Gerenciador de instalação do ProVeMaps
# Uso: sudo bash provemaps.sh
# Testado em: Ubuntu 22.04 LTS / 24.04 LTS / Debian 12

set -Eeuo pipefail

# ─── Configurações Gerais ─────────────────────────────────────────────────────
REPO_URL="https://github.com/kaled182/provemaps_beta.git"
INSTALL_DIR="${INSTALL_DIR:-/opt/provemaps}"
REAL_USER="${SUDO_USER:-root}"
LOG_FILE="/var/log/provemaps_install.log"

# ─── Cores e Funções Visuais ──────────────────────────────────────────────────
NC=$'\e[0m'; BLU=$'\e[34m'; GRN=$'\e[32m'; YLW=$'\e[33m'; RED=$'\e[31m'; BLD=$'\e[1m'
log()  { echo -e "${BLU}[provemaps]${NC} $*"; }
ok()   { echo -e "${GRN}[ok]${NC} $*"; }
warn() { echo -e "${YLW}[aviso]${NC} $*"; }
err()  { echo -e "${RED}[erro]${NC} $*\n${YLW}[!] Detalhes no log: ${LOG_FILE}${NC}" >&2; exit 1; }
sep()  { echo -e "\n${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

# ─── Barra de Progresso ───────────────────────────────────────────────────────
TOTAL_STEPS=9
CURRENT_STEP=0

show_step() {
    local msg="$1"
    CURRENT_STEP=$((CURRENT_STEP + 1))
    local percent=$((CURRENT_STEP * 100 / TOTAL_STEPS))
    local completed=$((percent * 40 / 100))
    local remaining=$((40 - completed))
    local bar_color="${BLU}"
    [[ $percent -eq 100 ]] && bar_color="${GRN}"
    local bar=""
    for ((i=0; i<completed; i++)); do bar+="█"; done
    for ((i=0; i<remaining; i++)); do bar+="░"; done
    echo -e "\n${BLD}Progresso: ${bar_color}[${bar}] ${percent}%${NC}"
    echo -e "${BLU}➔ ${msg}${NC}"
}

# ─── Spinner ──────────────────────────────────────────────────────────────────
spinner() {
    local pid=$1
    local label="${2:-Processando...}"
    local delay=0.1
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    tput civis 2>/dev/null || true
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " ${BLU}%c${NC} %s" "$spinstr" "$label"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\r\033[K"
    done
    tput cnorm 2>/dev/null || true
    wait "$pid"
    return $?
}

# ─── Verificações iniciais ────────────────────────────────────────────────────
[[ "$EUID" -ne 0 ]] && { echo -e "${RED}[erro]${NC} Execute como root: sudo bash $0" >&2; exit 1; }
[[ "$(uname -s)" != "Linux" ]] && { echo -e "${RED}[erro]${NC} Este script é para Linux/Ubuntu." >&2; exit 1; }

# ══════════════════════════════════════════════════════════════════════════════
#  MENU PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
show_menu() {
    clear
    sep
    echo -e "${BLD}  ProVeMaps — Gerenciador de Instalação${NC}"
    sep
    echo ""
    echo -e "  Diretório: ${BLD}${INSTALL_DIR}${NC}"
    echo -e "  Usuário:   ${BLD}${REAL_USER}${NC}"
    echo ""
    echo -e "  ${BLD}1)${NC} Instalar / Atualizar"
    echo -e "  ${BLD}2)${NC} Desinstalar (apaga tudo)"
    echo -e "  ${BLD}3)${NC} Reinstalar do zero  ${YLW}(desinstala + instala)${NC}"
    echo -e "  ${BLD}0)${NC} Sair"
    echo ""
    read -r -p "  Escolha uma opção: " OPTION
}

# ══════════════════════════════════════════════════════════════════════════════
#  FUNÇÃO: DESINSTALAR
# ══════════════════════════════════════════════════════════════════════════════
run_uninstall() {
    sep
    echo -e "${RED}${BLD}  ATENÇÃO: Isso irá apagar TUDO — dados, banco e volumes Docker.${NC}"
    sep
    echo ""
    echo -e "  Diretório: ${BLD}${INSTALL_DIR}${NC}"
    echo ""
    read -r -p "  Tem certeza? Digite 'sim' para confirmar: " CONFIRM
    [[ "${CONFIRM}" != "sim" ]] && { echo "  Cancelado."; return 0; }

    COMPOSE_FILE="${INSTALL_DIR}/docker/docker-compose.yml"

    sep
    log "Parando e removendo containers e volumes..."
    if [[ -f "${COMPOSE_FILE}" ]]; then
        docker compose -f "${COMPOSE_FILE}" down --volumes --remove-orphans 2>/dev/null || true
    else
        log "docker-compose.yml não encontrado — parando containers pelo nome..."
        docker ps -q --filter "name=docker-" | xargs -r docker stop 2>/dev/null || true
        docker ps -aq --filter "name=docker-" | xargs -r docker rm -v 2>/dev/null || true
    fi
    ok "Containers e volumes removidos."

    sep
    log "Removendo imagens Docker do projeto..."
    docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' \
        | grep -E "docker-web|docker-celery|docker-beat|docker-nginx|provemaps" \
        | awk '{print $2}' \
        | xargs -r docker rmi -f 2>/dev/null || true
    ok "Imagens removidas."

    sep
    log "Limpando cache Docker não utilizado..."
    docker system prune -f 2>/dev/null || true
    ok "Cache Docker limpo."

    sep
    log "Removendo diretório de instalação: ${INSTALL_DIR}..."
    rm -rf "${INSTALL_DIR}"
    ok "Diretório removido."

    sep
    echo ""
    echo -e "${GRN}${BLD}  Remoção concluída. Servidor limpo.${NC}"
    echo ""
}

# ══════════════════════════════════════════════════════════════════════════════
#  FUNÇÃO: INSTALAR
# ══════════════════════════════════════════════════════════════════════════════
run_install() {
    # Reinicia contadores (importante para opção "reinstalar")
    CURRENT_STEP=0

    > "$LOG_FILE"
    [[ "${REAL_USER}" != "root" ]] && chown "${REAL_USER}:${REAL_USER}" "$LOG_FILE" 2>/dev/null || true

    sep
    echo -e "${BLD}  ProVeMaps — Instalação${NC}"
    echo -e "  Diretório: ${BLD}${INSTALL_DIR}${NC}   Log: ${BLD}${LOG_FILE}${NC}"
    sep

    # ── 1. Dependências ───────────────────────────────────────────────────────
    show_step "Instalando dependências do sistema (git, curl)..."
    (
        apt-get update -y
        apt-get install -y git curl ca-certificates gnupg
    ) >> "$LOG_FILE" 2>&1 &
    spinner $! "Instalando dependências..." || err "Falha ao instalar dependências."
    ok "Dependências instaladas."

    # ── 2. Docker ─────────────────────────────────────────────────────────────
    show_step "Instalando Docker..."
    if command -v docker &>/dev/null && docker compose version &>/dev/null; then
        ok "Docker já instalado: $(docker --version)"
    else
        (
            install -m 0755 -d /etc/apt/keyrings
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
                | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes
            chmod a+r /etc/apt/keyrings/docker.gpg
            echo \
                "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
                https://download.docker.com/linux/ubuntu \
                $(. /etc/os-release && echo "${VERSION_CODENAME:-$(lsb_release -cs)}") stable" \
                | tee /etc/apt/sources.list.d/docker.list > /dev/null
            apt-get update -y
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
        ) >> "$LOG_FILE" 2>&1 &
        spinner $! "Instalando Docker..." || err "Falha ao instalar o Docker."
        ok "Docker instalado: $(docker --version)"
    fi
    systemctl enable docker --quiet
    systemctl start docker
    ok "Serviço Docker ativo."
    if [[ "${REAL_USER}" != "root" ]]; then
        usermod -aG docker "${REAL_USER}" 2>/dev/null || true
        log "Usuário '${REAL_USER}' adicionado ao grupo docker."
    fi

    # ── 3. Node.js ────────────────────────────────────────────────────────────
    show_step "Instalando Node.js 20 LTS..."
    if command -v node &>/dev/null && node --version | grep -q "^v20"; then
        ok "Node.js já instalado: $(node --version)"
    else
        (
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
            apt-get install -y nodejs
        ) >> "$LOG_FILE" 2>&1 &
        spinner $! "Instalando Node.js..." || err "Falha ao instalar o Node.js."
        ok "Node.js instalado: $(node --version)"
    fi

    # ── 4. Repositório ────────────────────────────────────────────────────────
    show_step "Baixando/Atualizando repositório..."
    (
        if [[ -d "${INSTALL_DIR}/.git" ]]; then
            git -C "${INSTALL_DIR}" fetch origin
            git -C "${INSTALL_DIR}" reset --hard origin/main
        else
            mkdir -p "${INSTALL_DIR}"
            git clone "${REPO_URL}" "${INSTALL_DIR}"
        fi
    ) >> "$LOG_FILE" 2>&1 &
    spinner $! "Clonando repositório..." || err "Falha ao configurar o repositório Git."
    ok "Código fonte pronto em ${INSTALL_DIR}."
    if [[ "${REAL_USER}" != "root" ]]; then
        chown -R "${REAL_USER}:${REAL_USER}" "${INSTALL_DIR}" >> "$LOG_FILE" 2>&1 &
        spinner $! "Ajustando permissões..." || warn "Não foi possível ajustar o dono dos arquivos."
    fi

    # ── 5. Permissões ─────────────────────────────────────────────────────────
    show_step "Configurando permissões e diretórios de dados..."
    chmod +x "${INSTALL_DIR}/docker/docker-entrypoint.sh"
    find "${INSTALL_DIR}/scripts" -name "*.sh" -exec chmod +x {} \;
    mkdir -p \
        "${INSTALL_DIR}/backend/staticfiles" \
        "${INSTALL_DIR}/backend/media" \
        "${INSTALL_DIR}/database" \
        "${INSTALL_DIR}/logs"
    chmod -R 777 \
        "${INSTALL_DIR}/backend/staticfiles" \
        "${INSTALL_DIR}/backend/media" \
        "${INSTALL_DIR}/database" \
        "${INSTALL_DIR}/logs"
    ok "Permissões configuradas."

    # ── 6. Frontend ───────────────────────────────────────────────────────────
    show_step "Compilando frontend Vue 3 (pode demorar alguns minutos)..."
    (
        cd "${INSTALL_DIR}/frontend"
        if [[ "${REAL_USER}" != "root" ]]; then
            sudo -u "${REAL_USER}" npm install --prefer-offline 2>/dev/null \
                || sudo -u "${REAL_USER}" npm install
            sudo -u "${REAL_USER}" npm run build
        else
            npm install
            npm run build
        fi
    ) >> "$LOG_FILE" 2>&1 &
    spinner $! "Compilando Vue 3..." || err "Falha na compilação do Vue 3. Consulte: ${LOG_FILE}"
    ok "Frontend compilado com sucesso."

    # ── .env ──────────────────────────────────────────────────────────────────
    ENV_FILE="${INSTALL_DIR}/.env"
    if [[ ! -f "${ENV_FILE}" ]]; then
        touch "${ENV_FILE}"
        [[ "${REAL_USER}" != "root" ]] && chown "${REAL_USER}:${REAL_USER}" "${ENV_FILE}"
    fi

    # ── 7. Docker Compose ─────────────────────────────────────────────────────
    show_step "Iniciando containers do Docker Compose..."
    COMPOSE_FILE="${INSTALL_DIR}/docker/docker-compose.yml"
    (
        if docker compose -f "${COMPOSE_FILE}" ps -q 2>/dev/null | grep -q .; then
            docker compose -f "${COMPOSE_FILE}" down --remove-orphans
        fi
        docker compose -f "${COMPOSE_FILE}" up -d
    ) >> "$LOG_FILE" 2>&1 &
    spinner $! "Iniciando containers..." || err "Falha ao iniciar containers do Docker Compose."
    ok "Containers iniciados."

    # ── 8. Health check ───────────────────────────────────────────────────────
    show_step "Aguardando aplicação ficar online..."
    (
        for i in $(seq 1 90); do
            if curl -sf "http://localhost:8100/healthz" > /dev/null 2>&1; then
                exit 0
            fi
            sleep 1
        done
        exit 1
    ) &
    spinner $! "Verificando health check (até 90s)..."
    if [[ $? -eq 0 ]]; then
        ok "Aplicação online e respondendo!"
    else
        warn "Timeout ao aguardar /healthz."
        warn "Verifique com: docker compose -f ${COMPOSE_FILE} logs -f web"
    fi

    # ── 9. Finalização (100%) ─────────────────────────────────────────────────
    show_step "Finalizando instalação..."
    sleep 1
    ok "Tudo pronto!"

    # ── Resumo ────────────────────────────────────────────────────────────────
    sep
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo -e "${GRN}${BLD}  Instalação concluída com sucesso!${NC}"
    echo ""
    echo -e "  Acesso:       ${BLD}http://${SERVER_IP}:8100${NC}"
    echo -e "  Configuração: ${BLD}http://${SERVER_IP}:8100/setup_app/first_time/${NC}"
    echo ""
    echo -e "  Comandos úteis:"
    echo -e "    docker compose -f ${COMPOSE_FILE} ps"
    echo -e "    docker compose -f ${COMPOSE_FILE} logs -f web"
    echo -e "    tail -f ${LOG_FILE}  ${YLW}# log completo${NC}"
    echo ""
    if [[ "${REAL_USER}" != "root" ]]; then
        warn "Faça logout e login novamente para usar Docker sem sudo."
    fi
    sep
}

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
show_menu

case "${OPTION}" in
    1)
        run_install
        ;;
    2)
        run_uninstall
        ;;
    3)
        run_uninstall
        echo ""
        read -r -p "  Iniciar instalação agora? [S/n] " NEXT
        [[ "${NEXT,,}" != "n" ]] && run_install
        ;;
    0)
        echo "  Saindo."
        exit 0
        ;;
    *)
        echo -e "${RED}  Opção inválida.${NC}"
        exit 1
        ;;
esac
