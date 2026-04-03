# QUICKSTART — Local & Docker (Unificado)

> Este guia substitui `QUICKSTART_LOCAL.md` e `TUTORIAL_DOCKER.md`. Use este único documento para iniciar o projeto tanto em ambiente local quanto via Docker Compose.

## 📌 Migration Notes

**2025-11-07**: Este guia consolidou e substituiu os seguintes documentos:
- `doc/getting-started/QUICKSTART_LOCAL.md` (removido)
- `doc/getting-started/TUTORIAL_DOCKER.md` (removido)
- `doc/developer/QUICKSTART_LOCAL.md` (removido)

Todas as referências no projeto foram atualizadas para apontar para este guia unificado.

---

## 🎯 Objetivo
Fornecer um caminho rápido e confiável para colocar o MapsProveFiber em funcionamento em:
- Ambiente local (Python + SQLite)
- Ambiente containerizado (Docker Compose: web, celery, beat, redis, db)

---

## 🧩 Visão Geral da Stack (Docker)

| Serviço | Função |
|---------|--------|
| web | Django + Gunicorn/Uvicorn (porta 8000) |
| celery | Worker para tarefas assíncronas |
| beat | Agendador de tarefas periódicas |
| redis | Cache e broker Celery |
| db | MariaDB (dados persistentes) |

Script `docker-entrypoint.sh` automatiza: espera de saúde, migrações, collectstatic, start do servidor.

---

## ✅ Credenciais Padrão
| Item | Valor |
|------|-------|
| App | http://localhost:8000 |
| Admin | http://localhost:8000/admin/ |
| Usuário | `admin` |
| Senha | `admin123` |

No Docker o superusuário é criado automaticamente (variáveis `INIT_ENSURE_SUPERUSER=true`). Localmente rode: `python manage.py ensure_superuser`.

---

## 🚀 Caminhos Rápidos

| Objetivo | Ambiente Local | Docker Compose |
|----------|----------------|----------------|
| Iniciar aplicação | `python manage.py runserver` | `docker compose up -d --build` |
| Rodar testes | `pytest -q` | `docker compose exec web pytest -q` |
| Criar superuser | `python manage.py createsuperuser` | `docker compose exec web python manage.py createsuperuser` |
| Migrações | `python manage.py migrate` | `docker compose exec web python manage.py migrate` |
| Shell Django | `python manage.py shell` | `docker compose exec web python manage.py shell` |
| Coletar estáticos | `python manage.py collectstatic --noinput` | (automático) |

---

## 🛠️ Setup Local (Python + SQLite)

1. Criar ambiente virtual:
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
2. Migrar banco:
```powershell
python manage.py migrate
python manage.py ensure_superuser
```
3. Rodar servidor:
```powershell
python manage.py runserver
```
4. Acessar: http://localhost:8000

### Comandos úteis
```powershell
python manage.py makemigrations
python manage.py collectstatic --noinput
python manage.py shell
```

### Testes
```powershell
pytest -q
pytest tests/test_smoke.py -v
pytest --cov --cov-report=html
```

### Health & Metrics
```powershell
Invoke-WebRequest http://localhost:8000/healthz
Invoke-WebRequest http://localhost:8000/metrics/metrics
```

---

## 🐳 Setup Docker (Stack Completa)

1. Instalar Docker:
```bash
docker --version
docker compose version
```
2. Clonar repositório:
```bash
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta
```
3. Preparar `.env`:
```bash
cp .env.example .env
```
Exemplo mínimo:
```env
DB_HOST=db
DB_USER=app
DB_PASSWORD=app
REDIS_URL=redis://redis:6379/1
DJANGO_SETTINGS_MODULE=settings.dev
SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS=3600
SERVICE_ACCOUNT_WEBHOOK_CONNECT_TIMEOUT=3
SERVICE_ACCOUNT_WEBHOOK_READ_TIMEOUT=5
```
4. Subir stack:
```bash
docker compose up -d --build
```
5. Verificar:
```bash
docker compose ps
docker compose logs -f web
```
6. Acessar: http://localhost:8000

### Comandos frequentes
```bash
docker compose logs -f web
docker compose restart web
docker compose down
docker compose down -v  # remove volumes
```

### Hot Reload (Desenvolvimento)
No `docker-compose.yml` garantir volume montado:
```yaml
volumes:
  - .:/app
  - ./logs:/app/logs
```
Start:
```bash
docker compose up -d web
```

### Bootstrap manual (se necessário)
```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py collectstatic --noinput
```

### Script de Deploy
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh --compose docker-compose.yml --settings settings.prod --health http://localhost:8000/healthz
```

---

## 🔍 Endpoints Essenciais
| Tipo | URL |
|------|-----|
| Dashboard | `/maps_view/dashboard/` |
| Setup | `/setup_app/` |
| Rotas (API) | `/api/v1/inventory/routes/tasks/` |
| Admin | `/admin/` |
| Health | `/healthz`, `/ready`, `/live` |
| Metrics | `/metrics/metrics` |
| Docs | `/setup_app/docs/` |
| API Inventory | `/api/v1/inventory/` |

---

## 🩺 Verificações Rápidas
```powershell
Invoke-WebRequest http://localhost:8000/ready | Select-Object StatusCode
Invoke-WebRequest http://localhost:8000/metrics/metrics
```

```bash
curl -I http://localhost:8000/healthz
curl http://localhost:8000/api/v1/inventory/sites/
```

---

## 🛡️ Redis Offline (Desenvolvimento)
Sem Redis:
- App continua funcional (fallback)
- Latência ↑ pois acessos vão direto ao Zabbix
- Health checks não falham

Para subir Redis isolado:
```bash
docker compose up -d redis
```

---

## 🧪 Testes em Docker
```bash
docker compose exec web pytest -q
docker compose exec web pytest tests/test_smoke.py -v
```

Cobertura:
```bash
docker compose exec web pytest --cov --cov-report=term-missing
```

---

## 🧰 Troubleshooting
| Sintoma | Ação |
|---------|------|
| Porta ocupada (local) | `python manage.py runserver 8080` |
| Web não sobe (Docker) | `docker compose logs -f web` |
| DB erros | `docker compose exec web python manage.py migrate` |
| Health falha | Revisar `.env` e variáveis obrigatórias |
| Redis indisponível | `docker compose restart redis` |
| Superuser ausente | Verificar `INIT_ENSURE_SUPERUSER=true` ou rodar manual |

Resetar banco local:
```powershell
Remove-Item db.sqlite3
python manage.py migrate
python manage.py ensure_superuser
```

---

## 🔄 Atualizações & Rollback
Atualizar:
```bash
git pull
docker compose build
docker compose up -d
```
Rollback rápido (último build saudável):
```bash
docker compose down
git checkout <commit-estável>
docker compose up -d --build
```

---

## 📌 Próximos Passos
1. Explorar dashboard
2. Configurar credenciais Zabbix (opcional)
3. Verificar health e métricas
4. Ler docs em `/setup_app/docs/`
5. Executar testes

---

## 🗃️ Histórico
Este documento unifica conteúdos antes separados:
- `QUICKSTART_LOCAL.md`
- `TUTORIAL_DOCKER.md`

Os arquivos antigos serão marcados como DEPRECATED e removidos futuramente.

---

## 🏁 Notas Finais
- Produção: usar MariaDB gerenciado e Redis HA
- Ajustar intervalos de rotação de service accounts conforme política interna
- Para builds repetíveis: `docker compose build --pull --no-cache`

---

**Última atualização:** 2025-11-07
