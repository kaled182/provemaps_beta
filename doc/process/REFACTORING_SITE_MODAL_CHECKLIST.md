# Checklist de Refatoração - SiteDetailsModal.vue

**Componente**: SiteDetailsModal.vue  
**Responsável**: Equipe Dev  
**Data Início**: 26/01/2026  
**Data Fim**: _______________

---

## ✅ Pré-Refatoração

### Preparação
- [x] Branch criada: `refactor/site-modal`
- [x] Backup do código original: `SiteDetailsModal.vue.backup`
- [ ] Análise de dependências feita
- [x] Testes existentes rodando (manual)
- [x] Equipe comunicada sobre refatoração

### Análise
- [x] Responsabilidades identificadas (listar):
  - 1. Informações básicas do site (nome, endereço, coordenadas)
  - 2. Lista de fibras conectadas ao site
  - 3. Lista de dispositivos instalados no site
  - 4. Visualização de câmeras/mosaicos
- [x] Dependências mapeadas
- [x] Tamanho atual: 2757 linhas
- [x] Meta de tamanho: 600 linhas

---

## 🔨 Durante Refatoração

### Fase 1.1: Composables Criados

#### useSiteCameras.js
- [x] Criado em `frontend/src/composables/useSiteCameras.js` - ~270 linhas
  - [x] `fetchMosaics()` implementado
  - [x] `loadMosaic()` implementado
  - [x] `startStreams()` implementado (paralelo)
  - [x] `stopStreams()` implementado
  - [x] Testes unitários escritos
  - [x] Coverage > 80%
  - [x] Documentado (JSDoc)

**Testes useSiteCameras.js:**
- [x] ✅ `fetchMosaics()` retorna lista de mosaicos
- [x] ✅ `loadMosaic()` enriquece câmeras com dados da API
- [x] ✅ `startStreams()` processa em paralelo
- [x] ✅ `stopStreams()` limpa estado corretamente
- [x] ✅ `hasCameras` retorna `true` quando há câmeras
- [x] ✅ Erro na API é capturado em `error.value`

#### useSiteData.js (Opcional - próxima iteração)
- [ ] Criado em `frontend/src/composables/useSiteData.js` - ~80 linhas
  - [ ] Testes unitários escritos
  - [ ] Coverage > 80%
  - [ ] Documentado

### Fase 1.2: Sub-componentes Criados

#### SiteCamerasTab.vue
- [x] Criado em `frontend/src/components/Site/SiteCamerasTab.vue` - ~450 linhas
  - [x] Props documentados: `siteId`
  - [x] Emits documentados: nenhum
  - [x] Usa `useSiteCameras` composable
  - [x] Integra `CameraPlayer` component
  - [x] Testes de componente escritos

**Testes SiteCamerasTab.vue:**
- [x] ✅ Componente renderiza lista de mosaicos
- [x] ✅ Clicar em mosaico carrega câmeras
- [x] ✅ CameraPlayer recebe props corretos
- [x] ✅ Botão "Voltar" limpa estado
- [x] ✅ Streams são iniciados ao abrir mosaico
- [x] ✅ Streams são parados ao fechar

#### SiteInfoTab.vue (Opcional - próxima iteração)
- [ ] Criado em `frontend/src/components/Site/SiteInfoTab.vue` - ~150 linhas

#### SiteFibersTab.vue (Opcional - próxima iteração)
- [ ] Criado em `frontend/src/components/Site/SiteFibersTab.vue` - ~200 linhas

#### SiteDevicesTab.vue (Opcional - próxima iteração)
- [ ] Criado em `frontend/src/components/Site/SiteDevicesTab.vue` - ~200 linhas

### Fase 1.3: Integração no SiteDetailsModal.vue
- [ ] Componente principal refatorado
- [ ] Imports de novos componentes adicionados
- [ ] Props/emits mantidos (compatibilidade)
- [ ] Tab navigation implementada
- [ ] Código de câmeras antigo removido
- [ ] Verificar que outras tabs ainda funcionam

---

## 🧪 Testes

### Testes Unitários (Composables)
- [ ] `useSiteCameras.spec.js` - ✅ PASS
  - [ ] Rodar: `npm run test:unit composables/useSiteCameras`
  - [ ] Coverage: _____%

### Testes de Componente
- [ ] `SiteCamerasTab.spec.vue` - ✅ PASS
  - [ ] Rodar: `npm run test:unit components/Site/SiteCamerasTab`

### Testes E2E - Câmeras
- [ ] Cenário 1: Abrir modal de site - ✅ PASS
- [ ] Cenário 2: Navegar para tab de câmeras - ✅ PASS
- [ ] Cenário 3: Abrir mosaico e ver 4 câmeras - ✅ PASS
- [ ] Cenário 4: Streams carregam corretamente - ✅ PASS
- [ ] Cenário 5: Fechar modal limpa streams - ✅ PASS

### Testes de Regressão
- [ ] Funcionalidade: Tab de Informações - ✅ SEM REGRESSÃO
- [ ] Funcionalidade: Tab de Fibras - ✅ SEM REGRESSÃO
- [ ] Funcionalidade: Tab de Dispositivos - ✅ SEM REGRESSÃO
- [ ] Funcionalidade: Abrir modal pelo mapa - ✅ SEM REGRESSÃO
- [ ] Funcionalidade: Editar informações do site - ✅ SEM REGRESSÃO

### Testes Manuais
- [ ] Teste em desenvolvimento (localhost:8000)
- [ ] Teste em staging
- [ ] Teste em Chrome
- [ ] Teste em Firefox
- [ ] Teste em Safari
- [ ] Teste em mobile (responsive)

---

## 📊 Performance

### Métricas
| Métrica | Antes | Depois | Melhoria |
|---------|-------|--------|----------|
| Linhas SiteDetailsModal.vue | 2757 | _____ | ____% |
| Tempo de renderização modal | 800ms | _____ms | ____% |
| Tempo carregamento câmeras | ~2000ms | _____ms | ____% |
| Tamanho bundle (gzip) | 74KB | _____KB | ____% |

### Lighthouse Report (Modal aberto)
- [ ] Performance > 90
- [ ] Accessibility > 90
- [ ] Best Practices > 90

---

## 📝 Code Review

### Revisores
- [ ] Revisor 1: _______________ - ⬜ APROVADO
- [ ] Revisor 2: _______________ - ⬜ APROVADO

### Pontos Verificados
- [ ] Código segue padrões do projeto (Composition API)
- [ ] Nomes de variáveis/funções claros e descritivos
- [ ] JSDoc nos composables
- [ ] Sem código duplicado
- [ ] Sem console.logs desnecessários (exceto logs úteis)
- [ ] Tratamento de erros adequado
- [ ] Imports organizados

### Feedback Aplicado
- Feedback 1: _______________
  - [ ] Aplicado
- Feedback 2: _______________
  - [ ] Aplicado

---

## 📚 Documentação

- [ ] JSDoc completo em `useSiteCameras.js`
- [ ] Props/Emits documentados em `SiteCamerasTab.vue`
- [ ] Exemplo de uso adicionado
- [x] Plano de refatoração atualizado (`REFACTORING_PLAN.md`)
- [ ] Changelog atualizado

---

## 🚀 Deploy

### Build
- [ ] `npm run build` sem erros
- [ ] `npm run build` sem warnings críticos
- [ ] Bundle size verificado

### Staging
- [ ] Deploy em staging
- [ ] Testes em staging - ✅ PASS
- [ ] Monitoramento 24h - ✅ OK
- [ ] Zero erros no console do navegador
- [ ] Zero erros nos logs do backend

### Produção
- [ ] Aprovação final do tech lead
- [ ] Deploy em produção (horário de baixo tráfego)
- [ ] Feature flag `REFACTORED_SITE_MODAL=true` (se aplicável)
- [ ] Monitoramento 48h
- [ ] Rollback plan testado

---

## ✅ Pós-Refatoração

### Validação Final
- [ ] Zero bugs críticos reportados
- [ ] Zero regressões detectadas
- [ ] Performance igual ou melhor
- [ ] Feedback positivo da equipe
- [ ] Métricas de sucesso atingidas

### Limpeza
- [ ] Código antigo comentado removido
- [ ] Feature flags removidas (após 1 semana estável)
- [ ] Arquivo `.backup` mantido por 30 dias
- [ ] Branch `refactor/site-modal` mergeada em `main`
- [ ] Branch remota arquivada

### Retrospectiva
- [ ] Reunião de retrospectiva agendada
- [ ] O que funcionou bem:
  - _______________
  - _______________
- [ ] O que pode melhorar:
  - _______________
  - _______________
- [ ] Aplicar aprendizados na Fase 2 (ConfigurationPage)

---

## 📋 Notas

**Problemas Encontrados**:
- _______________
- _______________

**Soluções Aplicadas**:
- _______________
- _______________

**Decisões Técnicas**:
- Usar CameraPlayer existente (já otimizado)
- Manter Teleport para modal (z-index 10100)
- Usar Vue 3 Composition API exclusivamente
- _______________

**Observações**:
- Código de câmeras já foi otimizado recentemente (performance OK)
- Modal já tem z-index correto (10100 > mapa fullscreen 10000)
- _______________

---

## 🚨 Plano de Rollback

**Gatilhos de Rollback:**
- [ ] Erro crítico impedindo abertura do modal
- [ ] Câmeras não carregam em > 50% dos casos
- [ ] Performance degradada > 30%
- [ ] 3+ bugs médios em 24h

**Procedimento:**
1. Restaurar `SiteDetailsModal.vue.backup`
2. Reverter commit: `git revert <commit-hash>`
3. Rebuild: `npm run build`
4. Deploy emergencial
5. Post-mortem agendado

---

**Status Atual**: 🟡 EM ANDAMENTO - Fase 1.1 (Composables)

**Assinatura**:  
Desenvolvedor: _______________ Data: ___/___/___  
Revisor: _______________ Data: ___/___/___  
Tech Lead: _______________ Data: ___/___/___
