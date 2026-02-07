#!/usr/bin/env bash
# ===================================================
# 📧 EMAIL CHANNEL - Envio de Alertas por Email (v0.3.1)
# ===================================================

EMAIL_FROM="${ALERT_EMAIL_FROM:-alerts@mapsprove.com}"
EMAIL_TO="${ALERT_EMAIL_TO:-}"
SMTP_SERVER="${SMTP_SERVER:-localhost}"
SMTP_PORT="${SMTP_PORT:-25}"
SUBJECT_PREFIX="[MAPSPROVE]"
TIMEOUT_SEC=5
LOG_DIR="${LOG_DIR:-/var/log/mapsprove}"
MAX_CONSECUTIVE_FAILS=3
FAIL_FILE="${LOG_DIR}/.email_fails.count"

get_consecutive_fails()   { cat "$1" 2>/dev/null || echo 0; }
reset_fail_counter()      { echo 0 > "$1"; }
increment_fail_counter()  { local c=$(get_consecutive_fails "$1"); echo $((c + 1)) > "$1"; }

send_email_alert() {
  local alert_type="$1" message="$2"
  local subject="${SUBJECT_PREFIX} ${alert_type^^}"

  [[ -z "$EMAIL_TO" ]] && { log_error "EMAIL_TO não configurada" "email"; return 1; }
  if ! command -v mailx &>/dev/null; then log_error "mailx não instalada" "email"; return 1; fi

  # Circuit breaker: se muitas falhas, desativa temporariamente o canal
  local fails=$(get_consecutive_fails "$FAIL_FILE")
  if (( fails >= MAX_CONSECUTIVE_FAILS )); then
    log_warn "🚧 Canal email temporariamente desativado ($fails falhas)" "email"
    return 1
  fi

  local mail_cmd=( mailx -S smtp="smtp://${SMTP_SERVER}:${SMTP_PORT}" -s "$subject" -r "$EMAIL_FROM" -v )
  if timeout $TIMEOUT_SEC echo "$message" | "${mail_cmd[@]}" "$EMAIL_TO" 2>&1 | log_debug "Enviando email" "email"; then
    reset_fail_counter "$FAIL_FILE"
    log_info "✅ Email enviado para $EMAIL_TO" "email"
    log_metric "email_success" 1
    return 0
  else
    increment_fail_counter "$FAIL_FILE"
    log_error "❌ Falha no envio (Código $?)" "email"
    log_metric "email_failure" 1
    return 1
  fi
}

test_email_channel() {
  send_email_alert "TEST" "Teste de canal email em $(date)"
}

export -f send_email_alert test_email_channel
