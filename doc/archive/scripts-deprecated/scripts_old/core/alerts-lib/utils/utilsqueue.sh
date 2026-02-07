#!/usr/bin/env bash
# ===================================================
# 📬 ALERT QUEUE - Gerenciamento de Fila de Alertas (v0.3.1)
# ===================================================
# Uso: 
#   enqueue_alert <priority> <type> <message> [metadata_json]
#   process_alert_queue
# ===================================================

# --- Configurações ---
VERSION="0.3.1"
LOG_DIR="${LOG_DIR:-/var/log/mapsprove}"
QUEUE_FILE="${ALERT_QUEUE:-${LOG_DIR}/alert_queue.json}"
QUEUE_LOCK="${QUEUE_FILE}.lock"
BACKUP_DIR="${LOG_DIR}/queue_backups"
MAX_BACKUPS=7
PRIORITY_UPGRADE_TIME=3600  # 1h → medium → high

# --- Inicialização ---
init_queue() {
  mkdir -p "$(dirname "$QUEUE_FILE")" "$BACKUP_DIR"
  [ -f "$QUEUE_FILE" ] || echo '{"version":"'"$VERSION"'","alerts":[]}' > "$QUEUE_FILE"
}

# --- Documentação ---
queue_help() {
  cat <<EOF
ALERT QUEUE v$VERSION - Comandos:

► enqueue_alert <priority> <type> <message> [metadata]
  Prioridades: high/medium/low
  Exemplo:
    enqueue_alert "high" "cpu" "CPU 95%" '{"host":"svr01"}'

► process_alert_queue
  Processa todos os alertas pendentes

► get_queue_size
  Retorna número de alertas pendentes

► get_pending_alerts
  Lista alertas no formato JSON
EOF
}

# --- Rotação de Backups ---
rotate_backups() {
  find "$BACKUP_DIR" -name "*.bak" -type f -mtime +$MAX_BACKUPS -delete 2>/dev/null
}

# --- Enfileirar Alerta ---
enqueue_alert() {
  [[ $# -lt 3 ]] && { queue_help; return 1; }

  local priority="${1}"
  local type="${2}"
  local message="${3}"
  local metadata="${4:-{}}"
  local timestamp
  timestamp=$(date +%s)

  # Validação de JSON
  if ! jq -e . <<< "$metadata" &>/dev/null; then
    metadata="{}"
    log_warn "⚠️ Metadados inválidos - usando padrão" "queue"
  fi

  local alert_json
  alert_json=$(jq -n \
    --arg p "$priority" \
    --arg t "$type" \
    --arg m "$message" \
    --argjson ts "$timestamp" \
    --argjson md "$metadata" \
    '{priority: $p, type: $t, message: $m, timestamp: $ts, metadata: $md}')

  (
    flock -x -w 5 200 || {
      log_error "⏱️ Timeout ao acessar fila" "queue"
      return 1
    }

    if jq --argjson alert "$alert_json" '.alerts += [$alert]' "$QUEUE_FILE" > "${QUEUE_FILE}.tmp"; then
      mv "${QUEUE_FILE}.tmp" "$QUEUE_FILE"
      log_debug "✅ [$priority] $type enfileirado" "queue"
    else
      log_error "❌ Falha ao atualizar fila" "queue"
      return 1
    fi
  ) 200>"$QUEUE_LOCK"
}

# --- Processar Fila ---
process_alert_queue() {
  local start_time
  start_time=$(date +%s)

  (
    flock -x -w 10 200 || {
      log_error "⏱️ Timeout ao processar fila" "queue"
      return 1
    }

    # Backup com timestamp
    local backup_file
    backup_file="${BACKUP_DIR}/alert_queue_$(date +%Y%m%d_%H%M%S).bak"
    cp "$QUEUE_FILE" "$backup_file"

    # Atualiza prioridades
    local now
    now=$(date +%s)
    jq --argjson now "$now" --argjson upgrade "$PRIORITY_UPGRADE_TIME" '
      .alerts |= map(
        if .priority == "low" and ($now - .timestamp) > $upgrade then
          .priority = "medium"
        elif .priority == "medium" and ($now - .timestamp) > $upgrade then
          .priority = "high"
        else . end
      )
    ' "$QUEUE_FILE" > "${QUEUE_FILE}.tmp" && mv "${QUEUE_FILE}.tmp" "$QUEUE_FILE"

    # Processa em ordem de prioridade
    local processed=0
    while read -r alert; do
      local type message
      type=$(jq -r '.type' <<< "$alert")
      message=$(jq -r '.message' <<< "$alert")

      if send_alert_via_all_channels "$type" "$message"; then
        log_info "📤 [$type] Enviado com sucesso" "queue"
        ((processed++))
      else
        log_warn "⚠️ [$type] Falha no envio" "queue"
      fi
    done < <(jq -c '.alerts | sort_by(.priority, .timestamp)[]' "$QUEUE_FILE")

    # Limpa fila e registra métricas
    echo '{"version":"'"$VERSION"'","alerts":[]}' > "$QUEUE_FILE"
    log_metric "queue_processed" "$processed"
    log_metric "queue_processing_time" "$(( $(date +%s) - start_time ))"
    rotate_backups

  ) 200>"$QUEUE_LOCK"
}

# --- Funções Auxiliares ---
send_alert_via_all_channels() {
  local type="$1" message="$2"
  # Aqui vai a chamada real para slack/email/etc
  # Exemplo: send_slack_alert "$type" "$message" || send_email_alert "$type" "$message"
  return 0
}

get_queue_size() {
  jq '.alerts | length' "$QUEUE_FILE"
}

get_pending_alerts() {
  jq -c '.alerts[]' "$QUEUE_FILE"
}

# --- Inicializar ---
init_queue
