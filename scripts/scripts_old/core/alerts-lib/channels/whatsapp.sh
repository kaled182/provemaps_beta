#!/usr/bin/env bash
# ===================================================
# 💬 WHATSAPP CHANNEL - Alerta WhatsApp (v0.3)
# Local: scripts/core/alerts-lib/channels/whatsapp.sh
# ===================================================
# Requisitos:
# - TWILIO_SID, TWILIO_TOKEN
# - WA_TO (ex: whatsapp:+5511999999999)
# - Opcional: WA_FROM (padrão sandbox Twilio), WA_TEMPLATE
# ===================================================

set -euo pipefail

# --- Dependências ---
command -v curl >/dev/null || { echo "ERRO CRÍTICO: 'curl' não está instalado." >&2; exit 1; }

# --- Configuração ---
WHATSAPP_SID="${TWILIO_SID:-}"
WHATSAPP_TOKEN="${TWILIO_TOKEN:-}"
WA_FROM="${WA_FROM:-whatsapp:+14155238886}"  # sandbox por padrão
WA_TO="${WA_TO:-}"                            # ex.: whatsapp:+5511999999999
WA_API_URL="${WA_API_URL:-https://api.twilio.com/2010-04-01/Accounts/${WHATSAPP_SID}/Messages.json}"
WA_TIMEOUT="${WA_TIMEOUT:-10}"                # segundos
WA_TEMPLATE="${WA_TEMPLATE:-"[{type}] {message}"}"  # template simples
# DRY_RUN=true para simular envio (sem chamar API)

# --- Helpers de log (usam monitor-utils.sh se carregado) ---
log_info()   { command -v log_info   >/dev/null && log_info   "$1" "whatsapp" || echo "INFO[whatsapp]: $1"; }
log_warn()   { command -v log_warn   >/dev/null && log_warn   "$1" "whatsapp" || echo "WARN[whatsapp]: $1"; }
log_error()  { command -v log_error  >/dev/null && log_error  "$1" "whatsapp" || echo "ERROR[whatsapp]: $1" >&2; }
log_metric() { command -v log_metric >/dev/null && log_metric "$1" "${2:-1}" || true; }

# --- Formatação de mensagem a partir de template ---
_format_message() {
  local alert_type="$1" message="$2"
  # substitui {type} e {message} no template
  sed -e "s/{type}/${alert_type}/g" -e "s/{message}/$(printf '%s' "$message" | sed 's/[&/\]/\\&/g')/g" <<< "$WA_TEMPLATE"
}

# --- Validações leves ---
_validate_config() {
  if [[ -z "$WHATSAPP_SID" || -z "$WHATSAPP_TOKEN" ]]; then
    log_error "TWILIO_SID/TWILIO_TOKEN não configurados."
    return 1
  fi
  if [[ -z "$WA_TO" ]]; then
    log_error "WA_TO não configurado (ex.: whatsapp:+5511999999999)."
    return 1
  fi
  case "$WA_TO" in
    whatsapp:+[0-9]* ) : ;;   # passa
    * ) log_warn "Formato de WA_TO não parece WhatsApp-Twilio (esperado whatsapp:+<E164>)." ;;
  esac
  return 0
}

# --- Função principal ---
send_whatsapp_alert() {
  local alert_type="$1"
  local message="$2"

  _validate_config || return 1

  local body
  body=$(_format_message "$alert_type" "$message")

  # Simulação
  if [[ "${DRY_RUN:-false}" == "true" ]]; then
    log_info "DRY_RUN ativo: simulando envio WhatsApp para '$WA_TO' com corpo: $body"
    log_metric "whatsapp_dry_run" 1
    return 0
  fi

  # Monta payload
  local payload=(
    --data-urlencode "To=$WA_TO"
    --data-urlencode "From=$WA_FROM"
    --data-urlencode "Body=$body"
  )

  # Chamada com captura de status/resposta
  local response_file http_code
  response_file="$(mktemp)"
  trap 'rm -f "$response_file"' RETURN

  http_code="$(
    curl --silent --show-error \
      --max-time "$WA_TIMEOUT" \
      --output "$response_file" \
      --write-out "%{http_code}" \
      -X POST \
      "${payload[@]}" \
      -u "$WHATSAPP_SID:$WHATSAPP_TOKEN" \
      "$WA_API_URL"
  )"

  if [[ "$http_code" -ge 200 && "$http_code" -lt 300 ]]; then
    log_info "✅ WhatsApp enviado para $WA_TO (HTTP $http_code)"
    log_metric "whatsapp_success" 1
    return 0
  else
    local error_details
    error_details="$(cat "$response_file")"
    log_error "❌ Falha ao enviar WhatsApp para $WA_TO (HTTP $http_code). Resposta: $error_details"
    log_metric "whatsapp_failure" 1
    return 1
  fi
}

# Teste rápido do canal
test_whatsapp_channel() {
  send_whatsapp_alert "TEST" "Mensagem de teste do MapsPROVE via WhatsApp - $(date)"
}

export -f send_whatsapp_alert test_whatsapp_channel

# Execução direta (opcional)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  test_whatsapp_channel
fi
