# MapsProveFiber

**Version:** 2.1.0 (Production Package Release)  
**Status:** ✅ Production-ready with Docker deployment automation

MapsProveFiber is a Django 5.x platform for fiber optic network infrastructure management, integrating real-time monitoring with Zabbix telemetry and advanced route planning capabilities.

## Core Features
- 🗺️ **Real-time Network Dashboard** — Live status visualization with WebSocket updates
- 🔌 **Fiber Route Management** — KML import, power budget analysis, and segment workflows
- 📊 **Zabbix Integration** — Resilient API client with circuit breaker, retry logic, and caching
- 🏗️ **Inventory Management** — Authoritative models for Sites, Devices, Ports, Routes, and Fiber Cables
- 📈 **Observability** — Prometheus metrics, health checks, structured logging, and request tracing
- ⚡ **Async Processing** — Celery workers for background tasks and Channels for real-time WebSocket
- 🐳 **Docker Production** — One-command deployment with automated SSL, backup, and monitoring
- 🎨 **First-Time Setup Wizard** — Modern UI for initial configuration with encrypted credential storage

---

## 🏛️ Architecture (v2.0 — Modular)

### Django Apps Structure
- **`core/`** — Settings, root URLs, ASGI/WSGI, Channels routing, middleware, health checks
- **`inventory/`** — Authoritative domain models (Site, Device, Port, Route, FiberCable, etc.)
  - REST APIs at `/api/v1/inventory/*`
  - Usecases, services, domain logic, cache management
- **`monitoring/`** — Health checks, combined Zabbix + inventory status
  - Usecases: `get_devices_with_zabbix()`, `build_zabbix_map()`, `process_host_status()`
- **`integrations/zabbix/`** — Resilient Zabbix API client
  - Circuit breaker, exponential backoff, connection pooling
  - Prometheus metrics for API calls, failures, cache hits
- **`maps_view/`** — Network dashboard views and real-time WebSocket publisher
  - SWR cache pattern for dashboard data
  - Templates and static assets for map visualization
- *(Legacy `routes_builder/` assets have been retired; route logic now lives in `inventory.models_routes`.)*
- **`setup_app/`** — Runtime credentials, encrypted settings (Fernet), documentation viewer

### Database Schema (Post-Migration)
```
inventory_site               # Physical locations
inventory_device             # Network devices (OLTs, switches, routers)
inventory_port               # Device interfaces
inventory_fibercable         # Fiber connections between ports
inventory_route              # Planned/active fiber routes (renamed from routes_builder_route)
inventory_routesegment       # Route segments (renamed from routes_builder_routesegment)
inventory_routeevent         # Route change events (renamed from routes_builder_routeevent)
```

### External Integrations
- **Zabbix** — Network monitoring platform (API v6.x+)
- **Redis** — Cache and Celery broker (optional; graceful degradation if unavailable)
- **Prometheus** — Metrics scraping endpoint at `/metrics/`

---

## 🚀 Quick Start

### Prerequisites
- **Production**: Linux (Debian/Ubuntu), Docker & Docker Compose
- **Development**: Python 3.11+, MariaDB/MySQL or SQLite, Redis (optional)

### Production Deployment (Docker - Recommended) 🐳

**One-command installation** for Linux production servers:

```bash
# Clone repository
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta

# Run automated installation
chmod +x scripts/deploy-docker.sh
sudo ./scripts/deploy-docker.sh install

# Access your system
# https://your-domain.com → First-Time Setup Wizard
```

**Duration**: 10-15 minutes (fully automated)

**Includes**:
- ✅ Nginx with SSL/TLS (Let's Encrypt)
- ✅ PostgreSQL 15 + PostGIS
- ✅ Redis cache
- ✅ Django + Celery workers
- ✅ Auto-migrations
- ✅ Health checks
- ✅ Backup automation

📚 **Full guide**: [Docker Production Deployment](./doc/operations/DOCKER_PRODUCTION.md)

### Local Development (Docker)
```bash
# Clone repository
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta

# Copy environment template
cp .env.example .env

# Edit .env with your Zabbix credentials
# ZABBIX_API_URL=http://your-zabbix-server/api_jsonrpc.php
# ZABBIX_API_USER=your_user
# ZABBIX_API_PASSWORD=your_password

# Start all services
docker compose up -d

# Check health
curl http://localhost:8000/healthz
```

### Local Development (Manual)
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver

# In separate terminals:
celery -A core worker --loglevel=info
celery -A core beat --loglevel=info
```

### First-Time Setup Wizard 🎨

After installation, access your domain and you'll be **automatically redirected** to the setup wizard:

1. **Access**: `https://your-domain.com` → `/setup_app/first_time/`
2. **Configure** (modern UI with dark mode):
   - 🏢 Company info (name, logo)
   - 📊 Zabbix integration (URL, API token)
   - 🗺️ Google Maps API key
   - 🔑 License key
3. **Save** → Credentials encrypted with Fernet
4. **Redirect** → Dashboard ready!

**Features**:
- Modern gradient design (blue → emerald)
- Dark mode synchronized with dashboard
- Visual cards per section
- Encrypted credential storage
- One-time configuration lock

---

## 📡 API Endpoints

### Inventory API (`/api/v1/inventory/`)
- `GET /api/v1/inventory/sites/` — List all sites
- `GET /api/v1/inventory/devices/` — List devices (with Zabbix status)
- `GET /api/v1/inventory/ports/` — List ports
- `GET /api/v1/inventory/fibers/` — List fiber cables
- `GET /api/v1/inventory/fibers/oper-status/` — Fiber operational status (cached)
- `POST /api/v1/inventory/fibers/` — Create fiber cable
- `PUT /api/v1/inventory/fibers/<id>/` — Update fiber cable
- `DELETE /api/v1/inventory/fibers/<id>/` — Delete fiber cable

### Health & Observability
- `GET /healthz` — Basic health check (database connectivity)
- `GET /ready` — Readiness probe (services ready to accept traffic)
- `GET /live` — Liveness probe (application is alive)
- `GET /celery/status` — Celery workers health
- `GET /metrics/` — Prometheus metrics endpoint

### Legacy Endpoints (⚠️ Deprecated)
- `/zabbix_api/*` — **REMOVED in v2.0.0** (use `/api/v1/inventory/*`)
- `/routes_builder/api/*` — **REMOVED in v2.0.0** (use inventory APIs)

---

## 🔧 Configuration

### Environment Variables (Production)
```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database
DB_ENGINE=mysql  # or postgresql
DB_NAME=mapsprovefiber
DB_USER=mapsprove_user
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=3306

# Zabbix
ZABBIX_API_URL=https://zabbix.yourdomain.com/api_jsonrpc.php
ZABBIX_API_USER=zabbix_api_user
ZABBIX_API_PASSWORD=zabbix_api_password
# Or use API key (Zabbix 6.4+)
ZABBIX_API_KEY=your_api_key_here

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CSRF_TRUSTED_ORIGINS=https://yourdomain.com

# Google Maps (optional)
GOOGLE_MAPS_API_KEY=your_google_maps_key

# Fernet Encryption
FERNET_KEY=your_fernet_key  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Django Settings Modules
- `settings.dev` — Development (DEBUG=True, SQLite default)
- `settings.test` — Testing (in-memory database, minimal logging)
- `settings.prod` — Production (HTTPS enforced, security hardened)

Set via: `DJANGO_SETTINGS_MODULE=settings.prod`

---

## 🧪 Testing

### Run Full Test Suite
```bash
# All tests
pytest -q

# With coverage
pytest --cov --cov-report=term-missing

# Specific app
pytest inventory/tests/ -v

# Parallel execution
pytest -n auto
```

### Test Results (v2.0.0)
- **199 tests passing** (100% success rate)
- Coverage: ~85% (excluding migrations and static files)
- Test execution time: ~116 seconds

---

---

## 📚 Documentation

Comprehensive documentation is available at `/setup_app/docs/` or in the `doc/` directory.

### Key Documents

#### Getting Started
- 🚀 **[Quick Start Guide](./doc/getting-started/QUICKSTART.md)** — Get started in 5 minutes
- 📦 **[Installation Guide](./doc/getting-started/INSTALLATION_GUIDE.md)** — Complete installation manual (14 steps)
- 🐳 **[Docker Production](./doc/operations/DOCKER_PRODUCTION.md)** — One-command Docker deployment

#### Architecture & Development
- 🏗️ **[Architecture Overview](./doc/architecture/OVERVIEW.md)** — System design and modules
- 🛠️ **[Development Guide](./doc/guides/DEVELOPMENT.md)** — Local development workflow
- 🔄 **[Migration Guide](./doc/developer/REFATORAR.md)** — v1.x → v2.0 migration (Phases 0-5)

#### Testing & Quality
- 🧪 **[Testing Guide](./doc/testing/TESTING_GUIDE.md)** — Complete testing documentation (600+ lines)
- 📊 **[Testing Structure](./doc/testing/README.md)** — Test organization overview
- 📝 **[Testing Index](./doc/testing/INDEX.md)** — Navigation guide

#### Operations & Deployment
- 🚢 **[Deployment Guide](./doc/operations/DEPLOYMENT.md)** — Production deployment steps
- 🐳 **[Docker Setup](./doc/developer/DOCKER_SETUP.md)** — Containerized environment
- 📡 **[API Reference](./doc/api/ENDPOINTS.md)** — Complete endpoint documentation

#### Security
- 🔒 **[Security Practices](./doc/security/SECURITY.md)** — Security hardening guide

### Breaking Changes (v2.0.0)
⚠️ **Important**: Version 2.0.0 introduces significant architectural changes. See:
- **[Breaking Changes v2.0.0](./doc/releases/v2.0.0/BREAKING_CHANGES_v2.0.0.md)**
- **[Migration Playbook](./doc/developer/REFATORAR.md#guia-de-migração-para-desenvolvedores--fase-5)**

**Key Changes:**
- Removed `/zabbix_api/*` endpoints → Use `/api/v1/inventory/*`
- Renamed database tables: `routes_builder_route*` → `inventory_route*`
- Removed `zabbix_api` app completely
- Retired `routes_builder` app; route services now consolidated under `inventory`

---

## 🔍 Observability & Monitoring

### Health Checks
```bash
# Basic health (database connectivity)
curl http://localhost:8000/healthz

# Readiness probe (all services ready)
curl http://localhost:8000/ready

# Liveness probe (application alive)
curl http://localhost:8000/live

# Celery workers status
curl http://localhost:8000/celery/status
```

### Prometheus Metrics
```bash
# Scrape endpoint
curl http://localhost:8000/metrics/

# Key metrics:
# - django_http_requests_total_by_view_transport_method
# - django_http_responses_total_by_status
# - celery_task_duration_seconds
# - zabbix_api_requests_total
# - zabbix_api_errors_total
# - zabbix_circuit_breaker_state
```

### Logs & Tracing
- Structured JSON logging to `logs/app.log`
- Request ID tracing via `X-Request-ID` header
- Celery task execution logs
- Zabbix API client debug logs

---

## 🛡️ Security

### Best Practices Implemented
- ✅ **No hard-coded credentials** — All secrets via environment variables
- ✅ **Encrypted storage** — Fernet encryption for sensitive runtime config
- ✅ **HTTPS enforcement** — `SECURE_SSL_REDIRECT` in production
- ✅ **HSTS enabled** — 1-year HSTS with subdomains and preload
- ✅ **CSP headers** — Content Security Policy middleware
- ✅ **CSRF protection** — Django CSRF with trusted origins
- ✅ **SQL injection prevention** — Django ORM with parameterized queries
- ✅ **XSS protection** — Template auto-escaping enabled
- ✅ **Dependency scanning** — Regular `pip-audit` checks

### Security Audit Results (Phase 5)
- ✅ **0 hard-coded credentials** in production code
- ✅ **0 deprecation warnings** (Django 5.x compatible)
- ✅ **0 N+1 queries** detected (all queries optimized with `select_related`)
- ✅ **100% test coverage** for authentication and authorization

See [Security Audit Report](./doc/developer/REFATORAR.md#-auditorias-de-segurança-e-performance--fase-5)

---

## 🚀 Deployment

### Docker Production Commands

```bash
# Gerenciamento
sudo ./scripts/deploy-docker.sh start         # Iniciar containers
sudo ./scripts/deploy-docker.sh stop          # Parar containers
sudo ./scripts/deploy-docker.sh restart       # Reiniciar containers
sudo ./scripts/deploy-docker.sh status        # Ver status

# Logs
sudo ./scripts/deploy-docker.sh logs          # Todos os logs
sudo ./scripts/deploy-docker.sh logs web      # Logs do Django
sudo ./scripts/deploy-docker.sh logs nginx    # Logs do Nginx

# Atualização
sudo ./scripts/deploy-docker.sh update        # Atualizar código + rebuild

# Banco de dados
sudo ./scripts/deploy-docker.sh backup        # Backup PostgreSQL
sudo ./scripts/deploy-docker.sh restore <file> # Restore backup

# Django
sudo ./scripts/deploy-docker.sh migrate       # Executar migrations
sudo ./scripts/deploy-docker.sh collectstatic # Coletar static files
sudo ./scripts/deploy-docker.sh createsuperuser # Criar admin

# SSL
sudo ./scripts/deploy-docker.sh ssl           # Configurar Let's Encrypt

# Shell
sudo ./scripts/deploy-docker.sh shell         # Bash no container Django
```

### Production Checklist
- [ ] Set `DEBUG=False` and `SECRET_KEY` from secure vault
- [ ] Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- [ ] Enable HTTPS with `SECURE_SSL_REDIRECT=True`
- [ ] Apply database migrations: `python manage.py migrate`
- [ ] Collect static files: `python manage.py collectstatic --noinput`
- [ ] Configure Redis for caching and Celery broker
- [ ] Set up Celery workers and beat scheduler
- [ ] Configure reverse proxy (nginx/Caddy) for static files
- [ ] Set up monitoring (Prometheus + Grafana)
- [ ] Configure backup strategy for database
- [ ] Test all health endpoints and metrics

### Migration from v1.x to v2.0
```bash
# 1. Backup database
mysqldump -u user -p mapsprovefiber > backup_pre_v2.sql

# 2. Verify pre-migration state
python scripts/migration_phase5_verify.py --phase pre --snapshot pre.json

# 3. Apply migrations
python manage.py migrate

# 4. Verify post-migration state
python scripts/migration_phase5_verify.py --phase post --compare pre.json

# 5. Restart services
systemctl restart mapsprovefiber
systemctl restart celery-worker
systemctl restart celery-beat
```

See [Complete Deployment Playbook](./doc/developer/REFATORAR.md#playbook-de-deploy-em-produção--fase-5)

---

## 🤝 Contributing

We welcome contributions! Please read:
- [Contributing Guidelines](./doc/contributing/README.md)
- [Code Style Guide](./doc/contributing/CODE_STYLE.md)
- [PR Guidelines](./doc/contributing/PR_GUIDELINES.md)
- [Testing Standards](./doc/contributing/TESTING_STANDARDS.md)

### Development Workflow
```bash
# 1. Fork and clone repository
git clone https://github.com/YOUR_USERNAME/provemaps_beta.git

# 2. Create feature branch
git checkout -b feature/your-feature-name

# 3. Make changes and add tests
# ... code ...

# 4. Run tests and linting
pytest -q
make lint
make fmt

# 5. Commit and push
git commit -m "feat: add your feature description"
git push origin feature/your-feature-name

# 6. Open Pull Request against 'inicial' branch
```

---

## 📊 Project Status

### Version 2.1.0 (Current)
- ✅ **199/199 tests passing** (100%)
- ✅ **Modular architecture** complete (Phases 0-5)
- ✅ **Security audits** passed (0 vulnerabilities)
- ✅ **Performance optimized** (0 N+1 queries)
- ✅ **Docker Production** deployment ready
- ✅ **First-Time Setup Wizard** with modern UI
- ✅ **Comprehensive testing documentation** (1000+ lines)
- ✅ **One-command installation** script
- ✅ **SSL auto-renewal** with Let's Encrypt

### Version 2.0.0 (Previous)
- ✅ Modular architecture refactor
- ✅ Production-ready deployment playbook

### Roadmap
- 🔄 PostGIS integration for spatial queries
- 🔄 Advanced catalog management
- 🔄 Multi-tenant support
- 🔄 GraphQL API
- 🔄 Mobile-responsive dashboard
- 🔄 Advanced monitoring dashboards (Grafana)

---

## 📞 Support

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/kaled182/provemaps_beta/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/kaled182/provemaps_beta/discussions)
- 🔒 **Security**: See [Security Policy](./doc/security/SECURITY.md)
- 📧 **Contact**: maintainers@simplesinternet.com

---

## 📄 License

MIT License - see [LICENSE](./LICENSE) file for details.

---

## 🙏 Acknowledgments

- Django Software Foundation for the excellent framework
- Zabbix for monitoring capabilities
- Contributors and maintainers of all dependencies

---

**© 2025 — MapsProveFiber by Simples Internet**  
Built with ❤️ using Django 5.x
