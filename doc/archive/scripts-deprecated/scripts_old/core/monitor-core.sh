#!/usr/bin/env bash

# ===================================================
# 📦 MAPSPROVE MONITOR - MÓDULO UTILITÁRIO (v5.2)
# ===================================================
# Arquivo: monitor-utils.sh
# Última atualização: 25/04/2025
# 
# Histórico de versões:
# v5.0 - Versão inicial modularizada
# v5.1 - Adicionado suporte a Slack/Telegram
# v5.2 - Aprimoramentos de segurança e performance
#
# Descrição:
# Módulo central com funções compartilhadas para:
# - Configurações globais
# - Logging padronizado
# - Gerenciamento de arquivos
# - Verificação de pré-requisitos
# ===================================================

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 🎨 CONFIGURAÇÕES DE CORES (ANSI)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
RED='\033[0;31m'       # Erros e alertas críticos
GREEN='\033[0;32m'     # Sucesso e operações normais
YELLOW='\033[1;33m'    # Avisos e alertas médios
BLUE='\033[0;34m'      # Informações principais
MAGENTA='\033[0;35m'   # Debug e desenvolvimento
CYAN='\033[0;36m'      # Ações em andamento
NC='\033[0m'           # Reset de cor

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 📂 CONFIGURAÇÕES DE DIRETÓRIOS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="${BASE_DIR}/logs/monitor"
JSON_FILE="${LOG_DIR}/latest.json"
ALERT_LOG="${LOG_DIR}/alerts.log"

# Cria estrutura de diretórios com tratamento de erro
if ! mkdir -p "$LOG_DIR"; then
    echo -e "${RED}Falha crítica: Não foi possível criar diretório de logs${NC}" >&2
    exit 1
fi

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ⚙️ VARIÁVEIS CONFIGURÁVEIS (com valores padrão)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Limiares para alertas:
: "${CPU_WARNING:=80}"              # Uso de CPU para alerta amarelo
: "${CPU_CRITICAL:=90}"             # Uso de CPU para alerta vermelho
: "${MEM_WARNING:=85}"              # Uso de memória para alerta amarelo
: "${MEM_CRITICAL:=95}"             # Uso de memória para alerta vermelho
: "${DISK_WARNING:=80}"             # Uso de disco para alerta amarelo
: "${DISK_CRITICAL:=90}"            # Uso de disco para alerta vermelho
: "${TEMP_WARNING:=70}"             # Temperatura para alerta amarelo
: "${TEMP_CRITICAL:=85}"            # Temperatura para alerta vermelho

# Configurações gerais:
: "${LOG_RETENTION_DAYS:=7}"        # Dias para manter logs históricos
: "${ALERT_EMAIL:=}"                # E-mail para notificações (opcional)

# Processos críticos para monitorar:
: "${CRITICAL_PROCESSES:="nginx mysql postgres redis"}"

# Integrações com mensageria:
: "${SLACK_WEBHOOK_URL:=}"          # Webhook para alertas no Slack
: "${TELEGRAM_BOT_TOKEN:=}"         # Token do bot do Telegram
: "${TELEGRAM_CHAT_ID:=}"           # ID do chat no Telegram

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 📝 FUNÇÕES DE LOGGING
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# log_info "mensagem" - Para informações gerais
log_info() {
    echo -e "${CYAN}[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1${NC}"
}

# log_warn "mensagem" - Para alertas não críticos
log_warn() {
    echo -e "${YELLOW}[AVISO] $(date '+%Y-%m-%d %H:%M:%S') - $1${NC}"
}

# log_error "mensagem" - Para erros e problemas sérios
log_error() {
    echo -e "${RED}[ERRO] $(date '+%Y-%m-%d %H:%M:%S') - $1${NC}" >&2
}

# log_debug "mensagem" - Somente exibe se DEBUG=true
log_debug() {
    [ "${DEBUG:-false}" = "true" ] && \
    echo -e "${MAGENTA}[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $1${NC}"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 🔍 VERIFICAÇÕES DO SISTEMA
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Verifica comandos essenciais e dependências
check_prerequisites() {
    local missing=0
    local required_cmds=("top" "free" "df" "ping" "ip" "awk" "grep" "sed")
    
    for cmd in "${required_cmds[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            log_error "Dependência crítica não encontrada: $cmd"
            missing=1
        fi
    done

    # jq é opcional mas recomendado
    if ! command -v jq &>/dev/null; then
        log_warn "Dependência opcional 'jq' não encontrada - algumas funcionalidades estarão limitadas"
    fi

    return $missing
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 🗃️ GERENCIAMENTO DE ARQUIVOS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Limpa logs antigos conforme LOG_RETENTION_DAYS
clean_old_logs() {
    log_info "Iniciando limpeza de logs (retenção: $LOG_RETENTION_DAYS dias)"
    if ! find "$LOG_DIR" -name "monitor_*.log" -mtime +"$LOG_RETENTION_DAYS" -delete 2>/dev/null; then
        log_error "Falha ao limpar logs antigos"
        return 1
    fi
    log_info "Limpeza de logs concluída com sucesso"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 📊 MANIPULAÇÃO DE DADOS
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Classifica valores conforme limiares (ok/warning/critical)
# Uso: check_threshold <valor> <warning> <critical>
check_threshold() {
    local value=$1 warning=$2 critical=$3
    (( $(echo "$value >= $critical" | bc -l) )) && echo "critical" && return
    (( $(echo "$value >= $warning" | bc -l) )) && echo "warning" || echo "ok"
}

# Extrai valores de JSON mesmo sem jq instalado
# Uso: safe_json_get <json> <chave>
safe_json_get() {
    local json=$1 key=$2
    if command -v jq &>/dev/null; then
        jq -r "$key" <<< "$json" 2>/dev/null || echo "null"
    else
        grep -oP "\"$key\":\s*\"?\K[^,\"}]+" <<< "$json" | head -1 || echo "null"
    fi
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ⚙️ CARREGAMENTO DE CONFIGURAÇÕES
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Carrega configurações de múltiplas fontes
load_config() {
    local config_files=(
        "$BASE_DIR/.env"                # Configurações do projeto
        "$BASE_DIR/config/monitor.conf" # Configurações específicas
        "/etc/monitor.conf"             # Configurações globais
    )

    for config_file in "${config_files[@]}"; do
        if [ -f "$config_file" ]; then
            log_debug "Carregando configurações de: $config_file"
            # Carrega apenas variáveis seguras (MAIÚSCULAS com _)
            while IFS='=' read -r key value; do
                [[ $key =~ ^[A-Z_]+$ ]] && export "$key=$value"
            done < <(grep -E '^[A-Z_]+=' "$config_file")
        fi
    done
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# 🚀 INICIALIZAÇÃO DO MÓDULO
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Execução direta (modo teste)
    echo -e "${GREEN}⏳ Iniciando teste do monitor-utils.sh${NC}"
    load_config
    if check_prerequisites; then
        echo -e "${GREEN}✅ Todos os pré-requisitos estão instalados${NC}"
        echo -e "Configurações carregadas:"
        echo -e " - CPU_WARNING=$CPU_WARNING"
        echo -e " - LOG_DIR=$LOG_DIR"
        echo -e " - CRITICAL_PROCESSES=$CRITICAL_PROCESSES"
    else
        echo -e "${RED}❌ Falha na verificação de pré-requisitos${NC}" >&2
        exit 1
    fi
else
    # Carregado como módulo
    load_config
    check_prerequisites || {
        log_error "Falha crítica: Pré-requisitos não atendidos"
        return 1 2>/dev/null || exit 1
    }
fi
