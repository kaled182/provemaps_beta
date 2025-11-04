# Zabbix Retrieval Optimization (Temporary Plan)

## Contexto
- Leituras Zabbix têm apresentado latência elevada (ex.: endpoint `zabbix_api/api/device-ports-optical/<id>/`, dashboards e demais consultas `item.get`, `host.get`, etc.).
- Sintomas comuns: múltiplos `item.get` sequenciais (~0,6–0,8s cada), mensagens "Session terminated, re-login" no caminho `retry_with_authorization` e alto volume de chamadas simultâneas.
- Ambiente: containers Docker locais (web/celery/beat/db/redis) executando branch `feature/docs-ci`.

## Objetivo Geral
Reduzir o tempo de resposta de qualquer leitura no Zabbix (óptica ou não), garantindo estabilidade na autenticação (sem loops de backoff) e menor volume de chamadas HTTP.

## Linha do Tempo / Decisões
- 2025-11-04: Ajustes no `ResilientZabbixClient` para manter API key permanente após falha de sessão; confirmação via logs.
- 2025-11-04: Docker rebuild e containers em execução para validar no dashboard.
- 2025-11-04: Monitoramento do dashboard (SWR) confirmou miss → hit fresco → stale-hit com refresh em background; identificado 404 recorrente em `update-cable-oper-status/<id>/`.

## Pendências Prioritárias
1. **Garantir autenticação estável via API key**
   - Validar presença de `ZABBIX_API_KEY` (compose/env/runtime). Sem chave fixa o cliente cai em `user.login` e as novas chamadas em lote continuam sofrendo `Session terminated`.
   - Novo log de aviso (`ZABBIX_API_KEY not configured`) ajuda a detectar ambiente sem chave.
2. **Consolidar baseline de chamadas após batching**
   - `_preload_optical_discovery_cache` já carrega itens em lote e a view `api_device_ports_with_optical` recebe cache de 60s; precisamos de uma execução completa para medir a redução real de `item.get`.
   - Assim que a sessão estabilizar, repetir o `manage.py shell` com `ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG=1` e capturar contagem/tempo total.
3. **Rever respostas `Invalid params` com Authorization header**
   - Continuar investigação do porquê Zabbix invalida a sessão mesmo com API key; confirmar se ocorre apenas quando a chave não está ativa.
4. **Cobrir casos residuais da descoberta óptica**
   - Heurística de preload inclui termos adicionais (`power`, `laser`, `optical`, `dbm`). Ajustar novamente se itens legítimos ainda ficarem fora.
5. **SWR/refresh e outros fluxos**
   - Após estabilizar leituras e baseline, revisar cadência das atualizações contínuas para evitar estourar o cache curto.
6. **Sincronizar cabos monitorados no dashboard**
   - Front configura polling para `update-cable-oper-status/<id>/`; banco atual (compose `web`) retornou apenas IDs `[6, 7, 3]`, enquanto o frontend tenta atualizar o ID `4`, gerando 404.

## Próximos Passos (sugeridos)
- [x] Conferir/ativar `ZABBIX_API_KEY` no ambiente que está sendo medido.
- [x] Rodar baseline novamente e registrar quantidade/tempo de `item.get` (esperado: apenas chamadas do preload + `_fetch_item_value`).
- [x] Documentar resultados e decidir se precisamos ampliar a heurística (ex.: export completo via `item.get` paginado).
- [ ] Caso `Invalid params` persista com API key ativa, avaliar ajustes no fluxo de retry (`retry_without_auth`).
- [ ] Alinhar lista de cabos monitorados: ou restaurar o cabo `id=4` na base ou remover o polling correspondente no dashboard, evitando 404 contínuo.

### Resultados 2025-11-04
- `ZABBIX_API_KEY` confirmado via `manage.py shell` (`True`).
- Baseline com `ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG=1`: primeira chamada após deploy gerou **6,74s** (preload completo com 9 `item.get`); com o novo cache (`optical:discovery` em Redis, TTL 180s) as chamadas subsequentes para o mesmo host caíram para **0,73s** (apenas a leitura `item.get` final). Logs continuam sem `Invalid params`.
- Logs recentes (`docker compose logs --tail 100 web`) não registraram novas mensagens de sessão inválida; apenas warnings de rota inexistente `update-cable-oper-status`.
- Tailing prolongado mostrou sequência SWR: miss inicial, hit fresco (<60s), stale-hit (~55s) disparando refresh assíncrono (web + celery) e mantendo latência baixa.
- Consulta dentro do container `web` (`docker compose exec web python manage.py shell ...`) confirmou que `FiberCable` possui apenas IDs 6, 7 e 3; API `list_fiber_cables()` reflete os mesmos valores. O ID 4 não existe na base atual, justificando os 404.
- Execução manual de `get_device_ports_with_optical(5)` com `ZABBIX_RETRY_MAX_ATTEMPTS_DEBUG=1` (`docker compose exec web env ...`) resultou em ~6,67s, 9 chamadas `item.get` (todas `attempt 1`), sem ocorrências de `Invalid params`, validando o fluxo com API key ativa.
- Próxima heurística em uso: manter caching do dataset de descoberta por host por 180s. Reavaliar após observar carga real; se rotas exibirem valores desatualizados, reduzir TTL ou invalidar ao salvar inventário.

> **Nota:** Este documento é temporário para alinhamento; atualizar conforme avanços e marcar itens concluídos.
