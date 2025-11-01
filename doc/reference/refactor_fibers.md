# Refatoracao dos Fluxos de Fibras e Inventario

## Iteracao 1 (concluida)
- Helper de optica movido para `zabbix_api/domain/optical.py`.
- Calculos geograficos/Haversine movidos para `zabbix_api/domain/geometry.py`.
- Caso de uso principal em `zabbix_api/usecases/fibers.py` cobre importacao KML, criacao manual, status em tempo real e refresh em massa.
- Views de fibras (`zabbix_api/inventory_fibers.py`) agora apenas traduzem `HttpRequest` -> JSON usando os usecases.
- Tratamento padronizado de erros (`FiberValidationError`, `FiberUseCaseError`).

## Iteracao 2 (inventario) – progresso
- `zabbix_api/usecases/inventory.py` centraliza device/port/site, discovery e historicos com erros tipados (`InventoryNotFound`, `InventoryValidationError`).
- Views de inventario (`api_device_*`, `api_sites`, `api_port_traffic_history`, `api_add_device_from_zabbix`) sao wrappers finos que delegam para os usecases.
- Tasks/commands (`zabbix_api/tasks.py`, `management/commands/warm_optical_cache.py`) reutilizam `_fetch_port_optical_snapshot` da camada de dominio.
- `zabbix_api/inventory.py` manteve compatibilidade (aliases de `combine_cable_status`, `zabbix_request`) e passou a reutilizar `staff_guard` apenas onde necessario.

## Pendencias previstas no cronograma
1. Extrair `api_update_cable_oper_status` para um usecase em `zabbix_api/usecases/fibers.py`, reduzindo acesso direto a modelos em views.
2. Revisar `api_zabbix_discover_hosts` e `api_bulk_create_inventory` para validacao granular, feedback parcial e logs estruturados.
3. Adicionar testes unitarios especificos para `usecases/fibers.py` e `usecases/inventory.py` (cenarios de erro, modo incremental de trafego, discovery sem itens).
4. Seguir com a modularizacao de `zabbix_service` (enderecar geolocalizacao e ping em modulos dedicados) conforme proxima etapa do cronograma.
