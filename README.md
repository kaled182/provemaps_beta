# 🛰️ MapsProveFiber — Guia Completo de Operação e Implantação

**MapsProveFiber** é um sistema Django que coleta telemetria do **Zabbix** e a apresenta em duas experiências web integradas:

- **🌍 Maps Dashboard (`/maps_view/dashboard/`)** — Exibe status em tempo real, disponibilidade de hosts e atalhos de diagnóstico.  
- **🧭 Fiber Route Builder (`/routes_builder/fiber-route-builder/`)** — Permite desenhar ou importar rotas ópticas (KML), monitorar potência óptica e gerenciar metadados de cabos.  

O projeto possui **observabilidade nativa** com métricas Prometheus, logs estruturados e análise de queries lentas.  
As **chaves e segredos** são gerenciadas de forma segura via painel `setup_app`, fora do repositório.

---

## ⚙️ 1. Requisitos

| Componente | Versão / Observações |
|-------------|----------------------|
| **Python** | 3.12+ (testado com 3.12) |
| **Node.js** | 18+ (toolchain do frontend) |
| **MariaDB/MySQL** | Banco principal (`mapspro_db`), log de queries lentas opcional |
| **Redis** | Broker/result backend do Celery (`redis://127.0.0.1:6379/0`) |
| **Celery Worker** | Necessário para tarefas assíncronas (snapshots ópticos, etc.) |
| **Prometheus (opcional)** | Coleta métricas em `/metrics/` para dashboards e alertas |

**Instalação das dependências:**
```bash
python -m venv .venv
source .venv/bin/activate         # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 🧩 2. Configuração de Ambiente

O projeto usa `django-environ` para gerenciar variáveis de ambiente.

1. Copie `.env.example` para `.env` e preencha credenciais (DB, Redis, API keys).  
2. Gere uma chave Fernet (usada para criptografia de segredos):
   ```bash
   python manage.py generate_fernet_key --write
   ```
3. Em produção, defina `ENV_FILE_PATH` apontando para o `.env` seguro.

**Principais variáveis:**
- `ENABLE_DIAGNOSTIC_ENDPOINTS` → habilita ping/telnet e diagnósticos ópticos.  
- `CHANNEL_LAYER_URL` → backend Channels (`redis://127.0.0.1:6379/1` em produção).  

### 🏥 Health Checks & Observabilidade

O projeto expõe três endpoints de saúde para monitoramento:

| Endpoint | Propósito | Uso |
|----------|-----------|-----|
| `/healthz` | Health check completo (DB, cache, storage, métricas) | Load balancer, status geral |
| `/ready` | Readiness probe (DB connectivity) | Kubernetes readinessProbe |
| `/live` | Liveness probe (processo ativo) | Kubernetes livenessProbe |

**Variáveis de configuração:**

```bash
# Modo de severidade (padrão: true = falhas em qualquer check resultam em 503)
HEALTHCHECK_STRICT=true

# Ignorar falhas de cache (útil em dev quando Redis está offline)
HEALTHCHECK_IGNORE_CACHE=false

# Timeout para verificação de DB em segundos (Unix/Linux apenas)
HEALTHCHECK_DB_TIMEOUT=5

# Limiar de espaço em disco em GB (padrão: 1 GB)
HEALTHCHECK_DISK_THRESHOLD_GB=1.0

# Habilitar/desabilitar verificação de storage
HEALTHCHECK_STORAGE=true

# Incluir métricas de sistema (CPU, memória) no payload
HEALTHCHECK_SYSTEM_METRICS=false

# Modo debug (força log mesmo quando healthy)
HEALTHCHECK_DEBUG=false
```

**Exemplos de uso:**

```bash
# Health check em modo não-estrito (apenas DB é crítico)
HEALTHCHECK_STRICT=false python manage.py runserver

# Desenvolvimento sem Redis (ignora falhas de cache)
HEALTHCHECK_IGNORE_CACHE=true python manage.py runserver

# Verificar status
curl http://localhost:8000/healthz
# Responde: HTTP 200 (ok) ou HTTP 503 (degraded)
```

**Prometheus Metrics:** `/metrics/metrics` expõe ~200 métricas (GC, requests, DB, cache).

---

## 🚀 3. Primeira Execução

1. Aplique migrações e colete os arquivos estáticos:
   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```
2. Crie o usuário administrador:
   ```bash
   python manage.py createsuperuser
   ```
3. Inicie os serviços:
   ```bash
   # Django (desenvolvimento)
   python manage.py runserver 0.0.0.0:8000

   # Worker Celery
   celery -A core worker -l info
   # Celery Beat (tarefas agendadas / tempo real)
   celery -A core beat -l info
   ```
4. Acesse `/setup_app/first_time/` para inserir credenciais e inicializar o ambiente.  

---

## 🛰️ 4. Operações Diárias

### Fiber Route Builder
- Desenhe ou importe KMLs de rotas ópticas.  
- Cada importação aciona atualização automática no painel.  

### Métricas & Logs
- `/metrics/` expõe métricas Prometheus (Django, MariaDB, Redis, Celery).  
- Logs estruturados em `logs/application.log` (rotação automática 5 MB).  
- Análise de queries lentas:
  ```bash
  python manage.py show_slow_queries --limit 10
  ```

### Dashboard em Tempo Real
- WebSocket `/ws/dashboard/status/` transmite status de hosts via Django Channels.  
- Fallback para HTTP periódico quando o socket estiver offline.  

### Checklist de Observabilidade
- Conectar `/metrics/` ao Prometheus/Grafana.  
- Automatizar análise de slow logs.  
- Integrar APM opcional para rastreamento Celery/HTTP.  

---

## 🧠 5. Diagnóstico e APIs

| Módulo | Responsabilidade |
|--------|------------------|
| `reports.py` | Leitura (hosts, problemas, cache) |
| `inventory.py` | CRUD de dispositivos/portas/cabos, importação KML |
| `diagnostics.py` | Ferramentas restritas (ping, telnet, mocks) |
| `lookup.py` | Autocompletes e consultas rápidas |

Endpoints são expostos via `zabbix_api/views.py` para compatibilidade retroativa.  
Documentação detalhada em [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md).

---

## 🧪 6. Testes

Execute:
```bash
python manage.py test tests setup_app
```

A suíte cobre configurações dinâmicas, guards de diagnóstico e APIs de inventário.  
Para Pytest:
```bash
pytest -v --disable-warnings
```

---

## 🏗️ 7. Implantação (Deploy)

1. Copie `.env.example` e preencha valores reais.  
2. Configure:
   ```env
   DEBUG=False
   ALLOWED_HOSTS=mapsprovefiber.yourdomain.com
   ```
3. Execute migrações e colete estáticos.  
4. Suba via Gunicorn/Uvicorn (ASGI).  
5. Inicie Celery Worker + Beat.  
6. Aponte Prometheus para `/metrics/`.  
7. Configure rotação de logs e backups.

Consulte [`DEPLOYMENT.md`](./DEPLOYMENT.md) para detalhes de automação e scripts.

---

## 💾 8. Backup e Empacotamento

O script PowerShell cria pacotes limpos para distribuição:
```powershell
pwsh scripts\package-release.ps1
```
Gera `dist/django-maps-release-YYYYmmddHHMM.zip`.  
Também é possível usar:
```powershell
Compress-Archive -Path * -DestinationPath dist\mapsprovefiber-backup.zip -Exclude *.pyc,*__pycache__*,.git*,.venv*,logs\*
```

---

## 🧭 9. Comandos Úteis

| Comando | Descrição |
|----------|-----------|
| `python manage.py show_slow_queries` | Verifica queries lentas |
| `python manage.py collectstatic` | Coleta arquivos estáticos |
| `celery -A core worker -l info` | Inicia worker Celery |
| `celery -A core beat -l info` | Inicia agendador Celery |
| `python manage.py shell_plus` | Shell ORM interativo |

---

## 📚 10. Referências

- [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md) — Endpoints REST  
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — Guia de contribuição  
- [`SECURITY.md`](./SECURITY.md) — Políticas de segurança e disclosure  
- [`DEPLOYMENT.md`](./DEPLOYMENT.md) — Estratégias de implantação  
- `docs/performance_phase*.md` — Melhorias progressivas e observabilidade  
- `docs/operations_checklist.md` — Checklist operacional  

---

## 🔧 Refatoração em andamento
- Casos de uso de fibras/inventário migrados para `zabbix_api/usecases`.  
- `inventory.py` atua agora apenas como camada HTTP.  
- Histórico documentado em `docs/refactor_fibers.md`.

---

## ✅ Testes rápidos
```bash
python -m pytest tests
```

## 📦 Gerar pacote
```bash
pwsh scripts/package-release.ps1
```

---

### © 2025 — Projeto **MapsProveFiber**
Mantido por Simples Internet.  
Documentação e código sob licença MIT.
