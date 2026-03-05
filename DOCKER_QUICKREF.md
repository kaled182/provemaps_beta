# Docker Quick Reference - MapsProveFiber

## 🚀 Comandos Rápidos

### Gerenciamento de Containers
```powershell
# Iniciar todos os serviços
docker compose -f docker/docker-compose.yml up -d

# Parar todos os serviços
docker compose -f docker/docker-compose.yml down

# Ver status dos containers
docker compose -f docker/docker-compose.yml ps

# Ver logs em tempo real
docker compose -f docker/docker-compose.yml logs -f

# Ver logs de um serviço específico
docker compose -f docker/docker-compose.yml logs -f web
docker compose -f docker/docker-compose.yml logs -f celery
docker compose -f docker/docker-compose.yml logs -f postgres

# Reiniciar serviços
docker compose -f docker/docker-compose.yml restart
docker compose -f docker/docker-compose.yml restart web
```

### Comandos Django
```powershell
# Executar migrations
docker compose -f docker/docker-compose.yml exec web python manage.py migrate

# Criar superusuário
docker compose -f docker/docker-compose.yml exec web python manage.py createsuperuser

# Coletar arquivos estáticos
docker compose -f docker/docker-compose.yml exec web python manage.py collectstatic --noinput

# Abrir shell Django
docker compose -f docker/docker-compose.yml exec web python manage.py shell

# Abrir bash no container web
docker compose -f docker/docker-compose.yml exec web bash

# Alterar senha do admin
docker compose -f docker/docker-compose.yml exec web python manage.py changepassword admin
```

### Banco de Dados
```powershell
# Conectar ao PostgreSQL
docker compose -f docker/docker-compose.yml exec postgres psql -U app -d app

# Backup do banco
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U app app > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup.sql | docker compose -f docker/docker-compose.yml exec -T postgres psql -U app app
```

---

## 🔌 Portas dos Serviços

| Serviço | Porta Externa | Porta Interna | URL |
|---------|---------------|---------------|-----|
| **Django Web** | 8100 | 8000 | http://localhost:8100 |
| **PostgreSQL** | 5433 | 5432 | localhost:5433 |
| **Redis** | 6380 | 6379 | localhost:6380 |
| **Prometheus** | 9090 | 9090 | http://localhost:9090 |
| **Grafana** | 3002 | 3000 | http://localhost:3002 |
| **Video HLS** | 8083 | 8080 | http://localhost:8083 |
| **Video Transmuxer** | 9000 | 9000 | http://localhost:9000 |
| **WhatsApp QR** | 3001 | 3000 | http://localhost:3001 |
| **MediaMTX (RTSP)** | 8554 | 8554 | rtsp://localhost:8554 |
| **MediaMTX (HLS)** | 8888 | 8888 | http://localhost:8888 |
| **MediaMTX (WebRTC)** | 8889 | 8889 | http://localhost:8889 |
| **RTMP** | 1935 | 1935 | rtmp://localhost:1935 |

### 📝 Nota sobre Portas
As portas externas foram ajustadas para evitar conflitos com outros serviços:
- **8000 → 8100** - Evita conflito com outros projetos Django
- **3000 → 3002** - Evita conflito com Chatwoot/Typebot
- **8082 → 8083** - Evita conflito com Typebot Viewer

---

## 🔑 Credenciais Padrão

### Django Admin
- **URL:** http://localhost:8100/admin
- **Username:** `admin`
- **Senha:** `admin123`
- **Email:** `admin@localhost`

⚠️ **IMPORTANTE:** Altere a senha após o primeiro acesso!

```powershell
# Alterar senha via comando
docker compose -f docker/docker-compose.yml exec web python manage.py changepassword admin
```

### PostgreSQL
- **Host:** localhost
- **Porta:** 5433
- **Database:** app
- **User:** app
- **Password:** app

### Redis
- **Host:** localhost
- **Porta:** 6380
- **Database:** 0
- **Senha:** (sem senha no ambiente de desenvolvimento)

---

## 🏥 Health Checks

```powershell
# Health básico (conectividade com banco)
curl http://localhost:8100/healthz

# Readiness (todos os serviços prontos)
curl http://localhost:8100/ready

# Liveness (aplicação viva)
curl http://localhost:8100/live

# Status dos workers Celery
curl http://localhost:8100/celery/status

# Métricas Prometheus
curl http://localhost:8100/metrics/
```

---

## 📊 Monitoramento

### Prometheus
- **URL:** http://localhost:9090
- **Métricas Django:** http://localhost:8100/metrics/
- **Targets:** http://localhost:9090/targets

### Grafana
- **URL:** http://localhost:3002
- **Credenciais padrão:** admin/admin (configurar no primeiro acesso)
- **Datasource Prometheus:** http://prometheus:9090

---

## 🔧 Troubleshooting

### Containers não iniciam
```powershell
# Ver logs de erro
docker compose -f docker/docker-compose.yml logs

# Reconstruir imagens
docker compose -f docker/docker-compose.yml up -d --build --force-recreate

# Limpar volumes (⚠️ apaga dados!)
docker compose -f docker/docker-compose.yml down -v
```

### Erro de porta já alocada
```powershell
# Verificar portas em uso
netstat -ano | findstr :8100
netstat -ano | findstr :5433

# Parar processo usando a porta (substitua PID)
taskkill /PID <PID> /F

# Ou alterar porta no docker-compose.yml
```

### Banco de dados não conecta
```powershell
# Verificar se PostgreSQL está healthy
docker compose -f docker/docker-compose.yml ps postgres

# Ver logs do PostgreSQL
docker compose -f docker/docker-compose.yml logs postgres

# Reiniciar PostgreSQL
docker compose -f docker/docker-compose.yml restart postgres
```

### Celery não processa tarefas
```powershell
# Verificar status dos workers
docker compose -f docker/docker-compose.yml logs celery

# Reiniciar Celery workers
docker compose -f docker/docker-compose.yml restart celery
docker compose -f docker/docker-compose.yml restart beat
```

### Redis não conecta
```powershell
# Verificar status do Redis
docker compose -f docker/docker-compose.yml ps redis

# Testar conexão Redis
docker compose -f docker/docker-compose.yml exec redis redis-cli ping
# Deve retornar: PONG
```

---

## 🗂️ Estrutura de Volumes

```
Volumes Docker:
├── postgres_data/     # Dados do PostgreSQL
├── redis_data/        # Dados do Redis
├── grafana_data/      # Dashboards e configurações Grafana
├── prometheus_data/   # Métricas Prometheus
├── hls_cache/         # Cache de vídeos HLS
└── mediamtx_data/     # Configurações MediaMTX
```

### Backup de Volumes
```powershell
# Backup PostgreSQL
docker compose -f docker/docker-compose.yml exec postgres pg_dump -U app app > backup_db_$(Get-Date -Format "yyyyMMdd_HHmmss").sql

# Backup Redis (RDB snapshot)
docker compose -f docker/docker-compose.yml exec redis redis-cli SAVE
docker cp $(docker compose -f docker/docker-compose.yml ps -q redis):/data/dump.rdb ./backup_redis_$(Get-Date -Format "yyyyMMdd_HHmmss").rdb
```

---

## 🔄 Atualizações

### Atualizar código sem perder dados
```powershell
# 1. Parar containers
docker compose -f docker/docker-compose.yml down

# 2. Atualizar código (git pull ou copiar arquivos)
git pull origin main

# 3. Reconstruir e iniciar
docker compose -f docker/docker-compose.yml up -d --build

# 4. Aplicar migrations
docker compose -f docker/docker-compose.yml exec web python manage.py migrate
```

### Reset completo (⚠️ APAGA TUDO!)
```powershell
# Parar e remover tudo (containers, volumes, imagens)
docker compose -f docker/docker-compose.yml down -v --rmi all

# Iniciar do zero
docker compose -f docker/docker-compose.yml up -d --build
```

---

## 📚 Links Úteis

### Aplicação
- **Dashboard:** http://localhost:8100
- **Admin Django:** http://localhost:8100/admin
- **API Docs:** http://localhost:8100/api/v1/
- **Setup Wizard:** http://localhost:8100/setup_app/first_time/
- **Documentação:** http://localhost:8100/setup_app/docs/

### Monitoramento
- **Prometheus:** http://localhost:9090
- **Grafana:** http://localhost:3002
- **Métricas:** http://localhost:8100/metrics/

### Integrações
- **WhatsApp QR:** http://localhost:3001
- **Video HLS:** http://localhost:8083/hls
- **MediaMTX:** http://localhost:8888

---

**Última atualização:** 25/02/2026  
**Versão:** 2.1.0
