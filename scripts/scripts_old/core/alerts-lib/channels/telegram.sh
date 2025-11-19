#!/usr/bin/env bash
# ===================================================
# 📱 TELEGRAM CHANNEL - Envio de Alertas (v0.3.1)
# ===================================================

TELEGRAM_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
API_TIMEOUT=5

send_telegram_alert() {
  local alert_type="$1" message="$2"
  [[ -z "$TELEGRAM_TOKEN" || -z "$TELEGRAM_CHAT_ID" ]] && {
    log_error "Configuração Telegram incompleta" "telegram"; return 1; }

  local escaped_msg
  escaped_msg=$(sed 's/[_\*\[`]/\\&/g' <<< "$message")

  local api_url="https://api.telegram.org/bot${TELEGRAM_TOKEN}/sendMessage"
  local text="*[${alert_type^^}]* ${escaped_msg}"

  if curl --max-time $API_TIMEOUT -s -X POST "$api_url" \
    -d "chat_id=$TELEGRAM_CHAT_ID" \
    -d "text=$text" \
    -d "parse_mode=markdown" >/dev/null; then
    log_info "✅ Telegram enviado para chat $TELEGRAM_CHAT_ID" "telegram"
    log_metric "telegram_success" 1
    return 0
  else
    log_error "❌ Falha na API Telegram (Timeout=${API_TIMEOUT}s)" "telegram"
    log_metric "telegram_failure" 1
    return 1
  fi
}

test_telegram_channel() {
  send_telegram_alert "TEST" "Teste de canal Telegram em $(date)"
}

export -f send_telegram_alert test_telegram_channel
