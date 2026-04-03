#!/usr/bin/env bash
# ===================================================
# 🧪 TESTE UNITÁRIO - monitor-alerts/main.sh (v5.7)
# ===================================================
# Testes para:
# 1. Parsing de argumentos
# 2. Validação de ambiente
# 3. Tratamento de erros
# 4. Fluxo principal
# ===================================================

set -eo pipefail

# --- Configuração ---
TEST_DIR="$(dirname "$(realpath "$0")")"
MAIN_SCRIPT="${TEST_DIR}/../main.sh"
TEMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TEMP_DIR"' EXIT

# --- Utilitários de Teste ---
setup() {
    # Cria ambiente de teste isolado
    export LOG_DIR="$TEMP_DIR/logs"
    mkdir -p "$LOG_DIR"
    echo '{"cpu":{"usage":10}}' > "$TEMP_DIR/valid.json"
    echo 'invalid' > "$TEMP_DIR/invalid.json"
}

assert() {
    local condition="$1"
    local message="$2"
    if ! eval "$condition"; then
        echo "❌ Falha: $message"
        return 1
    fi
    echo "✔ $message"
}

run_test() {
    local test_name="$1"
    local test_func="$2"
    echo "🔵 TESTE: $test_name"
    if $test_func; then
        echo "✅ Sucesso"
    else
        echo "❌ Falhou"
        return 1
    fi
}

# --- Casos de Teste ---

test_argument_parsing() {
    # Testa --debug
    "$MAIN_SCRIPT" --debug | grep -q "Modo debug ativado" || return 1
    # Testa --help
    "$MAIN_SCRIPT" --help | grep -q "Uso:" || return 1
    # Testa --dry-run
    "$MAIN_SCRIPT" --dry-run | grep -q "Modo simulação" || return 1
    # Testa argumento inválido
    "$MAIN_SCRIPT" --invalid-arg 2>&1 | grep -q "ignorado" || return 1
}

test_file_validation() {
    # Arquivo não existe
    "$MAIN_SCRIPT" --json /nonexistent.json 2>&1 | grep -q "não encontrado" || return 1
    # Arquivo inválido
    "$MAIN_SCRIPT" --json "$TEMP_DIR/invalid.json" 2>&1 | grep -q "JSON inválido" || return 1
    # Sem permissão
    chmod 000 "$TEMP_DIR/valid.json"
    "$MAIN_SCRIPT" --json "$TEMP_DIR/valid.json" 2>&1 | grep -q "sem permissão" || return 1
    chmod 644 "$TEMP_DIR/valid.json"
}

test_success_flow() {
    local output
    output="$("$MAIN_SCRIPT" --json "$TEMP_DIR/valid.json")"
    echo "$output" | grep -q "Processamento concluído" || return 1
}

test_timeout_handling() {
    # Simula arquivo grande (lerá indefinidamente de /dev/zero)
    timeout 3 "$MAIN_SCRIPT" --json /dev/zero && return 1
    return 0
}

# --- Execução dos Testes ---
main() {
    setup
    
    declare -a tests=(
        "test_argument_parsing Parsing de argumentos"
        "test_file_validation Validação de arquivos"
        "test_success_flow Fluxo bem-sucedido"
        "test_timeout_handling Tratamento de timeout"
    )
    
    local failures=0
    
    for test_case in "${tests[@]}"; do
        IFS=' ' read -r func desc <<< "$test_case"
        if ! run_test "$desc" "$func"; then
            ((failures++))
        fi
    done
    
    if (( failures > 0 )); then
        echo "🔴 $failures testes falharam"
        exit 1
    else
        echo "🟢 Todos os testes passaram"
        exit 0
    fi
}

main "$@"
