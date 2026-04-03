#!/bin/bash

# ======================================
# 🚀 DEPLOY AUTOMATIZADO PARA O MAPSPROVE
# ======================================
# Versão 2.1 - Março 2025
# ======================================

set -euo pipefail
IFS=$'\n\t'

# Cores para mensagens
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações de diretório
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${BASE_DIR}/logs/deploy"
LOG_FILE="${LOG_DIR}/deploy_$(date +%Y%m%d_%H%M%S).log"
ENV_FILE="${BASE_DIR}/.env"
COMPOSE_FILE="docker-compose.yml"

# Função de log melhorada
log() {
  local level=$1
  local message=$2
  local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
  
  case $level in
    "INFO") color="${BLUE}" ;;
    "SUCCESS") color="${GREEN}" ;;
    "WARNING") color="${YELLOW}" ;;
    "ERROR") color="${RED}" ;;
    *) color="${NC}" ;;
  esac
  
  echo -e "${color}[${timestamp}] ${level}: ${message}${NC}"
  echo "[${timestamp}] ${level}: ${message}" >> "$LOG_FILE"
}

# Tratamento de erros
handle_error() {
  local step=$1
  log "ERROR" "❌ Falha crítica no passo: $step"
  log "ERROR" "🔍 Consulte os logs em: $LOG_FILE"
  exit 1
}

# Verificação de pré-requisitos
check_prerequisites() {
  log "INFO" "🔍 Verificando pré-requisitos..."
  
  declare -a commands=("docker" "docker-compose" "git")
  for cmd in "${commands[@]}"; do
    if ! command -v "$cmd" &> /dev/null; then
      log "ERROR" "$cmd não está instalado"
      exit 1
    fi
  done
  
  if [ ! -f "$ENV_FILE" ]; then
    log "ERROR" "Arquivo .env não encontrado em ${ENV_FILE}"
    exit 1
  fi
  
  log "SUCCESS" "✅ Todos os pré-requisitos atendidos"
}

# Carregar e validar variáveis de ambiente
load_env() {
  log "INFO" "📦 Carregando variáveis de ambiente..."
  
  export $(grep -v '^#' "$ENV_FILE" | xargs)
  
  declare -a required_vars=("NODE_ENV" "DB_HOST")
  for var in "${required_vars[@]}"; do
    if [ -z "${!var:-}" ]; then
      log "ERROR" "Variável $var não está definida"
      exit 1
    fi
  done
  
  log "SUCCESS" "✅ Variáveis de ambiente carregadas"
}

# Validação do ambiente
validate_environment() {
  log "INFO" "🔧 Validando ambiente..."
  
  if [[ "$NODE_ENV" == "production" && "$COMPOSE_FILE" == *".dev.yml" ]]; then
    log "WARNING" "⚠️  AVISO: Usando compose de desenvolvimento em produção!"
    read -p "Continuar? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      exit 1
    fi
  fi
}

# Construção de containers
build_containers() {
  log "INFO" "🏗️  Construindo containers Docker..."
  docker-compose -f "$COMPOSE_FILE" build --no-cache || handle_error "build_containers"
  log "SUCCESS" "✅ Containers construídos com sucesso"
}

# Inicialização de serviços
start_services() {
  log "INFO" "🔄 Iniciando serviços..."
  docker-compose -f "$COMPOSE_FILE" up -d || handle_error "start_services"
  log "SUCCESS" "✅ Serviços iniciados com sucesso"
}

# Execução de migrações
run_migrations() {
  log "INFO" "🛠️  Executando migrações de banco de dados..."
  docker-compose -f "$COMPOSE_FILE" exec backend npm run migrate || handle_error "run_migrations"
  log "SUCCESS" "✅ Migrações executadas com sucesso"
}

# Health check
health_check() {
  log "INFO" "🏥 Realizando health check..."
  if ! docker-compose -f "$COMPOSE_FILE" ps | grep backend | grep -q "Up"; then
    log "ERROR" "❌ O container principal não está rodando"
    exit 1
  fi
  log "SUCCESS" "✅ Health check passou com sucesso"
}

# Limpeza de recursos
cleanup() {
  log "INFO" "🧹 Limpando recursos antigos..."
  docker-compose -f "$COMPOSE_FILE" down --remove-orphans || true
  docker system prune -f || true
  log "SUCCESS" "✅ Limpeza concluída"
}

# Rollback automático
perform_rollback() {
  log "WARNING" "⏮️  Iniciando rollback..."
  docker-compose -f "$COMPOSE_FILE" down
  git checkout -- .
  docker-compose -f "$COMPOSE_FILE" up -d
  log "SUCCESS" "✅ Rollback concluído"
}

# Fluxo principal
main() {
  local DEPLOY_START=$(date +%s)
  mkdir -p "$LOG_DIR"
  
  # Tratamento de argumentos
  case "${1:-}" in
    --dev) 
      COMPOSE_FILE="docker-compose.dev.yml"
      log "INFO" "Modo desenvolvimento ativado"
      ;;
    --logs)
      docker-compose -f "$COMPOSE_FILE" logs -f --tail=100
      exit 0
      ;;
    --rollback)
      perform_rollback
      exit 0
      ;;
    *)
      COMPOSE_FILE="docker-compose.yml" 
      ;;
  esac

  log "INFO" "🚀 Iniciando processo de deploy do MapsProve"
  log "INFO" "📂 Diretório base: ${BASE_DIR}"
  log "INFO" "📝 Arquivo compose: ${COMPOSE_FILE}"

  check_prerequisites
  load_env
  validate_environment
  cleanup
  
  build_containers
  start_services
  run_migrations
  health_check

  local DEPLOY_END=$(date +%s)
  local DEPLOY_TIME=$((DEPLOY_END - DEPLOY_START))

  log "SUCCESS" "🎉 Deploy concluído com sucesso em ${DEPLOY_TIME} segundos!"
  log "INFO" "📋 Log completo disponível em: ${LOG_FILE}"

  echo -e "\n${GREEN}=== RESUMO DO DEPLOY ===${NC}"
  echo -e "${BLUE}➤ Ambiente:${NC} ${NODE_ENV:-undefined}"
  echo -e "${BLUE}➤ Versão:${NC} $(git rev-parse --short HEAD)"
  echo -e "${BLUE}➤ Tempo:${NC} ${DEPLOY_TIME} segundos"
  echo -e "${BLUE}➤ Arquivo Compose:${NC} ${COMPOSE_FILE}"
  echo -e "${BLUE}➤ Logs:${NC} ${LOG_FILE}"
}

main "$@"
