# 🏗️ Architecture Documentation

System design, module structure, and architecture decisions for MapsProveFiber v2.0.0.

---

## 📚 Architecture Documents

| Document | Description | Status | Audience |
|----------|-------------|--------|----------|
| **[OVERVIEW.md](OVERVIEW.md)** | Complete architecture v2.0.0 | ✅ Ready | All developers |
| **[MODULES.md](MODULES.md)** | ✅ **Django app structure** (updated 2025-11-07) | Ready | Backend developers |
| **[DATA_FLOW.md](DATA_FLOW.md)** | ✅ **Request flows and data patterns** (updated 2025-11-07) | Ready | Backend developers |
| **[ADR/](ADR/)** | Architecture Decision Records | Placeholder | Tech leads, architects |

### Recent Updates (2025-11-07)

- ✅ **MODULES.md** — Comprehensive documentation of all 10 Django apps:
  - Core infrastructure apps (core, inventory, maps_view, monitoring, setup_app)
  - Integration layer (integrations/zabbix with circuit breaker)
   - Archived apps (routes_builder retired in Nov/2025)
  - Future placeholders (dwdm, gpon, service_accounts)
  - Complete dependency graph and migration history
  
- ✅ **DATA_FLOW.md** — Complete data flow documentation:
  - Dashboard real-time updates (SWR + WebSocket + Celery)
  - Zabbix API integration (circuit breaker, retry, metrics)
  - Inventory sync (periodic Celery tasks)
  - Route building (async computation pipeline)
  - Cache hierarchy & degradation strategies
  - Performance SLAs and failure recovery scenarios

---

## 🎯 Quick Navigation

### Understanding the System

1. **Start here**: [OVERVIEW.md](OVERVIEW.md)
   - High-level architecture
   - Module responsibilities
   - Technology stack
   - Design principles

2. **Deep dive**: [MODULES.md](MODULES.md)
   - Each Django app in detail
   - Module interfaces
   - Dependencies
   - Data models

3. **Trace requests**: [DATA_FLOW.md](DATA_FLOW.md)
   - Request lifecycle
   - Data flow diagrams
   - Integration patterns
   - Caching strategy

4. **Understand decisions**: [ADR/](ADR/)
   - Why we made specific choices
   - Trade-offs and alternatives
   - Evolution of architecture

---

## 🏛️ Architecture Principles

MapsProveFiber v2.0.0 follows these core principles:

### 1. **Modularity**
- Each Django app has a single, clear responsibility
- Modules communicate through well-defined interfaces
- No circular dependencies

### 2. **Single Source of Truth**
- `inventory` app owns all authoritative data (Site, Device, Port, Route)
- Other modules read from inventory, never duplicate
- Zabbix is external data source, never authoritative

### 3. **Resilience**
- Graceful degradation when external services fail
- Circuit breaker pattern for Zabbix client
- Redis optional (in-memory fallback)
- Comprehensive error handling

### 4. **Observability**
- Prometheus metrics on all critical paths
- Health checks at multiple levels
- Structured logging
- Distributed tracing ready

### 5. **API-First**
- REST API as primary interface (`/api/v1/inventory/*`)
- Web UI built on top of API
- External integrations use same API
- Versioned endpoints

---

## 🗺️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      External Clients                        │
│  (Browser, CLI, Mobile App, External Systems)               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Django Core (core/)                       │
│  Settings, URLs, ASGI/WSGI, Channels Routing, Metrics      │
└─────┬───────────────────┬───────────────────┬──────────────┘
      │                   │                   │
      ▼                   ▼                   ▼
┌──────────┐      ┌──────────────┐    ┌──────────────┐
│inventory/│      │  maps_view/  │    │ monitoring/  │
│  (SSOT)  │◄─────┤ (Dashboard)  │◄───┤  (Health)    │
└────┬─────┘      └──────────────┘    └──────┬───────┘
     │                                        │
     │                                        ▼
     │                              ┌──────────────────┐
     │                              │ integrations/    │
     │                              │   zabbix/        │
     │                              │ (Resilient       │
     │                              │  Client)         │
     └──────────────────────────────┴──────────────────┘
```

See [OVERVIEW.md](OVERVIEW.md) for detailed diagrams.

---

## 📦 Module Overview

### Core Modules

| Module | Responsibility | Key Features |
|--------|----------------|--------------|
| **`inventory/`** | Authoritative data | Site, Device, Port, Route models; REST API |
| **`monitoring/`** | Health & status | Combine inventory + Zabbix; health checks |
| **`integrations/zabbix/`** | External API client | Circuit breaker, retry, metrics, cache |
| **`maps_view/`** | Real-time dashboard | WebSocket, SWR cache, live updates |
| **`core/`** | Django spine | Settings, URLs, metrics, routing |

### Legacy Modules (Deprecated)

| Module | Status | Migration Path |
|--------|--------|----------------|
| **`routes_builder/`** | ❌ Archived (Nov 2025) | Use `inventory/routes/` |
| **`zabbix_api/`** | ❌ Removed (v2.0.0) | Use `integrations/zabbix/` |

See [MODULES.md](MODULES.md) for complete module reference.

---

## 🔄 Data Flow Patterns

### Pattern 1: Dashboard Status Update

```
Browser ──websocket──> maps_view/consumers.py
                           │
                           ▼
                    monitoring/usecases.py
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
        inventory/models.py   integrations/zabbix/
        (authoritative)       (status enrichment)
                │                     │
                └──────────┬──────────┘
                           ▼
                   Combine & Return
```

### Pattern 2: API Request

```
Client ──HTTP──> core/urls.py
                     │
                     ▼
              inventory/api/views.py
                     │
                     ▼
              inventory/services/
                     │
                     ▼
              inventory/models.py
                     │
                     ▼
                 Database
```

See [DATA_FLOW.md](DATA_FLOW.md) for detailed flow diagrams.

---

## 📐 Architecture Decision Records (ADR)

ADRs document significant architectural decisions and their rationale.

**Current ADRs**:
- See [ADR/](ADR/) folder

**ADR Template**:
```markdown
# ADR-XXX: [Title]

**Status**: Accepted | Proposed | Deprecated  
**Date**: YYYY-MM-DD  
**Context**: Why we needed to make this decision  
**Decision**: What we decided  
**Consequences**: Trade-offs and implications  
**Alternatives**: Options we considered  
```

---

## 🔍 Key Architectural Decisions

### Why Modular Django Apps?

**Decision**: Separate Django apps for inventory, monitoring, integrations  
**Rationale**:
- Clear separation of concerns
- Independent testing and deployment
- Easier to reason about
- Supports future microservices migration

**Trade-offs**:
- More boilerplate (apps.py, admin.py, etc.)
- Requires discipline to avoid circular dependencies

---

### Why `inventory` as Single Source of Truth?

**Decision**: All authoritative data in `inventory` app  
**Rationale**:
- Prevents data duplication
- Clear ownership
- Simplifies consistency
- API-first design

**Trade-offs**:
- `inventory` becomes critical dependency
- Requires careful migration strategy

---

### Why Circuit Breaker for Zabbix?

**Decision**: Implement circuit breaker in `integrations/zabbix/client.py`  
**Rationale**:
- Zabbix downtime shouldn't kill dashboard
- Fast failure prevents cascading issues
- Improves user experience (graceful degradation)

**Trade-offs**:
- More complexity in client code
- Requires tuning (failure threshold, timeout)

See [ADR/](ADR/) for complete decision history.

---

## 🎓 Learning Path

**New to the architecture?** Follow this path:

1. **High-Level Overview** (30 min)
   - Read [OVERVIEW.md](OVERVIEW.md)
   - Understand module boundaries
   - Review design principles

2. **Module Deep Dive** (1 hour)
   - Read [MODULES.md](MODULES.md)
   - Explore `inventory/` code
   - Trace a simple API request

3. **Data Flows** (45 min)
   - Read [DATA_FLOW.md](DATA_FLOW.md)
   - Trace dashboard update flow
   - Understand caching strategy

4. **Decisions & Rationale** (30 min)
   - Browse [ADR/](ADR/)
   - Understand key trade-offs
   - Review alternatives considered

---

## 🔧 Architecture Evolution

### v1.x → v2.0.0 Migration

**Key Changes**:
- ❌ Removed `zabbix_api/` module
- ✅ Introduced `integrations/zabbix/` (resilient client)
- ✅ Consolidated routes in `inventory/routes/`
- ✅ API-first design (`/api/v1/inventory/*`)
- ✅ Service layer pattern

**Migration Guide**: [../releases/v2.0.0/BREAKING_CHANGES.md](../releases/v2.0.0/BREAKING_CHANGES.md)

---

## 📖 Related Documentation

- **[API Reference](../api/)** — REST API endpoints
- **[Operations Guide](../operations/)** — Deployment and monitoring
- **[Development Guide](../guides/DEVELOPMENT.md)** — Daily workflows
- **[Breaking Changes](../releases/v2.0.0/BREAKING_CHANGES.md)** — v2.0.0 migration

---

**Questions about architecture?** Check [ADR/](ADR/) or open a discussion issue.
