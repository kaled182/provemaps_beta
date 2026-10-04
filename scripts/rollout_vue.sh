#!/bin/bash
# Rollout Gradual do Vue 3 Dashboard (versão Linux/Bash)
# Uso: ./rollout_vue.sh <percentage> [monitor_time]
# Exemplo: ./rollout_vue.sh 10
# Exemplo: ./rollout_vue.sh 100 60  (100% rollout, monitorar por 60s)

set -e

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✅ $1${NC}"; }
info() { echo -e "${CYAN}ℹ️  $1${NC}"; }
warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
failure() { echo -e "${RED}❌ $1${NC}"; }

# Parse arguments
PERCENTAGE=${1:-}
MONITOR_TIME=${2:-30}

if [ -z "$PERCENTAGE" ]; then
    failure "Erro: Percentual não fornecido"
    echo "Uso: $0 <percentage> [monitor_time]"
    echo "Exemplo: $0 10"
    echo "Exemplo: $0 100 60"
    exit 1
fi

if [ "$PERCENTAGE" -lt 0 ] || [ "$PERCENTAGE" -gt 100 ]; then
    failure "Erro: Percentual deve estar entre 0-100"
    exit 1
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"

info "Vue Dashboard Rollout Script"
info "============================="
info "Percentual alvo: $PERCENTAGE%"
info "Diretório: $DOCKER_DIR"
echo ""

# 1. Validar ambiente Docker
info "[1/6] Validando ambiente Docker..."

if [ ! -f "$COMPOSE_FILE" ]; then
    failure "docker-compose.yml não encontrado em $DOCKER_DIR"
    exit 1
fi

cd "$DOCKER_DIR"

if ! docker compose ps --quiet > /dev/null 2>&1; then
    failure "Nenhum container rodando. Execute 'docker compose up -d' primeiro"
    exit 1
fi
success "Docker Compose está rodando"

# 2. Atualizar variável de ambiente
info "[2/6] Atualizando variável de ambiente..."

# Criar .env se não existe
if [ ! -f "$ENV_FILE" ]; then
    info "Criando arquivo .env..."
    touch "$ENV_FILE"
fi

# Backup do .env
cp "$ENV_FILE" "$ENV_FILE.bak"

# Atualizar ou adicionar variáveis
USE_VUE_VALUE="false"
if [ "$PERCENTAGE" -gt 0 ]; then
    USE_VUE_VALUE="true"
fi

# Remove linhas antigas e adiciona novas
grep -v "^VUE_DASHBOARD_ROLLOUT_PERCENTAGE=" "$ENV_FILE" | \
grep -v "^USE_VUE_DASHBOARD=" > "$ENV_FILE.tmp" || true

echo "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$PERCENTAGE" >> "$ENV_FILE.tmp"
echo "USE_VUE_DASHBOARD=$USE_VUE_VALUE" >> "$ENV_FILE.tmp"

mv "$ENV_FILE.tmp" "$ENV_FILE"

info "  Atualizado: VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$PERCENTAGE"
info "  Atualizado: USE_VUE_DASHBOARD=$USE_VUE_VALUE"
success "Arquivo .env atualizado"

# 3. Reiniciar serviço web
info "[3/6] Reiniciando serviço web..."

if docker compose restart web > /dev/null 2>&1; then
    success "Serviço web reiniciado"
else
    failure "Erro ao reiniciar web"
    mv "$ENV_FILE.bak" "$ENV_FILE"
    exit 1
fi

info "  Aguardando serviço iniciar (10s)..."
sleep 10

# 4. Health Check
info "[4/6] Verificando health check..."

MAX_ATTEMPTS=6
ATTEMPT=0
HEALTHY=false

while [ $ATTEMPT -lt $MAX_ATTEMPTS ] && [ "$HEALTHY" = false ]; do
    ATTEMPT=$((ATTEMPT + 1))
    
    if curl -s -f -o /dev/null -w "%{http_code}" http://localhost:8000/ready | grep -q "200"; then
        HEALTHY=true
        success "Serviço web está saudável (HTTP 200)"
    else
        info "  Tentativa $ATTEMPT/$MAX_ATTEMPTS - Aguardando..."
        sleep 5
    fi
done

if [ "$HEALTHY" = false ]; then
    failure "Serviço não passou no health check após $MAX_ATTEMPTS tentativas"
    warning "Verifique logs: docker compose logs web"
    mv "$ENV_FILE.bak" "$ENV_FILE"
    exit 1
fi

# 5. Validar configuração aplicada
info "[5/6] Validando configuração no container..."

ROLLOUT_VALUE=$(docker compose exec -T web env | grep "VUE_DASHBOARD_ROLLOUT_PERCENTAGE" | cut -d'=' -f2 | tr -d '\r\n' || echo "")
USE_VUE_VALUE_CHECK=$(docker compose exec -T web env | grep "^USE_VUE_DASHBOARD=" | cut -d'=' -f2 | tr -d '\r\n' || echo "")

if [ "$ROLLOUT_VALUE" = "$PERCENTAGE" ]; then
    success "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$ROLLOUT_VALUE (esperado: $PERCENTAGE) ✓"
else
    failure "VUE_DASHBOARD_ROLLOUT_PERCENTAGE=$ROLLOUT_VALUE (esperado: $PERCENTAGE) ✗"
    warning "Configuração não aplicada corretamente. Tente reiniciar manualmente."
fi

EXPECTED_USE_VUE="False"
if [ "$PERCENTAGE" -gt 0 ]; then
    EXPECTED_USE_VUE="True"
fi
info "USE_VUE_DASHBOARD=$USE_VUE_VALUE_CHECK (esperado: $EXPECTED_USE_VUE)"

# 6. Monitorar logs
info "[6/6] Monitorando logs por ${MONITOR_TIME}s..."
info "Pressione Ctrl+C para parar monitoramento antecipadamente"
info "----------------------------------------"

timeout ${MONITOR_TIME}s docker compose logs --tail=20 -f web 2>&1 || true

# Resumo Final
echo ""
info "========================================"
success "Rollout concluído com sucesso!"
info "========================================"
echo ""
info "Configuração aplicada:"
info "  VUE_DASHBOARD_ROLLOUT_PERCENTAGE: $PERCENTAGE%"
echo ""

if [ "$PERCENTAGE" -eq 0 ]; then
    warning "⚠️  Dashboard Vue DESABILITADO (100% legacy)"
    info "Todos os usuários verão o dashboard legado"
elif [ "$PERCENTAGE" -eq 100 ]; then
    success "🎉 Dashboard Vue ATIVADO para 100% dos usuários!"
    info "Todos os usuários verão o dashboard Vue 3"
else
    info "📊 Rollout canary: ~$PERCENTAGE% dos usuários verão Vue"
    info "~$((100 - PERCENTAGE))% dos usuários verão legacy dashboard"
fi

echo ""
info "Próximos passos:"
info "  1. Monitorar logs: docker compose logs -f web"
info "  2. Verificar erros: docker compose logs web | grep ERROR"
info "  3. Testar dashboard: http://localhost:8000/monitoring/backbone/"
echo ""

if [ "$PERCENTAGE" -gt 0 ] && [ "$PERCENTAGE" -lt 100 ]; then
    info "Rollout gradual sugerido:"
    if [ "$PERCENTAGE" -lt 10 ]; then
        info "  Próximo: ./scripts/rollout_vue.sh 10"
    elif [ "$PERCENTAGE" -lt 25 ]; then
        info "  Próximo: ./scripts/rollout_vue.sh 25"
    elif [ "$PERCENTAGE" -lt 50 ]; then
        info "  Próximo: ./scripts/rollout_vue.sh 50"
    else
        info "  Próximo: ./scripts/rollout_vue.sh 100"
    fi
fi

if [ "$PERCENTAGE" -eq 100 ]; then
    info "Após 24-48h sem problemas, considere:"
    info "  - Remover código legacy (backend/static/dashboard.js)"
    info "  - Deletar template legado (maps_view/templates/dashboard.html)"
    info "  - Commit: 'feat: Remove legacy dashboard (-2,000 lines)'"
fi

# Cleanup backup
rm -f "$ENV_FILE.bak"

echo ""
success "Script finalizado!"
