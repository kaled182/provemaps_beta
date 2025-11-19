#!/usr/bin/env bash
# ===================================================
# 🛡️ VALIDAÇÃO - monitor-alerts (v0.2)
# Arquivo: validation.sh
# Local: scripts/core/alerts-lib/utils/
# ===================================================
# Responsabilidades:
# 1. Validação de estrutura e tipos no JSON
# 2. Verificação do ambiente de execução
# 3. Geração de logs detalhados para debugging
# ===================================================

# --- Constantes ---
declare -r DEFAULT_REQUIRED_FIELDS=("cpu" "memory" "timestamp" "disks")
declare -r TIMESTAMP_REGEX='^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(Z|[+-][0-9]{2}:[0-9]{2})?$'
declare -r MIN_DISK_USAGE=0  # Uso mínimo válido para discos (0% a 100%)

# --- Funções Públicas ---

validate_json() {
    local json_data="$1"
    local debug_file="${LOG_DIR}/last_json_error.log"
    local -a required_fields=("${REQUIRED_FIELDS[@]:-${DEFAULT_REQUIRED_FIELDS[@]}}")

    # Validação básica de JSON
    if ! jq -e . <<< "$json_data" >/dev/null 2> "$debug_file"; then
        [[ "${DEBUG:-false}" == "true" ]] && log_debug "Erro de sintaxe: $(cat "$debug_file")"
        log_error "JSON malformado (ver ${debug_file})"
        return 1
    fi

    # Validação de campos e tipos
    for field in "${required_fields[@]}"; do
        if ! jq -e "has(\"${field}\")" <<< "$json_data" >/dev/null; then
            log_error "Campo obrigatório ausente: '$field'"
            return 1
        fi

        case "$field" in
            "timestamp")
                local ts
                ts=$(jq -r '.timestamp' <<< "$json_data")
                if ! [[ "$ts" =~ $TIMESTAMP_REGEX ]]; then
                    log_error "Formato de timestamp inválido (use ISO 8601: YYYY-MM-DDTHH:MM:SS±TZ)"
                    return 1
                fi
                ;;
            
            "cpu"|"memory")
                if ! jq -e ".${field}.usage | numbers and . >= 0 and . <= 100" <<< "$json_data" >/dev/null; then
                    log_error "${field}.usage deve ser número entre 0-100"
                    return 1
                fi
                ;;
            
            "disks")
                if ! jq -e ".disks | arrays and length > 0" <<< "$json_data" >/dev/null; then
                    log_error "disks deve ser um array não vazio"
                    return 1
                fi
                
                jq -c '.disks[]' <<< "$json_data" | while read -r disk; do
                    if ! jq -e '.usage | numbers and . >= 0 and . <= 100' <<< "$disk" >/dev/null; then
                        log_error "disks[].usage deve ser número entre 0-100"
                        return 1
                    fi
                done
                ;;
        esac
    done

    log_debug "JSON validado - todos os checks passaram"
    return 0
}

validate_environment() {
    local -a required_vars=("LOG_DIR" "ALERT_EMAIL")
    local missing=0

    # Verifica variáveis obrigatórias
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "Variável de ambiente obrigatória: $var"
            missing=1
        fi
    done

    [[ "$missing" -ne 0 ]] && return 1

    # Verifica permissões
    if [[ ! -w "$LOG_DIR" ]]; then
        log_error "Sem permissão de escrita em LOG_DIR: $LOG_DIR"
        return 1
    fi

    # Verifica comandos essenciais
    if ! command -v jq &> /dev/null; then
        log_error "Dependência faltando: jq (instale com 'sudo apt install jq')"
        return 1
    fi

    log_debug "Ambiente validado - recursos disponíveis"
    return 0
}
