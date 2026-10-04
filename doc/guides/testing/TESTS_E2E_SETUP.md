# Testes E2E - Configuração e Execução

**Última atualização**: 2026-10-04

> Os testes de frontend vivem em `frontend/`: **Vitest** (unitários e de componente) e
> **Playwright** (E2E, `@playwright/test`). As páginas HTML soltas
> (`frontend/test-mosaic-dom.html`, `test-mosaic-refs.html`, `test-modal.html`) foram
> removidas do repositório em 2026-10-04 (EV-0020). Para comandos de teste do backend e
> cobertura, ver [TESTING.md](../TESTING.md) e `CLAUDE.md` §9.

## 📦 Dependências

### Frontend (`frontend/package.json`)
- `vitest` + `@vue/test-utils` + `jsdom` - testes unitários e de componente
- `@playwright/test` (^1.49) - testes E2E no navegador

```bash
cd frontend
npm install
npx playwright install chromium   # só na primeira vez (navegador do Playwright)
```

### Backend / Docker
- O Playwright **Python** (`playwright`, `pytest-playwright`) e o Chromium **não** fazem parte de
  `backend/requirements.txt` nem da imagem de produção (`docker/dockerfile`).
- `backend/tests/test_mosaic_rendering.py` (Playwright Python) continua no repositório como teste
  legado: sem `pip install playwright` ele apenas avisa e sai. O serviço `test-e2e` do
  `docker/docker-compose.yml` (profile `testing`) depende dele e hoje não funciona: a imagem não traz
  Playwright e o volume aponta para `../test_mosaic_rendering.py`, que não existe na raiz.

---

## 🧪 Testes Disponíveis

### 1. **Vitest** (unitários e de componente)
**Pastas:** `frontend/tests/unit`, `frontend/tests/components`, `frontend/src/**/__tests__`

```bash
cd frontend
npm run test:unit                                  # toda a suite (vitest run)
npm run test:unit:watch                            # modo watch
npx vitest run tests/unit/SiteCamerasTab.spec.js   # um ficheiro
```

**O que cobre (exemplos):**
- ✓ Abas do modal de site: `SiteCamerasTab`, `SiteDevicesTab`, `SiteFibersTab`
- ✓ Composables: `useSiteCameras`, `useWebSocket`, `useRealtimeStatus`, `useMapService`
- ✓ Stores Pinia, gráficos (`TimeSeriesChart`), utilitários

**Vantagens:**
- Não precisa de backend nem de navegador
- Execução em segundos
- É o que corre no CI

---

### 2. **Playwright** (E2E automatizado)
**Pasta:** `frontend/tests/e2e` (`testDir` em `frontend/playwright.config.js`)

| Spec | O que verifica |
|------|----------------|
| `dashboard.spec.js` | Fluxo do dashboard: carga, hosts, WebSocket, mapa |
| `map-loading.spec.js` | Carga do mapa em `/monitoring/backbone` |
| `mapView.spec.js` | Smoke test do `MapView` (com e sem API mock) |
| `nav_menu.spec.ts` | Menu de navegação visível nas rotas principais |
| `radius-search.spec.js` | Ferramenta de busca por raio |

`fixtures/auth.js` faz login com o utilizador `playwright_test` em `/accounts/login/`; esse
utilizador tem de existir na base usada pelo teste.

**Como executar localmente:**
```bash
# 1. Servidor a correr (a porta padrão do Playwright é 8000)
make run                       # backend local; ou: make up (compose dev, porta 8100)

# 2. Executar
cd frontend
npm run test:e2e                                  # toda a suite E2E
npx playwright test tests/e2e/mapView.spec.js     # um spec
```

> O `baseURL` vem de `E2E_BASE_URL` (padrão `http://localhost:8000`). O compose de desenvolvimento
> publica a porta **8100**; nesse caso use `E2E_BASE_URL=http://localhost:8100`. A fixture
> `auth.js` usa `http://localhost:8000` fixo no login.

**Saídas geradas:**
- `frontend/playwright-report/` - relatório HTML (reporter `html`, ignorado pelo Git)
- Screenshot em caso de falha (`screenshot: 'only-on-failure'`)
- Trace na primeira repetição (`trace: 'on-first-retry'`)

---

## 🔍 Interpretação dos Resultados

```bash
cd frontend
npx playwright show-report            # abre o relatório HTML
npx playwright show-trace <trace.zip> # inspeciona um trace
```

- **0 testes listados**: confira que está a correr em `frontend/` e que o `testDir` é `./tests/e2e`
  (os specs do Vitest não são do Playwright).
- **Falha em `authenticate`**: o utilizador `playwright_test` não existe ou a senha não confere.
- **Timeout ao abrir o mapa**: backend parado ou chave de mapas não configurada.

---

## 🐛 Debug Avançado

```bash
cd frontend
npx playwright test --headed          # navegador visível
npx playwright test --debug           # Playwright Inspector, passo a passo
npx playwright test --ui              # modo UI
npx playwright test --list            # lista os specs descobertos
```

---

## 📋 Checklist de Troubleshooting

Se o teste falhar, verificar em ordem:

1. **Backend está rodando?**
   ```bash
   docker compose -f docker/docker-compose.yml ps
   curl http://localhost:8000/ready
   ```

2. **Câmeras cadastradas?** (a API exige sessão autenticada)
   ```bash
   curl -i http://localhost:8000/api/v1/cameras/
   ```

3. **Frontend compilado?**
   ```bash
   ls backend/staticfiles/vue-spa/assets/
   ```

4. **Modal de mosaico existe no código?**
   ```bash
   grep -r "mosaicVideoRefs" frontend/src/components/
   ```

5. **Vue refs sendo criadas?**
   - Abrir DevTools no navegador (build de desenvolvimento)
   - Console → procurar logs `[SiteDetailsModal]`
   - Verificar "Keys disponíveis: [...]"

---

## 🔧 Manutenção

### Atualizar Playwright
```bash
cd frontend
npm install -D @playwright/test@latest
npx playwright install chromium
```

### Adicionar novo teste
1. E2E: criar `frontend/tests/e2e/<nome>.spec.js` (importar `authenticate` de `./fixtures/auth.js` se precisar de sessão)
2. Unitário/componente: criar `frontend/tests/unit/<nome>.spec.js` ou `frontend/tests/components/<Area>/<nome>.test.js`
3. Executar: `npm run test:unit` ou `npx playwright test tests/e2e/<nome>.spec.js`

---

## 📞 Suporte

Se os testes continuarem falhando após verificar o checklist:
1. Gerar trace: `npx playwright test --trace on`
2. Coletar logs: `docker compose -f docker/docker-compose.yml logs web > logs.txt`
3. Verificar console do navegador (DevTools)
4. Comparar com implementação funcional em [MosaicViewerView.vue](../../../frontend/src/views/video/MosaicViewerView.vue)
