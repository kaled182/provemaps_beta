# Endpoints da API · ProVeMaps

Índice dos caminhos HTTP que existem no código. **Formas de pedido e resposta não estão aqui**: a referência viva é o Swagger autenticado em `/api/schema/swagger/` (OpenAPI 3, só cobre as rotas DRF) e, para as function views, o código indicado.

**Versão do produto**: ver [VERSION](../../VERSION) · **Versão da API**: `v1`

## Autenticação

- Pessoas: sessão Django + CSRF. Integrações: `Authorization: Bearer <token>` de conta de serviço (ADR 0008). Detalhe em [AUTHENTICATION.md](AUTHENTICATION.md).
- Tudo exige autenticação, exceto `/healthz`, `/ready`, `/live` e `/metrics/` (lista branca em `backend/core/middleware/auth_required.py:40-45`). `/api/*` sem credencial responde 401 JSON.
- Quem pode escrever ou diagnosticar (staff) é decidido em cada view; consulta o código da rota.
- As rotas `diagnostics/*` dependem ainda de `ENABLE_DIAGNOSTIC_ENDPOINTS` (`integrations/zabbix/guards.py`).

## Sondas e métricas (sem barra final)

`GET /healthz` · `GET /ready` · `GET /live` · `GET /celery/status` · `/metrics/` (Prometheus) — `backend/core/urls.py:64,115-118`.

## REST (DRF) — `/api/v1/`

Router em `backend/inventory/urls_rest.py:14-20`; incluído em `backend/core/urls.py:105`.

| Recurso | Caminho |
|---|---|
| Sites | `/api/v1/sites/` |
| Dispositivos | `/api/v1/devices/` |
| Grupos de dispositivos | `/api/v1/device-groups/` |
| Portas | `/api/v1/ports/` |
| Cabos | `/api/v1/fiber-cables/` |
| Regras de importação | `/api/v1/import-rules/` |

As ações extra de cada viewset (`optical-summary`, `topology`, `alarm-board`, …) estão em `backend/inventory/viewsets.py` e no Swagger.

Outros prefixos DRF: `/api/v1/monitoring/` (`hosts/status/`, `dashboard/snapshot/` — `backend/monitoring/urls_api.py`), `/api/v1/evolucao/`, `/api/v1/telemetry/`, `/api/v1/cameras/`.

## Inventário (function views) — `/api/v1/inventory/`

Definidas em `backend/inventory/urls_api.py`. Grupos:

| Grupo | Caminhos (relativos ao prefixo) |
|---|---|
| Dispositivos | `devices/<id>/`, `devices/<id>/ports/`, `devices/<id>/ports/live/`, `devices/<id>/ports/optical/`, `devices/grouped/`, `devices/zabbix-status/`, `devices/select-options/`, `devices/autocomplete/`, `devices/add-from-zabbix/`, `devices/import-batch/`, `sites/`, `bulk/` |
| Portas | `ports/<id>/optical/`, `ports/<id>/traffic/` |
| Zabbix | `zabbix/discover-hosts/`, `zabbix/lookup/hosts/`, `zabbix/lookup/hosts/grouped/`, `zabbix/lookup/hosts/<hostid>/status/`, `zabbix/lookup/hosts/<hostid>/interfaces/`, `zabbix/lookup/server-info/`, `zabbix/lookup/host-groups/` |
| Cabos | `fibers/`, `fibers/<id>/`, `fibers/<id>/oper-status/`, `fibers/oper-status/`, `fibers/<id>/live-status/`, `fibers/live-status/`, `fibers/<id>/cached-status/`, `fibers/<id>/cached-live-status/`, `fibers/<id>/refresh-optical/`, `fibers/refresh-status/`, `fibers/<id>/value-mapping/`, `fibers/<id>/audit-log/`, `fibers/<id>/photos/`, `fibers/<id>/move-folder/`, `fibers/<id>/force-delete/`, `fibers/delete-bulk/`, `fibers/import-kml/`, `fibers/manual-create/`, `fibers/validate-port/`, `fibers/validate-name/`, `fibers/validate-device-coords/`, `fibers/validate-nearby/` |
| Pastas, grupos e tipos de cabo; responsáveis | `cable-folders/`, `cable-groups/`, `cable-types/`, `responsibles/` (+ `create/`, `<id>/`, `<id>/delete/`) |
| Infraestrutura, fusões, rota | `infrastructure/`, `splice-boxes/<id>/matrix/`, `splice-boxes/<id>/context/`, `fusions/`, `trace-route/` |
| Rotas ópticas (tarefas) | `routes/tasks/{build,batch,bulk,import,invalidate,health}/`, `routes/tasks/status/<task_id>/` |
| Diagnóstico | `diagnostics/{telnet,ping,ping-telnet}/`, `diagnostics/cables/<id>/{up,down,unknown}/` |
| Sistema | `search/`, `system/{info,stats,check-update,perform-update}/`, `alarm-config-sources/`, `maintenance-alert/{recipients,send}/` |

Rotas que dependem de GDAL (divisão de cabo, CEO avulsa, pontas soltas) só existem com GDAL disponível (`urls_api.py:20-36`).

## Outros

- `/api/users/…`, `/api/groups/`, `/api/departments/` — `backend/core/urls.py:71-89`.
- `/api/config/` — configuração do frontend (autenticada) — `core/urls.py:110`.
- `/maps_view/api/dashboard/data/`, `/maps_view/api/dashboard/sites/` — `backend/maps_view/urls.py:16-17`.
- `/setup_app/api/…` — configuração, testes de ligação, backups, vídeo, etc.: `backend/setup_app/urls.py`.
- WebSocket `/ws/dashboard/status/` (sessão).
