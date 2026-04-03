# 🚀 Guia Completo de Instalação - MapsProveFiber v2.1.0

**Data**: 7 de Fevereiro de 2026  
**Versão**: 2.1.0  
**Plataformas**: Debian 11/12, Ubuntu 20.04/22.04/24.04

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Pré-Requisitos](#pré-requisitos)
3. [Instalação Rápida (Script Automatizado)](#instalação-rápida)
4. [Instalação Manual Passo a Passo](#instalação-manual)
5. [Configuração Pós-Instalação](#configuração-pós-instalação)
6. [First-Time Setup](#first-time-setup)
7. [Validação da Instalação](#validação)
8. [Troubleshooting](#troubleshooting)
9. [Próximos Passos](#próximos-passos)

---

## 🎯 Visão Geral

MapsProveFiber é uma plataforma Django 5 para gestão de infraestrutura de fibra óptica com monitoramento Zabbix em tempo real e planejamento geoespacial de rotas.

### Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                      Usuário                            │
└─────────────────┬──────────────────────────────────────┘
                  │ HTTPS (443)
┌─────────────────▼──────────────────────────────────────┐
│              Nginx (Reverse Proxy)                      │
│  - SSL/TLS Termination                                  │
│  - Static/Media Files                                   │
│  - Load Balancing                                       │
└─────────────────┬──────────────────────────────────────┘
                  │ HTTP (8000)
┌─────────────────▼──────────────────────────────────────┐
│         Django + Gunicorn (ASGI/WSGI)                   │
│  - REST API (DRF)                                       │
│  - WebSockets (Channels)                                │
│  - Business Logic                                       │
└─────┬──────────┬──────────┬──────────┬────────────────┘
      │          │          │          │
      ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
│PostgreSQL│ │ Redis  │ │ Celery │ │  Zabbix    │
│ +PostGIS │ │ Cache  │ │ Worker │ │ Monitoring │
└──────────┘ └────────┘ └────────┘ └────────────┘
```

### Componentes

| Componente | Versão | Descrição |
|------------|--------|-----------|
| **Django** | 5.0+ | Framework web principal |
| **PostgreSQL** | 13-16 | Banco de dados relacional |
| **PostGIS** | 3.1+ | Extensão geoespacial |
| **Redis** | 6+ | Cache e message broker |
| **Celery** | 5.3+ | Tasks assíncronas |
| **Nginx** | 1.18+ | Reverse proxy |
| **Gunicorn** | 21+ | WSGI/ASGI server |
| **Node.js** | 18+ | Build do frontend Vue 3 |

---

## ⚙️ Pré-Requisitos

### Hardware Mínimo

| Recurso | Desenvolvimento | Produção (Pequeno) | Produção (Médio) |
|---------|----------------|-------------------|------------------|
| **CPU** | 2 cores | 4 cores | 8 cores |
| **RAM** | 4 GB | 8 GB | 16 GB |
| **Disco** | 20 GB SSD | 100 GB SSD | 500 GB SSD |
| **Rede** | 100 Mbps | 1 Gbps | 1 Gbps |

### Sistema Operacional

- **Debian**: 11 (Bullseye) ou 12 (Bookworm)
- **Ubuntu**: 20.04 LTS, 22.04 LTS, ou 24.04 LTS
- **Arquitetura**: x86_64 (AMD64)

### Portas Necessárias

| Porta | Serviço | Acesso |
|-------|---------|--------|
| **80** | HTTP (redireciona para 443) | Público |
| **443** | HTTPS (Nginx) | Público |
| **8000** | Django (desenvolvimento) | Localhost |
| **5432** | PostgreSQL | Localhost |
| **6379** | Redis | Localhost |

### Credenciais Necessárias

Prepare as seguintes informações ANTES de instalar:

- ✅ **Zabbix**:
  - URL do servidor Zabbix (ex: `https://zabbix.example.com`)
  - API Token OU (usuário + senha)
  
- ✅ **Google Maps**:
  - API Key com Maps JavaScript API, Geocoding API, Directions API habilitadas
  
- ✅ **Domínio**:
  - Nome de domínio (ex: `maps.example.com`)
  - Certificado SSL (Let's Encrypt recomendado)

- ✅ **Email** (opcional mas recomendado):
  - Servidor SMTP
  - Usuário e senha
  
- ✅ **Licença**:
  - Chave de licença do produto (fornecida pelo fornecedor)

---

## 🚀 Instalação Rápida

### Opção 1: Script Automatizado (Recomendado)

```bash
# 1. Baixar o script de instalação
wget https://raw.githubusercontent.com/kaled182/provemaps_beta/main/scripts/install-production.sh

# 2. Tornar executável
chmod +x install-production.sh

# 3. Executar como root
sudo ./install-production.sh

# O script irá:
# - Instalar todas as dependências
# - Configurar PostgreSQL + PostGIS
# - Configurar Redis
# - Instalar e configurar Nginx
# - Configurar SSL com Let's Encrypt
# - Criar usuário de sistema
# - Configurar serviços systemd
# - Executar migrações Django
# - Coletar arquivos estáticos
```

**Duração estimada**: 10-15 minutos

### Durante a Instalação

O script irá perguntar:

1. **Domínio**: `maps.example.com`
2. **Email para SSL**: `admin@example.com`
3. **Senha do PostgreSQL**: (crie uma senha forte)
4. **Instalar Let's Encrypt**: `Y` (recomendado)

### Após a Instalação Automática

```bash
# Verificar status dos serviços
sudo systemctl status mapsprovefiber
sudo systemctl status mapsprovefiber-celery
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis

# Acessar o sistema
# Abra https://maps.example.com no navegador
# Você será redirecionado para /setup_app/first_time/
```

---

## 🛠️ Instalação Manual

Para ter controle total do processo ou customizar a instalação.

### Passo 1: Atualizar Sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### Passo 2: Instalar Dependências Base

```bash
# Python e ferramentas
sudo apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip \
    build-essential \
    pkg-config \
    git \
    curl \
    wget

# PostgreSQL + PostGIS
sudo apt install -y \
    postgresql-15 \
    postgresql-15-postgis-3 \
    postgresql-client-15 \
    libpq-dev

# Redis
sudo apt install -y redis-server

# Node.js (para build do frontend)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Nginx
sudo apt install -y nginx

# GDAL (bibliotecas geoespaciais)
sudo apt install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal

# Certbot (Let's Encrypt)
sudo apt install -y certbot python3-certbot-nginx
```

### Passo 3: Configurar PostgreSQL

```bash
# Iniciar PostgreSQL
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Criar usuário e banco de dados
sudo -u postgres psql << EOF
CREATE USER mapsprovefiber WITH PASSWORD 'SUA_SENHA_FORTE_AQUI';
CREATE DATABASE mapsprovefiber OWNER mapsprovefiber;
\c mapsprovefiber
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
GRANT ALL PRIVILEGES ON DATABASE mapsprovefiber TO mapsprovefiber;
GRANT ALL ON SCHEMA public TO mapsprovefiber;
EOF

# Configurar acesso (editar pg_hba.conf)
sudo nano /etc/postgresql/15/main/pg_hba.conf
# Adicionar:
# local   mapsprovefiber    mapsprovefiber                            md5

# Reiniciar PostgreSQL
sudo systemctl restart postgresql
```

### Passo 4: Configurar Redis

```bash
# Editar configuração
sudo nano /etc/redis/redis.conf

# Configurações recomendadas:
# maxmemory 2gb
# maxmemory-policy allkeys-lru
# bind 127.0.0.1
# requirepass SUA_SENHA_REDIS

# Reiniciar Redis
sudo systemctl enable redis-server
sudo systemctl restart redis-server
```

### Passo 5: Criar Usuário de Sistema

```bash
# Criar usuário sem shell
sudo useradd -r -s /bin/bash -m -d /opt/mapsprovefiber mapsprovefiber

# Criar diretórios
sudo mkdir -p /opt/mapsprovefiber/{logs,media,staticfiles}
sudo chown -R mapsprovefiber:mapsprovefiber /opt/mapsprovefiber
```

### Passo 6: Clonar Repositório

```bash
# Como usuário mapsprovefiber
sudo -u mapsprovefiber bash
cd /opt/mapsprovefiber

# Clonar repositório
git clone https://github.com/kaled182/provemaps_beta.git app
cd app

# Checkout da branch de produção
git checkout main  # ou tag específica: git checkout v2.1.0
```

### Passo 7: Configurar Ambiente Python

```bash
# Criar virtualenv
python3.12 -m venv venv
source venv/bin/activate

# Atualizar pip
pip install --upgrade pip setuptools wheel

# Instalar dependências
pip install -r backend/requirements.txt
```

### Passo 8: Configurar Variáveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar .env
nano .env
```

**Conteúdo mínimo do .env**:

```bash
# Django
SECRET_KEY="GERAR_CHAVE_ALEATORIA_AQUI"  # python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=False
ALLOWED_HOSTS=maps.example.com,www.maps.example.com
DJANGO_SETTINGS_MODULE=settings.prod

# Database
DATABASE_ENGINE=postgresql
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=mapsprovefiber
DATABASE_USER=mapsprovefiber
DATABASE_PASSWORD=SUA_SENHA_POSTGRESQL

# Redis
REDIS_URL=redis://localhost:6379/0
# REDIS_PASSWORD=SUA_SENHA_REDIS  # se configurou senha

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# Fernet (para encriptação de credenciais)
FERNET_KEY="GERAR_CHAVE_FERNET_AQUI"  # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Email (opcional)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seu-email@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-ou-app-password

# Logging
LOG_LEVEL=INFO
```

### Passo 9: Executar Migrações

```bash
# Ativar virtualenv se não estiver ativo
source venv/bin/activate

# Executar migrações
cd backend
python manage.py migrate

# Criar superusuário
python manage.py createsuperuser
# Username: admin
# Email: admin@example.com
# Password: ********
```

### Passo 10: Coletar Arquivos Estáticos

```bash
# Coletar static files
python manage.py collectstatic --noinput

# Permissões corretas
sudo chown -R mapsprovefiber:www-data /opt/mapsprovefiber/staticfiles
sudo chmod -R 755 /opt/mapsprovefiber/staticfiles
```

### Passo 11: Build do Frontend

```bash
# Voltar para raiz do projeto
cd /opt/mapsprovefiber/app/frontend

# Instalar dependências
npm install

# Build de produção
npm run build

# Arquivos de build estarão em dist/
# Nginx irá servir esses arquivos
```

### Passo 12: Configurar Nginx

```bash
# Criar configuração do site
sudo nano /etc/nginx/sites-available/mapsprovefiber
```

**Conteúdo do arquivo**:

```nginx
# Upstream para Django
upstream django {
    server 127.0.0.1:8000;
}

# Redirecionar HTTP para HTTPS
server {
    listen 80;
    server_name maps.example.com www.maps.example.com;
    return 301 https://$host$request_uri;
}

# Servidor HTTPS principal
server {
    listen 443 ssl http2;
    server_name maps.example.com www.maps.example.com;

    # SSL Certificates (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/maps.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/maps.example.com/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/maps.example.com/chain.pem;

    # SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logs
    access_log /var/log/nginx/mapsprovefiber_access.log;
    error_log /var/log/nginx/mapsprovefiber_error.log;

    # Client Max Body Size (para uploads)
    client_max_body_size 100M;

    # Root para frontend estático
    root /opt/mapsprovefiber/app/frontend/dist;
    index index.html;

    # Static files do Django
    location /static/ {
        alias /opt/mapsprovefiber/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (uploads)
    location /media/ {
        alias /opt/mapsprovefiber/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # API Backend (Django)
    location /api/ {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Timeouts para requests longos
        proxy_connect_timeout 600;
        proxy_send_timeout 600;
        proxy_read_timeout 600;
    }

    # Admin Django
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

    # WebSockets (Channels)
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

    # Frontend SPA (Vue Router)
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

```bash
# Ativar site
sudo ln -s /etc/nginx/sites-available/mapsprovefiber /etc/nginx/sites-enabled/

# Remover site padrão
sudo rm /etc/nginx/sites-enabled/default

# Testar configuração
sudo nginx -t

# Reiniciar Nginx
sudo systemctl reload nginx
```

### Passo 13: Configurar SSL (Let's Encrypt)

```bash
# Obter certificado
sudo certbot --nginx -d maps.example.com -d www.maps.example.com

# Seguir instruções interativas:
# - Email para renovações
# - Aceitar termos
# - Redirecionar HTTP para HTTPS? Yes

# Testar renovação automática
sudo certbot renew --dry-run
```

### Passo 14: Configurar Serviços Systemd

**Serviço Django (Gunicorn)**:

```bash
sudo nano /etc/systemd/system/mapsprovefiber.service
```

```ini
[Unit]
Description=MapsProveFiber Django Application
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=notify
User=mapsprovefiber
Group=mapsprovefiber
WorkingDirectory=/opt/mapsprovefiber/app
Environment="PATH=/opt/mapsprovefiber/app/venv/bin"
EnvironmentFile=/opt/mapsprovefiber/app/.env

ExecStart=/opt/mapsprovefiber/app/venv/bin/gunicorn \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 600 \
    --access-logfile /opt/mapsprovefiber/logs/gunicorn-access.log \
    --error-logfile /opt/mapsprovefiber/logs/gunicorn-error.log \
    core.asgi:application

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Serviço Celery Worker**:

```bash
sudo nano /etc/systemd/system/mapsprovefiber-celery.service
```

```ini
[Unit]
Description=MapsProveFiber Celery Worker
After=network.target redis.service postgresql.service
Wants=redis.service

[Service]
Type=forking
User=mapsprovefiber
Group=mapsprovefiber
WorkingDirectory=/opt/mapsprovefiber/app/backend
Environment="PATH=/opt/mapsprovefiber/app/venv/bin"
EnvironmentFile=/opt/mapsprovefiber/app/.env

ExecStart=/opt/mapsprovefiber/app/venv/bin/celery -A core worker \
    --loglevel=info \
    --logfile=/opt/mapsprovefiber/logs/celery-worker.log \
    --pidfile=/tmp/celery-worker.pid \
    --detach

ExecStop=/bin/kill -s TERM $MAINPID

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Serviço Celery Beat**:

```bash
sudo nano /etc/systemd/system/mapsprovefiber-celerybeat.service
```

```ini
[Unit]
Description=MapsProveFiber Celery Beat Scheduler
After=network.target redis.service
Wants=redis.service mapsprovefiber-celery.service

[Service]
Type=simple
User=mapsprovefiber
Group=mapsprovefiber
WorkingDirectory=/opt/mapsprovefiber/app/backend
Environment="PATH=/opt/mapsprovefiber/app/venv/bin"
EnvironmentFile=/opt/mapsprovefiber/app/.env

ExecStart=/opt/mapsprovefiber/app/venv/bin/celery -A core beat \
    --loglevel=info \
    --logfile=/opt/mapsprovefiber/logs/celery-beat.log \
    --pidfile=/tmp/celery-beat.pid

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar serviços
sudo systemctl enable mapsprovefiber
sudo systemctl enable mapsprovefiber-celery
sudo systemctl enable mapsprovefiber-celerybeat

# Iniciar serviços
sudo systemctl start mapsprovefiber
sudo systemctl start mapsprovefiber-celery
sudo systemctl start mapsprovefiber-celerybeat

# Verificar status
sudo systemctl status mapsprovefiber
sudo systemctl status mapsprovefiber-celery
sudo systemctl status mapsprovefiber-celerybeat
```

---

## ⚙️ Configuração Pós-Instalação

### Logs

```bash
# Logs Django
tail -f /opt/mapsprovefiber/logs/gunicorn-error.log

# Logs Celery
tail -f /opt/mapsprovefiber/logs/celery-worker.log

# Logs Nginx
tail -f /var/log/nginx/mapsprovefiber_error.log

# Logs PostgreSQL
tail -f /var/log/postgresql/postgresql-15-main.log
```

### Backup Automático

```bash
# Criar script de backup
sudo nano /opt/mapsprovefiber/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/backup/mapsprovefiber"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -U mapsprovefiber -h localhost mapsprovefiber | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /opt/mapsprovefiber/media/

# Backup .env
cp /opt/mapsprovefiber/app/.env $BACKUP_DIR/.env_$DATE

# Manter apenas 30 dias de backups
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# Tornar executável
sudo chmod +x /opt/mapsprovefiber/backup.sh

# Agendar com cron (diariamente às 2am)
sudo crontab -e
# Adicionar:
0 2 * * * /opt/mapsprovefiber/backup.sh >> /opt/mapsprovefiber/logs/backup.log 2>&1
```

---

## 🎨 First-Time Setup

Após a instalação, acesse o sistema pela primeira vez:

### 1. Acessar URL

```
https://maps.example.com
```

Você será **automaticamente redirecionado** para:

```
https://maps.example.com/setup_app/first_time/
```

### 2. Preencher Configuração Inicial

O wizard de first-time setup solicitará:

#### Informações da Empresa
- **Nome da empresa**: Ex: "Fiber Networks LTDA"
- **Logo**: Upload de imagem PNG (recomendado 200x60px)

#### Integração Zabbix
- **URL do Zabbix**: `https://zabbix.example.com`
- **Método de autenticação**: Token ou Usuário/Senha
  - **API Token**: (recomendado) Cole o token gerado no Zabbix
  - OU **Usuário**: nome de usuário Zabbix
  - OU **Senha**: senha do usuário Zabbix

#### Google Maps
- **API Key**: Cole a chave da API do Google Maps
  - Certifique-se que as seguintes APIs estão habilitadas:
    - Maps JavaScript API
    - Geocoding API
    - Directions API
    - Places API (opcional)

#### Banco de Dados
- **Host**: `localhost` (ou IP do servidor PostgreSQL)
- **Porta**: `5432`
- **Nome do banco**: `mapsprovefiber`
- **Usuário**: `mapsprovefiber`
- **Senha**: (senha criada no Passo 3)

#### Redis
- **URL**: `redis://localhost:6379/0`

#### Licença
- **Chave de licença**: Cole a chave fornecida pelo fornecedor

### 3. Salvar Configuração

Ao clicar em **Salvar**:

1. ✅ Configuração é salva no banco de dados (criptografada)
2. ✅ Sistema testa conectividade com Zabbix
3. ✅ Sistema testa conectividade com banco de dados
4. ✅ Arquivo `.env` é atualizado
5. ✅ Serviços são reiniciados automaticamente
6. ✅ Você é redirecionado para o dashboard

### 4. Primeira Dashboard

Após o setup inicial, você verá:

- ✅ Dashboard com mapa
- ✅ Menu lateral com todas as funcionalidades
- ✅ Painel de monitoramento de dispositivos
- ✅ Opções de configuração avançada em `/setup_app/config/`

---

## ✅ Validação

### 1. Verificar Serviços

```bash
# Todos devem estar "active (running)"
sudo systemctl status mapsprovefiber
sudo systemctl status mapsprovefiber-celery
sudo systemctl status mapsprovefiber-celerybeat
sudo systemctl status nginx
sudo systemctl status postgresql
sudo systemctl status redis
```

### 2. Health Checks

```bash
# Health check básico
curl https://maps.example.com/healthz/

# Health check com dependências
curl https://maps.example.com/healthz/ready/

# Status Celery
curl https://maps.example.com/api/v1/celery/status/
```

Respostas esperadas:
```json
{"status": "healthy"}
{"status": "ready", "database": "ok", "redis": "ok"}
{"active_tasks": 0, "workers": 1}
```

### 3. Testar API

```bash
# Login (obter token)
curl -X POST https://maps.example.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "sua-senha"}'

# Listar dispositivos (com token)
curl https://maps.example.com/api/v1/inventory/devices/ \
  -H "Authorization: Bearer SEU_TOKEN_AQUI"
```

### 4. Verificar Logs

```bash
# Sem erros críticos
sudo journalctl -u mapsprovefiber -n 50 --no-pager
sudo journalctl -u mapsprovefiber-celery -n 50 --no-pager

# Logs de acesso
tail -100 /var/log/nginx/mapsprovefiber_access.log
```

### 5. Smoke Test

```bash
cd /opt/mapsprovefiber/app
source venv/bin/activate
python scripts/smoke_test_phase4.py
```

Esperado: `6/6 tests passed`

---

## 🔧 Troubleshooting

### Problema: Nginx mostra "502 Bad Gateway"

**Causa**: Django não está rodando

**Solução**:
```bash
# Verificar status
sudo systemctl status mapsprovefiber

# Ver logs
sudo journalctl -u mapsprovefiber -n 100

# Reiniciar
sudo systemctl restart mapsprovefiber
```

### Problema: "CSRF verification failed"

**Causa**: Configuração de domínio incorreta

**Solução**:
```bash
# Editar .env
nano /opt/mapsprovefiber/app/.env

# Adicionar/corrigir:
ALLOWED_HOSTS=maps.example.com,www.maps.example.com
CSRF_TRUSTED_ORIGINS=https://maps.example.com,https://www.maps.example.com

# Reiniciar
sudo systemctl restart mapsprovefiber
```

### Problema: Mapas não carregam

**Causa**: Google Maps API Key inválida ou sem permissões

**Solução**:
1. Acessar Google Cloud Console
2. Habilitar APIs necessárias
3. Verificar restrições da chave
4. Re-salvar chave em `/setup_app/config/`

### Problema: Celery tasks não executam

**Causa**: Redis não acessível ou Celery parado

**Solução**:
```bash
# Verificar Redis
redis-cli ping  # Deve retornar "PONG"

# Verificar Celery
sudo systemctl status mapsprovefiber-celery

# Reiniciar Celery
sudo systemctl restart mapsprovefiber-celery
sudo systemctl restart mapsprovefiber-celerybeat
```

### Problema: Erro de conexão com PostgreSQL

**Causa**: Senha incorreta ou permissões

**Solução**:
```bash
# Testar conexão manual
psql -U mapsprovefiber -d mapsprovefiber -h localhost

# Verificar pg_hba.conf
sudo nano /etc/postgresql/15/main/pg_hba.conf

# Deve ter:
local   mapsprovefiber    mapsprovefiber                            md5

# Reiniciar
sudo systemctl restart postgresql
```

### Problema: SSL certificate error

**Causa**: Certificado Let's Encrypt expirado ou não renovado

**Solução**:
```bash
# Renovar manualmente
sudo certbot renew --force-renewal

# Verificar auto-renewal
sudo systemctl status certbot.timer

# Testar renewal
sudo certbot renew --dry-run
```

---

## 📚 Próximos Passos

Após instalação bem-sucedida:

1. **Configuração Avançada**
   - [ ] Configurar alertas e notificações
   - [ ] Importar dados de infraestrutura
   - [ ] Configurar usuários e permissões

2. **Monitoramento**
   - [ ] Configurar Prometheus + Grafana (ver [doc/operations/MONITORING.md](../operations/MONITORING.md))
   - [ ] Habilitar dashboards em `/metrics`
   - [ ] Configurar alertas de sistema

3. **Backup e Recovery**
   - [ ] Testar restore de backup
   - [ ] Configurar backup offsite
   - [ ] Documentar procedimento de disaster recovery

4. **Performance Tuning**
   - [ ] Ajustar workers Gunicorn conforme carga
   - [ ] Configurar Redis HA (Sentinel)
   - [ ] Otimizar queries PostgreSQL

5. **Segurança**
   - [ ] Configurar firewall (UFW)
   - [ ] Habilitar fail2ban
   - [ ] Configurar 2FA para usuários admin
   - [ ] Auditar logs de acesso

---

## 📞 Suporte

- **Documentação**: [doc/README.md](../README.md)
- **Issues**: GitHub Issues
- **Email**: support@example.com

---

**Última Atualização**: 7 de Fevereiro de 2026  
**Versão do Guia**: 1.0.0  
**Versão da Aplicação**: 2.1.0
