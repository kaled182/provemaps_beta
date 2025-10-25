# Operações – Django Maps

Resumo rápido para administrar o ambiente em produção ou homologação.

## Serviços obrigatórios
- **Django / ASGI** (python manage.py runserver em dev / Daphne, Gunicorn+Uvicorn ou similar em producao).
- **MariaDB/MySQL** (mapspro_db) - configure backup (mysqldump).
- **Redis** - broker/result backend para Celery e Channels.
- **Camada Channels** - defina CHANNEL_LAYER_URL apontando para sua instancia Redis em producao (fallback in-memory somente para desenvolvimento).
- **Celery worker e beat** (celery -A core worker -l info + celery -A core beat -l info) para tarefas assincronas e transmissao em tempo real. No Windows acrescente --pool=solo.


## Monitoramento
- **Prometheus /metrics/metrics** – expõe ~200 métricas de Django, Celery, Redis e banco.
- **Health Checks** – `/healthz` (completo), `/ready` (readiness), `/live` (liveness).
- **Dashboard HTML** – `/maps_view/metrics/` facilita buscas rápidas.
- **Logs** – `logs/application.log` com `RotatingFileHandler` (5 × 5 MB).
- **Slow queries** – `python manage.py show_slow_queries --limit 10` lendo `MYSQL_SLOW_LOG_PATH` ou `--path` manual.

### Health Check Endpoints

| Endpoint | Finalidade | Status Code |
|----------|------------|-------------|
| `/healthz` | Verificação completa (DB, cache, storage, métricas de sistema) | 200 (ok), 503 (degraded) |
| `/ready` | Readiness probe (conectividade DB apenas) | 200 (ready), 503 (not ready) |
| `/live` | Liveness probe (processo Django ativo) | 200 (alive) |

**Configuração via variáveis de ambiente:**

```bash
# Modo estrito (padrão): falha em qualquer check resulta em 503
HEALTHCHECK_STRICT=true

# Ignorar falhas de cache (útil em dev sem Redis)
HEALTHCHECK_IGNORE_CACHE=false

# Timeout para verificação de DB (Unix/Linux, padrão 5s)
HEALTHCHECK_DB_TIMEOUT=5

# Limiar de espaço em disco (padrão 1 GB)
HEALTHCHECK_DISK_THRESHOLD_GB=1.0

# Controle de checks opcionais
HEALTHCHECK_STORAGE=true
HEALTHCHECK_SYSTEM_METRICS=false  # CPU/memória no payload
HEALTHCHECK_DEBUG=false           # força log mesmo quando ok
```

**Uso em Kubernetes/Docker:**

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

**Desenvolvimento sem Redis:**
```bash
HEALTHCHECK_IGNORE_CACHE=true python manage.py runserver
```

## Fluxos principais
- **Setup inicial**: `/setup_app/first_time/` (usa `FERNET_KEY`). Depois `Quick Actions` → `Configure System` para rotinas.
- **Importar KML**: botão “Import KML” no route builder. Modal aceita monitoração porta única.
- **Salvar rota manual**: desenhe no mapa, clique “Save” e preencha dispositivos/portas. Dropdown é limpo após cada criação.

## Checklist de deploy
1. Copiar `.env.example` → `.env`, gerar `FERNET_KEY` (`python manage.py generate_fernet_key --write`).
2. `python manage.py migrate` + `collectstatic`.
3. Criar superusuário (`createsuperuser`).
4. Configurar `DEBUG=False`, `ALLOWED_HOSTS`, TLS/CSRF.
5. Subir Celery worker e Celery beat (necessarios para tarefas agendadas e realtime).
6. Integrar Prometheus/Grafana ao `/metrics/`.
7. Revisar rotinas de backup (`mysqldump`, cópia do `.env` e do pacote gerado pelo script `scripts/package-release.ps1`).

## Rotinas de manutenção
- Verificar diariamente `/metrics/` ou painel Grafana.
- Rotacionar e coletar `logs/application.log` (já há rotação local).
- Rodar `python manage.py show_slow_queries` após janelas de manutenção do banco.
- Atualizar dependências com `pip install -r requirements.txt --upgrade` em ambiente controlado.

## Referências rápidas
- `README.md` – visão geral + onboarding.
- `API_DOCUMENTATION.md` – endpoints legados.
- `docs/performance_phase*.md` – evolução de performance/observabilidade.
- `docs/performance_phase6.md` – highlights atuais de observabilidade.

Manter este checklist atualizado ajuda a operar o Django Maps com previsibilidade em ambientes reais. Contributions são bem-vindas!
