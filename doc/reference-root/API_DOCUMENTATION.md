# 🧭 Documentação da API — MapsProveFiber

Este documento descreve todos os **endpoints REST** utilizados pelo MapsProveFiber, incluindo integração com **Zabbix**, **inventário local**, **rotas de fibra**, **tarefas Celery** e **probes de saúde**.  
Organizado por módulos, com foco em **claridade**, **segurança** e **diagnóstico rápido**.

---

## ⚙️ Estrutura dos módulos principais

| Módulo | Arquivo | Função principal |
|--------|----------|------------------|
| **Zabbix API** | `zabbix_api/` | Comunicação com Zabbix, diagnósticos e inventário |
| **Rotas de Fibra** | `routes_builder/` | Tarefas Celery para cálculo e cache de rotas |
| **Configuração inicial** | `setup_app/` | Gerenciamento do `.env` e variáveis do sistema |
| **Core** | `core/` | Núcleo Django, Celery, URLs e Health Checks |

---

## 🔐 Acesso e Segurança

- Todos os endpoints **exigem autenticação Django**.  
- Endpoints administrativos requerem **usuário staff**.
- Diagnósticos e execução de comandos são controlados por:
  ```bash
  ENABLE_DIAGNOSTIC_ENDPOINTS=true
  ```
  Quando desativado, as rotas retornam **HTTP 403** sem executar ações externas.

---

## 🌐 Base URL

```
http://localhost:8000/zabbix_api/
```

> Em produção, substitua `localhost` pelo domínio configurado.

---

## 🩺 Health & Status

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/healthz/` | GET | Health check completo (DB, cache, storage, sistema) |
| `/ready/` | GET | Readiness probe — pronto para receber tráfego |
| `/live/` | GET | Liveness probe — verifica se o processo está ativo |

**Exemplo de resposta:**
```json
{
  "status": "ok",
  "timestamp": 1731109200.123,
  "checks": {
    "db": {"ok": true, "type": "mysql"},
    "cache": {"ok": true, "backend": "RedisCache"},
    "storage": {"ok": true, "free_gb": 42.3}
  },
  "latency_ms": 23.6
}
```

---

## 🧩 Zabbix API

Endpoints organizados por categoria.  
Prefixo padrão: `/zabbix_api/`

### 📊 Status e Monitoramento

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/status/` | GET | Estado geral do ambiente Zabbix |
| `/monitoring/overview/` | GET | Visão global de hosts e problemas |
| `/monitoring/performance/` | GET | Métricas agregadas (CPU, memória, disco) |
| `/monitoring/availability/` | GET | Percentuais de uptime |
| `/monitoring/latest_all/` | GET | Últimos valores de todos os hosts |

---

### 🖥️ Hosts e Itens

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/hosts/` | GET | Lista hosts com metadados básicos |
| `/hosts/{id}/` | GET | Detalhes completos de um host |
| `/hosts/{id}/items/` | GET | Itens agrupados por categoria |
| `/hosts/{id}/triggers/` | GET | Triggers por severidade |
| `/hosts/{id}/graphs/` | GET | Gráficos disponíveis |
| `/hosts/{id}/latest/` | GET | Últimos valores de métricas |
| `/hosts/{id}/performance/` | GET | Performance (CPU, RAM, disco) |
| `/items/{hostid}/{itemid}/history/` | GET | Histórico de 24h do item |

---

### ⚠️ Problemas e Eventos

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/problems/` | GET | Problemas ativos |
| `/problems/summary/` | GET | Agrupamento por severidade |
| `/problems/by-severity/` | GET | Contagem por nível |
| `/problems/critical/` | GET | Apenas incidentes críticos |
| `/events/` | GET | Eventos recentes |
| `/events/recent/` | GET | Feed cronológico condensado |
| `/events/summary/` | GET | Distribuição por status/severidade |

---

### 🌐 Rede e Inventário

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/hosts/network-info/` | GET | Interfaces e IPs de todos os hosts |
| `/hosts/{id}/network-info/` | GET | Interfaces de um host específico |
| `/api/add-device-from-zabbix/` | POST | Cria dispositivo local com base no Zabbix |
| `/api/bulk-create-inventory/` | POST | Criação em massa de dispositivos |
| `/api/device-ports/{device_id}/` | GET | Lista portas do dispositivo |
| `/api/port-traffic-history/{port_id}/` | GET | Histórico de tráfego da porta |
| `/api/import-fiber-kml/` | POST | Importa topologia de fibra em KML |
| `/api/fiber/live-status/{cable_id}/` | GET | Estado atual do cabo |
| `/api/fiber/value-mapping-status/{cable_id}/` | GET | Mapeamento de valores (status) |

---

### 🧰 Ferramentas de Diagnóstico

> Disponíveis apenas quando `ENABLE_DIAGNOSTIC_ENDPOINTS=true` e o usuário é *staff*.

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/api/test/ping/` | GET | Teste de ping remoto |
| `/api/test/telnet/` | GET | Teste de porta via Telnet |
| `/api/test/ping_telnet/` | GET | Ping + Telnet combinados |
| `/api/test/cable-up/{id}/` | POST | Marca cabo como ativo |
| `/api/test/cable-down/{id}/` | POST | Marca cabo como inativo |

---

### 🔍 Endpoints de Lookup

Usados por **autocompletes** e **widgets interativos**.

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/lookup/hosts/` | GET | Busca leve por hosts |
| `/lookup/hosts/{id}/interfaces/` | GET | Interfaces de um host |
| `/lookup/interfaces/{id}/details/` | GET | Detalhes de interface |

---

## 🛰️ Routes Builder — API de Tarefas

Prefixo: `/routes/tasks/`

| Endpoint | Método | Descrição |
|-----------|---------|-----------|
| `/tasks/build/` | POST | Enfileira cálculo de rota |
| `/tasks/batch/` | POST | Enfileira múltiplas rotas |
| `/tasks/invalidate/` | POST | Invalida cache da rota |
| `/tasks/health/` | GET | Health check do worker |
| `/tasks/status/{task_id}/` | GET | Consulta status de uma task |
| `/tasks/bulk/` | POST | Executa operações em massa (build + invalidate) |

**Exemplo:**
```json
{
  "route_id": 12,
  "force": true,
  "options": {"recalc_topology": true}
}
```
Resposta:
```json
{
  "status": "enqueued",
  "task_id": "a23b9cfa-22bb-44c8-8c1f-bcd56f0",
  "queue": "maps"
}
```

---

## 🧱 Estrutura de Erros Padrão

| Código | Tipo | Descrição |
|--------|------|-----------|
| **400** | `Bad Request` | JSON inválido ou parâmetros ausentes |
| **401** | `Unauthorized` | Usuário não autenticado |
| **403** | `Forbidden` | Sem permissão ou diagnósticos desativados |
| **404** | `Not Found` | Recurso inexistente |
| **409** | `Conflict` | Rota bloqueada por outro processo |
| **500** | `Server Error` | Falha interna — ver logs Celery/Django |

---

## 🧠 Boas Práticas

- Utilize `HTTP 202` para operações assíncronas.
- Sempre valide `task_id` antes de consultar status.
- Use `DEBUG=false` em produção.
- Monitore workers com:
  ```bash
  celery -A core.celery_app inspect active
  ```
