#!/usr/bin/env bash
# ===================================================
# 🟢 WEBHOOK CHANNEL - Alerta HTTP POST genérico (v0.3)
# Local: scripts/core/alerts-lib/channels/webhook.sh
# ===================================================
# Recursos:
# - Verificação de status HTTP (2xx = sucesso)
# - Timeout de conexão e total (configuráveis)
# - Retries com backoff exponencial + jitter em 5xx/429
# - Circuit breaker (falhas consecutivas)
# - DRY_RUN para testes/CI
# - Headers extras via JSON (WEBHOOK_EXTRA_HEADERS)
# - Assinatura HMAC opcional (WEBHOOK_HMAC_SECRET)
# - Logs/metrics integrados (fallback se utils não carregado)
# ===================================================

set -euo pipefail

# ------------------ Dependências mínimas ------------------
command -v curl >/dev/null || { echo "[ERRO][webhook] 'curl' não instalado"; exit 1; }
command -v jq   >/dev/null || { echo "[ERRO][webhook] 'jq' não instalado";   exit 1; }
# openssl é opcional; só exigido se for usar HMAC
if [[ -n "${WEBHOOK_HMAC_SECRET:-}" ]]; then
  command -v openssl >/dev/null || { echo "[ERRO][webhook] 'openssl' não instalado (necessário p/ HMAC)"; exit 1; }
fi

# ------------------ Fallback de LOG/METRIC ----------------
: "${LOG_DIR:=/var/log/mapsprove}"
log_info()   { command -v log_info   >/dev/null && log_info   "$1" "webhook" || echo "[INFO][webhook] $1"; }
log_warn()   { command -v log_warn   >/dev/null && log_warn   "$1" "webhook" || echo "[AVISO][webhook] $1"; }
log_error()  { command -v log_error  >/dev/null && log_error  "$1" "webhook" || echo "[ERRO][webhook] $1" >&2; }
log_debug()  { command -v log_debug  >/dev/null && log_debug  "$1" "webhook" || { [ "${DEBUG:-false}" = "true" ] && echo "[DEBUG][webhook] $1"; }; }
log_metric() { command -v log_metric >/dev/null && log_metric "$1" "${2:-1}" || :; }

# ------------------ Configuração (ENV) --------------------
GENERIC_WEBHOOK_URL="${GENERIC_WEBHOOK_URL:-}"
WEBHOOK_CONNECT_TIMEOUT="${WEBHOOK_CONNECT_TIMEOUT:-5}"  # seg
WEBHOOK_TIMEOUT="${WEBHOOK_TIMEOUT:-15}"                 # seg
WEBHOOK_RETRIES="${WEBHOOK_RETRIES:-2}"                  # tentativas adicionais
WEBHOOK_BACKOFF_BASE="${WEBHOOK_BACKOFF_BASE:-2}"        # base do backoff (exponencial)
WEBHOOK_BACKOFF_JITTER_MAX="${WEBHOOK_BACKOFF_JITTER_MAX:-300}"  # ms de jitter
DRY_RUN="${DRY_RUN:-false}"

# Circuit breaker
MAX_CONSECUTIVE_FAILS="${MAX_CONSECUTIVE_FAILS:-3}"
FAIL_FILE="${FAIL_FILE:-${LOG_DIR}/.webhook_fails.count}"

# Headers extras: JSON de objeto, ex: {"X-Env":"prod","X-App":"mapsprove"}
WEBHOOK_EXTRA_HEADERS="${WEBHOOK_EXTRA_HEADERS:-}"

# HMAC (opcional)
# Se definido WEBHOOK_HMAC_SECRET, assina o corpo com sha256 e envia:
#   X-MapsProve-Signature: sha256=<hex>
WEBHOOK_HMAC_SECRET="${WEBHOOK_HMAC_SECRET:-}"

# ------------------ Helpers (fails consecutivos) ----------
get_consecutive_fails() { [ -f "$FAIL_FILE" ] && cat "$FAIL_FILE" 2>/dev/null || echo 0; }
reset_fail_counter()    { echo 0 > "$FAIL_FILE"; }
increment_fail_counter(){ echo $(( $(get_consecutive_fails) + 1 )) > "$FAIL_FILE"; }

# ------------------ Helpers diversos ----------------------
# Validação simples de URL (não exaustiva, mas útil)
is_probably_url() {
  local u="$1"
  [[ "$u" =~ ^https?://.+ ]]
}

# Constrói payload padrão caso não seja fornecido JSON bruto
build_default_payload() {
  local type="$1" message="$2"
  jq -n \
    --arg type "$type" \
    --arg message "$message" \
    --arg timestamp "$(date --iso-8601=seconds)" \
    --arg host "$(hostname 2>/dev/null || echo unknown)" \
    '{type:$type, message:$message, timestamp:$timestamp, host:$host}'
}

# Aplica HMAC sha256 ao corpo e retorna header pronto
maybe_hmac_header() {
  local body="$1"
  if [[ -n "$WEBHOOK_HMAC_SECRET" ]]; then
    # shellcheck disable=SC2155
    local sig="$(printf '%s' "$body" | openssl dgst -sha256 -hmac "$WEBHOOK_HMAC_SECRET" -r | awk '{print $1}')"
    printf 'X-MapsProve-Signature: sha256=%s' "$sig"
  fi
}

# Constrói array de headers adicionais a partir de JSON (objeto)
# Ex.: WEBHOOK_EXTRA_HEADERS='{"X-Env":"prod","X-App":"mapsprove"}'
build_extra_headers() {
  local -a hdrs=()
  if [[ -n "$WEBHOOK_EXTRA_HEADERS" ]]; then
    # valida objeto
    if jq -e 'type=="object"' >/dev/null 2>&1 <<<"$WEBHOOK_EXTRA_HEADERS"; then
      while IFS=$'\n' read -r kv; do
        hdrs+=("$kv")
      done < <(jq -r 'to_entries[] | "\(.key): \(.value)"' <<< "$WEBHOOK_EXTRA_HEADERS")
    else
      log_warn "WEBHOOK_EXTRA_HEADERS não é um objeto JSON. Ignorando."
    fi
  fi
  printf '%s\n' "${hdrs[@]}"
}

# Backoff exponencial com jitter
sleep_backoff() {
  local attempt="$1"  # 1..N
  local base="$WEBHOOK_BACKOFF_BASE"
  local secs=$(( base ** attempt ))
  # jitter em ms até WEBHOOK_BACKOFF_JITTER_MAX
  local jitter_ms=$(( RANDOM % WEBHOOK_BACKOFF_JITTER_MAX ))
  # converte ms para segundos fracionários
  local jitter="0.$(printf '%03d' "$jitter_ms")"
  local total
  total=$(awk "BEGIN {print $secs + $jitter}")
  log_debug "Backoff: ${total}s (tentativa #$attempt)"
  # sleep aceita float em bash moderno com coreutils (via `sleep 1.5`)
  sleep "$total"
}

# ------------------ Envio principal -----------------------
# Uso:
#   send_webhook_alert "<TYPE>" "<MESSAGE>" [<PAYLOAD_JSON_BRUTO>]
# Se o 3º arg estiver presente e for JSON válido, será usado como corpo.
send_webhook_alert() {
  local alert_type="$1"
  local message="$2"
  local raw_json="${3:-}"

  # Circuit breaker
  local fails
  fails="$(get_consecutive_fails)"
  if (( fails >= MAX_CONSECUTIVE_FAILS )); then
    log_warn "🚧 Canal Webhook temporariamente desativado (falhas consecutivas: $fails)"
    return 1
  fi

  # URL obrigatória
  if [[ -z "$GENERIC_WEBHOOK_URL" ]]; then
    log_error "GENERIC_WEBHOOK_URL não configurada"
    return 1
  fi
  if ! is_probably_url "$GENERIC_WEBHOOK_URL"; then
    log_warn "URL pode estar inválida: $GENERIC_WEBHOOK_URL"
  fi

  # Monta payload
  local body
  if [[ -n "$raw_json" ]]; then
    if jq -e . >/dev/null 2>&1 <<< "$raw_json"; then
      body="$raw_json"
    else
      log_warn "Payload JSON bruto inválido; usando payload padrão"
      body="$(build_default_payload "$alert_type" "$message")"
    fi
  else
    body="$(build_default_payload "$alert_type" "$message")"
  fi

  # DRY-RUN
  if [[ "${DRY_RUN}" == "true" ]]; then
    log_info "DRY_RUN ativo — simulação de POST para $GENERIC_WEBHOOK_URL"
    log_debug "Payload: $(jq -c . <<<"$body")"
    return 0
  fi

  # Headers
  local -a curl_headers=()
  curl_headers+=("-H" "Content-Type: application/json")
  # Headers extras
  while IFS= read -r h; do
    [[ -n "$h" ]] && curl_headers+=("-H" "$h")
  done < <(build_extra_headers)
  # Header HMAC (se houver)
  if [[ -n "$WEBHOOK_HMAC_SECRET" ]]; then
    curl_headers+=("-H" "$(maybe_hmac_header "$body")")
  fi

  # Execução com retries (em 5xx/429)
  local response_file http_code attempt=0
  response_file="$(mktemp)"
  trap 'rm -f "$response_file" 2>/dev/null || true' EXIT

  local max_attempts=$((WEBHOOK_RETRIES + 1))
  while (( attempt < max_attempts )); do
    attempt=$((attempt + 1))
    log_debug "Tentativa ${attempt}/${max_attempts} → $GENERIC_WEBHOOK_URL"

    http_code="$(curl --silent --show-error \
      --connect-timeout "$WEBHOOK_CONNECT_TIMEOUT" \
      --max-time "$WEBHOOK_TIMEOUT" \
      --output "$response_file" \
      --write-out "%{http_code}" \
      -X POST \
      "${curl_headers[@]}" \
      --data "$body" \
      "$GENERIC_WEBHOOK_URL" || echo "000")"

    # Sucesso 2xx
    if [[ "$http_code" =~ ^2[0-9]{2}$ ]]; then
      reset_fail_counter
      log_info "✅ Webhook enviado (HTTP $http_code)"
      log_metric "webhook_success" 1
      return 0
    fi

    # Erros que justificam retry: 5xx e 429
    if [[ "$http_code" =~ ^5[0-9]{2}$ || "$http_code" == "429" ]]; then
      local body_resp; body_resp="$(cat "$response_file" 2>/dev/null || echo '')"
      log_warn "Falha transitória (HTTP $http_code). Resposta: ${body_resp:0:400}"
      if (( attempt < max_attempts )); then
        # Repeito a Retry-After (se vier)
        local retry_after=""
        # Nota: sem --include, não temos headers; manter backoff padrão.
        sleep_backoff "$attempt"
        continue
      fi
    fi

    # Erro definitivo (4xx não-429 ou 000)
    local err_body; err_body="$(cat "$response_file" 2>/dev/null || echo '')"
    log_error "❌ Falha definitiva (HTTP $http_code). Resposta: ${err_body:0:400}"
    increment_fail_counter
    log_metric "webhook_failure" 1
    return 1
  done

  # Se saiu do loop sem sucesso
  increment_fail_counter
  log_error "❌ Falha após ${WEBHOOK_RETRIES} retries"
  log_metric "webhook_failure" 1
  return 1
}

# ------------------ Teste rápido --------------------------
test_webhook_channel() {
  send_webhook_alert "TEST" "Webhook MapsPROVE @ $(date)"
}

export -f send_webhook_alert test_webhook_channel

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  test_webhook_channel
fi
