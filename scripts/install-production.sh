#!/usr/bin/env bash
#
# MapsProveFiber Production Installation Script
# Automated installation for Debian 11/12 and Ubuntu 20.04/22.04/24.04
#
# Usage:
#   wget https://raw.githubusercontent.com/kaled182/provemaps_beta/main/scripts/install-production.sh
#   chmod +x install-production.sh
#   sudo ./install-production.sh
#
# Version: 2.1.0
# Date: 2026-02-07
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
INSTALL_DIR="/opt/mapsprovefiber"
APP_USER="mapsprovefiber"
REPO_URL="https://github.com/kaled182/provemaps_beta.git"
REPO_BRANCH="main"
PYTHON_VERSION="3.12"
NODE_VERSION="18"
POSTGRESQL_VERSION="15"

# Functions
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
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        
        if [[ "$OS" == "debian" && ("$OS_VERSION" == "11" || "$OS_VERSION" == "12") ]]; then
            log_success "Detected Debian $OS_VERSION"
        elif [[ "$OS" == "ubuntu" && ("$OS_VERSION" == "20.04" || "$OS_VERSION" == "22.04" || "$OS_VERSION" == "24.04") ]]; then
            log_success "Detected Ubuntu $OS_VERSION"
        else
            log_error "Unsupported OS: $OS $OS_VERSION"
            log_error "This script supports Debian 11/12 and Ubuntu 20.04/22.04/24.04"
            exit 1
        fi
    else
        log_error "Cannot detect OS. /etc/os-release not found"
        exit 1
    fi
}

prompt_config() {
    log_info "=== Configuration ==="
    echo ""
    
    # Domain
    read -p "Enter domain name (e.g., maps.example.com): " DOMAIN
    if [[ -z "$DOMAIN" ]]; then
        log_error "Domain is required"
        exit 1
    fi
    
    # Email for SSL
    read -p "Enter email for SSL certificate: " SSL_EMAIL
    if [[ -z "$SSL_EMAIL" ]]; then
        log_error "Email is required"
        exit 1
    fi
    
    # PostgreSQL password
    read -sp "Enter PostgreSQL password: " DB_PASSWORD
    echo ""
    if [[ -z "$DB_PASSWORD" ]]; then
        log_error "Password is required"
        exit 1
    fi
    
    # Redis password (optional)
    read -sp "Enter Redis password (leave empty for no password): " REDIS_PASSWORD
    echo ""
    
    # Install Let's Encrypt
    read -p "Install Let's Encrypt SSL certificate? (Y/n): " INSTALL_SSL
    INSTALL_SSL=${INSTALL_SSL:-Y}
    
    echo ""
    log_success "Configuration saved"
    echo ""
}

update_system() {
    log_info "Updating system packages..."
    apt update
    apt upgrade -y
    log_success "System updated"
}

install_dependencies() {
    log_info "Installing dependencies..."
    
    # Base tools
    apt install -y \
        curl \
        wget \
        git \
        build-essential \
        pkg-config \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release
    
    # Python
    log_info "Installing Python ${PYTHON_VERSION}..."
    apt install -y \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-venv \
        python${PYTHON_VERSION}-dev \
        python3-pip
    
    # PostgreSQL + PostGIS
    log_info "Installing PostgreSQL ${POSTGRESQL_VERSION} + PostGIS..."
    apt install -y \
        postgresql-${POSTGRESQL_VERSION} \
        postgresql-${POSTGRESQL_VERSION}-postgis-3 \
        postgresql-client-${POSTGRESQL_VERSION} \
        libpq-dev
    
    # Redis
    log_info "Installing Redis..."
    apt install -y redis-server
    
    # Nginx
    log_info "Installing Nginx..."
    apt install -y nginx
    
    # GDAL
    log_info "Installing GDAL..."
    apt install -y \
        gdal-bin \
        libgdal-dev \
        python3-gdal
    
    # Node.js
    log_info "Installing Node.js ${NODE_VERSION}..."
    curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash -
    apt install -y nodejs
    
    # Certbot (if SSL requested)
    if [[ "$INSTALL_SSL" =~ ^[Yy]$ ]]; then
        log_info "Installing Certbot..."
        apt install -y certbot python3-certbot-nginx
    fi
    
    log_success "All dependencies installed"
}

configure_postgresql() {
    log_info "Configuring PostgreSQL..."
    
    # Start PostgreSQL
    systemctl enable postgresql
    systemctl start postgresql
    
    # Create database and user
    sudo -u postgres psql << EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${APP_USER}') THEN
        CREATE USER ${APP_USER} WITH PASSWORD '${DB_PASSWORD}';
    END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${APP_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${APP_USER}')\gexec

\c ${APP_USER}

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

GRANT ALL PRIVILEGES ON DATABASE ${APP_USER} TO ${APP_USER};
GRANT ALL ON SCHEMA public TO ${APP_USER};
EOF
    
    # Configure pg_hba.conf
    PG_HBA_FILE="/etc/postgresql/${POSTGRESQL_VERSION}/main/pg_hba.conf"
    
    if ! grep -q "local.*${APP_USER}.*${APP_USER}.*md5" "$PG_HBA_FILE"; then
        echo "local   ${APP_USER}    ${APP_USER}                            md5" >> "$PG_HBA_FILE"
        systemctl restart postgresql
    fi
    
    log_success "PostgreSQL configured"
}

configure_redis() {
    log_info "Configuring Redis..."
    
    REDIS_CONF="/etc/redis/redis.conf"
    
    # Backup original config
    cp "$REDIS_CONF" "${REDIS_CONF}.backup"
    
    # Configure memory
    sed -i 's/^# maxmemory .*/maxmemory 2gb/' "$REDIS_CONF"
    sed -i 's/^# maxmemory-policy .*/maxmemory-policy allkeys-lru/' "$REDIS_CONF"
    
    # Bind to localhost only
    sed -i 's/^bind .*/bind 127.0.0.1/' "$REDIS_CONF"
    
    # Set password if provided
    if [[ -n "$REDIS_PASSWORD" ]]; then
        sed -i "s/^# requirepass .*/requirepass ${REDIS_PASSWORD}/" "$REDIS_CONF"
    fi
    
    # Enable and start
    systemctl enable redis-server
    systemctl restart redis-server
    
    log_success "Redis configured"
}

create_app_user() {
    log_info "Creating application user..."
    
    if ! id "$APP_USER" &>/dev/null; then
        useradd -r -s /bin/bash -m -d "$INSTALL_DIR" "$APP_USER"
        log_success "User $APP_USER created"
    else
        log_warning "User $APP_USER already exists"
    fi
    
    # Create directories
    mkdir -p "${INSTALL_DIR}"/{logs,media,staticfiles,backups}
    chown -R "${APP_USER}:${APP_USER}" "$INSTALL_DIR"
}

clone_repository() {
    log_info "Cloning repository..."
    
    if [[ -d "${INSTALL_DIR}/app" ]]; then
        log_warning "Application directory already exists, pulling latest changes..."
        cd "${INSTALL_DIR}/app"
        sudo -u "$APP_USER" git pull
    else
        sudo -u "$APP_USER" git clone "$REPO_URL" "${INSTALL_DIR}/app"
        cd "${INSTALL_DIR}/app"
        sudo -u "$APP_USER" git checkout "$REPO_BRANCH"
    fi
    
    log_success "Repository cloned"
}

setup_python_env() {
    log_info "Setting up Python environment..."
    
    cd "${INSTALL_DIR}/app"
    
    # Create virtualenv
    if [[ ! -d "venv" ]]; then
        sudo -u "$APP_USER" python${PYTHON_VERSION} -m venv venv
    fi
    
    # Install dependencies
    sudo -u "$APP_USER" bash << EOF
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt
EOF
    
    log_success "Python environment configured"
}

generate_secrets() {
    log_info "Generating secret keys..."
    
    # Generate SECRET_KEY
    SECRET_KEY=$(sudo -u "$APP_USER" bash -c "cd ${INSTALL_DIR}/app && source venv/bin/activate && python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\"")
    
    # Generate FERNET_KEY
    FERNET_KEY=$(sudo -u "$APP_USER" bash -c "cd ${INSTALL_DIR}/app && source venv/bin/activate && python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    
    log_success "Secret keys generated"
}

create_env_file() {
    log_info "Creating .env file..."
    
    ENV_FILE="${INSTALL_DIR}/app/.env"
    
    # Build REDIS_URL
    if [[ -n "$REDIS_PASSWORD" ]]; then
        REDIS_URL="redis://:${REDIS_PASSWORD}@localhost:6379/0"
    else
        REDIS_URL="redis://localhost:6379/0"
    fi
    
    sudo -u "$APP_USER" cat > "$ENV_FILE" << EOF
# Django Configuration
SECRET_KEY=${SECRET_KEY}
DEBUG=False
ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN}
DJANGO_SETTINGS_MODULE=settings.prod

# Database
DATABASE_ENGINE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=${APP_USER}
DATABASE_USER=${APP_USER}
DATABASE_PASSWORD=${DB_PASSWORD}

# Redis
REDIS_URL=${REDIS_URL}

# Celery
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}

# Fernet Encryption
FERNET_KEY=${FERNET_KEY}

# Logging
LOG_LEVEL=INFO

# Email (configure later in /setup_app/config/)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Static/Media
STATIC_ROOT=${INSTALL_DIR}/staticfiles
MEDIA_ROOT=${INSTALL_DIR}/media
EOF
    
    chmod 600 "$ENV_FILE"
    chown "${APP_USER}:${APP_USER}" "$ENV_FILE"
    
    log_success ".env file created"
}

run_migrations() {
    log_info "Running database migrations..."
    
    sudo -u "$APP_USER" bash << EOF
cd "${INSTALL_DIR}/app/backend"
source ../venv/bin/activate
python manage.py migrate --noinput
EOF
    
    log_success "Migrations completed"
}

collect_static() {
    log_info "Collecting static files..."
    
    sudo -u "$APP_USER" bash << EOF
cd "${INSTALL_DIR}/app/backend"
source ../venv/bin/activate
python manage.py collectstatic --noinput
EOF
    
    chown -R "${APP_USER}:www-data" "${INSTALL_DIR}/staticfiles"
    chmod -R 755 "${INSTALL_DIR}/staticfiles"
    
    log_success "Static files collected"
}

build_frontend() {
    log_info "Building frontend..."
    
    sudo -u "$APP_USER" bash << EOF
cd "${INSTALL_DIR}/app/frontend"
npm install
npm run build
EOF
    
    log_success "Frontend built"
}

configure_nginx() {
    log_info "Configuring Nginx..."
    
    NGINX_CONF="/etc/nginx/sites-available/mapsprovefiber"
    
    cat > "$NGINX_CONF" << 'EOF'
# Upstream Django
upstream django {
    server 127.0.0.1:8000;
}

# HTTP redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;
    
    # Allow Certbot
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    # SSL Configuration (Certbot will add certificates here)
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/mapsprovefiber_access.log;
    error_log /var/log/nginx/mapsprovefiber_error.log;

    # Client settings
    client_max_body_size 100M;

    # Frontend root
    root INSTALL_DIR_PLACEHOLDER/app/frontend/dist;
    index index.html;

    # Static files
    location /static/ {
        alias INSTALL_DIR_PLACEHOLDER/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias INSTALL_DIR_PLACEHOLDER/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # API
    location /api/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }

    # Admin
    location /admin/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Setup App
    location /setup_app/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSockets
    location /ws/ {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        proxy_read_timeout 86400;
    }

    # Frontend SPA
    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF
    
    # Replace placeholders
    sed -i "s|DOMAIN_PLACEHOLDER|${DOMAIN}|g" "$NGINX_CONF"
    sed -i "s|INSTALL_DIR_PLACEHOLDER|${INSTALL_DIR}|g" "$NGINX_CONF"
    
    # Enable site
    ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test config
    nginx -t
    
    # Reload Nginx
    systemctl reload nginx
    
    log_success "Nginx configured"
}

install_ssl() {
    if [[ "$INSTALL_SSL" =~ ^[Yy]$ ]]; then
        log_info "Installing SSL certificate..."
        
        certbot --nginx \
            -d "$DOMAIN" \
            -d "www.${DOMAIN}" \
            --non-interactive \
            --agree-tos \
            --email "$SSL_EMAIL" \
            --redirect
        
        log_success "SSL certificate installed"
    else
        log_warning "Skipping SSL installation (you can run 'certbot --nginx' later)"
    fi
}

create_systemd_services() {
    log_info "Creating systemd services..."
    
    # Django service
    cat > /etc/systemd/system/mapsprovefiber.service << EOF
[Unit]
Description=MapsProveFiber Django Application
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${INSTALL_DIR}/app/backend
Environment="PATH=${INSTALL_DIR}/app/venv/bin"
EnvironmentFile=${INSTALL_DIR}/app/.env

ExecStart=${INSTALL_DIR}/app/venv/bin/gunicorn \\
    --bind 127.0.0.1:8000 \\
    --workers 4 \\
    --worker-class uvicorn.workers.UvicornWorker \\
    --timeout 600 \\
    --access-logfile ${INSTALL_DIR}/logs/gunicorn-access.log \\
    --error-logfile ${INSTALL_DIR}/logs/gunicorn-error.log \\
    core.asgi:application

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Celery Worker service
    cat > /etc/systemd/system/mapsprovefiber-celery.service << EOF
[Unit]
Description=MapsProveFiber Celery Worker
After=network.target redis.service postgresql.service
Wants=redis.service

[Service]
Type=forking
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${INSTALL_DIR}/app/backend
Environment="PATH=${INSTALL_DIR}/app/venv/bin"
EnvironmentFile=${INSTALL_DIR}/app/.env

ExecStart=${INSTALL_DIR}/app/venv/bin/celery -A core worker \\
    --loglevel=info \\
    --logfile=${INSTALL_DIR}/logs/celery-worker.log \\
    --pidfile=/tmp/celery-worker.pid \\
    --detach

ExecStop=/bin/kill -s TERM \$MAINPID

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Celery Beat service
    cat > /etc/systemd/system/mapsprovefiber-celerybeat.service << EOF
[Unit]
Description=MapsProveFiber Celery Beat Scheduler
After=network.target redis.service
Wants=redis.service mapsprovefiber-celery.service

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${INSTALL_DIR}/app/backend
Environment="PATH=${INSTALL_DIR}/app/venv/bin"
EnvironmentFile=${INSTALL_DIR}/app/.env

ExecStart=${INSTALL_DIR}/app/venv/bin/celery -A core beat \\
    --loglevel=info \\
    --logfile=${INSTALL_DIR}/logs/celery-beat.log \\
    --pidfile=/tmp/celery-beat.pid

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    log_success "Systemd services created"
}

start_services() {
    log_info "Starting services..."
    
    # Enable services
    systemctl enable mapsprovefiber
    systemctl enable mapsprovefiber-celery
    systemctl enable mapsprovefiber-celerybeat
    
    # Start services
    systemctl start mapsprovefiber
    systemctl start mapsprovefiber-celery
    systemctl start mapsprovefiber-celerybeat
    
    # Check status
    sleep 3
    
    if systemctl is-active --quiet mapsprovefiber; then
        log_success "Django service started"
    else
        log_error "Django service failed to start"
        journalctl -u mapsprovefiber -n 20 --no-pager
    fi
    
    if systemctl is-active --quiet mapsprovefiber-celery; then
        log_success "Celery service started"
    else
        log_warning "Celery service may have issues"
    fi
}

print_summary() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                  Installation Complete!                         ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}📌 Installation Details:${NC}"
    echo -e "   Application: ${INSTALL_DIR}/app"
    echo -e "   Logs: ${INSTALL_DIR}/logs"
    echo -e "   Domain: https://${DOMAIN}"
    echo ""
    echo -e "${BLUE}🔧 Services Status:${NC}"
    echo -e "   Django:      $(systemctl is-active mapsprovefiber)"
    echo -e "   Celery:      $(systemctl is-active mapsprovefiber-celery)"
    echo -e "   Celery Beat: $(systemctl is-active mapsprovefiber-celerybeat)"
    echo -e "   PostgreSQL:  $(systemctl is-active postgresql)"
    echo -e "   Redis:       $(systemctl is-active redis)"
    echo -e "   Nginx:       $(systemctl is-active nginx)"
    echo ""
    echo -e "${YELLOW}⚠️  Next Steps:${NC}"
    echo -e "   1. Open https://${DOMAIN} in your browser"
    echo -e "   2. You will be redirected to First-Time Setup"
    echo -e "   3. Fill in Zabbix credentials, Google Maps API key, and license"
    echo -e "   4. Complete setup and access the dashboard"
    echo ""
    echo -e "${BLUE}📚 Documentation:${NC}"
    echo -e "   Installation Guide: ${INSTALL_DIR}/app/doc/getting-started/INSTALLATION_GUIDE.md"
    echo -e "   Testing Guide: ${INSTALL_DIR}/app/doc/testing/TESTING_GUIDE.md"
    echo ""
    echo -e "${BLUE}🔍 Useful Commands:${NC}"
    echo -e "   Check logs:    sudo journalctl -u mapsprovefiber -f"
    echo -e "   Restart app:   sudo systemctl restart mapsprovefiber"
    echo -e "   Check status:  sudo systemctl status mapsprovefiber"
    echo ""
    echo -e "${GREEN}Installation log saved to: /var/log/mapsprovefiber-install.log${NC}"
    echo ""
}

# Main installation flow
main() {
    echo ""
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        MapsProveFiber Production Installation v2.1.0            ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Pre-flight checks
    check_root
    check_os
    
    # Get configuration
    prompt_config
    
    # Installation steps
    update_system
    install_dependencies
    configure_postgresql
    configure_redis
    create_app_user
    clone_repository
    setup_python_env
    generate_secrets
    create_env_file
    run_migrations
    collect_static
    build_frontend
    configure_nginx
    install_ssl
    create_systemd_services
    start_services
    
    # Done!
    print_summary
}

# Log all output
exec > >(tee -a /var/log/mapsprovefiber-install.log)
exec 2>&1

# Run main function
main "$@"
