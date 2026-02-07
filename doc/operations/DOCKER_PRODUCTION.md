# 🐳 Docker Production Deployment - MapsProveFiber v2.1.0

**Data**: 7 de Fevereiro de 2026  
**Status**: ✅ Production Ready

---

## 📦 O Que Foi Criado

### 1. Docker Compose Production (`docker/docker-compose.prod.yml`)

Configuração completa com:
- ✅ **Nginx** com SSL/TLS, HTTP/2, gzip, rate limiting
- ✅ **Django** (Gunicorn + Uvicorn workers ASGI)
- ✅ **PostgreSQL 15 + PostGIS 3.4**
- ✅ **Redis 7** (cache + message broker)
- ✅ **Celery Worker** (4 workers, 3 queues)
- ✅ **Celery Beat** (scheduler com Django Beat)
- ✅ **Health checks** para todos os serviços
- ✅ **Resource limits** (CPU/RAM)
- ✅ **Volumes persistentes** (dados, logs, media)
- ✅ **Networks** (frontend + backend isolados)

### 2. Nginx Production Config (`docker/nginx/nginx.prod.conf`)

Recursos:
- ✅ SSL/TLS com ciphers modernos (Mozilla Modern)
- ✅ HTTP/2 support
- ✅ OCSP Stapling
- ✅ HSTS (HTTP Strict Transport Security)
- ✅ Gzip compression (6 níveis)
- ✅ Rate limiting (10 req/s geral, 30 req/s API)
- ✅ WebSocket support para Django Channels
- ✅ Security headers (X-Frame-Options, CSP, etc)
- ✅ Static file serving com cache (30 dias)
- ✅ SPA Vue Router support (try_files)

### 3. Script de Deploy (`scripts/deploy-docker.sh`)

Automação completa:
- ✅ Instalação one-command (`sudo ./deploy-docker.sh install`)
- ✅ Update automático (`sudo ./deploy-docker.sh update`)
- ✅ Backup/restore banco de dados
- ✅ SSL Let's Encrypt com renovação automática
- ✅ Build frontend Vue 3
- ✅ Migrations Django
- ✅ Logs, status, shell interativo

---

## 🚀 Como Usar no Linux

### Instalação Completa (Primeira Vez)

```bash
# 1. Clonar repositório
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta

# 2. Tornar script executável
chmod +x scripts/deploy-docker.sh

# 3. Executar instalação
sudo ./scripts/deploy-docker.sh install

# Durante a instalação, será solicitado:
# - Domínio (ex: maps.example.com)
# - Email para SSL
# - Zabbix URL e API Token
# - Google Maps API Key
```

**Duração**: 10-15 minutos (automático)

### Comandos Disponíveis

```bash
# Gerenciamento básico
sudo ./scripts/deploy-docker.sh start         # Iniciar containers
sudo ./scripts/deploy-docker.sh stop          # Parar containers
sudo ./scripts/deploy-docker.sh restart       # Reiniciar containers
sudo ./scripts/deploy-docker.sh status        # Ver status

# Logs
sudo ./scripts/deploy-docker.sh logs          # Todos os logs
sudo ./scripts/deploy-docker.sh logs web      # Logs do Django
sudo ./scripts/deploy-docker.sh logs nginx    # Logs do Nginx
sudo ./scripts/deploy-docker.sh logs celery   # Logs do Celery

# Atualização
sudo ./scripts/deploy-docker.sh update        # Atualizar código + rebuild

# Banco de dados
sudo ./scripts/deploy-docker.sh backup        # Backup PostgreSQL
sudo ./scripts/deploy-docker.sh restore /path/to/backup.sql.gz

# Django
sudo ./scripts/deploy-docker.sh migrate       # Executar migrations
sudo ./scripts/deploy-docker.sh collectstatic # Coletar static files
sudo ./scripts/deploy-docker.sh createsuperuser # Criar admin

# SSL
sudo ./scripts/deploy-docker.sh ssl           # Configurar Let's Encrypt

# Shell interativo
sudo ./scripts/deploy-docker.sh shell         # Bash no container Django
```

---

## 📁 Estrutura de Arquivos

```
provemaps_beta/
├── docker/
│   ├── docker-compose.prod.yml      # Compose production ✅ NOVO
│   ├── docker-compose.yml           # Compose development (existente)
│   ├── dockerfile                   # Dockerfile (existente)
│   ├── docker-entrypoint.sh         # Entrypoint (existente)
│   └── nginx/
│       └── nginx.prod.conf          # Nginx config ✅ NOVO
├── scripts/
│   └── deploy-docker.sh             # Script de deploy ✅ NOVO
├── .env.production                  # Criado pelo script
├── backend/
├── frontend/
└── ...
```

---

## ⚙️ Configuração

### Variáveis de Ambiente (`.env.production`)

Gerado automaticamente pelo script `install`, mas pode ser editado:

```bash
# Django
SECRET_KEY=<gerado automaticamente>
DEBUG=False
ALLOWED_HOSTS=maps.example.com,www.maps.example.com
CSRF_TRUSTED_ORIGINS=https://maps.example.com

# Database
DB_NAME=mapsprovefiber
DB_USER=mapsprovefiber
DB_PASSWORD=<gerado automaticamente>

# Redis
REDIS_URL=redis://redis:6379/0

# Security
FERNET_KEY=<gerado automaticamente>

# Zabbix
ZABBIX_URL=https://zabbix.example.com
ZABBIX_API_TOKEN=<seu token>

# Google Maps
GOOGLE_MAPS_API_KEY=<sua chave>

# Domain
DOMAIN_NAME=maps.example.com
```

---

## 🔒 SSL/TLS com Let's Encrypt

### Configuração Automática

```bash
sudo ./scripts/deploy-docker.sh ssl
```

Isso irá:
1. Obter certificado Let's Encrypt para o domínio
2. Copiar certificados para volume Docker
3. Configurar renovação automática (cron às 3h)
4. Reiniciar Nginx

### Renovação Manual

```bash
sudo certbot renew --force-renewal
sudo cp /etc/letsencrypt/live/SEU_DOMINIO/*.pem /opt/mapsprovefiber/docker/nginx/ssl/
sudo ./scripts/deploy-docker.sh restart nginx
```

---

## 📊 Monitoramento

### Health Checks

Todos os containers possuem health checks:

```bash
# Ver status de saúde
sudo ./scripts/deploy-docker.sh status

# Formato esperado:
# web        healthy   
# nginx      healthy   
# postgres   healthy   
# redis      healthy   
# celery     healthy   
```

### Endpoints de Health

```bash
# Health básico (HTTP 200)
curl http://localhost/healthz/

# Health com dependências
curl https://maps.example.com/ready/
```

### Logs

```bash
# Logs em tempo real
sudo ./scripts/deploy-docker.sh logs

# Logs por serviço
sudo ./scripts/deploy-docker.sh logs web
sudo ./scripts/deploy-docker.sh logs celery
sudo ./scripts/deploy-docker.sh logs nginx
sudo ./scripts/deploy-docker.sh logs postgres
```

---

## 🗃️ Backup & Restore

### Backup Automático

```bash
# Criar backup
sudo ./scripts/deploy-docker.sh backup

# Backup salvo em:
# /opt/mapsprovefiber/backups/db_backup_YYYYMMDD_HHMMSS.sql.gz
```

### Backup Agendado (Cron)

```bash
# Editar crontab
sudo crontab -e

# Adicionar (backup diário às 2h da manhã):
0 2 * * * /opt/mapsprovefiber/scripts/deploy-docker.sh backup >> /opt/mapsprovefiber/logs/backup.log 2>&1
```

### Restore

```bash
sudo ./scripts/deploy-docker.sh restore /opt/mapsprovefiber/backups/db_backup_20260207_020000.sql.gz
```

---

## 🔧 Troubleshooting

### Container não inicia

```bash
# Ver logs detalhados
sudo ./scripts/deploy-docker.sh logs web

# Verificar arquivo .env
cat .env.production

# Rebuild do zero
cd /opt/mapsprovefiber
sudo docker compose -f docker/docker-compose.prod.yml down -v
sudo ./scripts/deploy-docker.sh install
```

### Erro de permissão em volumes

```bash
# Ajustar permissões
sudo chown -R 1000:1000 /opt/mapsprovefiber/backend/media
sudo chown -R 1000:1000 /opt/mapsprovefiber/backend/logs
```

### SSL não funciona

```bash
# Verificar certificados
ls -la /opt/mapsprovefiber/docker/nginx/ssl/

# Reconfigurar SSL
sudo ./scripts/deploy-docker.sh ssl

# Testar Nginx config
sudo docker compose -f docker/docker-compose.prod.yml exec nginx nginx -t
```

### Banco de dados lento

```bash
# Ver configurações PostgreSQL
sudo docker compose -f docker/docker-compose.prod.yml exec postgres cat /var/lib/postgresql/data/postgresql.conf

# Ajustar recursos no docker-compose.prod.yml:
# deploy:
#   resources:
#     limits:
#       cpus: '4.0'      # Aumentar
#       memory: 4G       # Aumentar
```

---

## 📈 Performance Tuning

### Ajustar Workers Gunicorn

Editar `docker-compose.prod.yml`:

```yaml
web:
  command: >
    gunicorn core.asgi:application
    --workers 8              # (2 x CPU cores) + 1
    --max-requests 2000      # Reiniciar worker após N requests
```

### Ajustar Concurrency Celery

```yaml
celery:
  command: >
    celery -A core.celery_app worker
    --concurrency=8          # Número de processos paralelos
    --max-tasks-per-child=500
```

### Redis Memory

```yaml
redis:
  command: >
    redis-server
    --maxmemory 1gb          # Aumentar conforme necessário
```

---

## 🔐 Segurança

### Portas Expostas

- ✅ **80** (HTTP) → redireciona para 443
- ✅ **443** (HTTPS) → Nginx
- ❌ **5432** (PostgreSQL) → apenas localhost
- ❌ **6379** (Redis) → apenas localhost
- ❌ **8000** (Django) → apenas rede interna Docker

### Firewall (UFW)

```bash
# Configurar firewall
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### Secrets Management

**NUNCA** commitar `.env.production` no Git!

```bash
# Adicionar ao .gitignore
echo ".env.production" >> .gitignore
```

---

## 🚀 Workflow de Deploy

### Deploy Inicial

```bash
sudo ./scripts/deploy-docker.sh install
sudo ./scripts/deploy-docker.sh createsuperuser
sudo ./scripts/deploy-docker.sh ssl
```

### Deploy de Atualização

```bash
# 1. Criar backup
sudo ./scripts/deploy-docker.sh backup

# 2. Atualizar código
sudo ./scripts/deploy-docker.sh update

# 3. Verificar status
sudo ./scripts/deploy-docker.sh status
sudo ./scripts/deploy-docker.sh logs web
```

### Rollback

```bash
# 1. Parar containers
sudo ./scripts/deploy-docker.sh stop

# 2. Checkout versão anterior
cd /opt/mapsprovefiber
git checkout v2.0.0  # ou commit anterior

# 3. Rebuild
sudo docker compose -f docker/docker-compose.prod.yml build
sudo ./scripts/deploy-docker.sh start

# 4. Restaurar banco (se necessário)
sudo ./scripts/deploy-docker.sh restore /path/to/backup.sql.gz
```

---

## 📚 Recursos Adicionais

- **Documentação Docker**: [doc/operations/DOCKER.md](../doc/operations/DOCKER.md)
- **Instalação Manual**: [doc/getting-started/INSTALLATION_GUIDE.md](../doc/getting-started/INSTALLATION_GUIDE.md)
- **Troubleshooting**: [doc/troubleshooting/](../doc/troubleshooting/)

---

## ✅ Checklist Pós-Instalação

- [ ] Containers rodando (`status` mostra "healthy")
- [ ] Nginx responde em HTTPS
- [ ] SSL válido (sem warnings no navegador)
- [ ] First-time setup acessível (`/setup_app/first_time/`)
- [ ] Zabbix conectando
- [ ] Google Maps carregando
- [ ] Celery processando tasks (`logs celery`)
- [ ] Backup agendado (cron)
- [ ] Firewall configurado
- [ ] Monitoramento ativo

---

**Instalação Production Docker Completa! 🎉**

**Tempo total**: 10-15 minutos (automático)  
**Complexidade**: Baixa (one-command install)  
**Manutenção**: Simples (scripts automatizados)
