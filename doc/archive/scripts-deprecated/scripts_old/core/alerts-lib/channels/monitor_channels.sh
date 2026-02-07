#!/usr/bin/env bash
# ===================================================
# 🔍 TESTE DE CANAIS - Validação rápida dos canais (v0.2)
# Local: scripts/core/alerts-lib/channels/test_channels.sh
# ===================================================

set -euo pipefail

# --- Importar canais ---
source "$(dirname "$0")/email.sh"
source "$(dirname "$0")/slack.sh"
source "$(dirname "$0")/telegram.sh"
source "$(dirname "$0")/webhook.sh"

# --- Função de teste genérica ---
check_channel_health() {
  local channel="$1"
  local test_func="test_${channel}_channel"

  if $test_func; then
    echo "🟢 $channel OK"
  else
    echo "🔴 $channel OFFLINE"
  fi
}

# --- Execução ---
for channel in email slack telegram webhook; do
  check_channel_health "$channel"
done
