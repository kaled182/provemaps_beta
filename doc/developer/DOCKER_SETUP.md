# Docker Setup Guide — MapsProveFiber

Este guia descreve, passo a passo, como preparar, iniciar e manter o ambiente Docker oficial do MapsProveFiber.

---

## 1. Pré-requisitos
- Docker Engine 24+
- Docker Compose Plugin 2.20+
- Git (para clonar o repositório)
- Acesso à internet para download das imagens base

Confirme as versões:
```powershell
docker --version
docker compose version
```

---

## 2. Clonagem e Estrutura
```powershell
git clone https://github.com/kaled182/provemaps_beta.git
cd mapsprovefiber
```

Os principais serviços definidos em `docker-compose.yml`:
- **web** — Django + Gunicorn/Uvicorn (porta 8000)
- **celery** — Worker de tarefas assíncronas
- **beat** — Agendador Celery (tarefas periódicas)
- **redis** — Broker e cache
- **db** — MariaDB com volume persistente

---

## 3. Configurar Variáveis
Crie o arquivo `.env` a partir do template e ajuste valores mínimos:
```powershell
Copy-Item .env.example .env

# Edite com seu editor favorito
notepad .env
```

Valores recomendados para o stack Docker padrão:
```env
DJANGO_SETTINGS_MODULE=settings.dev
DB_HOST=db
DB_USER=app
DB_PASSWORD=app
REDIS_URL=redis://redis:6379/1
# Intervalo de refresh do dashboard (segundos, padrão=60)
DASHBOARD_CACHE_REFRESH_INTERVAL=60
```

> Gere uma chave Fernet após o primeiro `up` com `docker compose exec web python manage.py generate_fernet_key --write` e armazene com segurança.

---

## 4. Primeira Execução
```powershell
docker compose up --build
```

O `docker-entrypoint.sh` executa automaticamente:
1. Espera por Redis e MariaDB
2. Aplica migrações Django
3. Coleta arquivos estáticos (`collectstatic`)
4. Inicia Gunicorn/Uvicorn

Após a subida:
- Aplicação: http://localhost:8000/
- Admin: http://localhost:8000/admin/
- Health check geral: http://localhost:8000/healthz

---

## 5. Tarefas Pós-Deploy
- Criar superusuário (caso não exista):
	```powershell
	docker compose exec web python manage.py ensure_superuser
	```
- Popular dados iniciais (opcional): execute comandos de carga ou fixtures via `docker compose exec web`.
- Validar estado dos workers Celery em `/celery/status`.

---

## 6. Comandos Essenciais
| Ação | Comando |
|------|---------|
| Ver status dos containers | `docker compose ps` |
| Ver logs em tempo real | `docker compose logs -f web` |
| Shell Django | `docker compose exec web python manage.py shell` |
| Aplicar migrações | `docker compose exec web python manage.py migrate` |
| Atualizar dependências Python | `docker compose exec web pip install -r requirements.txt` |
| Reiniciar apenas o worker Celery | `docker compose restart celery` |

---

## 7. Troubleshooting
- **Container não sobe:** verifique `.env`, portas ocupadas (`netstat -ano | findstr 8000`) e permissões de volume.
- **Erro de banco:** confira logs `docker compose logs db` e credenciais (`DB_*`).
- **Redis indisponível:** verifique `docker compose logs redis`; em ambientes Windows, revise [`doc/reference/SETUP_REDIS_WINDOWS.md`](../reference/SETUP_REDIS_WINDOWS.md).
- **Assets ausentes:** rode `docker compose exec web python manage.py collectstatic --noinput`.
- **Limpar stack:**
	```powershell
	docker compose down -v  # remove containers e volumes
	docker compose up --build
	```

---

## 8. Próximos Passos
- Ajuste configurações de produção seguindo [`doc/operations/DEPLOYMENT.md`](../operations/DEPLOYMENT.md).
- Configure observabilidade e alertas: [`doc/reference/prometheus_static_version.md`](../reference/prometheus_static_version.md) e [`doc/reference/PROMETHEUS_ALERTS.md`](../reference/PROMETHEUS_ALERTS.md).
- Revise a estratégia de Redis HA antes de ir para produção: [`doc/reference/REDIS_HIGH_AVAILABILITY.md`](../reference/REDIS_HIGH_AVAILABILITY.md).
