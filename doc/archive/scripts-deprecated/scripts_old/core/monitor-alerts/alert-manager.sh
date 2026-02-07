#!/usr/bin/env bash
# ===================================================
# 🧠 ALERT MANAGER - monitor-alerts (v0.5.1)
# Local: scripts/core/monitor-alerts/alert-manager.sh
# ===================================================
# Melhorias:
# - Timeout configurável por variável de ambiente
# - Validação de subprocessos com PID tracking
# - Mock DB com rotação automática
# - Logs estruturados para debugging
# ===================================================

# --- Carregar dependências ---
source "$(dirname "$0")/../alerts-lib/utils/log.sh" || {
  echo "Falha ao carregar log.sh"; exit 1
}
source "$(dirname "$0")/../alerts-lib/utils/queue.sh" || {
  log_error "Falha ao carregar queue.sh" "dependency"; exit 1
}

# --- Configurações ---
readonly MOCK_DB_FILE="${MOCK_DB_FILE:-/tmp/mapsprove_mock_db.json}"
readonly MAX_LOG_FILES="${MAX_LOG_FILES:-5}"
readonly ALERT_TIMEOUT="${ALERT_TIMEOUT:-30}"  # segundos
readonly PROCESSORS=("cpu" "memory" "disk")    # Módulos ativos

# --- Inicialização ---
mkdir -p "$(dirname "$MOCK_DB_FILE")"
touch "$MOCK_DB_FILE"

# --- Hooks (sobrescreva em scripts/extras/) ---
before_alert_processing() {
  log_debug "Ciclo de alertas iniciado" "lifecycle" \
    '{"timestamp":"'"$(date +%s)"'"}'
}

after_alert_processing() {
  log_debug "Ciclo de alertas finalizado" "lifecycle"
}

# --- Validações ---
validate_input_json() {
  local json_data="$1"
  
  if ! jq -e . >/dev/null 2>&1 <<< "$json_data"; then
    log_error "JSON malformado" "validation" \
      '{"input_sample":"'"${json_data:0:30}..."'"}'
    return 1
  fi

  local required_fields=("timestamp" "server_id")
  for field in "${required_fields[@]}"; do
    if ! jq -e ".${field}" >/dev/null 2>&1 <<< "$json_data"; then
      log_error "Campo obrigatório faltante: $field" "validation" \
        '{"missing_field":"'"$field"'"}'
      return 1
    fi
  done

  return 0
}

# --- Gerenciamento de Subprocessos ---
run_processors() {
  local json_data="$1" timestamp="$2" context="$3"
  declare -gA processor_pids=()

  for processor in "${PROCESSORS[@]}"; do
    source "$(dirname "$0")/../alerts-lib/processors/${processor}.sh" || {
      log_warn "Processor ${processor}.sh não carregado" "dependency"
      continue
    }

    "process_${processor}_alert" "$json_data" "$timestamp" "$context" &
    processor_pids["$processor"]=$!
    log_debug "Subprocesso iniciado: $processor (PID ${processor_pids[$processor]})" "parallel" \
      '{"processor":"'"$processor"'", "pid":'"${processor_pids[$processor]}"'}'
  done
}

wait_for_processors() {
  local timeout_reached=0

  for processor in "${!processor_pids[@]}"; do
    local pid=${processor_pids["$processor"]}
    
    if ! wait "$pid" 2>/dev/null; then
      log_warn "Processor $processor falhou (PID $pid)" "parallel" \
        '{"processor":"'"$processor"'", "pid":'"$pid"', "status":"failed"}'
    fi
  done
}

# --- Mock DB com Rotação ---
mock_insert_alert() {
  local alert_json="$1"
  
  # Rotação (mantém últimos 100 alertas)
  if [[ $(wc -l < "$MOCK_DB_FILE") -ge 100 ]]; then
    tail -n 50 "$MOCK_DB_FILE" > "${MOCK_DB_FILE}.tmp" && 
    mv "${MOCK_DB_FILE}.tmp" "$MOCK_DB_FILE"
  fi

  echo "$alert_json" | jq -c . >> "$MOCK_DB_FILE" || {
    log_error "Falha ao escrever no mock DB" "mock_db" \
      '{"alert_size":'"${#alert_json}"'}'
    return 1
  }
}

# --- Fluxo Principal ---
manage_alerts() {
  local json_data="$1" context="${2:-unspecified}"

  validate_input_json "$json_data" || return 1

  local timestamp
  timestamp=$(jq -r '.timestamp' <<< "$json_data")

  before_alert_processing

  run_processors "$json_data" "$timestamp" "$context"
  wait_for_processors

  after_alert_processing

  process_alert_queue "$context" | while read -r alert; do
    mock_insert_alert "$alert"
  done
}

# --- Execução ---
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  [[ $# -lt 1 ]] && {
    log_error "Uso: $0 '<json_data>' [contexto]" "cli" \
      '{"example_input":"{\"timestamp\":\"...\", \"server_id\":\"...\"}"}'
    exit 1
  }

  manage_alerts "$1" "${2:-cli}" || exit 1
fi
