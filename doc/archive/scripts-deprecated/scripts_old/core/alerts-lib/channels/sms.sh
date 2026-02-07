#!/usr/bin/env bash
# ===================================================
# 📲 SMS CHANNEL - Envio de Alertas por SMS (v0.3)
# Local: scripts/core/alerts-lib/channels/sms.sh
# ===================================================
# Melhorias:
# - Verificação de status HTTP (2xx = sucesso)
# - Timeout + retries com backoff (configuráveis)
# - Circuit breaker simples (falhas consecutivas)
# - DRY_RUN para ambientes de teste/CI
# - Sanitização de logs (sem vazar tokens)
# - Validação básica E.164 do número
# ===================================================

set -euo pipefail

# --- Dependências mínimas ---
command -v curl >/dev/null || { echo "[ERRO][sms] 'curl' não instalado"; exit 1; }
command -v mktemp >/dev/null || { echo "[ERRO][sms] 'mktemp' não disponível"; exit 1; }

# --- Fallback de LOG/METRIC (se não vier do monitor-utils) ---
: "${LOG_DIR:=/var/log/mapsprove}"
log_info()   { command -v log_info   >/dev/null && log_info   "$1" "sms" || echo "[INFO][sms] $1"; }
log_warn()   { command -v log_warn   >/dev/null && log_warn   "$1" "sms" || echo "[AVISO][sms] $1"; }
log_error()  { command -v log_error  >/dev/null && log_error  "$1" "sms" || echo "[ERRO][sms] $1" >&2; }
log_debug()  { command -v log_debug  >/dev/null && log_debug  "$1" "sms" || { [ "${DEBUG:-false}" = "true" ] && echo "[DEBUG][sms] $1"; }; }
log_metric() { command -v log_metric >/dev/null && log_metric "$1" "${2:-1}" || :; }

# --- Configuração (env) ---
TWILIO_SID="${TWILIO_SID:-}"
TWILIO_TOKEN="${TWILIO_TOKEN:-}"
SMS_FROM="${SMS_FROM:-+1000000000}"
SMS_TO="${SMS_TO:-}"                        # destino padrão opcional
SMS_API_URL="${SMS_API_URL:-https://api.twilio.com/2010-04-01/Accounts/${TWILIO_SID}/Messages.json}"

# Timeout e retries
CURL_CONNECT_TIMEOUT="${CURL_CONNECT_TIMEOUT:-5}"
CURL_MAX_TIME="${CURL_MAX_TIME:-15}"
SMS_RETRIES="${SMS_RETRIES:-2}"
SMS_BACKOFF_SECONDS="${SMS_BACKOFF_SECONDS:-2}"

# Circuit breaker
MAX_CONSECUTIVE_FAILS="${MAX_CONSECUTIVE_FAILS:-3}"
FAIL_FILE="${FAIL_FILE:-${LOG_DIR}/.sms_fails.count}"

# Modo simulação
DRY_RUN="${DRY_RUN:-false}"

# --- Helpers de falhas consecutivas ---
get_consecutive_fails() { [ -f "$FAIL_FILE" ] && cat "$FAIL_FILE" 2>/dev/null || echo 0; }
reset_fail_counter()    { echo 0 > "$FAIL_FILE"; }
increment_fail_counter(){ echo $(( $(get_consecutive_fails) + 1 )) > "$FAIL_FILE"; }

# --- Validação E.164 simples ---
is_e164() {
  # +DD........ (8 a 15 dígitos no total, aproximado)
  [[ "$1" =~ ^\+?[1-9][0-9]{7,14}$ ]]
}

# --- Envio principal ---
# Uso: send_sms_alert "<TYPE>" "<MESSAGE>" [<TO_OVERRIDE>]
send_sms_alert() {
  local alert_type="$1"
  local message="$2"
  local to_number="${3:-$SMS_TO}"

  # Circuit breaker
  local fails
  fails="$(get_consecutive_fails)"
  if (( fails >= MAX_CONSECUTIVE_FAILS )); then
    log_warn "🚧 Canal SMS temporariamente desativado (falhas consecutivas: $fails)"
    return 1
  fi

  # Valida config
  if [[ -z "$TWILIO_SID" || -z "$TWILIO_TOKEN" ]]; then
    log_error "Configuração Twilio incompleta (TWILIO_SID/TWILIO_TOKEN)"
    return 1
  fi
  if [[ -z "$to_number" ]]; then
    log_error "Destino SMS não informado (SMS_TO vazio e sem override)"
    return 1
  fi
  if ! is_e164 "$to_number"; then
    log_warn "Número destino possivelmente inválido (não E.164): '$to_number'"
  fi

  # DRY-RUN
  if [[ "$DRY_RUN" == "true" ]]; then
    log_info "DRY_RUN ativo — simulação de envio SMS para $to_number: [$alert_type] $message"
    return 0
  fi

  # Payload
  local payload=(
    --data-urlencode "To=$to_number"
    --data-urlencode "From=$SMS_FROM"
    --data-urlencode "Body=[$alert_type] $message"
  )

  # Execução com retries
  local attempt=0 http_code response_file
  response_file="$(mktemp)"
  trap 'rm -f "$response_file" 2>/dev/null || true' EXIT

  while (( attempt <= SMS_RETRIES )); do
    attempt=$((attempt + 1))
    log_debug "Tentativa ${attempt}/${SMS_RETRIES} para $to_number"

    http_code="$(curl --silent --show-error \
      --connect-timeout "$CURL_CONNECT_TIMEOUT" \
      --max-time "$CURL_MAX_TIME" \
      --output "$response_file" \
      --write-out "%{http_code}" \
      -X POST \
      "${payload[@]}" \
      -u "$TWILIO_SID:$TWILIO_TOKEN" \
      "$SMS_API_URL" || echo "000")"

    if [[ "$http_code" =~ ^2[0-9]{2}$ ]]; then
      reset_fail_counter
      log_info "✅ SMS enviado para $to_number (HTTP $http_code)"
      log_metric "sms_success" 1
      return 0
    else
      # Não vazamos o token em logs. Mostramos só o corpo e o status.
      local body; body="$(cat "$response_file" 2>/dev/null || echo '')"
      log_warn "Falha no envio (HTTP $http_code). Corpo: ${body:0:400}"
      if (( attempt <= SMS_RETRIES )); then
        sleep "$SMS_BACKOFF_SECONDS"
      fi
    fi
  done

  increment_fail_counter
  log_error "❌ Falha após ${SMS_RETRIES} tentativas para $to_number"
  log_metric "sms_failure" 1
  return 1
}

# --- Teste rápido (execução direta) ---
test_sms_channel() {
  send_sms_alert "TEST" "Alerta MapsPROVE via SMS @ $(date)"
}

export -f send_sms_alert test_sms_channel

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  test_sms_channel
fi
