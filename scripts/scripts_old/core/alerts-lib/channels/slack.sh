#!/usr/bin/env bash
# ===================================================
# 🔵 SLACK CHANNEL - Envio de Alertas (v0.3.1)
# ===================================================

SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"
SLACK_CHANNEL="${SLACK_CHANNEL:-#alerts}"
SLACK_USERNAME="Mapsprove Bot"
SLACK_TEMPLATE="${SLACK_TEMPLATE:-"🚨 [{type}] {message}"}"
CURL_TIMEOUT=10

send_slack_alert() {
  local alert_type="$1" message="$2"
  [[ -z "$SLACK_WEBHOOK" ]] && { log_error "SLACK_WEBHOOK_URL não configurado" "slack"; return 1; }

  # Template dinâmico
  local formatted_msg
  formatted_msg=$(sed -e "s/{type}/$alert_type/g" -e "s/{message}/$message/g" <<< "$SLACK_TEMPLATE")

  local payload
  payload=$(jq -n \
    --arg ch "$SLACK_CHANNEL" \
    --arg msg "$formatted_msg" \
    --arg user "$SLACK_USERNAME" \
    '{channel: $ch, text: $msg, username: $user, attachments: []}') || {
    log_error "Payload inválido" "slack"; return 1; }

  if curl --max-time $CURL_TIMEOUT -s -X POST -H 'Content-type: application/json' \
    --data "$payload" "$SLACK_WEBHOOK" >/dev/null; then
    log_info "✅ Slack enviado para $SLACK_CHANNEL" "slack"
    log_metric "slack_success" 1
    return 0
  else
    log_error "❌ Falha na API Slack (Timeout=${CURL_TIMEOUT}s)" "slack"
    log_metric "slack_failure" 1
    return 1
  fi
}

test_slack_channel() {
  send_slack_alert "TEST" "Teste de canal Slack $(date)"
}

export -f send_slack_alert test_slack_channel
