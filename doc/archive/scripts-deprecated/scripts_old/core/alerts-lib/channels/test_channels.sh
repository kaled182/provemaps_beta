#!/usr/bin/env bash
# ===================================================
# 🔎 TEST CHANNELS - Verificação dos Canais (v0.3)
# Local: scripts/core/alerts-lib/channels/test_channels.sh
# ===================================================
# Melhorias:
# - Execução dos testes em PARALELO para máxima velocidade.
# - Diagnóstico específico para TIMEOUT vs. FALHA.
# - Sumário final com cores para melhor legibilidade.
# ===================================================

set -euo pipefail

# --- Cores para o output ---
COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[0;33m'
COLOR_NC='\033[0m' # No Color

# --- Resolve paths ---
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHANNELS_DIR="$HERE"
CORE_DIR="$(cd "$HERE/../../" && pwd)"           # scripts/core/alerts-lib/..
ROOT_DIR="$(cd "$CORE_DIR/../../.." && pwd)"     # mapsprove/

# --- Carrega utils se existir; define fallbacks de log ---
if [[ -f "$CORE_DIR/monitor-utils.sh" ]]; then
  # scripts/core/monitor-utils.sh
  source "$CORE_DIR/monitor-utils.sh" || true
fi
log_info()   { command -v log_info   >/dev/null && log_info   "$1" "test_channels" || echo "INFO[test_channels]: $1"; }
log_warn()   { command -v log_warn   >/dev/null && log_warn   "$1" "test_channels" || echo "WARN[test_channels]: $1"; }
log_error()  { command -v log_error  >/dev/null && log_error  "$1" "test_channels" || echo "ERROR[test_channels]: $1" >&2; }
log_metric() { command -v log_metric >/dev/null && log_metric "$1" "${2:-1}" || true; }

# --- Carrega os canais (se presentes) ---
source "$CHANNELS_DIR/email.sh"     || true
source "$CHANNELS_DIR/slack.sh"     || true
source "$CHANNELS_DIR/telegram.sh"  || true
source "$CHANNELS_DIR/whatsapp.sh"  || true

# --- Opções / CLI ---
ONLY=""
DRY=false
PER_CHANNEL_TIMEOUT="${PER_CHANNEL_TIMEOUT:-20}"

show_help() {
  cat <<EOF
Uso: ${0##*/} [opções]

Opções:
  --only <lista>    Testar apenas os canais (csv): email,slack,telegram,whatsapp
  --dry-run         Ativa DRY_RUN=true (quando suportado pelo canal)
  --timeout <seg>   Timeout por canal (padrão: $PER_CHANNEL_TIMEOUT)
  -h, --help        Mostra esta ajuda

Exemplos:
  ${0##*/} --only slack,telegram
  ${0##*/} --dry-run --timeout 5
EOF
}

while (( $# )); do
  case "$1" in
    --only)    ONLY="${2:-}"; shift ;;
    --dry-run) DRY=true ;;
    --timeout) PER_CHANNEL_TIMEOUT="${2:-$PER_CHANNEL_TIMEOUT}"; shift ;;
    -h|--help) show_help; exit 0 ;;
    *)         log_warn "Argumento desconhecido: $1" ;;
  esac
  shift
done

$DRY && export DRY_RUN=true

# --- Seleção de canais ---
declare -a ALL_CHANNELS=(email slack telegram whatsapp)
if [[ -n "$ONLY" ]]; then
  IFS=',' read -r -a CHANNELS <<< "$ONLY"
else
  CHANNELS=("${ALL_CHANNELS[@]}")
fi

# --- Execução paralela ---
declare -A RESULTS=()   # OK/FAIL/TIMEOUT/NA
declare -A PIDS=()
declare -i FAILS=0
declare -i OKS=0
declare -i SKIPPED=0
declare -i TIMEOUTS=0

run_test_for() {
  local ch="$1"
  local fn="test_${ch}_channel"

  # Se a função não existe no shell atual, marcamos 127 (NA)
  if ! declare -F "$fn" >/dev/null; then
    return 127
  fi

  # Executa em subshell com timeout garantindo que deps estejam disponíveis lá
  export PER_CHANNEL_TIMEOUT DRY_RUN
  timeout "$PER_CHANNEL_TIMEOUT" bash -c ". \"$CORE_DIR/monitor-utils.sh\" 2>/dev/null || true; . \"$CHANNELS_DIR/${ch}.sh\"; $fn"
}

START_TS=$(date +%s)
log_info "Iniciando testes de canais: ${CHANNELS[*]}"
echo

# Lança todos em background
for ch in "${CHANNELS[@]}"; do
  run_test_for "$ch" &
  PIDS["$ch"]=$!
done

# Aguarda resultados
for ch in "${!PIDS[@]}"; do
  log_info "Aguardando: $ch..."
  if wait "${PIDS[$ch]}"; then
    RESULTS["$ch"]="OK"
    ((OKS++))
  else
    exit_code=$?
    if [[ $exit_code -eq 124 ]]; then
      RESULTS["$ch"]="TIMEOUT"
      ((TIMEOUTS++))
    elif [[ $exit_code -eq 127 ]]; then
      RESULTS["$ch"]="NA"
      ((SKIPPED++))
      log_warn "Canal '$ch' não disponível (função de teste ausente)."
    else
      RESULTS["$ch"]="FAIL"
      ((FAILS++))
    fi
  fi
done

DUR=$(( $(date +%s) - START_TS ))

# --- Sumário ---
echo
echo "================= SUMÁRIO DOS CANAIS ================="
for ch in "${ALL_CHANNELS[@]}"; do
  if [[ -v RESULTS["$ch"] ]]; then
    status="${RESULTS[$ch]}"
    case "$status" in
      OK)      echo -e "${COLOR_GREEN}🟢 $ch: OK${COLOR_NC}" ;;
      FAIL)    echo -e "${COLOR_RED}🔴 $ch: FAIL${COLOR_NC}" ;;
      TIMEOUT) echo -e "${COLOR_YELLOW}🟡 $ch: TIMEOUT (${PER_CHANNEL_TIMEOUT}s)${COLOR_NC}" ;;
      NA)      echo -e "${COLOR_YELLOW}🟡 $ch: NA (não disponível)${COLOR_NC}" ;;
    esac
  fi
done
echo "----------------------------------------------------"
echo "Tempo total: ${DUR}s"
echo -e "Resultados: ${COLOR_GREEN}OK: $OKS${COLOR_NC} | ${COLOR_RED}FAIL: $FAILS${COLOR_NC} | ${COLOR_YELLOW}TIMEOUT: $TIMEOUTS${COLOR_NC} | NA: $SKIPPED"
echo "======================================================"

# Métricas
log_metric "channels_test_ok"      "$OKS"
log_metric "channels_test_fail"    "$FAILS"
log_metric "channels_test_timeout" "$TIMEOUTS"
log_metric "channels_test_na"      "$SKIPPED"
log_metric "channels_test_time"    "$DUR"

# Exit: falha se tiver FAIL ou TIMEOUT
(( FAILS > 0 || TIMEOUTS > 0 )) && exit 1 || exit 0
