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
- Ambiente local (Python + PostgreSQL/PostGIS; GDAL/GEOS obrigatórios)
- Ambiente containerizado (Docker Compose: web, celery, beat, redis, postgres)

---

## 🧩 Visão Geral da Stack (Docker)

| Serviço | Função |
|---------|--------|
| web | Django + Gunicorn/Uvicorn (porta 8100 no host, 8000 no container) |
| celery | Worker para tarefas assíncronas |
| beat | Agendador de tarefas periódicas |
| redis | Cache e broker Celery |
| postgres | PostgreSQL 16 + PostGIS (dados persistentes; porta 5433 no host) |

O compose de desenvolvimento é `docker/docker-compose.yml` (atalhos: `make up`, `make down`, `make logs`). Script `docker-entrypoint.sh` automatiza: espera de saúde, migrações, collectstatic, start do servidor.

---

## ✅ Credenciais Padrão
| Item | Valor |
|------|-------|
| App | http://localhost:8100 (Docker) · http://localhost:8000 (local, `make run`) |
| Admin | http://localhost:8100/admin/ (Docker) |
| Usuário | `admin` |
| Senha | `admin123` |

No Docker o superusuário é criado automaticamente (variáveis `INIT_ENSURE_SUPERUSER=true`). Localmente rode: `python backend/manage.py ensure_superuser` (ou `make superuser`).

---

## 🚀 Caminhos Rápidos

| Objetivo | Ambiente Local | Docker Compose |
|----------|----------------|----------------|
| Iniciar aplicação | `make run` | `make up` (ou `docker compose -f docker/docker-compose.yml up -d --build`) |
| Rodar testes | `pytest -q` (da raiz do repo) | `docker compose -f docker/docker-compose.yml exec web pytest -q` |
| Criar superuser | `make superuser` | `docker compose -f docker/docker-compose.yml exec web python manage.py createsuperuser` |
| Migrações | `make migrate` | `docker compose -f docker/docker-compose.yml exec web python manage.py migrate` |
| Shell Django | `make shell` | `docker compose -f docker/docker-compose.yml exec web python manage.py shell` |
| Coletar estáticos | `make collectstatic` | (automático) |

---

## 🛠️ Setup Local (Python + PostgreSQL/PostGIS)

Requer GDAL/GEOS no sistema (veja [`doc/developer/gis-setup.md`](../developer/gis-setup.md)) e um PostgreSQL com PostGIS. O mais simples é subir só o banco e o Redis pelo Compose:
```bash
docker compose -f docker/docker-compose.yml up -d postgres redis   # postgres em localhost:5433, redis em localhost:6380
```

1. Criar ambiente virtual e instalar dependências (runtime + testes/lint):
```bash
python -m venv venv
source venv/bin/activate
make requirements-dev
```
2. Apontar o Django para o PostGIS (`.env` ou variáveis de ambiente):
```bash
export DB_ENGINE=postgis DB_HOST=127.0.0.1 DB_PORT=5433 DB_NAME=app DB_USER=app DB_PASSWORD=app
export REDIS_URL=redis://127.0.0.1:6380/0
```
3. Migrar banco:
```bash
make migrate
make superuser          # ou: python backend/manage.py ensure_superuser
```
4. Rodar servidor:
```bash
make run                # 0.0.0.0:8000, settings.dev
```
5. Acessar: http://localhost:8000

### Comandos úteis
```bash
make makemigrations
make collectstatic
make shell
```

### Testes
```bash
pytest -q                                   # da raiz do repo; settings.test usa SQLite por omissão,
                                            # TEST_DB_ENGINE=postgis (+ DB_*) liga ao PostGIS, como no CI
pytest -q backend/tests/test_smoke.py
make test-coverage                          # pytest --cov --cov-report=html
cd frontend && npm ci && npm run test:unit  # Vitest
```

### Health & Metrics
```bash
make health                                 # curl /healthz
curl http://localhost:8000/metrics/metrics
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
# O compose já define DB_ENGINE=postgis, DB_HOST=postgres e DB_NAME/DB_USER/DB_PASSWORD=app
REDIS_URL=redis://redis:6379/1
DJANGO_SETTINGS_MODULE=settings.dev
SERVICE_ACCOUNT_ROTATION_INTERVAL_SECONDS=3600
SERVICE_ACCOUNT_WEBHOOK_CONNECT_TIMEOUT=3
SERVICE_ACCOUNT_WEBHOOK_READ_TIMEOUT=5
```
4. Subir stack:
```bash
make up                 # ou: docker compose -f docker/docker-compose.yml up -d --build
```
5. Verificar:
```bash
docker compose -f docker/docker-compose.yml ps
make logs
```
6. Acessar: http://localhost:8100

### Comandos frequentes
```bash
docker compose -f docker/docker-compose.yml logs -f web
docker compose -f docker/docker-compose.yml restart web
make down
docker compose -f docker/docker-compose.yml down -v  # remove volumes
```

### Hot Reload (Desenvolvimento)
O `docker/docker-compose.yml` já monta `../backend` e `../frontend` no container (volumes `../backend:/app/backend`, `../frontend:/app/frontend`, `../logs:/app/backend/logs`). Start:
```bash
docker compose -f docker/docker-compose.yml up -d web
```

### Bootstrap manual (se necessário)
```bash
docker compose -f docker/docker-compose.yml exec web python manage.py migrate
docker compose -f docker/docker-compose.yml exec web python manage.py createsuperuser
docker compose -f docker/docker-compose.yml exec web python manage.py collectstatic --noinput
```

### Script de Deploy
Produção usa `docker/docker-compose.prod.yml` (padrão do script). Passo a passo e variáveis em [`DEPLOY.md`](../../DEPLOY.md):
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh --help
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
(Docker: porta 8100; local com `make run`: porta 8000.)
```bash
curl -I http://localhost:8100/ready
curl http://localhost:8100/metrics/metrics
curl -I http://localhost:8100/healthz
curl http://localhost:8100/api/v1/inventory/sites/   # requer sessão autenticada
```

---

## 🛡️ Redis Offline (Desenvolvimento)
Sem Redis:
- App continua funcional (fallback)
- Latência ↑ pois acessos vão direto ao Zabbix
- Health checks não falham

Para subir Redis isolado:
```bash
docker compose -f docker/docker-compose.yml up -d redis
```

---

## 🧪 Testes em Docker
```bash
docker compose -f docker/docker-compose.yml exec web pytest -q
docker compose -f docker/docker-compose.yml exec web pytest tests/test_smoke.py -v
```

Cobertura:
```bash
docker compose -f docker/docker-compose.yml exec web pytest --cov --cov-report=term-missing
```

---

## 🧰 Troubleshooting
| Sintoma | Ação |
|---------|------|
| Porta ocupada (local) | `python backend/manage.py runserver 8080` |
| Web não sobe (Docker) | `docker compose -f docker/docker-compose.yml logs -f web` |
| DB erros | `docker compose -f docker/docker-compose.yml exec web python manage.py migrate` |
| Health falha | Revisar `.env` e variáveis obrigatórias |
| Redis indisponível | `docker compose -f docker/docker-compose.yml restart redis` |
| Superuser ausente | Verificar `INIT_ENSURE_SUPERUSER=true` ou rodar manual |

Resetar banco local (apaga dados!):
```bash
make resetdb            # reset_db (django-extensions) + migrate + superuser admin
# ou, no Docker: docker compose -f docker/docker-compose.yml down -v && make up
```

---

## 🔄 Atualizações & Rollback
Atualizar:
```bash
git pull
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```
Rollback rápido (último build saudável):
```bash
docker compose -f docker/docker-compose.yml down
git checkout <commit-estável>
docker compose -f docker/docker-compose.yml up -d --build
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
- Produção: usar PostgreSQL 16 + PostGIS (o único banco suportado) e Redis HA; ver [`DEPLOY.md`](../../DEPLOY.md)
- Ajustar intervalos de rotação de service accounts conforme política interna
- Para builds repetíveis: `docker compose -f docker/docker-compose.yml build --pull --no-cache`

---

**Última atualização:** 2026-10-04
