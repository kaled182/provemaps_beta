# Levantamento geral do ProVeMaps — 2026-10-04

> Pedido do Paulo: «levantamento total do nosso projeto, pontos positivos e
> negativos, para melhorar; temos diversos problemas com a geração de gráficos
> e leitura dos mapas». Mais dois pedidos ligados: trazer a mecânica de
> trabalho do CRM Simples Internet (item 2) e o mesmo visual (item 3).
>
> Método: quatro auditorias paralelas sobre o código real (gráficos e mapas;
> saúde geral; mecânica de trabalho do CRM; design system do CRM), com os
> achados críticos reverificados à mão. Referências são `ficheiro:linha`.
> Nenhum código de produto foi alterado nesta sessão.

Branch auditada: `claude/adoring-planck-s6rgop` em `59e0bb8` (193 commits,
1.475 ficheiros rastreados). Backend ~80 mil linhas Python, frontend ~86 mil
linhas Vue/JS.

---

## 1. Sumário executivo

O ProVeMaps tem uma **fundação boa** — settings de produção defensivos,
cliente Zabbix resiliente, camada de usecases no inventário, pipeline de
release com imagem multi-stage, compose de produção maduro, observabilidade —
e uma **camada de apresentação e de processo que envelheceu mal**: código
copiado em vez de parametrizado, quatro pilhas de mapa, três motores de
gráfico, testes que não correm, documentação que descreve um produto que já
não existe e lixo versionado (backups, `staticfiles/`, tokens).

Os problemas de **gráficos** têm três causas de raiz, todas no código e todas
corrigíveis em poucos dias: (1) quando o Zabbix não devolve histórico, o
frontend **inventa pontos aleatórios** e desenha-os como se fossem reais;
(2) os endpoints de tráfego pedem `history: 3` fixo, e itens Zabbix do tipo
float devolvem vazio; (3) o alinhamento RX/TX e IN/OUT é por timestamp exato,
o que produz buracos ou um forward-fill que esconde quedas. Por cima disso há
quatro cópias do mesmo builder de gráfico, instâncias nunca destruídas e
renders por `setTimeout`.

Os problemas de **mapas** vêm de **quatro implementações paralelas** (só uma
honra os três provedores configuráveis), de payloads que mandam a geometria
completa de todos os cabos em duplicado, de polling onde já existe WebSocket,
de um parser KML que só entende um caso, e de **chaves de API servidas sem
login**.

Em **segurança** há dois itens que devem ser fechados antes de qualquer outra
coisa: `/api/config/` entrega as chaves Google/Mapbox/Esri a qualquer visitante
e há tokens Mapbox literais versionados (rotacionar).

Em **processo**, o projeto não tinha briefing para agentes, lockfile de skills,
ADRs vivos nem regra de memória. Esta sessão montou essa camada (§6) sem tocar
no produto. A Central de Evolução e a repaginação visual ficam como ADRs
propostos (§7), porque mudam produto e custo e precisam de decisão do Paulo.

**Números que importam**

| Métrica | Valor |
|---|---|
| Ficheiros rastreados que violam o próprio `.gitignore` | 192 → 162 após esta sessão |
| Testes backend definidos / nunca coletados | 1.087 / ~61 |
| Testes frontend definidos / fora do `include` do Vitest | 427 / 121 |
| Testes E2E listados pelo Playwright | 0 (configuração engole os specs do Vitest) |
| Apps medidas pela cobertura «60 %» do CI | 3 de 9 (`inventory` fora) |
| Pilhas de mapa paralelas no frontend | 4 |
| Builders de gráfico quase idênticos | 4 (+ 2 canvas manuais) |
| Maior ficheiro backend / frontend | `setup_app/api_views.py` 4.484 linhas / `FiberCableDetailModal.vue` 3.859 |
| Docs que citam a app removida `zabbix_api` / MariaDB | 42 / 20 |
| `console.log` no frontend (vai para produção, build sem minify) | 518 |

---

## 2. Pontos positivos (o que preservar)

1. **Settings de produção defensivos** — `prod.py` recusa `SECRET_KEY` default
   e `ALLOWED_HOSTS` vazio; HSTS, cookies secure, structlog, Sentry opcional,
   Redis Sentinel, fallback sem Redis (`backend/settings/prod.py`, `base.py`).
2. **Cliente Zabbix resiliente** — circuit breaker, retry/backoff, cache de
   token, API key Bearer (Zabbix 7), métricas Prometheus, `batch()`
   (`backend/integrations/zabbix/client.py`).
3. **Camada de domínio no inventário** — `usecases/`, `services/`, `domain/`,
   `cache/`, `api/` modular, helper de depreciação
   (`backend/inventory/`).
4. **Pipeline de release** — tag → testes em PostGIS → imagem multi-stage
   non-root → GHCR → GitHub Release (`.github/workflows/release.yml`,
   `docker/dockerfile`).
5. **Compose de produção maduro** — nginx+certbot, profiles, healthchecks,
   `${VAR:?}` obrigatórios, Redis autenticado, `DEPLOY.md` coerente com
   `scripts/deploy.sh` (backup pré-deploy, rollback).
6. **Observabilidade** — `/healthz` `/ready` `/live`, `/celery/status`,
   django-prometheus, request-id, cache SWR com indicador de staleness
   (`backend/core/views_health.py`, `maps_view/cache_swr.py`).
7. **Celery bem parametrizado** — filas separadas, `acks_late`, limites de
   tempo, JSON only, eager em testes (`backend/core/celery.py`).
8. **WebSocket autenticado** com publisher desacoplado
   (`backend/maps_view/realtime/`).
9. **Frontend com boas bases** — rotas lazy, abstração `IMapProvider` +
   factory, `useApi` com CSRF, 306 testes unitários a passar em ~10 s.
10. **Credenciais de runtime cifradas (Fernet)** com múltiplas chaves e comando
    de geração; `.env.production.example` exaustivo e comentado.
11. **Documentação de domínio ainda útil** — `doc/architecture/DATA_FLOW.md`,
    `FIBER_PHYSICAL_HIERARCHY.md`, `doc/api/`.

---

## 3. Gráficos — diagnóstico

### 3.1 Onde e como são desenhados

| Local | Técnica | Problema |
|---|---|---|
| `frontend/src/components/PortTrafficModal.vue` (1.464 linhas) | Chart.js para tráfego; **canvas desenhado à mão** para óptico (`renderOpticalCanvasChart`, tooltip manual) | dois motores no mesmo modal |
| `FiberCableDetailModal.vue` (3.859 linhas) | Chart.js, 4 canvases e **4 funções quase idênticas** (`createTrafficOriginChart`, `createTrafficDestinationChart`, `createOriginChart`, `createDestinationChart`) | ~450 linhas copiadas; só mudam cores e refs |
| `AlarmConfigModal.vue` | canvas manual (3.ª implementação do óptico) | `chartInstance` declarado e nunca usado |
| `Dashboard/FiberStatusChart.vue`, `StatusChart.vue` | barras em CSS | ok |

Exportação «PDF» = `canvas.toDataURL` + `window.open` + `document.write` +
`window.print()`, **triplicada**; falha em silêncio com popup-blocker; nome do
dispositivo interpolado no HTML sem escape. `vue-chartjs` está nas
dependências e não é usado em nenhum lugar.

### 3.2 Fluxo Zabbix → backend → frontend

Cinco endpoints paralelos com payloads diferentes:
`PortViewSet.optical_history` e `traffic_history` (`viewsets.py:575-810`),
`FiberCableViewSet.optical-history` e `traffic-history` (`viewsets.py:1230-1460`,
com `ThreadPoolExecutor` aninhado) e o legado `api_port_traffic_history`
(`inventory/api/devices.py:263` → `usecases/devices.py:2196-2383`), que é o
**único** que consulta `value_type`/`units` e calcula `limit`. O frontend usa
eixo de **categoria** com labels string, não eixo de tempo.

### 3.3 Defeitos (ordem de gravidade)

1. **Dados simulados exibidos como reais.** Histórico óptico vazio →
   `PortTrafficModal.vue:711-735` gera pontos com `Math.random()` em torno do
   RX/TX atual e desenha-os (só um `console.warn`). Mesmo padrão em
   `AlarmConfigModal.vue:217-258` (`generateMockData`, também em erro HTTP).
   **É a causa mais provável de «o gráfico não bate com a realidade».**
2. **`"history": 3` fixo** nos endpoints de tráfego (`viewsets.py:733, 754,
   1385`). Item float (comum com pré-processamento «change per second») →
   `history.get` devolve `[]` → «sem dados». Causa provável de gráfico vazio
   em alguns equipamentos.
3. **Merge por `clock` exato** (`viewsets.py:632-685, 731-787, 1300-1316`).
   Se RX e TX coletam em segundos diferentes, cada linha vem com um lado
   `null`. Depois: `PortTrafficModal.vue:326` transforma `0 bps` em `null`
   (tráfego zero desaparece); `fiberService.js:85-120` faz forward-fill
   (**link down continua «plano»**).
4. **Eixo categoria** com `toLocaleString('pt-BR')` — amostragem irregular não
   é proporcional; 7 dias ≈ 10 mil labels; sem `chartjs-adapter-date-fns`.
5. **Unidades** — frontend assume bps e divide por 1e6; os endpoints DRF
   ignoram `units`; thresholds `-24/-27 dBm` fixos em três componentes
   enquanto `AlarmConfigModal` lê da configuração.
6. **Sem `limit`** nos 4 endpoints DRF: 168 h × 1 min × 2 itens × 2 portas ≈
   40 mil pontos por chamada, todos renderizados.
7. **Vazamento de instâncias Chart.js** — `FiberCableDetailModal.vue` nunca
   chama `destroy()`; `PortTrafficModal` tem `opticalChartInstance` morto.
8. **Corridas com timers** — `waitForCanvas` + 6 retries de 150 ms; `setTimeout(200)`;
   `changePeriod` + dois `watch` disparam fetch óptico duplicado sem
   `AbortController` → «gráfico não aparece» ao trocar de aba depressa.
9. **Canvas manual** sem `devicePixelRatio` (borrado), redesenho a cada
   `mousemove`, `Math.min(...[])` = `Infinity` quando tudo é `null`,
   `ctx.fontWeight` não existe.
10. **Tema fixo escuro** (`#9ca3af`, `rgba(17,24,39)`); export pinta fundo
    `#111827` → PDF escuro em página branca.
11. **Erros indistintos** — `getCableOpticalHistory` devolve `null` para erro
    e para vazio; `FiberCable.objects.get(pk=pk)` sem 404; `float(entry["value"])`
    sem guarda.
12. **Segurança** — `api_port_traffic_history` sem `@login_required`
    (`api/devices.py:263`; os vizinhos têm).
13. **Testes** — nenhum teste para as 4 actions DRF de histórico;
    `fiberService.test.js:7-10` importa duas funções **que não existem**
    (teste quebrado e, por estar fora do `include`, nunca corre).

### 3.4 Direção de correção

- Backend: um só serviço de séries que consulta `item.get` (`value_type`,
  `units`), aplica `limit`/downsample proporcional ao período, **bucketiza**
  (60 s) e devolve `{t, in, out}` / `{t, rx, tx}` já alinhados com `null`
  real; as 5 rotas passam a fachadas dele (EV-0003, EV-0010, EV-0029).
- Frontend: `TimeSeriesChart.vue` único (eixo `time`, `spanGaps` configurável,
  `destroy` em `onBeforeUnmount`, cores por tokens, export único), usado pelos
  três modais; remover `Math.random()` e mostrar estado explícito «sem dados»
  / «Zabbix indisponível» (EV-0001, EV-0011, EV-0026).

---

## 4. Mapas — diagnóstico

### 4.1 Quatro pilhas paralelas

| Pilha | Ficheiros | Provedores | Estado |
|---|---|---|---|
| 1 | `components/MapView.vue` (1.943) — rota `/map` e embutido no Dashboard | **Google only** via `vue3-google-map`, ignora `mapProvider` | sem clustering; carrega bbox **e** todos os cabos; redesenho por `setTimeout(500)` |
| 2 | `views/monitoring/CustomMapViewer.vue` (2.874) + `composables/map/core/*` | google/mapbox/osm por `if provider ===` em cada função | a **única** que honra os três; polling de 30 s em vez do WebSocket |
| 3 | `NetworkDesign/NetworkDesignView.vue` (3.566) + `features/networkDesign/fiberRouteBuilder.js` (2.213) + `modules/mapCore.js` | `providers/maps/MapProviderFactory.js` regista **só google e mapbox** | com `osm` → `throw` → `alert()`; 8 referências diretas a `google.maps`; `mapCore-refactored.js` não é importado |
| 4 | `composables/useMapService.js` + `mapPlugins/*` → `Map/UnifiedMapView.vue` | Google only | **não roteada**; só aparece em `USAGE_EXAMPLES.vue` |

Mais três loaders de Google Maps (`utils/mapProviderAdapter.js`,
`utils/mapLoader.js`, `utils/googleMapsLoader.js`).

### 4.2 Importação KML

- Frontend: `features/networkDesign/partials/import_kml.js` é código DOM
  legado dentro da SPA (`document.getElementById`,
  `window.__FIBER_DEVICE_OPTIONS`, `#toastHost`).
- Backend `parse_kml_coordinates` (`usecases/fibers.py:278-306`): só
  `kml:LineString` do namespace 2.2; **todas as LineStrings do ficheiro são
  concatenadas num único traçado** (vários Placemarks → zigue-zague); sem KMZ,
  `MultiGeometry`, `gx:Track`; sem dedupe.
- `create_fiber_from_kml` em `single_port` usa origem como destino
  (`api/fibers.py:81-83`); `list_fiber_cables` assume as duas portas
  não-nulas (`usecases/fibers.py:522`) embora o modelo permita `null` →
  `AttributeError` em cabo com ponta solta.
- **Regra dos 100 m** (`api/devices.py:795-845`): haversine em Python sobre
  **todos** os sites, por item, dentro de `transaction.atomic()` — O(sites ×
  itens); ignora `Site.location` e `ST_DWithin` que já existem
  (`usecases/spatial.py:203`). Igual em «cabos próximos» (`api/fibers.py:753-808`).

### 4.3 Geometria, payload, tempo real

- **Dupla fonte de verdade**: `Site.latitude/longitude` e `Site.location`
  sem signal de sincronização (`signals_spatial.py` só garante SRID em `path`).
- **Sem serializer GeoJSON**; `FiberCableSerializer` expõe `path` **e**
  `path_coordinates` (geometria em duplicado). `list_fiber_cables` devolve o
  path completo de **todos** os cabos sem bbox/simplificação; `cable_type`
  fora do `select_related` (N+1); `build_optical_summary` por cabo.
- Frontend converte `{lat,lng}` → `[lng,lat]` → `{lat,lng}`
  (`MapView.vue:684-735`).
- `get_break_location` interpola com «1 grau ≈ 111 km» (`serializers.py:181`):
  erro de até ~30 % em longitude nas latitudes do Brasil.
- **WebSocket existe e não é usado pelos mapas**: `CustomMapViewer` faz
  polling; `SiteDetailsModal.vue:1536` cria **um socket por abertura** sem
  cleanup.
- **`/api/config/` sem autenticação** devolve `googleMapsApiKey`,
  `mapboxToken`, `esriApiKey` (`core/views_api.py:11-60`; whitelist em
  `core/middleware/auth_required.py`), anulando o `mapbox_proxy.py`, que exige
  login.

### 4.4 Direção de correção

Eleger `providers/maps/` como única abstração, registar Leaflet/OSM na
factory, migrar `MapView.vue` e `CustomMapViewer.vue`, apagar as pilhas 3 e 4
mortas e os loaders extra (EV-0012); bbox + `ST_Simplify` + um só campo de
geometria (EV-0013); WebSocket em vez de polling (EV-0014); KML por Placemark
com `MultiGeometry`/KMZ e componente Vue sem `window.*` (EV-0015);
`ST_DWithin` + signal lat/lng → `location` (EV-0024); `@login_required` em
`/api/config/` e Mapbox só pelo proxy (EV-0002).

---

## 5. Saúde geral — demais áreas

### 5.1 Higiene do repositório

- **192 ficheiros rastreados violavam o `.gitignore`** (`git ls-files | git
  check-ignore --stdin --no-index`): `staticfiles/` (153, saída do
  `collectstatic`), `frontend/playwright-report/index.html` (520 KB, o maior
  blob), `frontend/test-results/`, `docker/test_*.py`, `scripts/test_*.py`.
  Pior: o padrão global `test_*.py` **escondia 14 testes legítimos** em
  subpastas de `backend/tests/` — testes novos ali não entravam no `git add`.
  Corrigido nesta sessão (§6).
- **Mortos/duplicados**: `backend/setup_app_backup/` (76 ficheiros, já
  divergente), `backend/d\uF03A\uF05Ctemp_fibers.json` (nome corrompido de
  `d:\temp_fibers.json`), `SiteDetailsModal.vue.broken_backup` e
  `.phase12_step1` (idêntico ao atual), `ConfigurationPage_REFACTORED.vue`,
  JS do route builder em **três** cópias (`backend/static/js/modules/`,
  `frontend/src/features/networkDesign/modules/`, `staticfiles/js/modules/`),
  10 HTMLs de teste manual (vários com tokens), `temp_zabbix_update.txt`,
  `backend/test_zabbix_hosts.py`, `data/sqlite_dump.json` (**com 2 registros
  `auth.user`**), `requirements_full.txt` em UTF-16, `settings/dev_baseline.py`
  sem referência.
- `package-lock.json` está no `.gitignore` e **não existe**, mas Dockerfile e
  o workflow diário usam `npm ci` (exige lock) → build não reprodutível; o
  workflow diário ainda corre `npm ci` na raiz, onde não há `package.json`.

### 5.2 Backend

- `DB_ENGINE` default `mysql` sem driver em `requirements.txt`; `.env.example`
  usa `DATABASE_*` que nenhum settings lê; `core/asgi.py:17` aponta
  `core.settings` (inexistente); `docker-compose.test.yml` ainda com MariaDB.
- Branding/nomes antigos: `Celery("mapsprovefiber")`, cookies, `KEY_PREFIX`,
  «SIMPLES INTERNET»/«Maps Prove Fiber» hardcoded em `base.py` e `core/urls.py`.
- `fernet_keys = [SECRET_KEY]` como fallback + `decrypt_string` devolve o
  ciphertext em silêncio em `InvalidToken` → rotacionar `SECRET_KEY` sem
  `FERNET_KEY` corrompe credenciais sem erro.
- **God-modules**: `setup_app/api_views.py` 4.484 linhas / 66 funções
  (Zabbix, DB, Redis, FTP, SMTP, SMS, OAuth Drive, backups, QR WhatsApp, HLS,
  edição do `.env`, mosaicos); `core/api_users.py` 1.015; `usecases/devices.py`
  2.501.
- **2FA**: TOTP próprio sem `pyotp`, segredo em **texto puro**
  (`core/models.py:43`) apesar de existir `EncryptedCharField`; lockout por
  contador de sessão (contornável limpando o cookie).
- `service_accounts` (1.133 linhas): tokens com hash, rotação, audit — e
  **nenhuma classe de autenticação os consome**.
- API: router DRF `/api/v1/`, 95 function views em `/api/v1/inventory/`,
  rotas não versionadas `/api/sites/`, `/api/users/*`, `/setup_app/api/*`;
  sem `DEFAULT_VERSIONING_CLASS`, sem OpenAPI, sem throttling DRF.
- `zabbix_service.py` mistura serviço puro com views Django (`get_interfaces(request)`).
- `beat_schedule` em `celery.py` **e** `django_celery_beat` populado por
  `init_app_data` → duas fontes de agendamento.
- `telemetry` ligado por padrão, grava `data/installation.id` dentro do repo.

### 5.3 Frontend

- 124 `.vue`, 76 `.js`, **1 `.ts`** (`stores/filters.ts`, morto e divergente
  de `filters.js`); sem `tsconfig.json`.
- `useApi.js` centraliza CSRF, mas há **27 ficheiros com `fetch(` direto**;
  `axios` em `dependencies` com 0 imports; `vite` em `dependencies`;
  `pyright` no frontend (usado para checar o backend).
- `vite.config.js` com `minify: false` «para manter console.log» → **518
  `console.log` vão para produção**.
- ESLint 8 (EOL) com `no-undef`, `no-unused-vars`, `no-console` desligados e
  mesmo assim `npm run lint` falha com 18 erros; lint não corre em CI.
- `base_spa.html` carrega **Tailwind e FontAwesome via CDN** («temporary
  during migration») → CSP com `'unsafe-inline' 'unsafe-eval'`.
- Bloco `"jest"` residual em `package.json` apontando para caminho inexistente;
  `babel.config.js` e `@babel/*` só servem ao Jest.

### 5.4 Testes

- **Três configs pytest divergentes** (`pytest.ini`, `backend/pytest.ini`,
  `[tool.pytest.ini_options]`); o da raiz lista `tests` (inexistente).
- **~61 testes nunca coletados**: `backend/inventory/routes/tests/` (46) fora
  de `testpaths`; `service_accounts/tests.py` (7) e
  `maps_view/tests_mapbox_proxy.py` (8) fora de `python_files`.
- **Cobertura mede só `core`, `maps_view`, `setup_app`**
  (`backend/pyproject.toml [tool.coverage.run]`) — `inventory`,
  `integrations`, `monitoring`, `service_accounts` ficam fora do «60 %».
- Coleta local: 914 itens, 7 erros por falta de GDAL (não documentado para
  correr sem Docker).
- Frontend: 306 testes passam (28 ficheiros, 10,6 s), mas **121 não correm**
  por estarem fora do `include` (`src/composables/__tests__/` 100,
  `RadiusSearchTool.test.js` 15, `fiberService.test.js` 6).
- **E2E inoperante**: `playwright.config.js` com `testDir: './tests'` engole
  os specs do Vitest → `--list` dá «0 tests in 0 files».

### 5.5 CI/CD

- `tests.yml`: Python **3.13** (Dockerfile e release usam 3.12), só pytest;
  **sem frontend, sem ruff/black/isort**, sem scanner de segredos. Nesta
  sessão entrou um job `frontend-unit` (§6).
- `daily-inventory-tests.yml`: `npm ci` na raiz sem `package.json` →
  provavelmente vermelho.
- `release.yml`: bom; mas o build Docker roda `npm ci` sem lock.
- `.pre-commit-config.yaml` existe e **não é aplicado** (evidência: blob de
  520 KB passou pelo `check-added-large-files --maxkb=500`).
- Dockerfile: `pip install gunicorn uvicorn celery` **sem pin** no stage
  final; `COPY backend/` leva `setup_app_backup/`, testes e scripts;
  `requirements.txt` único leva `pytest`, `coverage`, `django-debug-toolbar`,
  `django-stubs` para produção.
- nginx: `X-Frame-Options SAMEORIGIN` vs Django `DENY` (inofensivo, incoerente).

### 5.6 Documentação

- 290 ficheiros em 19 pastas + 5 relatórios de reorganização na raiz de
  `doc/`; `doc/reports/` com 68 diários de sprint; duplicações temáticas
  (`testing/` × `guides/testing/` × `reference/TESTING_*`; três
  `TROUBLESHOOTING`).
- **42 docs citam `zabbix_api`** (removida em 2.0.0), **20 citam MariaDB**;
  `doc/README.md` diz «v2.0.0 100 % Complete» (VERSION é 1.4.1).
- `doc/process/AGENTS.md` e `.github/copilot-instructions.md` desatualizados
  (apps inexistentes, `make run-web-local`, Jest, `django-environ`).
- Versões: `VERSION` 1.4.1 · `CHANGELOG.md` 2.0.0 → 1.2.0 → 1.4.1 (regressão
  semver) · `frontend/package.json` 0.1.3 · `backups/*v2.1.0*`.
- README: tabela de apps omite `service_accounts`; «971 testes» (há 1.087
  `def test_`); build do frontend «na raiz» (está em `frontend/`); documenta
  `admin/admin123` que também está no código.

### 5.7 Dependências

- `django-stubs 5.1.1` vs Django 5.2.7; DRF 3.15.2 aqui vs 3.16.1 em
  `requirements_full.txt`; `psycopg>=3.2`/`setuptools>=61` sem pin num
  ficheiro todo pinado; stack Google de 2024.
- Frontend: ESLint 8 EOL, Vitest 1.x com Vite 7 (combinação não suportada),
  `@vueuse/core` 11 (13 atual), três bibliotecas de mapa.
- `services/video-transmuxer` (FastAPI 0.111, meados de 2024);
  `services/whatsapp-qr` usa Baileys (biblioteca não oficial do WhatsApp —
  risco de ToS e quebra).

### 5.8 Segurança (passagem rápida)

- **Endpoints sem autenticação** por whitelist: `/api/config/` (chaves),
  `/metrics/`, `/celery/status`, `/setup_app/docs/`.
- **Tokens Mapbox literais** em `backend/maps_view/tests_mapbox_proxy.py:27`,
  `backend/static/test-mapbox-*.html`, `frontend/test-mapbox*.html`,
  `backups/QUICK_START.txt:40` → **rotacionar e remover**.
  `data/sqlite_dump.json` com `auth.user`.
- Senha default `admin123` em três comandos e no README.
- CSP fraco por causa do CDN (ver 5.3).
- `service_reloader.py:33` corre `subprocess.run(..., shell=True)` com
  comandos vindos de settings/env; `update_env_file` (staff) edita o `.env`
  → cadeia staff → `.env` → shell merece revisão.
- Positivo: `IsAuthenticated` global no DRF, histórico de `AllowAny`
  corrigido, CSRF ativo, HSTS/secure cookies em prod.

---

## 6. O que esta sessão fez (item 2 — mecânica de trabalho do CRM)

Só camada de tooling, conforme o próprio roteiro do CRM
(`docs/prompt-replicar-setup.md`): **nenhum código de produto, nenhuma
dependência de runtime, nenhum visual**.

| Entrega | Ficheiro | Equivalente no CRM |
|---|---|---|
| Manual operacional canônico (regras de trabalho, quadro, princípios, stack, convenções, red flags, memória) | `CLAUDE.md` | `CLAUDE.md` |
| Lockfile de skills com hashes reais (9 skills) + script + alvo | `skills-lock.json`, `scripts/skills-install.sh`, `make skills` | idem |
| Servidores MCP versionados | `.mcp.json` | idem |
| Convenção de ADR + template + 3 ADRs | `doc/adr/`, `doc/templates/adr.md` | `docs/adr/`, `docs/templates/` |
| Inventário de ferramentas e roteiro de máquina nova | `doc/ferramentas-agente.md` | `docs/ferramentas-agente.md` |
| Editor config | `.editorconfig` | idem |
| Ignorar estado por programador; destravar testes escondidos | `.gitignore` | idem |
| Ponteiros nos briefings antigos | `doc/process/AGENTS.md`, `.github/copilot-instructions.md` | — |
| Job de testes do frontend no CI | `.github/workflows/tests.yml` | `test-front` |

**Fica por máquina** (não versionável, roteiro em `doc/ferramentas-agente.md` §5):
plugins do harness (`superpowers`, `claude-code-setup`), hooks `Stop`/`PreToolUse`,
memória em `~/.claude/projects/<slug>/memory/`, RTK/Headroom (decisão do Paulo).

**Fica como ADR proposto**: Central de Evolução (ADR 0006), porque é código
de produto e tem uma decisão (fila própria vs fila partilhada com o CRM).

---

## 7. Item 3 — visual do CRM: o que é e como chegar lá

O CRM não usa kit de UI: é **Tailwind 3.4 + Headless UI**, teal `#42B4B8`,
neutros Slate por variáveis `--n-*` que invertem no escuro, `surface`/`canvas`,
Inter/JetBrains Mono/Outfit auto-hospedadas, header fixo de **duas linhas sem
sidebar**, cartões `p-4` com borda e sem sombra, `rounded-md`/`rounded-lg`,
`text-sm`, ícones Lucide. Detalhe completo no ADR 0007 e no ADR 0016 do CRM.

O ProVeMaps tem CSS próprio por variáveis (`theme.css`), acento verde, menu
lateral, Phosphor icons, Tailwind via CDN e 124 componentes com estilo scoped.

**Proposta (ADR 0007)** em quatro fases, cada uma fechando num deploy:
(1) tokens + fontes auto-hospedadas + remover CDN — a app inteira muda para
teal/Slate sem tocar em componentes; (2) shell: header de duas linhas,
`useNavSections` do ProVeMaps, toggle de tema por classe, botão Reportar;
(3) Tailwind local com o `tailwind.config` do CRM e primitivos portados
(`Button`, `Input`, `Select`, `Modal`, `DataTable`, `ConfirmDialog`),
migrando componente a componente — começando pelos modais gigantes que os
gráficos já obrigam a partir; (4) pacote `@simplesinternet/design-system`
consumido pelos dois produtos.

---

## 8. Backlog priorizado (semente da Central)

Os códigos `EV-NNNN` são os do quadro no `CLAUDE.md`. Prioridades são
**propostas**; a triagem é do Paulo.

**P1 — fechar primeiro (segurança e verdade dos dados)**

| Código | Problema | Correção proposta |
|---|---|---|
| EV-0001 | gráfico óptico com `Math.random()` | remover; estado explícito «sem dados»/«erro» |
| EV-0002 | `/api/config/` sem login | `@login_required`; Mapbox só via proxy |
| EV-0003 | `history: 3` fixo | consultar `value_type`/`units` via `item.get` |
| EV-0004 | `api_port_traffic_history` sem auth | decorator ou remover rota legada |
| EV-0005 | tokens Mapbox e dump versionados | rotacionar; apagar ficheiros |
| EV-0006 | cobertura mede 3 apps | `source` com todas as apps; ajustar limiar |
| EV-0007 | sem lockfile + `npm ci` | versionar `package-lock.json`; corrigir workflow diário |

**P2 — estruturais (gráficos, mapas, testes, segurança)**

EV-0008 testes não coletados · EV-0009 testes frontend fora do include e E2E
morto · EV-0010 alinhamento por bucket · EV-0011 ciclo de vida dos gráficos ·
EV-0012 uma pilha de mapa · EV-0013 payload de cabos · EV-0014 WebSocket nos
mapas · EV-0015 KML · EV-0016 TOTP · EV-0017 partir god-modules · EV-0018
dependências e imagem · EV-0019 build do SPA e CDN.

**P3 — higiene**

EV-0020 lixo versionado · EV-0021 docs e versões · EV-0022 CI com lint ·
EV-0023 `service_accounts` · EV-0024 proximidade com PostGIS · EV-0025 config
default.

**Ideias**: EV-0026 `TimeSeriesChart.vue` · EV-0027 Central de Evolução ·
EV-0028 visual Fase 1 · EV-0029 séries bucketizadas no backend · EV-0030
OpenAPI.

---

## 9. Decisões pendentes do Paulo

1. **Triagem do quadro** (§8): aceitar/recusar/priorizar os 30 itens. A
   sugestão é começar por EV-0001 a EV-0005 na mesma semana.
2. **ADR 0006** — Central própria no ProVeMaps (recomendado) ou fila partilhada
   no CRM com campo `produto`.
3. **ADR 0007** — confirmar a abordagem por fases e as três perguntas da Fase 2
   (busca global no header, nav em modo mapa, login com mascote ou só paleta).
4. **Ferramentas por máquina** — ativar `superpowers` e `claude-code-setup`;
   decidir RTK/Headroom/`claude-mem`.
5. **Rotação de credenciais** — os tokens Mapbox versionados devem ser
   rotacionados independentemente de quando os ficheiros forem apagados.

---

## 10. Anexos

- Comandos de verificação usados: `git ls-files | git check-ignore --stdin
  --no-index | wc -l`; `grep -rc "def test_" backend | …`; `python -m pytest
  -q --co`; `npx vitest run`; `npx playwright test --list`; `skills find
  django`; `cmp SiteDetailsModal.vue SiteDetailsModal.vue.phase12_step1`.
- Fontes do CRM consultadas: `CLAUDE.md`, `docs/prompt-replicar-setup.md`,
  `docs/ferramentas-agente.md`, `docs/adr/0016`, `docs/adr/0042`,
  `frontend/tailwind.config.ts`, `frontend/src/style.css`,
  `frontend/src/layouts/AppLayout.vue`, `backend/app/evolucao/`,
  `scripts/evolucao_fechados.sh`, `backend/scripts/evolucao_quadro.py`.
