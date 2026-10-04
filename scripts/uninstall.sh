#!/usr/bin/env bash
# uninstall.sh — Remove COMPLETO do ProVeMaps do servidor
# Uso: sudo bash uninstall.sh
# AVISO: Apaga todos os dados, volumes Docker e o diretório de instalação.

set -Eeuo pipefail

NC=$'\e[0m'; RED=$'\e[31m'; YLW=$'\e[33m'; GRN=$'\e[32m'; BLD=$'\e[1m'
log()  { echo -e "${YLW}[uninstall]${NC} $*"; }
ok()   { echo -e "${GRN}[ok]${NC} $*"; }
err()  { echo -e "${RED}[erro]${NC} $*" >&2; exit 1; }
sep()  { echo -e "\n${BLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }

[[ "$EUID" -ne 0 ]] && err "Execute como root: sudo bash $0"

INSTALL_DIR="${INSTALL_DIR:-/opt/provemaps}"

sep
echo -e "${RED}${BLD}  ATENÇÃO: Isso irá apagar TUDO — dados, banco, volumes.${NC}"
sep
echo ""
echo -e "  Diretório: ${BLD}${INSTALL_DIR}${NC}"
echo ""
read -r -p "Tem certeza? Digite 'sim' para confirmar: " CONFIRM
[[ "${CONFIRM}" != "sim" ]] && { echo "Cancelado."; exit 0; }

sep
log "Parando e removendo containers Docker..."

COMPOSE_FILE="${INSTALL_DIR}/docker/docker-compose.yml"

if [[ -f "${COMPOSE_FILE}" ]]; then
    docker compose -f "${COMPOSE_FILE}" down --volumes --remove-orphans 2>/dev/null || true
    ok "Containers e volumes removidos."
else
    log "docker-compose.yml não encontrado — tentando parar containers pelo nome..."
    docker ps -q --filter "name=docker-" | xargs -r docker stop 2>/dev/null || true
    docker ps -aq --filter "name=docker-" | xargs -r docker rm -v 2>/dev/null || true
fi

sep
log "Removendo imagens Docker do projeto..."
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' \
    | grep -E "docker-web|docker-celery|docker-beat|docker-nginx|provemaps" \
    | awk '{print $2}' \
    | xargs -r docker rmi -f 2>/dev/null || true
ok "Imagens removidas (se existiam)."

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
echo -e "  Para reinstalar:"
echo -e "    sudo bash install_ubuntu.sh"
echo ""
