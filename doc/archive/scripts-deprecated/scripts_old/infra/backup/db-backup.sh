#!/bin/bash

# ======================================
# 🗄️  BACKUP AUTOMATIZADO - MAPSPROVE DB
# ======================================
# Versão 2.0 - Março 2025
# ======================================

set -euo pipefail
IFS=$'\n\t'

# Cores para mensagens
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configurações
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
BACKUP_DIR="${BASE_DIR}/database/backups"
LOG_DIR="${BASE_DIR}/logs/backups"
LOG_FILE="${LOG_DIR}/backup_$(date +%Y%m%d_%H%M%S).log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7
COMPRESS=true
ENCRYPT=false

# Nome do arquivo de backup
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
if [ "$COMPRESS" = true ]; then
  BACKUP_FILE="${BACKUP_FILE}.gz"
fi
if [ "$ENCRYPT" = true ]; then
  BACKUP_FILE="${BACKUP_FILE}.gpg"
fi

# Carregar variáveis de ambiente
ENV_FILE="${BASE_DIR}/.env"
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

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
    "DEBUG") color="${CYAN}" ;;
    *) color="${NC}" ;;
  esac
  
  echo -e "${color}[${timestamp}] ${level}: ${message}${NC}"
  echo "[${timestamp}] ${level}: ${message}" >> "$LOG_FILE"
}

# Verificar comandos necessários
check_command() {
  if ! command -v "$1" &> /dev/null; then
    log "ERROR" "❌ Comando '$1' não encontrado. Instale antes de continuar."
    exit 1
  fi
}

# Verificar pré-requisitos
check_prerequisites() {
  log "INFO" "🔍 Verificando pré-requisitos..."
  
  check_command "pg_dump"
  check_command "psql"
  
  if [ "$COMPRESS" = true ]; then
    check_command "gzip"
  fi
  
  if [ "$ENCRYPT" = true ]; then
    check_command "gpg"
  fi
  
  if [ -n "${CLOUD_STORAGE:-}" ]; then
    check_command "aws"
  fi

  mkdir -p "$BACKUP_DIR"
  mkdir -p "$LOG_DIR"

  log "SUCCESS" "✅ Pré-requisitos atendidos"
}

# Validar conexão com o banco
validate_db_connection() {
  log "INFO" "🔌 Testando conexão com o banco..."
  
  if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USERNAME" -d "$DB_DATABASE" -c "\q"; then
    log "ERROR" "❌ Falha na conexão com o banco de dados"
    exit 1
  fi
  
  log "SUCCESS" "✅ Conexão com o banco validada"
}

# Verificar espaço em disco
check_disk_space() {
  log "INFO" "💾 Verificando espaço em disco..."
  
  local required_space=$(($(psql -h "$DB_HOST" -U "$DB_USERNAME" -d "$DB_DATABASE" -c "SELECT pg_database_size('$DB_DATABASE');" | grep -o '[0-9]*') / 1024))
  local available_space=$(df -k "$BACKUP_DIR" | awk 'NR==2 {print $4}')
  
  if [ "$required_space" -gt "$available_space" ]; then
    log "ERROR" "❌ Espaço insuficiente para backup (Necessário: ${required_space}KB, Disponível: ${available_space}KB)"
    exit 1
  fi
  
  log "INFO" "🆓 Espaço disponível: $((available_space / 1024))MB"
}

# Executar backup
perform_backup() {
  log "INFO" "📀 Iniciando backup do banco de dados..."
  local start_time=$(date +%s)
  
  local backup_command="PGPASSWORD=\"$DB_PASSWORD\" pg_dump -h \"$DB_HOST\" -U \"$DB_USERNAME\" -d \"$DB_DATABASE\" --exclude-table-data='*.logs*' --exclude-table-data='*.audit*' --create"
  
  local pipeline="$backup_command"
  
  if [ "$COMPRESS" = true ]; then
    pipeline="$pipeline | gzip"
  fi
  
  if [ "$ENCRYPT" = true ]; then
    pipeline="$pipeline | gpg --encrypt --recipient \"${GPG_RECIPIENT:-backup@mapsprove.com}\""
  fi
  
  eval "$pipeline > \"$BACKUP_FILE\""
  
  local end_time=$(date +%s)
  local duration=$((end_time - start_time))
  local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
  
  log "SUCCESS" "✅ Backup concluído com sucesso!"
  log "INFO" "⏱️  Duração: ${duration} segundos"
  log "INFO" "📦 Tamanho: ${backup_size}"
  log "INFO" "🗄️  Arquivo: ${BACKUP_FILE}"
}

# Verificar integridade do backup
verify_backup() {
  log "INFO" "🔍 Verificando integridade do backup..."
  
  if [ "$COMPRESS" = true ]; then
    if ! gzip -t "$BACKUP_FILE"; then
      log "ERROR" "❌ Backup corrompido (falha na verificação gzip)"
      exit 1
    fi
  fi
  
  log "SUCCESS" "✅ Integridade do backup verificada"
}

# Rotacionar backups antigos
rotate_backups() {
  log "INFO" "🔄 Rotacionando backups (retenção: ${RETENTION_DAYS} dias)..."
  
  find "$BACKUP_DIR" -name "backup_*" -type f -mtime +$RETENTION_DAYS | while read -r file; do
    log "INFO" "🧹 Removendo backup antigo: $(basename "$file")"
    rm -f "$file"
  done
  
  log "SUCCESS" "✅ Rotação concluída"
}

# Upload para cloud storage
upload_to_cloud() {
  if [ -z "${CLOUD_STORAGE:-}" ]; then
    log "INFO" "☁️ Cloud storage não configurado. Pulando upload."
    return
  fi
  
  log "INFO" "☁️ Enviando backup para cloud storage..."
  
  if aws s3 cp "$BACKUP_FILE" "$CLOUD_STORAGE/$(basename "$BACKUP_FILE")"; then
    log "SUCCESS" "✅ Upload para cloud concluído"
  else
    log "WARNING" "⚠️  Falha no upload para cloud"
  fi
}

# Enviar notificação
send_notification() {
  local status=$1
  local message="Backup ${status}: $(basename "$BACKUP_FILE")"
  
  if [ -n "${SLACK_WEBHOOK:-}" ]; then
    curl -s -X POST -H 'Content-type: application/json'       --data "{\"text\":\"$message\"}"       "$SLACK_WEBHOOK" > /dev/null &&     log "DEBUG" "Notificação enviada para Slack"
  fi
  
  if [ -n "${EMAIL_TO:-}" ] && command -v mailx &> /dev/null; then
    echo "$message" | mailx -s "[MapsProve] Backup ${status}" "$EMAIL_TO"
    log "DEBUG" "Email enviado para $EMAIL_TO"
  fi
}

# Função principal
main() {
  log "INFO" "🚀 Iniciando processo de backup - $(date)"
  log "INFO" "📂 Diretório base: ${BASE_DIR}"
  
  check_prerequisites
  check_disk_space
  validate_db_connection
  perform_backup
  verify_backup
  rotate_backups
  upload_to_cloud
  
  log "SUCCESS" "🎉 Backup finalizado com sucesso!"
  log "INFO" "📋 Log completo: ${LOG_FILE}"
  
  echo -e "\n${GREEN}=== RESUMO DO BACKUP ===${NC}"
  echo -e "${BLUE}➤ Banco:${NC} ${DB_DATABASE}"
  echo -e "${BLUE}➤ Host:${NC} ${DB_HOST}"
  echo -e "${BLUE}➤ Arquivo:${NC} $(basename "$BACKUP_FILE")"
  echo -e "${BLUE}➤ Tamanho:${NC} $(du -h "$BACKUP_FILE" | cut -f1)"
  echo -e "${BLUE}➤ Checksum:${NC} $(sha256sum "$BACKUP_FILE" | cut -d' ' -f1)"
  echo -e "${BLUE}➤ Logs:${NC} ${LOG_FILE}"
  
  send_notification "SUCESSO"
}

trap 'send_notification "FALHA"; exit 1' ERR

main "$@"
