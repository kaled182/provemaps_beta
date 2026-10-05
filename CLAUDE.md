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
fila quando o Paulo o aceita. O assistente **abre** itens novos quando
encontra um problema com prova (ficheiro, linha, comando que reproduz).

**Implanta-se ANTES de passar ao item seguinte.** Um item «feito» que não está
em produção é um item que a fila diz resolvido e o utilizador continua a
sofrer.

**Ao fechar um item, o commit leva o verbo:** `fecha EV-0003`. Mencionar o
código sem o verbo **não** fecha — de propósito. Quando a Central de Evolução
existir (ADR 0006), é este verbo que fecha o item sozinho ao chegar a produção;
até lá, o verbo já vale como convenção e o quadro abaixo é atualizado à mão
no mesmo commit.

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

## 📌 QUADRO — o que falta

> **Manual até o deploy da Central.** A Central de Evolução existe desde EV-0027 (app `evolucao`,
> API `/api/v1/evolucao/`, ecrã `/system/evolucao`, botão Reportar na barra lateral). Assim que estiver em
> produção e semeada (`migrate` + `manage.py evolucao_seed_quadro`), este bloco passa a ser **gerado** por
> `make evolucao-sync` (fecha o que o `/healthz` diz estar no ar e reescreve o bloco) — uma edição à mão
> desaparece na geração seguinte. Até lá, edita-se **só** no commit que fecha ou abre um item, com o verbo
> `fecha EV-NNNN`. As prioridades do levantamento de 2026-10-04 foram aceitas pelo Paulo em 2026-10-04
> («podemos implementar tudo»); as fatias de EV-0012/0017/0027, com «Podemos seguir». Detalhe e evidência:
> [`doc/analysis/2026-10-04-levantamento-geral.md`](doc/analysis/2026-10-04-levantamento-geral.md).

<!-- EVOLUCAO:INICIO — quadro manual até a Central (app `evolucao`) estar em produção e semeada; depois `make evolucao-sync` gera este bloco. -->
**A fazer** — vazio em 2026-10-04: os 30 itens aceitos estão em «Feito — aguarda deploy».

**Entrada, por triar — 🐛 Problemas** (abertos pelo assistente com prova; a triagem é do Paulo)

- `EV-0037` **Produção corre com `DEBUG = True`: um 404 em `provemaps.simplesinternet.net.br` devolve a página técnica do Django com o URLconf inteiro** · prioridade por triar · **causa confirmada no deploy de 2026-10-05:** a instalação do `install_ubuntu.sh` corre o `docker/docker-compose.yml` com `DJANGO_SETTINGS_MODULE: settings.dev` fixo (linhas 27/123/174) e `settings/dev.py:67` tem `DEBUG = True` escrito à mão — o `/healthz` de produção diz `"settings": "settings.dev"`; mudar o `.env` não resolve · risco: enumeração de rotas e, num 500, variáveis de ambiente no traceback. Caminho: um perfil de produção nesta pilha (`settings.prod` com `SECRET_KEY`/`ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS` no `.env`) ou, no mínimo, `DEBUG` lido do ambiente em `settings/dev.py`
- `EV-0038` **`scripts/update.sh` falha no passo 2 em qualquer instalação com ficheiros do root: o `git reset --hard` corre como root e o `npm install` como `$SUDO_USER`** · prioridade por triar · `scripts/update.sh:69-72,101-108` · prova: deploy de 2026-10-05 falhou duas vezes com `EACCES` (`node_modules/.../lru-cache` e, depois do `chown`, o `package-lock.json` recriado pelo reset como root); só passou com `chown -R` + `npm ci && npm run build` à mão. Também usa `npm install` apesar do lockfile versionado (EV-0007). Caminho: correr o git como `$REAL_USER` (ou `chown -R` depois do reset) e `npm ci`
- `EV-0039` **Na pilha de produção real (`docker/docker-compose.yml`) o `/healthz` devolve `git_sha: "nosha"` e `version: "dev"`, por isso `make evolucao-sync` nunca fecha itens (fail-closed)** · prioridade por triar · `docker/docker-compose.yml` não passa `GIT_SHA` nem `APP_VERSION` ao build/ambiente (só o `docker-compose.prod.yml` o faz, EV-0027b); `.dockerignore:11` exclui `.git`, logo o fallback `settings/dev.py:234` também não encontra o SHA · prova: `curl localhost:8100/healthz` em produção após o deploy 1.5.0 → `"git_sha": "nosha", "version": "dev"`. Caminho: `build.args: GIT_SHA` nos três serviços + `export GIT_SHA=$(git rev-parse HEAD)` e `APP_VERSION=$(cat VERSION)` no `update.sh`
- `EV-0040` **`evolucao_seed_quadro` falha dentro do container porque o `CLAUDE.md` não entra na imagem** · prioridade por triar · `docker/dockerfile:121-123` copia `backend/`, `scripts/` e `VERSION`, não o `CLAUDE.md`; `evolucao_seed_quadro.py:104` usa `BASE_DIR/CLAUDE.md` por omissão · prova: produção 2026-10-05 → `CommandError: Ficheiro não encontrado: /app/CLAUDE.md`; passou só com `docker cp CLAUDE.md docker-web-1:/app/`. Caminho: `COPY CLAUDE.md /app/CLAUDE.md` no dockerfile (o `evolucao_quadro` que reescreve o bloco também precisa dele)
- `EV-0034` **Modal de importação KML do NetworkDesign é DOM legado: `features/networkDesign/partials/import_kml.js` (399 linhas) manipula por `getElementById` o HTML que vive em `NetworkDesignView.vue` e expõe `window.openKmlModal`/`closeKmlModal`/`initializeKmlModal`/`__FIBER_DEVICE_OPTIONS`** · prioridade por triar · `NetworkDesignView.vue:814-976,1689-1790`, `fiberRouteBuilder.js` (importa-o) · prova: `grep -n "window\." import_kml.js` → 9 globais; `waitForKmlModal` faz 5 tentativas à procura dos `id="kml*"` no DOM. Era o «Fica» de EV-0015 apontado para 0012d; não é problema de provider de mapa e ficou de fora da EV-0012. Caminho: `NetworkDesign/KmlImportModal.vue` com `useApi` e props/emits, sem `window.*`
- `EV-0032` **Healthcheck de produção bate em `/healthz/` com barra e recebe 302 para o login; o nginx responde «healthy» estático sem consultar o backend** · prioridade por triar · `docker/docker-compose.prod.yml:43,178`, `docker/nginx/nginx.prod.conf:78-82`, `backend/core/urls.py:121-123`, `core/middleware/auth_required.py:39-41` · prova: `Client(HTTP_HOST='localhost').get('/healthz/')` → `302 /accounts/login/?next=/healthz/` (sem barra → 200). `wget --spider` e `urllib` seguem o redirect e dão 200 na página de login, logo o container passa como saudável mesmo com a base em baixo. Caminho: healthchecks sem barra (ou aceitar ambas na whitelist) e o nginx a fazer proxy do `/healthz` real
- `EV-0033` **`doc/api/AUTHENTICATION.md`, `EXAMPLES.md` e `api/README.md` descrevem `Authorization: Token`, `rest_framework.authtoken`, `/api/token/`, Basic auth e CORS que não existem** · prioridade por triar · `backend/settings/base.py:657` (`REST_FRAMEWORK` só tem `SessionAuthentication`; não há `authtoken` nem `corsheaders` em `INSTALLED_APPS`); o login real é `/accounts/login/` em dois passos com TOTP · liga-se ao EV-0023 (`service_accounts` gera tokens que nada consome): ou se implementa a autenticação por token e a doc fica certa, ou a doc é reescrita para sessão+CSRF. **Atualização EV-0023:** a autenticação por token agora existe (`Authorization: Bearer`, ADR 0008) — a doc deve descrever esse esquema, não `authtoken`/`/api/token/`
- `EV-0031` **15 templates Django legados carregam Tailwind Play CDN (compilador em runtime) e obrigam o CSP a manter `'unsafe-eval'` e os hosts `cdn.tailwindcss.com`/`cdnjs.cloudflare.com`** · prioridade por triar · `backend/templates/{base,base_with_sidebar}.html`, `templates/registration/*.html` (8), `maps_view/templates/{dashboard,base_dashboard}.html`, `setup_app/templates/{base_setup_dashboard,base_first_time_setup,setup/manage_environment}.html`; `backend/settings/base.py:112-130` · prova: `grep -rl cdn.tailwindcss.com backend/templates backend/maps_view/templates backend/setup_app/templates` → 15. Caminho: ligar o CSS do build do Vite (manifest já disponível no context processor) e incluir esses templates no `content` do Tailwind; confirmar `darkMode` (o Play CDN usa `media` por omissão onde não há `tailwind.config`); só depois apertar o CSP

**Feito — aguarda deploy** (sai daqui quando o commit `fecha` chegar a produção). **2026-10-05: a 1.5.0 (`195c9f5`) está em produção** (`update.sh` + build manual, ver EV-0038) e a Central foi semeada com 37 itens; o bloco continua manual porque o `/healthz` de produção não expõe o SHA (EV-0039) e o `evolucao-sync` fica fail-closed — os itens abaixo só saem daqui quando isso estiver resolvido

- `EV-0042` **Em produção o WebSocket `/ws/dashboard/status/` falhava a ligar; o mapa caía no modo degradado (polling REST de 60 s)** · P2 · fechado em `fix(nginx)` 2026-10-05 — o proxy é o container `nginx` do próprio `docker/docker-compose.yml` (`docker-nginx-1`), que em modo HTTP (sem `DOMAIN_NAME`) carrega `docker/nginx/http.conf`; só o `https.conf.template` tinha o upgrade. `http.conf` ganha `location /ws/` com `proxy_http_version 1.1` + `Upgrade`/`Connection "upgrade"` e timeouts de 1 h. A config entra por bind mount, logo basta `docker compose restart nginx` (sem rebuild). Prova: consola do browser 2026-10-05, `WebSocket connection ... failed` ×10; `ps` mostra `docker-nginx-1` nas portas 80/443
- `EV-0041` **Mapbox em produção: «Erro ao carregar o mapa: Style is not done loading» — nenhum cabo desenhado (regressão de EV-0012c)** · P1 · fechado em `fix(mapa)` 2026-10-05 — `MapboxPolyline`/`MapboxPolygon` chamavam `addSource` no construtor, logo a seguir a `createMap`, antes do `load` do estilo (o `isMapReady` do `main` fazia esta guarda e saiu na fusão). `MapboxMap.whenStyleReady(fn)` executa já ou na fila do `load`/`style.load` (o fallback de estilo volta a esperar); estilo e traçado dados entretanto são guardados e usados ao entrar; `remove()` antes do load cancela a entrada. 3 testes. Visto em produção na 1.5.0, provedor Mapbox
- `EV-0036` **A aba «Sugestões & Bugs» do modal de Changelog (em produção) era um formulário falso: `submitSuggestion` esperava 800 ms e mostrava «Sua sugestão foi registrada» sem enviar nada** · P2 · fechado em `feat(changelog)` 2026-10-04 — a aba passa a explicar que os relatos vão para a Central de Evolução e tem um botão que emite `reportar`; a barra lateral fecha o changelog e abre o `ReportarModal` (EV-0027); link para `/system/evolucao`. Formulário, `types`, `submitSuggestion`, `resetForm` e o CSS respetivo apagados. Versão **1.5.0** (04 Out 2026) em `VERSION`, `version.json`, `frontend/package.json`/lock e no `ChangelogModal` (entrada que resume os 30 itens: funcionalidades, melhorias e correções); `version.json` é o que o `check_update` da produção lê no GitHub
- `EV-0035` **Todo o trabalho de 2026-10-04 (EV-0001…0030) assentava em `inicial` (59e0bb8, 2026-04-04); a produção corre `main` (v1.4.14.0, 9b4eccc, 2026-05-03), 120 commits à frente** · P1 · fechado em `merge(main)` 2026-10-04 — `origin/main` fundido no ramo (merge commit, `--no-ff`), 17 conflitos resolvidos **a favor da arquitetura nova**, portando o que o `main` acrescentou: à pilha antiga de mapa → `providers/maps/` (paleta «offline = âmbar», `displayStatus` agregado por site, lazy `defineAsyncComponent` dos modais, carga paralela, centro/zoom do builder pela configuração, `SiteEditModal` com `LocationPickerModal`); ao `api_views.py` (apagado em EV-0017) → `usecases/{connections,config,backups}.py` (psycopg 3 no teste de BD, corpo do e-mail de teste, limiares ópticos por distância `OPTICAL_THRESHOLDS_BY_DISTANCE`, `MAP_*`/`MAPBOX_TOKEN` lidos da base e purgados do `.env`, zip de backup sem cifra + `*.config.json` no `restore_db`); `views_spa` ganha o `VITE_ENTRY` do manifest sem a chave do Google; rotas `api/cron/*` e `first_time/restarting/`. Migrações minhas renumeradas atrás das do `main`: `inventory 0069→0071` (jsonb), `0070→0072` (location). 7 testes que o `main` deixou desalinhados com o próprio código (sonda `apiinfo.version` do cliente Zabbix 7 consumia os mocks; dashboard legado → 301 para `/`; `restore_db` lê `returncode`) corrigidos + 1 teste novo (Zabbix 7 → Bearer). 31 ficheiros do `main` formatados (black/isort/ruff) para o portão `lint-changed` passar **contra `origin/main`** — o PR tem de apontar a `main`; contra `inicial` o portão apanharia os 120 commits do `main`. Portões: 1.337 testes backend, 530 frontend, ESLint 0, build OK. **Fica:** cobertura caiu de 61 % para **59 %** (código do `main` sem testes: `inventory/tasks.py`, `fiber_alarm_configs.py`, `client.py`) → `--fail-under` 60 → **58**; o ratchet retoma daqui. `SystemPanel.vue` faz `fetch` POST cru para `perform-update` (SSE; `useApi` não faz streaming). Smoke visual nos três provedores e no dashboard continua por fazer antes do deploy (EV-0012/EV-0028 já o pediam)
- `EV-0012` **Quatro pilhas de mapa paralelas; só `CustomMapViewer` honra os três provedores; `NetworkDesign` quebra com `osm`** · P2 · fechado em 4 fatias 2026-10-04 (aprovadas pelo Paulo, «podemos seguir»): **0012a** `feat(mapa)` — `LeafletProvider` registado como `osm` na factory, `markerStyles.js` partilhado, mortos apagados; **0012b** `refactor(mapa)` — `MapView.vue` sem `vue3-google-map` (dependência removida), `IMap` ganha bounds/`idle`/`move`/`latLngToPixel` relativo ao container, `IMarker.iconUrl`, hover em `IPolyline`, `Map/MapPopup.vue` substitui o `InfoWindow`; **0012c** `refactor(mapa)` — `CustomMapViewer` (2.874 → 1.998 linhas) e os mini-mapas de `SiteEditModal`/`DeviceEditModal` sem ramos por provider; `IMarker.setStyle`, `IPolyline.setStyle`, `createPolygon`, `setCursor`, `resize`, `setTheme`, `fitBounds{padding,maxZoom}`, opções tema/controlos, estilo Mapbox com fallback no provider; `App.vue` sem pré-carregar o Google; **0012d** `refactor(mapa)` — a pilha `useMapService`/`mapPlugins`/`UnifiedMapView.vue` (Google-only, com `drawingPlugin` cuja API os consumidores nem chamavam certo) sai: `Map/MapCanvas.vue` cria o mapa pela factory e `composables/useRouteDrawing.js` desenha/edita traçados com vértices arrastáveis sobre `IMap`; `CableMapModal` (agora carrega o traçado atual) e `FiberRouteEditor` (agora salva o traçado editado) usam-nos; `fiberRouteBuilder.js` perde o `waitForGoogleMaps`/`window.initMap` e o realce de pesquisa Mapbox-only; apagados `utils/{mapLoader,googleMapsLoader}.js`, `@googlemaps/markerclusterer`, os 3 docs da `UnifiedMapView` (fica `Map/README.md`), e a `<meta google-maps-api-key>` do `base_spa.html` (a chave deixa de ir no HTML; `views_spa` não a injeta). Total: 4 commits, 120 testes novos de mapa; frontend 520 testes. **Fica:** `Map/RadiusSearchTool.vue` ainda é Google-only (só aparece com provider google, desligado por omissão); `import_kml.js` continua DOM legado (EV-0034); `tests/e2e/map-loading.spec.js` só fala do Google; validar a olho nos três provedores antes do deploy — os quatro commits não tiveram smoke visual
- `EV-0001` **Gráfico óptico desenha dados aleatórios quando o Zabbix não devolve histórico** · P1 · fechado em `fix(charts)` 2026-10-04 — `frontend/src/utils/opticalHistory.js` é a única fonte das mensagens «sem dados»/«erro»
- `EV-0002` **`/api/config/` entrega chaves Google/Mapbox/Esri a qualquer visitante, sem login** · P1 · fechado em `fix(auth)` 2026-10-04 — middleware responde 401 JSON a `/api/*` sem sessão; a view tem guarda própria. «Mapbox só via proxy» fica para EV-0012 (uma pilha de mapa)
- `EV-0003` **Endpoints de tráfego pedem `history: 3` fixo; itens float devolvem gráfico vazio** · P1 · fechado em `fix(zabbix)` 2026-10-04 — `inventory/domain/zabbix_history.py` resolve `value_type`/`units` por `item.get` e os dois endpoints DRF usam-no; resposta ganha `unit_in`/`unit_out`
- `EV-0004` **`api_port_traffic_history` sem `@login_required`** · P1 · fechado em `fix(auth)` 2026-10-04
- `EV-0005` **Tokens Mapbox literais e dump com `auth.user` versionados** · P1 · ficheiros removidos/placeholder em `chore(security)` 2026-10-04 — **a rotação do token no Mapbox é manual, pelo Paulo**; o token continua no histórico do Git até lá
- `EV-0007` **`package-lock.json` ignorado + `npm ci` no Dockerfile e no CI → build não reprodutível** · P1 · fechado em `build(frontend)` 2026-10-04 — lockfile versionado; workflow diário instala em `frontend/`
- `EV-0006` **Cobertura «60 %» do CI mede só `core`, `maps_view`, `setup_app`** · P1 · fechado em `ci(coverage)` 2026-10-04 — todas as apps medidas; cobertura real 51 % (inventory 48 %, setup_app 45 %); limiar do CI passa a 50 % com ratchet
- `EV-0008` **~61 testes backend nunca coletados; três configs pytest divergentes** · P2 · fechado em `test(pytest)` 2026-10-04 — 1.050 coletados (eram 996); `backend/pytest.ini` canónico, raiz espelha; destapou bug real: colunas `json` das rotas rebentavam no psycopg3 → migração `inventory 0071` para `jsonb` (era 0069; renumerada em EV-0035 atrás das do `main`)
- `EV-0009` **121 testes frontend fora do `include` do Vitest; Playwright lista 0 testes** · P2 · fechado em `test(frontend)` 2026-10-04 — 426 testes em 35 ficheiros (eram 311/29); Playwright lista os specs E2E; `fiberService.test.js` (importava funções inexistentes) removido
- `EV-0010` **Merge RX/TX e IN/OUT por `clock` exato gera buracos ou forward-fill que esconde quedas** · P2 · fechado em `fix(charts)` 2026-10-04 — backend alinha por bucket (60 s a 1 h conforme o período, ≤1.500 pontos) com `null` real; frontend sem forward-fill, zero preservado, `spanGaps` desligado
- `EV-0011` **Instâncias Chart.js nunca destruídas; render por `setTimeout`; fetch duplicado sem `AbortController`** · P2 · fechado em `refactor(charts)` 2026-10-04 — todo gráfico é um `TimeSeriesChart.vue` (destroy em `onBeforeUnmount`, nasce quando o canvas existe, resposta mais recente ganha)
- `EV-0026` **Componente único `TimeSeriesChart.vue`** · Ideia · fechado no mesmo commit — substitui os 4 builders de `FiberCableDetailModal` (3.859 → 3.385 linhas), o Chart.js e o canvas manual de `PortTrafficModal`, e o canvas de `AlarmConfigModal`; eixo temporal proporcional, cores por tokens
- `EV-0013` **`list_fiber_cables` devolve geometria duplicada de todos os cabos, sem bbox; N+1 em `cable_type`** · P2 · fechado em `perf(inventory)` 2026-10-04 — `cable_type` por JOIN, cabo com porta nula não rebenta, `?bbox=` filtra o payload cacheado. **Fica:** `path`+`path_coordinates` duplicados no serializer DRF e `ST_Simplify` — os consumidores são as pilhas de mapa (EV-0012)
- `EV-0014` **`CustomMapViewer` faz polling de 30 s em vez do WebSocket; `SiteDetailsModal` cria um socket por abertura sem cleanup** · P2 · fechado em `fix(realtime)` 2026-10-04 — destapou que o contrato do canal estava quebrado em TODOS os consumidores (store esperava `host_update`, modal esperava `data.devices`; o backend publica `dashboard.status`/`cable_status_update`): `composables/useRealtimeStatus.js` passa a ser o único intérprete
- `EV-0015` **KML: só `LineString` 2.2, Placemarks concatenados num único traçado, sem KMZ/MultiGeometry** · P2 · fechado em `feat(kml)` 2026-10-04 — `inventory/domain/kml.py`: qualquer namespace, KMZ, `MultiGeometry`, `gx:Track`, um traçado por Placemark (o mais longo vira o cabo), dedupe. **Fica:** mover `features/networkDesign/partials/import_kml.js` (DOM legado, `window.*`) para componente Vue — é parte da pilha NetworkDesign (EV-0012d)
- `EV-0016` **Segredo TOTP em texto puro, TOTP caseiro, lockout por sessão** · P2 · fechado em `fix(auth)` 2026-10-04 — `UserProfile.totp_secret` passa a `EncryptedCharField` (Fernet, migração `core 0006` cifra os segredos existentes e é reversível); TOTP pelo `pyotp` (RFC 6238) em vez da implementação caseira; lockout por utilizador na cache (3 falhas → 5 min), não na sessão — limpar o cookie já não zera as tentativas
- `EV-0018` **Dev-tools e pins sem versão na imagem de produção; `django-stubs 5.1` vs Django 5.2; três ficheiros de requirements** · P2 · fechado em `build(deps)` 2026-10-04 — `requirements.txt` só runtime, tudo pinado (`psycopg`, `setuptools`, `uvicorn`+`h11` que o Dockerfile instalava solto); `requirements-dev.txt` novo com pytest/coverage/lint/stubs (django-stubs 5.2.9, drf-stubs 3.16.9) que o CI e o `make requirements-dev` instalam; `requirements_full.txt` (freeze UTF-16 de Windows com MySQL e Playwright) apagado. **Fica:** `uvicorn.workers.UvicornWorker` está depreciado a favor do pacote `uvicorn-worker` — trocar nos compose quando se mexer na infra
- `EV-0019` **Build do SPA sem minify, 518 `console.log`, Tailwind/FontAwesome via CDN forçando CSP com `unsafe-eval`** · P2 · fechado em `build(frontend)` 2026-10-04 — Tailwind 3.4 **compilado no build** (`tailwind.config.js` mínimo: dark por classe, `primary` = esmeralda atual, safelist do grid do mosaico; o CDN nunca processou o `@apply` nem as 163 classes `primary-*`) e FontAwesome 6.5.1 auto-hospedado via npm; `base_spa.html` sem CDN; build minificado (esbuild) com `console.log/debug/info/trace` e `debugger` removidos só em produção (583 → 0; `warn`/`error` ficam). **Fica (EV-0031):** 15 templates Django legados ainda carregam o Play CDN, por isso `'unsafe-eval'` e os hosts de CDN continuam no CSP
- `EV-0020` **Lixo versionado: `setup_app_backup/`, `staticfiles/`, `playwright-report`, `.vue.broken_backup`, HTMLs de teste, `dtemp_fibers.json`** · P3 · fechado em `chore(repo)` 2026-10-04 — 277 ficheiros fora do Git (76 de `setup_app_backup/`, 153 da `staticfiles/` da raiz que o Django nunca serviu — `findstatic` confirma que as fontes vivas são `backend/static` e `maps_view/static` —, relatório do Playwright, 3 HTMLs de teste, 3 backups `.vue`, `.md.old`, `doc/archive/{backup-files,broken-components,scripts-deprecated}`, dois JSON soltos em `docker/`, `backend/data/postgis_inventory.json` e o `d:\temp_fibers.json` com nome mangled); `.gitignore` passa a recusar `*.backup|*.bak|*.old|*.broken*|*_REFACTORED.vue|*.phase*_step*` e `/test_media/`. **Fica (EV-0021):** `doc/guides/testing/TESTS_E2E_SETUP.md` e `TESTS_MOSAIC_MODAL.md` ainda citam os HTMLs de teste; `templates/partials/{header,add_device}.html` carregam `js/partials/{header,add_device}.js` que já não existiam em lado nenhum
- `EV-0021` **Docs obsoletas: 42 citam `zabbix_api`, 20 citam MariaDB; versões 1.4.1 / 2.0.0 / 0.1.3 inconsistentes** · P3 · fechado em `docs(doc)` 2026-10-04 — 38 docs de 2025 (sprints, deploy MySQL, testes MariaDB, caminhos Windows, planos de reorganização) arquivados em `doc/archive/2025-historico/` com banner e índice; 3 duplicados byte a byte removidos (`architecture/ADR/000+004`, `reference/REDIS_HIGH_AVAILABILITY.md`); ~34 docs vivos corrigidos (módulo → `inventory`/`integrations/zabbix`, PostgreSQL+PostGIS, comandos reais do `makefile`, métricas reais, `MODULES.md` reconstruído — eram dois documentos entrelaçados linha a linha); versão única = `VERSION` (1.4.1; `package.json` 0.1.3 → 1.4.1; `doc/README.md` e `releases/README.md` deixam de anunciar 2.0.x como atual; nota do reinício da numeração no CHANGELOG e README). **Fica:** 50 links partidos pré-existentes dentro de `reports/roadmap/archive` e 1 em `guides/WHATSAPP_CONTACTS_IMPLEMENTATION.md` (alvos que nunca existiram), 11 docs vivos com blocos `powershell` fora da lista, e a doc de API (EV-0033)
- `EV-0022` **CI sem lint Python nem ESLint; ESLint falha com 18 erros; pre-commit não aplicado** · P3 · fechado em `ci(lint)` 2026-10-04 — ESLint a zero (eram 17: escapes inúteis, `catch` vazios, `hasOwnProperty`, `break` morto) e job `frontend-lint`; job `backend-lint` corre `black`/`isort`/`ruff` **só nos `.py` alterados face à base** (`scripts/lint-changed.sh`, `make lint-changed`) porque a árvore inteira tem 2.985 achados e 283 ficheiros por formatar — a regra «lint limpo nos ficheiros tocados» passa a ser mecânica; `PLR09xx` (119 achados nos god-modules do EV-0017), `RUF012` e `DJ001` saem da seleção com nota de ratchet; `isort` e `ruff` alinhados (`known_first_party`, `combine_as_imports`); `pre-commit` em `requirements-dev` + `make precommit`. **Destapou bug real:** `fibercable-optical-history` chamava `merge_series`/`history_to_samples`/`choose_bucket_seconds` sem os importar (`NameError` em produção, sem teste) — import no topo do módulo, 404 em cabo inexistente e 2 testes novos
- `EV-0023` **`service_accounts` gera e roda tokens que nenhuma classe de autenticação consome** · P3 · fechado em `feat(auth)` 2026-10-04 — ADR 0008: `service_accounts/authentication.py` (`authenticate_bearer`, `ServiceAccountTokenAuthentication` primeira no DRF, antes da sessão → sem CSRF para clientes com token); o `AuthRequiredMiddleware` aceita o mesmo `Authorization: Bearer` nas rotas que guarda e o DRF reaproveita o principal; principal sem `is_staff`/`has_perm`; `ServiceAccountToken.last_used_at` (migração 0005, escrita ≤ 1×/min); 10 testes. **Fica:** sem throttling por token (EV-0030) e sem escopos por conta — por endpoint, quando houver caso real
- `EV-0024` **Regra dos 100 m e «cabos próximos» em Python O(n²) em vez de `ST_DWithin`; lat/lng não sincroniza com `location`** · P3 · fechado em `perf(spatial)` 2026-10-04 — `usecases/spatial.py` ganha `find_site_within` (ST_DWithin em `Site.location`, geography) e `find_cables_near_path` (pré-filtro `dwithin` em graus no GiST de `FiberCable.path` + `ST_DistanceSphere` exata em metros); o import em lote e `fibers/validate-nearby/` consomem-nas e perdem os dois haversines; `pre_save` em `Site` sincroniza `location` ↔ lat/lng e a migração `inventory 0072` (era 0070; renumerada em EV-0035) preenche os sites antigos (sem `location` eram invisíveis a toda consulta espacial); 10 testes. **Fica:** cabos sem `path` (só `path_coordinates`) não entram na deteção; `QuerySet.update()` não passa pelo sinal
- `EV-0025` **Config default incoerente: `DB_ENGINE=mysql` sem driver, `.env.example` com `DATABASE_*` que ninguém lê, `asgi.py` aponta `core.settings`** · P3 · fechado em `fix(config)` 2026-10-04 — `DB_ENGINE` default `postgis` (aliases `postgresql`/`postgres`); qualquer outro valor levanta `ImproperlyConfigured` no arranque; ramo MySQL/MariaDB removido de `settings/base.py` e `settings/test.py`; `asgi.py`/`wsgi.py` caem em `settings.prod` (fail-safe, recusa `SECRET_KEY` de dev) em vez do inexistente `core.settings`; `.env.example` só com variáveis que o código lê (`DJANGO_SETTINGS_MODULE`, `DB_*` na porta 5433 do compose dev, `TEST_DB_ENGINE`); `docker/docker-compose.test.yml` (MariaDB, sem referências) removido; 8 testes. **Fica:** `docker/docker-compose.postgis.yml` é uma 2ª pilha com nomes antigos (`mapsprovefiber`/`provemaps`) — decidir se se apaga
- `EV-0028` **Alinhamento visual com o CRM — Fase 1: tokens e fontes auto-hospedadas (ADR 0007)** · Ideia · fechado em `feat(design-system)` 2026-10-04 — `design-system/tokens.css` (escala neutra do CRM em RGB, invertida no escuro; `surface`/`canvas`; `primary` teal; semânticas; 10 `@font-face` de Inter/JetBrains Mono/Outfit, woff2 locais, 216 KB); `theme.css` deriva as ~60 variáveis antigas dos tokens (três blocos → um) — toda a app muda para teal/Slate sem tocar em componentes; `tailwind.config.js` = cores e fontes do CRM; 5 testes. **Fica (Fase 3):** 1.775 `dark:` e as classes `gray-*`/`green-*`/`blue-*` literais nos componentes; **validar a olho** (dark e light) antes do deploy — não houve smoke visual nesta sessão
- `EV-0029` **Backend bucketiza séries (60 s) e devolve séries alinhadas, com limite de pontos proporcional ao período** · Ideia · fechado em `refactor(zabbix)` 2026-10-04 — `zabbix_history.fetch_aligned_series(items, time_from, time_till, max_points)` é a fachada única: um `item.get` (tipo/unidades), históricos em paralelo com o `history` certo, bucket escolhido para ≤ `max_points`, `None` real nos buracos; `get_item_by_key` resolve itens ópticos pela chave. As **5 rotas** (porta óptica/tráfego DRF, cabo óptico/tráfego DRF, `ports/<id>/traffic/`) passaram a fachadas — a função-view perdeu o `limit` do Zabbix que cortava os pontos **mais recentes** em períodos longos (30 d a 1 min = 43 k pontos, `limit` 5 000 → só os 3,5 primeiros dias). Chaves mantidas (`timestamp`/`traffic_in`/`rx_power`): o frontend já as consome; mudar para `{t,in,out}` seria churn sem ganho. 3 testes novos + 1 ajustado
- `EV-0030` **OpenAPI (drf-spectacular) e um só esquema de versionamento para `/api/v1/`** · Ideia · fechado em `feat(api)` 2026-10-04 — `drf-spectacular` 0.30 com Swagger UI **auto-hospedado** (`drf-spectacular-sidecar`, sem CDN) em `/api/schema/` e `/api/schema/swagger/`, só para autenticados; esquemas de segurança `cookieAuth` (sessão) e `bearerAuth` (ADR 0008); `core/api_versioning.PathPrefixVersioning` lê `/api/v<N>/` do caminho, rotas legadas sem prefixo contam como `v1`, qualquer outra versão → 404; 5 testes. **Fica:** o gerador documenta 65 caminhos DRF e emite 46 avisos + 22 erros de introspeção (views sem serializer declarado ficam de fora) — resolvem-se com `@extend_schema` quando cada view for tocada; as function views Django (`/api/v1/inventory/*`, `/api/users/*`, `/setup_app/api/*`) não entram no esquema até virarem DRF
- `EV-0017` **`setup_app/api_views.py` com 4.484 linhas sem usecases; `usecases/devices.py` com 2.501** · P2 · fechado em `refactor(inventory)` 2026-10-04, em seis fatias aprovadas pelo Paulo («Podemos seguir») — **`setup_app/api_views.py` deixou de existir**: cada domínio virou `setup_app/api/<dominio>.py` (views finas: `staff_required`, JSON, códigos HTTP, `ConfigurationAudit`) + `setup_app/usecases/<dominio>.py` (lógica em dicts, exceções de domínio com `status`): 0017a backups+nuvem (`115706c`), 0017b `.env`+configuração (`8225ca0`), 0017c gateways+QR WhatsApp (`b01dc42`), 0017d vídeo/câmeras (`468e96d`), 0017e testes de ligação+perfil da empresa+monitorização (`17f30d4`); 0017f `inventory/usecases/devices.py` (2.527 linhas) → `devices_common.py` (tipos, exceções, `ZABBIX_REQUEST` — alvo único de patch), `devices_ports.py` (portas, óptico, tráfego) e `devices_discovery.py` (host Zabbix → Device/Site/Port, listagens); `devices.py` fica como fachada de re-export. Nenhuma rota, código HTTP ou mensagem mudou; 190 testes novos em `setup_app`. **Destapou 2 bugs reais:** `update_configuration` devolvia 500 depois de gravar (`existing_backup_password` indefinido, `7b64d5a`) e o teste de SMS recusava telefones com espaços/`+` (`re.sub(r"\\D")` em raw string). **Fica:** `setup_app/api/*` são function views Django fora do OpenAPI (EV-0030) — viram DRF quando houver caso; `devices_discovery.add_device_from_zabbix` continua com 740 linhas, candidato à próxima fatia quando se mexer na descoberta
- `EV-0027` **Portar a Central de Evolução (ADR 0006) e trocar este quadro manual pela vista gerada** · Ideia · fechado em `feat(evolucao)` 2026-10-04, em três fatias aprovadas pelo Paulo — 0027a (`c3876c2`) app `backend/evolucao/`: `EvolucaoItem` (código `EV-NNNN` por contador atómico; estados `entrada|aceite|a_fazer|feito|recusado`; CHECKs: recusa com motivo, agente com evidência, prioridade 1–4; ordem = prioridade com nulos no fim, depois código), `EvolucaoAnexo`, `usecases.py`, API DRF `/api/v1/evolucao/` (criar/ver: qualquer autenticado, autor da sessão; triagem só `is_staff`, auditada), `evolucao_seed_quadro` idempotente (34 itens deste bloco); 0027b (`17a3a87`) fecho observado: `GIT_SHA` cozido na imagem (dockerfile/compose/`deploy.sh`, que **recusa árvore suja**), `/healthz` com `git_sha`+`iniciado_em`, `scripts/evolucao_fechados.sh` (só commits alcançáveis, por VERBO, fail-closed) → `evolucao_fechar`, `evolucao/quadro.py` + `evolucao_quadro` que reescreve este bloco, `make evolucao-sync`; 0027c frontend: `views/EvolucaoView.vue` em **`/system/evolucao`** (não `/admin/sistema/…` — `/admin/` é o Django admin), abas Problemas/Ideias/Tudo, secções por estado, triagem inline para staff (recusa pede motivo), `components/Evolucao/ReportarModal.vue` (anexos carregam antes do item; captura rota/viewport/navegador), botão Reportar na barra lateral e entrada «Evolução» em System, `useEvolucao`/`useCurrentUser`; tarefa Celery diária `evolucao.tasks.avisar_parados_task` (um email ao staff com os itens parados há 14+ dias, carimbo só depois de enviar). 90 testes backend + 10 frontend. **Fica:** este bloco só passa a gerado depois do deploy + seed; sem hook `Stop` aqui (Fase 2 de `doc/ferramentas-agente.md`) o `make evolucao-sync` é manual; o email do aviso usa as `EMAIL_*` que `sync_gateway_env` escreve no `.env` — sem gateway SMTP ativo o aviso fica no log

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
  components/     Map/, Dashboard/, Inventory/, Fusion/, TraceRoute/, DeviceImport/, Video/, Configuration/, Layout/, Evolucao/ (ReportarModal)
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
tem as mesmas cores e fontes do CRM. Ainda falta: header de duas linhas (Fase 2),
primitivos e a troca de `gray-*`/`green-*` literais nos componentes (Fase 3),
pacote partilhado (Fase 4).

Regras desde já:

- UI nova usa **tokens**, nunca cor literal: utilitários Tailwind `neutral-*`,
  `surface`, `canvas`, `primary-*`, `success|warning|danger|info` (invertem
  sozinhos no escuro — sem pares `dark:`), ou `var(--n-700)` e afins em CSS
  scoped. Não acrescentar hex em `theme.css`; muda-se o token em `tokens.css`.
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
- [`doc/adr/`](doc/adr/README.md) — decisões; ADR 0005 (este manual), 0006 (Central), 0007 (visual), 0008 (tokens de conta de serviço).
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
