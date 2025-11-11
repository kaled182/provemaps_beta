# 🗺️ ROADMAP - Próximos Passos Pós-Merge Fase 5

**Status atual:** ✅ Fase 5 completa, PR aberto aguardando merge  
**Próximo objetivo:** Reorganização Backend/Frontend/Database + Vue 3 Migration  
**Início estimado:** Imediatamente após merge do PR Fase 5  

---

## 📅 CRONOGRAMA EXECUTIVO

### 🎯 **FASE 6: Reorganização de Estrutura** (3 dias úteis)

**Branch:** `refactor/folder-structure`  
**Base:** `inicial` (após merge da Fase 5)  
**Objetivo:** Separar backend/frontend/database em pastas dedicadas  

#### **Dia 1: Preparação + Backend Migration**
- ✅ Merge PR Fase 5 → `inicial`
- ✅ Tag release `v2.0.0`
- ✅ Criar branch `refactor/folder-structure`
- ✅ Criar estrutura de diretórios (backend/, frontend/, database/)
- ✅ Mover Django apps para `backend/`
- ✅ Atualizar `settings/base.py` (BASE_DIR paths)
- ✅ Testar: `python backend/manage.py check`

**Entregas do Dia 1:**
- [ ] Estrutura de pastas criada
- [ ] Backend funcional em `backend/`
- [ ] Settings ajustados
- [ ] Testes passando (199/199)

#### **Dia 2: Frontend + Database + Docker**
- ✅ Mover `package.json`, `babel.config.js` para `frontend/`
- ✅ Consolidar static files em `frontend/static/`
- ✅ Mover `db.sqlite3`, `sql/` para `database/`
- ✅ Reescrever `dockerfile` com nova estrutura
- ✅ Atualizar `docker-compose.yml` (volumes, workdir)
- ✅ Testar build Docker: `docker-compose build`

**Entregas do Dia 2:**
- [ ] Frontend isolado em `frontend/`
- [ ] Database em `database/`
- [ ] Docker funcional
- [ ] Containers sobem corretamente

#### **Dia 3: Scripts + CI/CD + Validação Final**
- ✅ Atualizar scripts PowerShell (6 arquivos)
- ✅ Atualizar scripts Bash (4 arquivos)
- ✅ Ajustar GitHub Actions workflows
- ✅ Atualizar `.gitignore` com novos paths
- ✅ Rodar smoke tests completos
- ✅ Commit + Push + PR

**Entregas do Dia 3:**
- [ ] Todos scripts atualizados
- [ ] CI/CD funcional
- [ ] Smoke tests 100% passando
- [ ] PR criado para review

---

### 🎯 **FASE 7: Vue 3 Migration** (10-12 dias úteis)

**Branch:** `feat/vue3-frontend`  
**Base:** `inicial` (após merge da Fase 6)  
**Objetivo:** Migrar frontend de Vanilla JS para Vue 3 + Vite  

#### **Semana 1: Setup + Dashboard Migration**

**Dia 1-2: Setup Vue 3**
- ✅ Instalar Vue 3 + Vite + Pinia em `frontend/`
- ✅ Configurar `vite.config.js` para build Django-compatible
- ✅ Setup Vue Router
- ✅ Criar estrutura de componentes base

**Entregas:**
- [ ] Vue 3 instalado e funcionando
- [ ] Vite build gerando static files corretos
- [ ] Estrutura `frontend/src/` criada

**Dia 3-5: Migrar Dashboard (maps_view)**
- ✅ Converter `dashboard.js` (1,137 linhas) → componentes Vue
- ✅ Criar `DashboardMap.vue` (Google Maps)
- ✅ Criar `HostCard.vue` (cards de dispositivos)
- ✅ Criar `TrafficChart.vue` (gráficos)
- ✅ Implementar Pinia store para WebSocket
- ✅ Testar funcionalidade completa

**Entregas:**
- [ ] Dashboard funcionando em Vue 3
- [ ] WebSocket integrado
- [ ] Gráficos funcionais
- [ ] UI responsiva mantida

#### **Semana 2: Route Builder + Setup App**

**Dia 6-9: Migrar Route Builder (routes_builder)**
- ✅ Converter `fiber_route_builder.js` (1,039 linhas) → Vue
- ✅ Criar `MapEditor.vue` (Google Maps + editing)
- ✅ Criar `PointsList.vue` (lista de pontos)
- ✅ Criar `CableForm.vue` (formulário de cabos)
- ✅ Implementar Pinia store para state management
- ✅ Migrar módulos ES6 para composables Vue

**Entregas:**
- [ ] Route Builder funcionando em Vue 3
- [ ] Edição de rotas funcional
- [ ] Drag & drop mantido
- [ ] Context menu funcionando

**Dia 10: Migrar Setup App (setup_app)**
- ✅ Converter `form_first_time_setup.js` → Vue
- ✅ Criar componentes de formulário
- ✅ Testar fluxo de first-time setup

**Entregas:**
- [ ] Setup App em Vue 3
- [ ] Forms funcionais
- [ ] Validação mantida

#### **Semana 2 (fim): API Backend + Integration**

**Dia 11-12: Django REST API + Final Integration**
- ✅ Criar endpoints DRF para todas APIs
- ✅ Serializers para todos models
- ✅ Configurar CORS se necessário
- ✅ Integrar Vue Router com Django URLs
- ✅ Testes end-to-end
- ✅ Performance optimization (lazy loading)

**Entregas:**
- [ ] APIs REST completas
- [ ] Frontend 100% em Vue 3
- [ ] Build otimizado (code splitting)
- [ ] Performance >= versão anterior

---

## 📊 ESTRUTURA FINAL ESPERADA

```
provemaps_beta/
├── backend/                     # 🆕 Django backend
│   ├── manage.py
│   ├── core/                    # Django core app
│   ├── inventory/               # Inventory app
│   ├── monitoring/              # Monitoring app
│   ├── maps_view/              # Maps view app (apenas API)
│   │   ├── api/                # 🆕 DRF endpoints
│   │   │   ├── views.py
│   │   │   └── serializers.py
│   │   ├── models.py
│   │   └── services.py
│   ├── routes_builder/         # Route builder app (apenas API)
│   ├── setup_app/              # Setup app
│   ├── gpon/                   # GPON app
│   ├── dwdm/                   # DWDM app
│   ├── integrations/           # Integrations
│   ├── settings/               # Django settings
│   ├── templates/              # Django templates (minimal)
│   │   └── spa.html           # 🆕 SPA shell
│   ├── tests/                  # Backend tests
│   ├── requirements.txt
│   └── pytest.ini
│
├── frontend/                    # 🆕 Vue 3 frontend
│   ├── src/
│   │   ├── components/         # 🆕 Vue components
│   │   │   ├── Dashboard/
│   │   │   │   ├── DashboardMap.vue
│   │   │   │   ├── HostCard.vue
│   │   │   │   ├── HostTable.vue
│   │   │   │   └── TrafficChart.vue
│   │   │   ├── RouteBuilder/
│   │   │   │   ├── MapEditor.vue
│   │   │   │   ├── PointsList.vue
│   │   │   │   ├── CableForm.vue
│   │   │   │   └── ContextMenu.vue
│   │   │   ├── Setup/
│   │   │   │   └── FirstTimeSetup.vue
│   │   │   └── Common/
│   │   │       ├── NavBar.vue
│   │   │       ├── Sidebar.vue
│   │   │       └── LoadingSpinner.vue
│   │   ├── views/              # 🆕 Vue views/pages
│   │   │   ├── DashboardView.vue
│   │   │   ├── RouteBuilderView.vue
│   │   │   ├── SetupView.vue
│   │   │   └── LoginView.vue
│   │   ├── stores/             # 🆕 Pinia stores
│   │   │   ├── dashboard.js
│   │   │   ├── routes.js
│   │   │   ├── auth.js
│   │   │   └── setup.js
│   │   ├── composables/        # 🆕 Vue composables
│   │   │   ├── useWebSocket.js
│   │   │   ├── useGoogleMaps.js
│   │   │   └── useApi.js
│   │   ├── router/             # 🆕 Vue Router
│   │   │   └── index.js
│   │   ├── assets/             # 🆕 Assets (CSS, images)
│   │   │   ├── css/
│   │   │   └── images/
│   │   ├── utils/              # 🆕 Utilities
│   │   │   └── api.js
│   │   └── main.js             # 🆕 Vue entry point
│   ├── public/                 # 🆕 Public assets
│   ├── dist/                   # 🆕 Build output → Django static
│   ├── package.json            # 🆕 Frontend deps
│   ├── vite.config.js          # 🆕 Vite config
│   ├── index.html              # 🆕 Dev entry point
│   └── .eslintrc.js            # 🆕 ESLint config
│
├── database/                    # 🆕 Database files
│   ├── db.sqlite3
│   ├── test_db.sqlite3
│   └── sql/                    # SQL scripts
│       └── ...
│
├── docker/                      # 🆕 Docker files (opcional)
│   ├── dockerfile
│   ├── docker-compose.yml
│   ├── docker-compose.test.yml
│   └── docker-entrypoint.sh
│
├── scripts/                     # Scripts (já existe)
│   ├── smoke_phase5.ps1
│   ├── deploy_initial_v2.ps1
│   └── ...
│
├── doc/                         # Documentação (já existe)
│   └── ...
│
└── [root config files]
    ├── .env
    ├── .env.example
    ├── .gitignore
    ├── README.md
    └── makefile
```

---

## 🎯 MÉTRICAS DE SUCESSO

### **Fase 6 (Reorganização):**
- ✅ 199/199 testes passando
- ✅ Docker build sem erros
- ✅ Smoke tests 100% passando
- ✅ CI/CD verde
- ✅ Zero warnings de deprecação

### **Fase 7 (Vue 3):**
- ✅ Lighthouse Performance >= 90
- ✅ Bundle size < 500KB (gzipped)
- ✅ First Contentful Paint < 1.5s
- ✅ Time to Interactive < 3s
- ✅ 100% feature parity com versão Vanilla JS
- ✅ Testes E2E passando (Playwright/Cypress)

---

## 🔧 TECNOLOGIAS A SEREM ADICIONADAS

### **Fase 6 (Reorganização):**
- Nenhuma tecnologia nova (apenas reorganização)

### **Fase 7 (Vue 3):**

#### **Core:**
- ✅ **Vue 3** (v3.4+) - Framework frontend
- ✅ **Vite** (v5+) - Build tool moderno
- ✅ **Pinia** (v2+) - State management
- ✅ **Vue Router** (v4+) - Routing

#### **UI/UX:**
- ✅ **Tailwind CSS** (v3+) - Utility-first CSS
- ✅ **Headless UI** - Componentes acessíveis
- ✅ **VueUse** - Composables utilitários

#### **Maps & Charts:**
- ✅ **@googlemaps/js-api-loader** - Google Maps para Vue
- ✅ **Chart.js** + **vue-chartjs** - Gráficos
- ✅ **@vueuse/motion** - Animações

#### **Dev Tools:**
- ✅ **Vitest** - Testing framework
- ✅ **Playwright** - E2E testing
- ✅ **ESLint** + **Prettier** - Linting
- ✅ **TypeScript** (opcional) - Type safety

#### **Build & Deploy:**
- ✅ **Vite PWA Plugin** - Progressive Web App
- ✅ **Vite Compression Plugin** - Gzip/Brotli
- ✅ **Rollup Visualizer** - Bundle analysis

---

## ⚠️ RISCOS E MITIGAÇÕES

### **Fase 6 (Reorganização):**

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| Quebra de imports Python | 🔴 Alto | 🟡 Média | Testar `python -c "import core"` a cada fase |
| Docker build falha | 🔴 Alto | 🟡 Média | Build local antes de commit |
| CI/CD pipeline quebra | 🟡 Médio | 🟡 Média | PR draft, testar workflows |
| Scripts de deploy falham | 🟡 Médio | 🟢 Baixa | Testar cada script individualmente |
| Rollback necessário | 🔴 Alto | 🟢 Baixa | **Branch separada** permite rollback fácil |

### **Fase 7 (Vue 3):**

| Risco | Impacto | Probabilidade | Mitigação |
|-------|---------|---------------|-----------|
| Performance degradation | 🔴 Alto | 🟡 Média | Lighthouse CI, bundle size limits |
| Google Maps integration issues | 🟡 Médio | 🟡 Média | Usar biblioteca oficial @googlemaps |
| WebSocket reconnection bugs | 🟡 Médio | 🟡 Média | Replicar lógica existente, testes extensivos |
| State management complexity | 🟡 Médio | 🟢 Baixa | Pinia é simples, documentação boa |
| SEO regression | 🟢 Baixo | 🟢 Baixa | Django serve página inicial, Vue apenas enhance |

---

## 📚 RECURSOS E REFERÊNCIAS

### **Fase 6:**
- ✅ `ANALYSIS_FOLDER_RESTRUCTURE.md` - Análise de impacto completa
- ✅ Django Best Practices - Two Scoops of Django
- ✅ 12-Factor App - Configuração de ambiente

### **Fase 7:**
- ✅ [Vue 3 Official Docs](https://vuejs.org/)
- ✅ [Vite Guide](https://vitejs.dev/guide/)
- ✅ [Pinia Documentation](https://pinia.vuejs.org/)
- ✅ [Google Maps Vue Component](https://github.com/xkjyeah/vue-google-maps)
- ✅ [Vue Router Guide](https://router.vuejs.org/)
- ✅ [VueUse](https://vueuse.org/) - Collection of Vue Composition Utilities

---

## 🚀 COMANDO DE INÍCIO

### **Após merge do PR Fase 5:**

```powershell
# 1. Atualizar branch inicial
git checkout inicial
git pull origin inicial

# 2. Verificar que merge foi feito
git log --oneline -3

# 3. Criar tag v2.0.0
git tag -a v2.0.0 -m "Release v2.0.0 - Phase 5 Complete: Django Modularization"
git push origin v2.0.0

# 4. Criar branch para reorganização
git checkout -b refactor/folder-structure

# 5. INICIAR FASE 6 - Reorganização
# (seguir script automatizado que será criado)
```

---

## ✅ CHECKLIST PRÉ-INÍCIO

Antes de iniciar Fase 6, confirmar:

- [ ] PR Fase 5 foi merged em `inicial`
- [ ] Tag `v2.0.0` foi criada e pushed
- [ ] Branch `refactor/modularization` foi deletada (opcional)
- [ ] Working directory está limpo (`git status`)
- [ ] Todos testes estão passando em `inicial`
- [ ] Backup do projeto foi feito (opcional)
- [ ] Time está alinhado (se houver equipe)

---

## 📞 PONTOS DE DECISÃO

Durante a execução, haverá pontos de decisão:

### **Fase 6:**
1. **Docker files:** Manter na raiz ou mover para `docker/`?
   - Recomendação: Mover para `docker/` (mais limpo)

2. **Static files de apps:** Consolidar ou manter nos apps?
   - Recomendação: Manter nos apps (Django namespacing funciona)

### **Fase 7:**
1. **SPA Full ou Híbrido?**
   - SPA Full: Vue Router cuida de tudo, Django só API
   - Híbrido: Django templates + Vue em partes específicas
   - Recomendação: **SPA Full** (mais moderno, melhor UX)

2. **TypeScript ou JavaScript?**
   - TypeScript: Type safety, melhor DX
   - JavaScript: Mais rápido inicialmente
   - Recomendação: **JavaScript primeiro**, migrar para TS depois

3. **Tailwind CSS ou manter CSS atual?**
   - Tailwind: Utility-first, rápido desenvolvimento
   - CSS atual: Manter estilos existentes
   - Recomendação: **Tailwind CSS** (já que vai refatorar tudo)

---

## 🎉 RESULTADO ESPERADO

### **Após Fase 6:**
- ✅ Projeto organizado profissionalmente
- ✅ Backend/Frontend/Database separados
- ✅ Fácil onboarding de novos desenvolvedores
- ✅ Escalável para crescimento futuro

### **Após Fase 7:**
- ✅ Frontend moderno em Vue 3
- ✅ Performance otimizada
- ✅ Developer Experience melhorada
- ✅ Manutenibilidade superior
- ✅ Pronto para features complexas (Fase 8+)

---

**Última atualização:** 08/11/2025  
**Versão:** 1.0  
**Autor:** GitHub Copilot + Equipe MapsProveFiber
