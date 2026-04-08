# ProVeMaps

**Versão:** 1.4.1  
**Status:** 🚧 Beta ativo — funcionalidades em produção, desenvolvimento contínuo

ProVeMaps é uma plataforma full-stack para gestão de infraestrutura de redes de fibra óptica. Combina um backend Django 5.x com um frontend Vue 3 para monitoramento em tempo real via integração Zabbix, gerenciamento de inventário físico e fluxos de campo (fusões, rastreamento de rota, câmeras).

---

## ✨ Funcionalidades principais

- **📡 Dashboard de rede em tempo real** — Mapa interativo com status live via WebSocket (Google Maps / Mapbox)
- **🔌 Inventário físico completo** — Sites, dispositivos, portas, cabos de fibra, rotas e segmentos com PostGIS
- **📊 Integração Zabbix** — Client resiliente com circuit breaker, retry exponencial, cache e métricas Prometheus
- **🔬 Gestão de fusões** — Splice matrix, view de cabo despojado, rastreamento de rota por fibra
- **🚨 Configuração de alarmes** — Templates de alerta por categoria/canal (WhatsApp, SMS, e-mail, Telegram)
- **📈 Tráfego e sinal óptico** — Gráficos IN/OUT e nível óptico com exportação PNG/PDF
- **📥 Importação em lote** — Import de devices via KML com regra de proximidade 100 m anti-duplicatas
- **🎥 Câmeras e vídeo** — Player integrado, suporte HLS, gateway de vídeo configurável
- **⚡ Processamento assíncrono** — Celery workers + beat scheduler para tarefas em background
- **🔔 Notificações e contatos** — Gestão de grupos de contatos e templates de mensagem
- **🛠️ Setup Wizard** — Configuração inicial com credenciais criptografadas (Fernet)
- **📚 Observabilidade** — Prometheus metrics, health checks, logging estruturado, request tracing

---

## 🏛️ Arquitetura

### Backend (Django 5.x + Python 3.12)

| App | Responsabilidade |
|---|---|
| `core/` | Settings, URLs root, ASGI/WSGI, middleware, auth (2FA TOTP), health checks |
| `inventory/` | Modelos de domínio (Site, Device, Port, FiberCable, Route, RouteSegment) + REST API `/api/v1/inventory/*` |
| `monitoring/` | Combinação status Zabbix + inventário, health checks de dispositivos |
| `integrations/zabbix/` | Client Zabbix com circuit breaker, pool de conexões, métricas |
| `maps_view/` | Views do dashboard, publisher WebSocket, cache SWR |
| `setup_app/` | Configuração runtime, credenciais criptografadas, docs viewer, gateways de notificação |
| `dwdm/` | Modelos específicos para equipamentos DWDM |
| `gpon/` | Modelos específicos para redes GPON |
| `telemetry/` | Coleta e armazenamento de dados de telemetria |

### Frontend (Vue 3 + Vite)

Componentes principais:

- **`MapView.vue`** — Mapa interativo principal (Google Maps / Mapbox)
- **`DeviceDetailsModal.vue`** — Detalhes, tráfego e sinal óptico de dispositivos
- **`FiberCableDetailModal.vue`** — Detalhes de cabo com gráficos de tráfego e export
- **`Fusion/`** — Splice matrix e view de cabo despojado
- **`TraceRoute/`** — Rastreamento de rota por fibra
- **`DeviceImport/`** — Import em lote com mapa de preview
- **`AlarmConfigModal.vue`** — Configuração de alarmes por dispositivo
- **`Video/`** — Player de câmeras HLS

### Banco de dados

PostgreSQL 15 + PostGIS para dados geoespaciais.

```
inventory_site               # Localizações físicas (com coordenadas geográficas)
inventory_device             # Equipamentos de rede (OLTs, switches, roteadores)
inventory_port               # Interfaces de dispositivos
inventory_fibercable         # Conexões de fibra entre portas
inventory_route              # Rotas planejadas/ativas
inventory_routesegment       # Segmentos de rota
setup_alert_templates        # Templates de mensagens de alerta
setup_contacts               # Contatos para notificações
```

### Integrações externas

- **Zabbix** — Monitoramento de rede (API v6.x+)
- **Redis** — Cache e broker Celery (degradação graciosa se indisponível)
- **Prometheus + Grafana** — Métricas e dashboards
- **Google Maps / Mapbox** — Renderização do mapa

---

## 🚀 Quick Start (Docker)

### Pré-requisitos
- Docker e Docker Compose
- Linux (Debian/Ubuntu recomendado para produção)

### Subir ambiente local

```bash
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta

# Iniciar todos os serviços
cd docker
docker compose up -d

# Verificar saúde
curl http://localhost:8100/healthz
```

**Credenciais padrão:**
- Admin: http://localhost:8100/admin — `admin` / `admin123` ⚠️ Troque após o primeiro acesso

**Portas dos serviços:**

| Serviço | Porta |
|---|---|
| Django Web | `8100` |
| PostgreSQL | `5433` |
| Redis | `6380` |
| Prometheus | `9090` |
| Grafana | `3002` |
| Video HLS | `8083` |
| WhatsApp QR | `3001` |

### Build do frontend

```bash
# Na raiz do projeto (fora do Docker)
npm install
npm run build
```

---

## 🧪 Testes

```bash
# Dentro do container
docker compose exec web python -m pytest -q

# Com cobertura
docker compose exec web bash -c "coverage run -m pytest -q && coverage report"

# App específico
docker compose exec web python -m pytest inventory/tests/ -v
```

**Estado atual dos testes:**
- **971 testes passando** (0 falhas)
- **Cobertura:** 60% (threshold mínimo do CI)
- **Pre-push hook:** executa suite de testes críticos automaticamente antes de cada push

---

## 📡 API

### Inventory REST API (`/api/v1/inventory/`)

```
GET/POST   /api/v1/inventory/sites/
GET/POST   /api/v1/inventory/devices/
PATCH      /api/v1/inventory/devices/<id>/
GET/POST   /api/v1/inventory/ports/
GET/POST   /api/v1/inventory/fibers/
GET        /api/v1/inventory/fibers/oper-status/   # status operacional (cached)
GET/POST   /api/v1/inventory/routes/
GET        /api/v1/inventory/spatial/radius/        # busca geoespacial por raio
```

### Setup App API (`/setup_app/api/`)

```
GET        /setup_app/api/config/
POST       /setup_app/api/config/update/
GET        /setup_app/api/company-profile/
GET/POST   /setup_app/api/monitoring-servers/
GET/POST   /setup_app/api/gateways/
GET        /setup_app/api/audit-history/
GET/POST   /setup_app/api/alert-templates/    # DRF ViewSet (CRUD completo)
GET/POST   /setup_app/api/contacts/           # DRF ViewSet (CRUD completo)
```

### Health & Observabilidade

```
GET /healthz          # health check básico (DB)
GET /ready            # readiness probe
GET /live             # liveness probe
GET /celery/status    # status dos workers
GET /metrics/         # Prometheus scrape endpoint
```

---

## ⚙️ Configuração

### Variáveis de ambiente principais

```bash
# Django
SECRET_KEY=sua-chave-secreta
DEBUG=False
ALLOWED_HOSTS=seu-dominio.com
DJANGO_SETTINGS_MODULE=settings.prod

# Banco de dados (PostgreSQL + PostGIS)
DB_HOST=postgres
DB_PORT=5432
DB_NAME=mapsprovefiber
DB_USER=mapsprove_user
DB_PASSWORD=senha_segura

# Zabbix
ZABBIX_API_URL=https://zabbix.seudominio.com/api_jsonrpc.php
ZABBIX_API_KEY=sua_api_key          # Zabbix 6.4+
# ou usuário/senha:
ZABBIX_API_USER=usuario
ZABBIX_API_PASSWORD=senha

# Redis
REDIS_URL=redis://redis:6379/0

# Mapas
GOOGLE_MAPS_API_KEY=sua_chave_google_maps

# Criptografia (credenciais runtime)
FERNET_KEY=sua_fernet_key
# Gerar: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Segurança (produção)
SECURE_SSL_REDIRECT=True
CSRF_TRUSTED_ORIGINS=https://seu-dominio.com
```

### Settings modules

- `settings.dev` — Desenvolvimento (DEBUG=True, SQLite opcional)
- `settings.test` — Testes (banco em memória, logging mínimo)
- `settings.prod` — Produção (HTTPS forçado, hardened)

---

## 🛡️ Segurança

- Credenciais runtime criptografadas com Fernet (nunca no `.env`)
- 2FA TOTP opcional por usuário
- Middleware de autenticação obrigatória em todas as rotas (whitelist configurável)
- Security headers: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- CSRF protection com trusted origins
- Audit log de todas as alterações de configuração

---

## 📋 Changelog recente

| Versão | Data | Destaques |
|---|---|---|
| **1.4.1** | 2026-04-03 | Paleta de cores do menu unificada, status WebSocket compacto |
| **1.4.0** | 2026-04-03 | Import em lote de devices, regra 100 m anti-duplicatas, Modal de Changelog |
| **1.3.0** | 2026-03-28 | Gráficos de tráfego IN/OUT, export PNG/PDF, carregamento paralelo nos modais |
| **1.2.0** | 2026-03-15 | Painel de detalhes de cabo, lazy-load de providers de mapa |
| **2.0.0** | 2025-01-07 | Refatoração interna — migração `zabbix_api/` → `inventory/` + `integrations/` |

Histórico completo: [CHANGELOG.md](./CHANGELOG.md)

---

## 📞 Suporte

- 🐛 **Bugs**: [GitHub Issues](https://github.com/kaled182/provemaps_beta/issues)
- 📧 **Contato**: maintainers@simplesinternet.com

---

**© 2025-2026 — ProVeMaps by Simples Internet**  
Django 5.x · Vue 3 · PostgreSQL + PostGIS · Docker
