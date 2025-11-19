#!/usr/bin/env bash
# ===================================================
# ⏱️ DEBOUNCE - Controle de Repetição de Alertas (v0.3)
# Local: scripts/core/alerts-lib/utils/
# ===================================================
# Responsabilidade:
# - Bloquear alertas repetidos por tipo com lock seguro
# - Suporte a ambientes concorrentes e timeout
# - Limpeza automática de recursos
# ===================================================

# --- Dependências ---
if ! command -v jq &> /dev/null; then
  echo "[ERRO] 'jq' não instalado. Instale com: sudo apt install jq" >&2
  exit 1
fi

# --- Configurações ---
LOG_DIR="${LOG_DIR:-/var/log/mapsprove}"
DEBOUNCE_FILE="${DEBOUNCE_FILE:-${LOG_DIR}/.last_alerts.json}"
LOCK_FILE="${DEBOUNCE_FILE}.lock"
DEBOUNCE_SECONDS="${DEBOUNCE_SECONDS:-300}"  # 5 minutos
LOCK_TIMEOUT="${LOCK_TIMEOUT:-5}"           # Timeout de 5s para flock

# --- Inicialização ---
mkdir -p "$(dirname "$DEBOUNCE_FILE")"
[ -f "$DEBOUNCE_FILE" ] || echo '{}' > "$DEBOUNCE_FILE"

# --- Função Principal ---
can_send_alert() {
  local alert_type="$1"
  local now
  now=$(date +%s)

  (
    flock -x -w "$LOCK_TIMEOUT" 200 || {
      log_debug "🔒 Timeout ao obter lock para $alert_type" "debounce"
      return 1
    }

    trap 'rm -f "$LOCK_FILE"' EXIT

    # Valida JSON
    if ! jq empty "$DEBOUNCE_FILE" &>/dev/null; then
      echo '{}' > "$DEBOUNCE_FILE"
    fi

    local last_sent
    last_sent=$(jq -r --arg t "$alert_type" '.[$t] // 0' "$DEBOUNCE_FILE" 2>/dev/null || echo 0)

    if (( now - last_sent >= DEBOUNCE_SECONDS )); then
      jq --arg t "$alert_type" --argjson ts "$now" '.[$t]=$ts' "$DEBOUNCE_FILE" > "${DEBOUNCE_FILE}.tmp" && \
      mv "${DEBOUNCE_FILE}.tmp" "$DEBOUNCE_FILE"
      log_debug "✅ Alerta permitido para $alert_type" "debounce"
      return 0
    else
      local wait_time=$((DEBOUNCE_SECONDS - (now - last_sent)))
      log_debug "⏱️ Debounce ativo para $alert_type (aguarde ${wait_time}s)" "debounce"
      return 1
    fi
  ) 200>"$LOCK_FILE"
}
