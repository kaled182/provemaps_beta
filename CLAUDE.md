# CLAUDE.md — Manual operacional do projeto ProVeMaps

> **Lê isto sempre antes de agir.** Este ficheiro é o briefing canônico para
> qualquer sessão de Claude Code neste repositório. Se algo aqui contradiz
> uma instrução pontual do utilizador, **pergunta antes de assumir**.
>
> É o irmão do `CLAUDE.md` do CRM Simples Internet: mesma estrutura, mesmas
> regras de trabalho, adaptadas a este produto. Quando os dois divergirem
> numa regra de processo, vale o mais recente e avisa-se o Paulo.

---

## 📌 COMO SE TRABALHA NISTO — e o que falta

> **Pedido do Paulo, 2026-10-04, vinculativo:** trazer para o ProVeMaps a
> mesma mecânica de trabalho do CRM.

### A regra de trabalho

**Um pedido de cada vez, até ficar acabado.** Não organizar por ondas, não
despachar listas grandes, não abrir três frentes. Fecha-se um, fecha-se o item
no quadro, passa-se ao seguinte.

### Passo zero — verificar como acabou a sessão anterior

Antes de olhar para o quadro, ler `estado_da_sessao.md` na memória do projeto
(`~/.claude/projects/<slug-deste-caminho>/memory/`). Ele diz `em_curso` ou
`finalizada`, e é **a única coisa que distingue «acabou» de «morreu»** — as
duas deixam a mesma árvore de ficheiros.

- `finalizada` → seguir para o quadro normalmente.
- `em_curso` → **não começar nada novo.** Apurar onde ficou pelo que se pode
  VERIFICAR (`git log`, `git status`, estado do item), nunca pela memória do
  que se julga ter feito. Só depois decidir: retomar ou reportar.

**Escreve-se `em_curso` ao PEGAR no item, não no fim** — no fim pode não haver
ninguém para escrever (sessões morrem por SIGHUP, timeout, fecho do portátil).

### Por onde se começa: o quadro, seção «A fazer»

**A ordem de trabalho é: prioridade, depois identificador.** P1 primeiro;
entre iguais, o identificador menor (o mais velho). Pega-se no primeiro e
vai-se até ao fim.

**A triagem é do Paulo.** O assistente **não mexe na «Entrada»** — não
aceita, não recusa, não promove, não inventa prioridade. Um relato só entra na
fila quando o Paulo o aceita (na Central: `/system/evolucao`). O assistente **abre** itens
novos quando encontra um problema com prova (ficheiro, linha, comando que reproduz) —
na Central, com `origem="agente"` e a evidência obrigatória:

```bash
docker exec -i docker-web-1 python manage.py shell -c "
from django.contrib.auth import get_user_model; from evolucao import usecases as uc
uc.criar_item(autor=get_user_model().objects.get(username='<staff>'), tipo='problema', origem='agente',
  titulo='…', descricao='…', evidencia={'ficheiro': 'backend/x.py:12', 'comando': '…'})"
```

**Implanta-se ANTES de passar ao item seguinte.** Um item «feito» que não está
em produção é um item que a fila diz resolvido e o utilizador continua a
sofrer.

**Ao fechar um item, o commit leva o verbo:** `fecha EV-0003` (no assunto ou numa linha do
corpo). Mencionar o código sem o verbo **não** fecha — de propósito. É este verbo que fecha o
item na Central quando o commit chega a produção (ADR 0006). **Desde 2026-11-23 o quadro abaixo
é GERADO** — não se edita à mão (uma edição desaparece na geração seguinte):

```bash
# deploy com o commit e a versão na imagem (sem eles o /healthz não tem SHA e nada fecha)
export GIT_SHA=$(git rev-parse HEAD) APP_VERSION=$(cat VERSION)
docker compose -f docker/docker-compose.yml build web celery beat
docker compose -f docker/docker-compose.yml up -d web celery beat nginx
make evolucao-sync     # fecha o que está no ar e regenera o bloco deste ficheiro; commitar o resultado
```

O detalhe de cada item fechado até 2026-11-23 (o que mudou, números medidos, notas «Fica») está
arquivado em [`doc/analysis/2026-11-23-quadro-manual.md`](doc/analysis/2026-11-23-quadro-manual.md);
dali para a frente vive no commit e na descrição do item na Central.

**Um item grande demais para uma sessão NÃO se parte por iniciativa do
assistente.** Sobe ao Paulo com a leitura («isto não cabe numa sessão e tranca
os N que vêm atrás»); a decisão é dele.

### Agentes extra: autorizados, com condições medidas

Pode-se usar subagentes para ganhar tempo. As colisões não são no código, são
em três vias partilhadas:

- **Nunca dois agentes a correr `pytest` ao mesmo tempo.** A base de testes é
  uma (PostGIS no Docker ou SQLite em `settings.test`); um backend e um
  frontend (`vitest`) em paralelo é seguro, dois backends não.
- **Ninguém corre `make fmt`** nem comandos de âmbito global (black/ruff/isort
  na árvore toda); cada um limita-se aos seus caminhos.
- **Os agentes não fazem commit.** Entregam, o controlador revê e commita, um
  a um, lendo o `HEAD` fresco antes de cada commit.
- **Contrato fixado ANTES de despachar** (assinaturas, rotas, nomes de
  ficheiros). Cada tarefa declara `Files:` e `Depends-on:`; duas tarefas só
  partilham onda se nenhuma depende da outra **e** os `Files:` são disjuntos.
  Na dúvida, série.
- **Nível de modelo explícito** em cada despacho, nunca herdado em silêncio.

### Idioma

O assistente responde ao Paulo **sempre em português** (todo o texto
conversacional, incluindo raciocínio visível). Produto e documentação em
PT-BR nos termos de domínio (`cabo`, `fusão`, `rota`, `porta`, `OLT`); PT-PT
ou inglês aceitáveis em prosa técnica. Código, identificadores e mensagens de
log em inglês, como já está.

---

> Origem dos itens EV-0001…0030: [`doc/analysis/2026-10-04-levantamento-geral.md`](doc/analysis/2026-10-04-levantamento-geral.md); detalhe dos fechados até 2026-11-23: [`doc/analysis/2026-11-23-quadro-manual.md`](doc/analysis/2026-11-23-quadro-manual.md).

<!-- EVOLUCAO:INICIO — gerado por `manage.py evolucao_quadro` (ADR 0006). NÃO editar à mão. -->
## 📌 QUADRO — o que falta

> Gerado da Central de Evolução a 2026-11-24 (`make evolucao-quadro`). Para mexer, use
> `/system/evolucao` ou a API `/api/v1/evolucao/` — uma edição à mão aqui desaparece na
> próxima geração. A ordem de trabalho é prioridade, depois código; problemas antes de ideias.

**Aceites, por priorizar (1)**

💡 Ideias
- `EV-0085` **«Saúde da coleta»: equipamentos com host Zabbix inexistente e portas sem leitura, com o motivo e aviso por e-mail** · por triar · admin · há 0 dias

<!-- EVOLUCAO:FIM -->

---

## 1. Identidade do projeto

- **Nome:** ProVeMaps (antes MapsProveFiber / mapsprovefiber — o nome antigo
  ainda aparece em `Celery("mapsprovefiber")`, cookies e prefixos de cache).
- **Organização:** Simples Internet (ISP brasileiro).
- **Tipo:** plataforma **interna** de gestão de infraestrutura de fibra
  óptica: mapa em tempo real, inventário físico (sites, dispositivos, portas,
  cabos, rotas), fusões, importação KML, câmeras, alarmes.
- **Fonte de verdade da rede física:** o inventário (`backend/inventory/`).
  O Zabbix é fonte de **estado** (up/down, tráfego, nível óptico), nunca de
  topologia.
- **Responsável técnico:** Paulo Marcelino — `paulo@simplesinternet.net.br`.
- **Produto irmão:** CRM Simples Internet (FastAPI + Vue 3 + Tailwind). Os dois
  devem **parecer e funcionar** como uma família (ADR 0007).

## 2. Princípios não-negociáveis

1. **Nunca mostrar dado inventado como real.** Um gráfico sem histórico mostra
   «sem dados» ou «erro ao consultar o Zabbix», nunca uma série gerada com
   `Math.random()` (EV-0001). Vale para tabelas, KPIs e tooltips.
2. **Zabbix só pelo gateway.** Toda chamada passa por
   `integrations/zabbix/zabbix_service.zabbix_request` (token, retry,
   circuit breaker, métricas). Nenhum `requests.post` direto.
3. **Inventário por usecases.** Lógica de negócio em `inventory/usecases/*`
   devolvendo dicts; viewsets e function views ficam finos. Nunca criar ou
   alterar entidades de rede fora da camada de inventário.
4. **Depois de mutar cabos/portas/rotas, invalidar as duas caches:**
   `inventory.cache.fibers.invalidate_fiber_cache()` e
   `maps_view.cache_swr.invalidate_dashboard_cache()`.
5. **Segredos só em `setup_app` (Fernet) ou em variáveis de ambiente.** Nada em
   código, fixtures, HTML de teste ou docs. Tokens que já vazaram rodam-se.
6. **Tudo autenticado por omissão.** Um endpoint novo sem login é exceção
   escrita e justificada no PR; `/api/config/` não é modelo a seguir. Pessoas
   autenticam por sessão (+ TOTP); integrações por token de conta de serviço
   (`Authorization: Bearer`, ADR 0008) — o principal não é `User`, não tem
   `is_staff` nem permissões de modelo.
7. **Uma pilha de mapa.** A abstração é `frontend/src/providers/maps/`
   (`IMapProvider` + factory). Não se cria a quinta implementação; se falta um
   provedor (Leaflet/OSM), regista-se na factory.
8. **Sem CDN para fontes, ícones ou CSS** (LGPD e CSP). Auto-hospedar.
9. **Sem ficheiros de backup no repositório** (`*.broken_backup`,
   `*_REFACTORED.vue`, `*_backup/`). O Git é o backup.

## 3. Stack técnica

| Camada | Tecnologia |
|---|---|
| Backend | Python 3.12, Django 5.2, DRF 3.15, Channels 4 (WebSocket `/ws/dashboard/status/`), Celery 5.4 + beat, structlog, django-prometheus, Sentry opcional |
| Banco | PostgreSQL 16 + PostGIS (dev) / 15 (prod) — **único** backend (`DB_ENGINE=postgis` por omissão; outro valor falha no arranque, EV-0025); GDAL/GEOS obrigatórios; sem eles os campos espaciais degradam para JSON e os testes espaciais falham na coleta |
| Cache/broker | Redis (degradação graciosa sem Redis) |
| Frontend | Vue 3.5 + Vite 7 + Pinia 3 + vue-router 4, Tailwind 3.4 compilado no build (PostCSS), FontAwesome 6.5 auto-hospedado, Chart.js 4, `@phosphor-icons/vue`, `mapbox-gl`, `leaflet` (+ SDK Google carregado pelo provider), `hls.js`, Vitest, Playwright |
| Infra | Docker multi-stage (`docker/dockerfile`), compose dev (`docker/docker-compose.yml`, porta 8100) e prod (`docker-compose.prod.yml` com nginx+certbot e profiles), GHCR via `release.yml` |
| Serviços | `services/video-transmuxer` (FastAPI), `services/whatsapp-qr` (Node/Baileys), mediamtx |

## 4. Estrutura do repositório

```
backend/
  core/           settings root, URLs, ASGI/WSGI, middleware, auth 2FA, health
  settings/       base.py / dev.py / prod.py / test.py (django-environ só no Zabbix)
  inventory/      domínio: models, usecases/ (devices_{common,ports,discovery}.py, fibers.py, spatial.py…), services/, domain/, cache/, api/ (27 módulos), viewsets.py, serializers.py
  monitoring/     inventário + estado Zabbix
  integrations/zabbix/  client.py (resiliente), zabbix_service.py (gateway), guards, decorators
  maps_view/      dashboard, cache_swr.py, realtime/ (consumers, publisher, events), mapbox_proxy.py
  setup_app/      configuração runtime, credenciais Fernet, api/<dominio>.py + usecases/<dominio>.py (backups, config, gateways, video, connections, company, monitoring — EV-0017; api_views.py já não existe), docs viewer
  evolucao/       Central de Evolução (ADR 0006): models, usecases.py, api.py, serializers.py, management/commands/evolucao_seed_quadro.py
  service_accounts/, telemetry/, gpon/, dwdm/   (os dois últimos são scaffolds)
frontend/src/
  components/     Map/, Dashboard/, Inventory/, Fusion/, TraceRoute/, DeviceImport/, Video/, Configuration/, Layout/ (AppHeader + CommandPalette: shell de duas linhas, EV-0044), Evolucao/ (ReportarModal)
  views/          páginas roteadas (monitoring/, video/, EvolucaoView.vue em /system/evolucao, ...)
  providers/maps/ IMapProvider + MapProviderFactory (google | mapbox | osm)  ← abstração oficial
  components/Map/ MapCanvas.vue (cria o mapa pela factory), MapPopup.vue (janela ancorada por coordenada), MapControls, RadiusSearchTool (ainda Google-only)
  composables/    useApi (CSRF), useWebSocket, useRealtimeStatus, useRouteDrawing (traçados sobre IMap), map/{useMapData,useMapSelection} (dados/seleção do CustomMapViewer)
  stores/         Pinia (filters.js é o vivo; filters.ts é morto)
  services/       fiberService.js
  assets/         theme.css (tokens atuais), base.css
doc/
  adr/            decisões (MADR) — ler antes de decidir arquitetura
  analysis/       levantamentos
  architecture/   DATA_FLOW, FIBER_PHYSICAL_HIERARCHY, ADR legados
  archive/        documentos históricos (não descrevem o sistema atual) — índice em archive/README.md
  ferramentas-agente.md   inventário do ecossistema de agente
docker/, scripts/, services/
```

## 5. Convenções de código

- **Python:** black (linha 100), isort (profile black), ruff. `snake_case`,
  `PascalCase` para classes. Exceções Django (`Http404`, `PermissionDenied`),
  nunca `except:` nu. Tipagem encorajada; pyright estrito em
  `inventory/api`, `usecases`, `services`, `integrations/zabbix`.
- **DRF:** serializers mapeiam 1:1 os dicts dos usecases, **sem reordenar
  chaves** (há testes sensíveis à ordem). `get_object_or_404`, nunca
  `.objects.get(pk=pk)` sem guarda. Endpoint DRF novo ou tocado declara o
  esquema (`serializer_class`/`@extend_schema`) para aparecer limpo em
  `/api/schema/swagger/` (EV-0030); a versão é só `v1`, lida do prefixo do caminho.
- **Celery:** tasks em `tasks.py` de cada app; filas `default`, `zabbix`,
  `maps`; agendamento em `beat_schedule` de `core/celery.py` (o
  `django_celery_beat` é uma segunda fonte — não acrescentar lá).
- **Vue:** `<script setup>`, Composition API. Mutações **sempre** por
  `useApi()` (CSRF); nunca `fetch()` cru para POST/PUT/PATCH/DELETE. Stores
  esperam payload SWR `{data, timestamp, is_stale}`. Componentes acima de
  ~600 linhas são sinal de partir, não de continuar.
- **Gráficos:** Chart.js com eixo temporal; cores vêm de tokens CSS, nunca
  hex fixo; `destroy()` em `onBeforeUnmount`; `null` é buraco, não zero.
- **Mapas:** coordenadas do backend em GeoJSON `[lng, lat]`; não converter
  ida-e-volta no frontend.
- **Commits:** Conventional Commits em português (`fix(charts): ...`,
  `feat(mapa): ...`, `docs(adr): ...`), corpo com o porquê, e `fecha EV-NNNN`
  quando fecha um item.
- **PRs:** título Conventional Commits; corpo com Porquê / O quê / Como testar
  / Riscos / Referências (template em `.github/pull_request_template.md`).
  Acima de ~500 linhas de diff, fatiar.

## 6. Design System e UI

Estado atual (Fase 1 do ADR 0007 feita em EV-0028): os tokens do CRM vivem em
`frontend/src/design-system/tokens.css` — Slate por `--n-*` (invertida no
escuro por `data-theme="dark"`/`.dark`), `--surface`/`--canvas`, `--primary-*`
teal `#42B4B8`, semânticas em tripletos RGB, Inter/JetBrains Mono/Outfit
auto-hospedadas em `design-system/fonts/`. `theme.css` deriva todas as variáveis
antigas (`--text-primary`, `--surface-card`, …) desses tokens; `tailwind.config.js`
tem as mesmas cores e fontes do CRM. Fase 2 feita em EV-0044 (`AppHeader.vue`, secções em
`useNavSections.js` — página nova entra lá, não num menu à parte). Ainda falta:
primitivos e a troca de `gray-*`/`green-*` literais nos componentes (Fase 3),
pacote partilhado (Fase 4).

Regras desde já:

- UI nova usa **tokens**, nunca cor literal: utilitários Tailwind `neutral-*`,
  `surface`, `canvas`, `primary-*`, `success|warning|danger|info` (invertem
  sozinhos no escuro — sem pares `dark:`), ou `var(--n-700)` e afins em CSS
  scoped. Não acrescentar hex em `theme.css`; muda-se o token em `tokens.css`.
- Ecrã antigo com `gray-*`/`dark:` literais: `python3 scripts/tw-tokens.py <ficheiro.vue>` converte para tokens
  (só template e `@apply`); rever o diff à mão — cores fora da lista ficam como estão.
- **Modal novo ou tocado usa `components/Common/BaseModal.vue`** (EV-0064): tamanho `detail|md|sm`, `status` do ícone, `dirty` para o aviso de alterações — nunca `window.confirm` para descartar edição.
- Não acrescentar CSS global; estilos ficam scoped no componente.
- Não instalar outra biblioteca de ícones ou de UI sem ADR.
- Para críticas de UI usar a skill `impeccable` só com `critique` e `audit`
  (nunca `craft`, `init`, `document` — reescrevem o mundo visual).

## 7. Zabbix — regras críticas (achados do levantamento)

- `history.get` exige `history` igual ao `value_type` **do item**; perguntar
  com `item.get` (como faz `usecases/devices.py:2296`), nunca fixar `3`.
- Ler `units` do item: `bps` ≠ `Bps` ≠ contador bruto. Converter no backend
  e devolver já em bps.
- **Nunca usar o `limit` do `history.get` para encolher uma série**: corta pelo
  fim da janela (os pontos mais recentes). Quem limita a saída é o bucket
  (`choose_bucket_seconds`, ≤ 1 500 pontos); quem limita a entrada é o tecto do
  período da rota (7 d nas DRF, 30 d na função-view).
- **Toda rota de histórico é fachada de `zabbix_history.fetch_aligned_series`**
  (EV-0029). Não se escreve `history.get` novo em view ou usecase.
- Alinhar RX/TX e IN/OUT por **bucket** (ex.: 60 s), não por `clock` exato;
  devolver `null` real para buracos; o frontend não faz forward-fill.
- Thresholds ópticos (`-24/-27 dBm`) vêm da configuração (`/setup_app/api/config/`),
  não de constantes no componente.
- Distinguir «Zabbix fora» de «sem dados» até à UI.

## 8. Mapas — regras críticas

- A única abstração é `providers/maps/` (EV-0012, fechado): nenhum componente
  importa `google.maps`, `mapbox-gl` ou `leaflet` — só os três providers. Um ecrã
  novo com mapa usa `Map/MapCanvas.vue` (`@ready="map => …"`), desenha por `IMap`
  e põe janelas em `Map/MapPopup.vue`; traçados editáveis por
  `composables/useRouteDrawing.js`. Se falta algo ao `IMap` (estilo, overlay,
  evento), acrescenta-se à interface **e aos três providers**, com teste em
  `tests/unit/providers/`. Não se adiciona lógica `if provider === 'google'` fora dela.
- Tema: o fundo do mapa segue o tema da interface pela factory (`mapTheme.js`, EV-0045);
  nenhum componente chama `setTheme` à mão nem escolhe estilo Mapbox por tema.
- Marcadores de estado: `createMarker({color, size})` + `setStyle({color})` quando
  o estado muda; nunca recriar o marcador para mudar de cor. Polígonos (áreas) por
  `createPolygon`; cursor por `setCursor`; `ResizeObserver` → `resize()`.
- Janelas e tooltips sobre o mapa são Vue: `Map/MapPopup.vue` ancora o conteúdo
  por coordenada via `IMap.latLngToPixel` (pixel relativo ao container) e segue o
  evento `move`. Nada de `InfoWindow`/`L.popup`/`mapboxgl.Popup` nos componentes.
- Viewport: ouvir `idle` e ler `getBounds()` (bbox no formato da API). Enquadrar
  (`fitBounds`) só no primeiro lote de dados ou a pedido do utilizador — nunca a
  cada fetch por bbox.
- Estado em tempo real vem do WebSocket, não de polling. O backend publica
  `{event: 'dashboard.status', data: {hosts}}` e `{type: 'cable_status_update',
  cables}`; o **único** intérprete no frontend é
  `composables/useRealtimeStatus.js` (`normalizeRealtimeMessage`). Nenhum
  componente lê `lastMessage` à mão (EV-0014: três consumidores esperavam
  formatos que nunca chegavam).
- Payloads de cabos: aceitar `bbox`, simplificar geometria, nunca `path` e
  `path_coordinates` ao mesmo tempo.
- Geometria em PostGIS: proximidade é `ST_DWithin` via `usecases/spatial.py`
  (`find_site_within`, `find_cables_near_path`, `get_sites_within_radius`) —
  nunca haversine em Python sobre a tabela. `Site.location` é derivado de
  `latitude/longitude` pelo sinal `pre_save` (EV-0024); escreve-se lat/lng, não
  o `Point`. `FiberCable.path` é a geometria oficial do cabo.
- KML: um cabo por Placemark; suportar `MultiGeometry`, `gx:Track`, KMZ.

## 9. Workflow de desenvolvimento

### Comandos

```bash
# stack completo (PostGIS, Redis, web, celery) — porta 8100
make up            # docker compose -f docker/docker-compose.yml up -d
make logs / make down

# dependências: runtime (= imagem de produção) ou runtime + testes/lint/stubs
make requirements · make requirements-dev     # pip -r backend/requirements[-dev].txt

# backend local (precisa de GDAL/GEOS e DJANGO_SETTINGS_MODULE=settings.dev)
make run · make migrate · make makemigrations · make shell

# testes backend — SEMPRE a partir da raiz do repo
pytest -q backend/inventory/tests/test_fibers_api.py        # scoped (o padrão)
pytest -q -m "not slow and not integration"                 # rápidos
coverage run -m pytest -q && coverage report                 # como o CI

# qualidade backend
make lint-changed BASE=origin/main      # o que o CI exige: black/isort/ruff nos .py alterados face à base do PR (EV-0022; a base é `main` desde EV-0035)
make lint          # árvore inteira — ainda não passa (2.985 achados ruff, 283 ficheiros por formatar em 2026-10-04)
make precommit     # instala os hooks (black/ruff/isort/shellcheck nos ficheiros em staging)

# frontend
cd frontend && npm install && npm run test:unit             # 306 testes, ~10 s
cd frontend && npm run build                                # sai em backend/staticfiles/vue-spa (minificado; console.log sai só em produção)
cd frontend && npm run lint                                 # ESLint a zero desde EV-0022; o CI guarda isso

# saúde
make health · make ready · make live

# Central de Evolução (ADR 0006; depois do deploy com a app `evolucao`)
make evolucao-sync   # fecha na Central o que o /healthz diz estar no ar e regenera o bloco EVOLUCAO deste ficheiro

# ecossistema de agente
make skills        # repõe .claude/skills/ a partir de skills-lock.json
```

### Testes: scoped na iteração, suite completa só no portão

- Durante o desenvolvimento, correr **só a área mexida**. A suite completa
  corre a pedido explícito do utilizador, no momento de push/PR.
- Testes espaciais precisam de GDAL (`apt install gdal-bin libgdal-dev` ou o
  container). Sem GDAL, 7 ficheiros falham na **coleta** — não é regressão
  do código.
- Runs em background: `PYTHONUNBUFFERED=1 pytest -v ... > saida.log 2>&1`;
  **nunca** canalizar a saída do portão por `| tail`. Filtra-se na leitura.
- Cobertura: desde EV-0006 o CI mede **todas** as apps. Medido em
  2026-10-04 (fim do EV-0027, 1.322 testes): **61 %** no total (branch
  coverage) — `evolucao` 98 %, `maps_view` 90 %, `service_accounts` 86 %,
  `core` 85 %, `setup_app` 79 % (era 45 %), `inventory` 63 %, `integrations`
  62 %, `monitoring` 56 %, `telemetry` 42 %, `gpon`/`dwdm` 0 % (scaffolds).
  Depois de fundir o `main` (EV-0035, 1.337 testes): **59 %** — o `main`
  trouxe código sem testes (`inventory/tasks.py`, `fiber_alarm_configs.py`,
  `integrations/zabbix/client.py`). O limiar do CI
  sobe (ratchet) quando um item acrescenta testes: ao fechar um item com
  testes novos, correr a suite completa e subir `--fail-under` em
  `.github/workflows/tests.yml` para o valor medido menos um ponto de margem
  (EV-0006: 51 % → 50; EV-0008: 52 % → 51; EV-0015: 53 % → 52; EV-0023: 54 % → 53; EV-0017: 60 % → 59; EV-0027: 61 % → 60; EV-0035: 59 % → 58, única descida, pelo código do `main`).

### Checklist antes do commit

1. `make lint-changed` limpo (é o que o job `backend-lint` corre; formatar um ficheiro já sujo que se tocou faz parte).
2. Testes da área passam; teste novo acompanha código novo.
3. Migração revista à mão (nome, reversibilidade, índices).
4. Cache invalidada onde se mutou inventário (§2.4).
5. Nenhum `print`, `console.log` novo, `TODO` sem item `EV-`, segredo, HTML
   de teste ou ficheiro de backup.
6. Se mudou padrão transversal: este `CLAUDE.md` e, se arquitetural, um ADR.
7. Mensagem de commit com o porquê e, se fecha item, `fecha EV-NNNN`.

## 10. O que NÃO fazer (red flags)

- **Não gerar dados falsos** para preencher gráfico, tabela ou KPI (EV-0001).
- **Não chamar o Zabbix fora do gateway**, nem fixar `history: 3`.
- **Não criar endpoint sem autenticação** sem justificativa escrita.
- **Não adicionar uma quinta pilha de mapa** nem outro loader de Google Maps.
- **Não duplicar funções de gráfico** por cor ou por lado (origem/destino);
  parametriza-se.
- **Não usar `setTimeout` para esperar canvas/DOM**; usa-se `nextTick`,
  `ref` com `watch` e `onMounted`.
- **Não deixar instâncias Chart.js, sockets ou listeners sem cleanup.**
- **Não commitar `staticfiles/`, `playwright-report/`, dumps, `.env`,
  tokens, backups `.vue`.**
- **Não escrever no `.env` por API** sem revisão de segurança (a cadeia
  staff → `.env` → `shell=True` em `service_reloader.py` é sensível).
- **Não criar ficheiros `.md` de planeamento ad-hoc** no repositório. Notas
  de sessão vivem na memória ou em `*.local.md` (ignorado). Levantamentos
  formais vão para `doc/analysis/` com data no nome.
- **Não ampliar o diff por conta própria** («já que estou aqui»). Um item de
  cada vez.
- **Não correr `make fmt`/`black .` com outro agente ativo.**

## 11. O que sempre fazer

- **Começar por este ficheiro**, depois `estado_da_sessao.md`, depois o quadro.
- **Consultar `doc/adr/`** antes de decisão arquitetural; **criar ADR** quando
  tomar uma (template em `doc/templates/adr.md`).
- **Abrir item `EV-`** com prova quando encontrar problema fora do âmbito do
  pedido atual — em vez de corrigir «de passagem» ou deixar `TODO`.
- **Escrever testes junto com o código.**
- **Atualizar este `CLAUDE.md`** quando introduzir padrão novo.

### 🧩 Antes de codar: ver se há uma skill que ajude

1. Olhar as skills carregadas na sessão. Se alguma casa com a tarefa,
   invocá-la **antes** de tocar em código.
2. Se nenhuma casar e o domínio for novo: `skills find <termo>`.
3. Instalar só o que é desta stack:
   `skills add <owner/repo> --skill <nome> -a claude-code -y`. O lock
   (`skills-lock.json`) é versionado; `.claude/` não. Nunca
   `skills experimental_install` (escreve em `.agents/`). Skills novas só
   entram na sessão **seguinte**.

**Instaladas (2026-10-04):** `find-skills`, `skill-creator`,
`web-design-guidelines`, `task-observer`, `vue-best-practices`,
`vue-pinia-best-practices`, `vue-router-best-practices`,
`vue-testing-best-practices`, `impeccable` (só `critique`/`audit`). O
registro público não tem skills de Django/DRF/Celery/PostGIS (verificado com
`skills find`); se aparecerem, entram pelo lock. Inventário completo, plugins
e armadilhas em [`doc/ferramentas-agente.md`](doc/ferramentas-agente.md).

**Precedência:** este `CLAUDE.md` e os ADRs **vencem sempre** a skill. Uma
skill de terceiro é referência de ofício, não ordem; corre com todas as
permissões do agente — **ler antes de confiar**.

### 🔭 Ativação do `task-observer` (no arranque da sessão)

Antes da primeira chamada de ferramenta — incluindo antes de propor um plano —
invocar a skill `task-observer` **e executar o seu Session Start Protocol**.
Carregar e executar são passos separados. Ao terminar uma tarefa, reportar
uma linha com as observações registradas (ou «nenhuma, e porquê»). O registro
fica em `skill-observations/observation-log/` (ignorado pelo Git).

### ⛔ Gravar em memória ao FIM DE CADA sessão (obrigatório)

**Nenhuma sessão termina sem escrever memória**, em
`~/.claude/projects/<slug>/memory/`:

1. Uma linha em *Onde se mexeu por último* no `MEMORY.md` (com a data).
2. No livro da área (`livro_mapas.md`, `livro_graficos.md`,
   `livro_inventario.md`, `livro_zabbix.md`, `livro_sistema.md`): mover para
   **Feito** o que entrou, **com o nº do PR ou o SHA**, nunca um adjetivo; e
   acrescentar páginas novas (decisões, armadilhas, números medidos).
3. Toda ideia ou dívida discutida entra no roteiro do livro **nesse momento**.
4. `estado_da_sessao.md` passa a `finalizada`.

Regras de higiene: o «feito» ancora-se em PR/SHA verificável; antes de listar
pendências, verificar o estado real (`git log`, quadro); não reintroduzir
dívida que o Paulo deu como resolvida sem prova nova. Lições transversais vão
para `feedback_<tema>.md`.

> A garantia mecânica disto no CRM é um hook `Stop` em `~/.claude/settings.json`.
> Aqui ainda não existe — montá-lo é passo da Fase 2 de
> `doc/ferramentas-agente.md`. Até lá, a regra depende de disciplina.

## 12. Documentos de referência

- [`README.md`](README.md) — visão geral; [`doc/README.md`](doc/README.md) — índice da documentação (o que descreve um estado antigo está em `doc/archive/`).
- [`doc/analysis/2026-10-04-levantamento-geral.md`](doc/analysis/2026-10-04-levantamento-geral.md) — diagnóstico completo e origem do quadro.
- [`doc/adr/`](doc/adr/README.md) — decisões; ADR 0005 (este manual), 0006 (Central), 0007 (visual), 0008 (tokens de conta de serviço), 0009 (topologia em SVG próprio).
- `/api/schema/swagger/` (autenticado) — referência viva da API DRF (OpenAPI 3, EV-0030); `python manage.py spectacular --file openapi.yaml` gera o ficheiro.
- [`doc/ferramentas-agente.md`](doc/ferramentas-agente.md) — skills, MCP, plugins, hooks, memória; como repor numa máquina nova.
- [`doc/architecture/DATA_FLOW.md`](doc/architecture/DATA_FLOW.md), [`FIBER_PHYSICAL_HIERARCHY.md`](doc/architecture/FIBER_PHYSICAL_HIERARCHY.md) — domínio.
- [`DEPLOY.md`](DEPLOY.md), [`docker/docker-compose.prod.yml`](docker/docker-compose.prod.yml), [`scripts/deploy.sh`](scripts/deploy.sh) — produção.
- `.env.production.example` — todas as variáveis, comentadas.
- CRM Simples Internet (`kaled182/crm-simples-internet`): `CLAUDE.md`,
  `docs/adr/0016` (design system), `docs/adr/0042` (Central), `docs/prompt-replicar-setup.md`.

## MCP: `code-review-graph`

Quando ativo (`.mcp.json` + `enabledMcpjsonServers` em
`.claude/settings.local.json`), usar o grafo antes de `Grep`/`Read` para
explorar impacto de uma mudança. O grafo **não se atualiza sozinho**: correr
`build_or_update_graph_tool` após mudanças grandes. A base fica em
`.code-review-graph/` (ignorada).
