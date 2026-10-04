#!/bin/bash
# ==========================================
# MapsProveFiber - Docker Production Deployment Script
# Version: 2.1.0
# 
# Uso:
#   sudo ./scripts/deploy-docker.sh [comando]
#
# Comandos:
#   install   - Instalação completa (primeira vez)
#   update    - Atualizar aplicação (pull + rebuild)
#   start     - Iniciar containers
#   stop      - Parar containers
#   restart   - Reiniciar containers
#   logs      - Ver logs em tempo real
#   status    - Status dos containers
#   backup    - Criar backup do banco de dados
#   restore   - Restaurar backup
#   ssl       - Configurar certificado SSL
#   shell     - Abrir shell no container Django
# ==========================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configurações
PROJECT_DIR="/opt/mapsprovefiber"
DOCKER_COMPOSE_FILE="docker/docker-compose.prod.yml"
ENV_FILE=".env.production"

# ==========================================
# Funções Auxiliares
# ==========================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "Este script deve ser executado como root (use sudo)"
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker não está instalado. Instale: https://docs.docker.com/engine/install/"
    fi

    if ! command -v docker compose &> /dev/null; then
        log_error "Docker Compose não está instalado. Instale: https://docs.docker.com/compose/install/"
    fi

    log_success "Docker e Docker Compose encontrados"
}

check_env_file() {
    if [[ ! -f "$PROJECT_DIR/$ENV_FILE" ]]; then
        log_error "Arquivo $ENV_FILE não encontrado em $PROJECT_DIR"
    fi
}

# ==========================================
# Funções de Deploy
# ==========================================

install_dependencies() {
    log_info "Instalando dependências do sistema..."
    
    apt update
    apt install -y \
        curl \
        git \
        certbot \
        python3-certbot-nginx
    
    # Instalar Docker se não existir
    if ! command -v docker &> /dev/null; then
        log_info "Instalando Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        systemctl enable docker
        systemctl start docker
    fi

    log_success "Dependências instaladas"
}

clone_repository() {
    log_info "Clonando repositório..."

    if [[ ! -d "$PROJECT_DIR" ]]; then
        mkdir -p "$PROJECT_DIR"
        git clone https://github.com/kaled182/provemaps_beta.git "$PROJECT_DIR"
        cd "$PROJECT_DIR"
        git checkout main  # ou tag específica
    else
        log_warning "Diretório $PROJECT_DIR já existe"
        cd "$PROJECT_DIR"
        git pull origin main
    fi

    log_success "Repositório clonado/atualizado"
}

create_env_file() {
    log_info "Configurando arquivo .env.production..."

    if [[ -f "$PROJECT_DIR/$ENV_FILE" ]]; then
        log_warning "Arquivo $ENV_FILE já existe. Pulando..."
        return
    fi

    # Gerar secrets
    DJANGO_SECRET=$(python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
    FERNET_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    DB_PASSWORD=$(openssl rand -base64 32)

    read -p "Domínio (ex: maps.example.com): " DOMAIN
    read -p "Email para SSL (Let's Encrypt): " EMAIL
    read -p "Zabbix URL: " ZABBIX_URL
    read -p "Zabbix API Token (ou deixe em branco): " ZABBIX_TOKEN
    read -p "Google Maps API Key: " MAPS_KEY

    cat > "$PROJECT_DIR/$ENV_FILE" << EOF
# Django Configuration
SECRET_KEY=${DJANGO_SECRET}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}
DJANGO_SETTINGS_MODULE=settings.prod

# Database
DB_ENGINE=postgresql
DB_HOST=postgres
DB_PORT=5432
DB_NAME=mapsprovefiber
DB_USER=mapsprovefiber
DB_PASSWORD=${DB_PASSWORD}

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000

# Fernet Encryption
FERNET_KEY=${FERNET_KEY}

# Zabbix
ZABBIX_URL=${ZABBIX_URL}
ZABBIX_API_TOKEN=${ZABBIX_TOKEN}

# Google Maps
GOOGLE_MAPS_API_KEY=${MAPS_KEY}

# Email (opcional - configure se necessário)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Sentry (opcional)
SENTRY_DSN=

# Domain
DOMAIN_NAME=${DOMAIN}
EOF

    chmod 600 "$PROJECT_DIR/$ENV_FILE"
    log_success "Arquivo $ENV_FILE criado"
}

setup_ssl() {
    log_info "Configurando certificado SSL com Let's Encrypt..."

    source "$PROJECT_DIR/$ENV_FILE"

    if [[ -z "$DOMAIN_NAME" ]]; then
        log_error "DOMAIN_NAME não definido no $ENV_FILE"
    fi

    # Criar diretório SSL
    mkdir -p "$PROJECT_DIR/docker/nginx/ssl"

    # Obter certificado
    certbot certonly --standalone \
        --preferred-challenges http \
        -d "$DOMAIN_NAME" \
        -d "www.$DOMAIN_NAME" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive

    # Copiar certificados para volume Docker
    cp /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem "$PROJECT_DIR/docker/nginx/ssl/"
    cp /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem "$PROJECT_DIR/docker/nginx/ssl/"
    cp /etc/letsencrypt/live/$DOMAIN_NAME/chain.pem "$PROJECT_DIR/docker/nginx/ssl/"

    # Configurar renovação automática
    echo "0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN_NAME/*.pem $PROJECT_DIR/docker/nginx/ssl/ && docker compose -f $PROJECT_DIR/$DOCKER_COMPOSE_FILE restart nginx" | crontab -

    log_success "SSL configurado. Renovação automática agendada às 3h"
}

build_frontend() {
    log_info "Building frontend Vue 3..."

    cd "$PROJECT_DIR/frontend"

    # Instalar Node.js se não existir
    if ! command -v node &> /dev/null; then
        log_info "Instalando Node.js 18..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
        apt install -y nodejs
    fi

    npm install
    npm run build

    log_success "Frontend built em frontend/dist/"
}

docker_build() {
    log_info "Building imagens Docker..."

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" build --no-cache

    log_success "Imagens Docker criadas"
}

docker_up() {
    log_info "Iniciando containers Docker..."

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" up -d

    log_success "Containers iniciados"
}

docker_down() {
    log_info "Parando containers Docker..."

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" down

    log_success "Containers parados"
}

docker_restart() {
    log_info "Reiniciando containers..."

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" restart

    log_success "Containers reiniciados"
}

docker_logs() {
    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" logs -f "$@"
}

docker_status() {
    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" ps
}

run_migrations() {
    log_info "Executando migrações Django..."

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" exec web python manage.py migrate

    log_success "Migrações executadas"
}

collect_static() {
    log_info "Coletando arquivos estáticos..."

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" exec web python manage.py collectstatic --noinput

    log_success "Arquivos estáticos coletados"
}

create_superuser() {
    log_info "Criando superusuário Django..."

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" exec web python manage.py createsuperuser

    log_success "Superusuário criado"
}

backup_database() {
    log_info "Criando backup do banco de dados..."

    BACKUP_DIR="$PROJECT_DIR/backups"
    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql.gz"

    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres pg_dump -U mapsprovefiber mapsprovefiber | gzip > "$BACKUP_FILE"

    log_success "Backup criado: $BACKUP_FILE"
}

restore_database() {
    if [[ -z "$1" ]]; then
        log_error "Especifique o arquivo de backup: ./deploy-docker.sh restore /path/to/backup.sql.gz"
    fi

    log_warning "ATENÇÃO: Isso irá sobrescrever o banco de dados atual!"
    read -p "Continuar? (y/N): " confirm
    
    if [[ "$confirm" != "y" ]]; then
        log_info "Restore cancelado"
        exit 0
    fi

    log_info "Restaurando banco de dados..."

    cd "$PROJECT_DIR"
    gunzip -c "$1" | docker compose -f "$DOCKER_COMPOSE_FILE" exec -T postgres psql -U mapsprovefiber mapsprovefiber

    log_success "Banco de dados restaurado"
}

open_shell() {
    cd "$PROJECT_DIR"
    docker compose -f "$DOCKER_COMPOSE_FILE" exec web bash
}

# ==========================================
# Comandos Principais
# ==========================================

cmd_install() {
    log_info "=== Instalação Completa do MapsProveFiber ==="
    
    check_root
    install_dependencies
    check_docker
    clone_repository
    create_env_file
    build_frontend
    docker_build
    docker_up
    
    sleep 10  # Aguardar containers iniciarem
    
    run_migrations
    collect_static
    
    log_info "Configurar SSL? (requer domínio apontando para este servidor)"
    read -p "Configurar SSL agora? (y/N): " ssl_confirm
    
    if [[ "$ssl_confirm" == "y" ]]; then
        setup_ssl
        docker_restart
    fi
    
    log_success "=== Instalação Completa! ==="
    log_info "Acesse: https://$DOMAIN_NAME"
    log_info "Para criar superusuário: sudo ./scripts/deploy-docker.sh createsuperuser"
}

cmd_update() {
    log_info "=== Atualizando MapsProveFiber ==="
    
    check_root
    check_docker
    check_env_file
    
    clone_repository  # git pull
    build_frontend
    docker_build
    docker_down
    docker_up
    
    sleep 10
    
    run_migrations
    collect_static
    
    log_success "=== Atualização Completa! ==="
}

# ==========================================
# Main
# ==========================================

case "${1:-}" in
    install)
        cmd_install
        ;;
    update)
        cmd_update
        ;;
    start)
        docker_up
        ;;
    stop)
        docker_down
        ;;
    restart)
        docker_restart
        ;;
    logs)
        shift
        docker_logs "$@"
        ;;
    status)
        docker_status
        ;;
    backup)
        backup_database
        ;;
    restore)
        restore_database "$2"
        ;;
    ssl)
        setup_ssl
        ;;
    migrate)
        run_migrations
        ;;
    collectstatic)
        collect_static
        ;;
    createsuperuser)
        create_superuser
        ;;
    shell)
        open_shell
        ;;
    *)
        echo "Uso: $0 {install|update|start|stop|restart|logs|status|backup|restore|ssl|migrate|collectstatic|createsuperuser|shell}"
        echo ""
        echo "Comandos:"
        echo "  install          - Instalação completa (primeira vez)"
        echo "  update           - Atualizar aplicação (pull + rebuild)"
        echo "  start            - Iniciar containers"
        echo "  stop             - Parar containers"
        echo "  restart          - Reiniciar containers"
        echo "  logs [serviço]   - Ver logs em tempo real"
        echo "  status           - Status dos containers"
        echo "  backup           - Criar backup do banco de dados"
        echo "  restore <file>   - Restaurar backup"
        echo "  ssl              - Configurar certificado SSL"
        echo "  migrate          - Executar migrações Django"
        echo "  collectstatic    - Coletar arquivos estáticos"
        echo "  createsuperuser  - Criar superusuário Django"
        echo "  shell            - Abrir shell no container Django"
        exit 1
        ;;
esac
