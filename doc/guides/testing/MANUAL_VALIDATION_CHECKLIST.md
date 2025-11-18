# ✅ Checklist de Validação Manual - Dashboard Vue SPA

**Data**: 18 de Novembro de 2025  
**Testador**: AI Agent  
**Ambiente**: Docker Compose (localhost:8000)  
**Configuração**: `USE_VUE_DASHBOARD=True`, `VUE_DASHBOARD_ROLLOUT_PERCENTAGE=100`

---

## 🎯 Objetivo
Validar que Vue SPA está funcionando 100% antes de iniciar rollout gradual em produção.

---

## ✅ Checklist de Testes Manuais

### Pré-requisitos
- [x] ✅ Docker running: `docker-web-1` (Up 2 hours - healthy)
- [x] ✅ Django em `localhost:8000` acessível
- [x] ✅ Feature flag: `USE_VUE_DASHBOARD=True` (dev.py linha 128)
- [x] ✅ Rollout: `VUE_DASHBOARD_ROLLOUT_PERCENTAGE=100` (dev.py linha 129)
- [x] ✅ Testes E2E: 29/30 passing (96.7%)
- [x] ✅ Browser aberto: http://localhost:8000/monitoring/backbone/

### Testes Funcionais

#### 1. Carregamento Inicial
- [ ] **SPA carrega** - Ver `<div id="app">` renderizado (não vazio)
- [ ] **Vue detectado** - Abrir DevTools → Vue tab visível (se extensão instalada)
- [ ] **Sem erros** - Console sem mensagens de erro vermelhas
- [ ] **API chamada** - Network tab mostra `GET /maps_view/api/dashboard/data/` (200 OK)
- [ ] **Tempo de load** - Dashboard visível em < 1 segundo

**Critério de sucesso**: ✅ Todos os 5 itens passam

---

#### 2. Hosts Display
- [ ] **11 host cards** - Sidebar mostra 11 cards (backend tem 11 hosts)
- [ ] **Status colors** - Cards com cores corretas (verde/vermelho/cinza)
- [ ] **Host info** - Cada card mostra: hostname, IP, status
- [ ] **Resumo** - Header mostra: Total, Available, Unavailable, Unknown
- [ ] **data-testid** - Inspecionar elemento → `<article data-testid="host-card">`

**Critério de sucesso**: ✅ Todos os 5 itens passam

---

#### 3. Google Maps
- [ ] **Mapa carrega** - Ver tiles do Google Maps renderizados
- [ ] **Rotas de fibra** - Linhas coloridas visíveis no mapa
- [ ] **Zoom/Pan funciona** - Arrastar mapa + scroll para zoom
- [ ] **Sem "For development purposes only"** - Watermark não aparece (API key válida)
- [ ] **Marcadores** - Pins ou markers de sites visíveis

**Critério de sucesso**: ✅ Todos os 5 itens passam

---

#### 4. Controles de Mapa
- [ ] **Fit Bounds** - Botão "Fit Bounds" visível e clicável
  - [ ] Clicar → Mapa ajusta zoom para mostrar todas as rotas
- [ ] **Toggle Legend** - Botão "Toggle Legend" visível e clicável
  - [ ] Clicar → Legenda aparece/desaparece
  - [ ] Legenda mostra: Available (verde), Unavailable (vermelho), Unknown (cinza)

**Critério de sucesso**: ✅ Ambos controles funcionam perfeitamente

---

#### 5. Interação com Segmentos
- [ ] **Clicar em segmento** - Clicar numa linha de rota colorida
- [ ] **InfoWindow aparece** - Popup com informações do segmento
- [ ] **InfoWindow tem dados** - Mostra: Nome da rota, Status, Comprimento, etc.
- [ ] **Fechar InfoWindow** - Clicar fora ou no X → InfoWindow desaparece

**Critério de sucesso**: ✅ Interação completa funciona

---

#### 6. Responsive Design
- [ ] **Desktop** - Layout com sidebar + mapa lado a lado
- [ ] **Mobile** - Redimensionar janela para 375px largura
  - [ ] Sidebar empilha sobre o mapa (vertical)
  - [ ] Touch gestures funcionam (se mobile real)
- [ ] **Tablet** - Redimensionar para 768px
  - [ ] Layout adaptado (sidebar menor ou collapsed)

**Critério de sucesso**: ✅ Layout responsivo em 3+ breakpoints

---

#### 7. Loading States
- [ ] **Inicial** - Ao carregar página, ver spinner/skeleton
  - [ ] `[data-testid="loading-state"]` visível brevemente
- [ ] **Refetch** - Force refresh (Ctrl+Shift+R) → Loading state aparece novamente
- [ ] **Graceful** - Não mostra conteúdo parcial (skeleton completo)

**Critério de sucesso**: ✅ Loading UX é smooth

---

#### 8. Error Handling
- [ ] **Offline** - Desconectar internet → Ver mensagem de erro amigável
  - [ ] Não quebra página (no crash)
  - [ ] Mensagem: "Erro ao carregar dados" ou similar
- [ ] **API fail** - Simular erro 500 (parar Docker) → Error state
  - [ ] `[data-testid="error-state"]` visível

**Critério de sucesso**: ✅ Errors são tratados gracefully

---

#### 9. Performance
- [ ] **Load time** - Abrir DevTools → Network tab → Recarregar
  - [ ] Finish time < 2 segundos (target: < 1s)
  - [ ] DOMContentLoaded < 500ms
- [ ] **Render time** - Hosts aparecem rapidamente (< 100ms após API response)
- [ ] **Sem lag** - Scroll smooth, sem frame drops
- [ ] **Memory** - DevTools → Performance → Heap não cresce infinitamente

**Critério de sucesso**: ✅ Performance excelente (métricas abaixo dos targets)

---

#### 10. Console Errors
- [ ] **Zero erros** - Console do browser sem mensagens vermelhas
- [ ] **Zero warnings críticos** - Apenas warnings informativos (opcional)
- [ ] **Vue DevTools** - Sem warnings do Vue (props, emits, etc.)
- [ ] **Network** - Todas requests retornam 200/304 (sem 404/500)

**Critério de sucesso**: ✅ Console limpo (0 erros)

---

## 📊 Resultado Final

### Scorecard
```
Total de testes: 10 seções × ~5 checks = ~50 verificações
Passaram: ___/50
Falharam: ___/50
Pass rate: ___%
```

### Critério de Aprovação
- ✅ **95%+ pass rate** (mínimo 48/50 passing)
- ✅ **0 erros críticos** (crashes, API failures)
- ✅ **Performance < 1s** load time

### Decisão
- [ ] ✅ **APROVADO** - Iniciar rollout gradual 10% → 100%
- [ ] ⚠️ **APROVADO COM RESSALVAS** - Corrigir warnings não-críticos durante rollout
- [ ] ❌ **REPROVADO** - Corrigir erros antes de rollout

---

## 🐛 Bugs Encontrados

### Bug #1
**Descrição**: _Descrever bug aqui_  
**Severidade**: 🔴 Crítico / 🟡 Médio / 🟢 Baixo  
**Reprodução**: _Passos para reproduzir_  
**Status**: ⏳ Pendente / 🔧 Em correção / ✅ Corrigido  

### Bug #2
_Adicionar mais conforme necessário_

---

## 📝 Notas do Teste

### Funcionalidades Removidas (Confirmadas)
- ❌ **Ping/Telnet CMD Modal** - Decisão: Remover (Windows-only, uso limitado)
  - Alternativa: Usuários usam Windows Terminal/PuTTY diretamente
  - Impacto: Baixo (< 1% dos usuários)

### Funcionalidades Adicionadas (Bônus)
- ✅ **Acessibilidade** - Keyboard navigation (Tab, Enter, Esc)
- ✅ **Dark mode** - Tema escuro (localStorage: `ui.theme`)
- ✅ **Performance metrics** - Real User Monitoring (RUM)

---

## 🚀 Próxima Ação

**Após aprovação manual**:
1. ✅ Documentar resultado neste checklist
2. ✅ Commit: "test: Manual validation of Vue SPA - 100% passing"
3. ✅ Iniciar rollout gradual (criar PR para produção)
4. ✅ Configurar monitoramento (logs + métricas)

---

**Última atualização**: 18 de Novembro de 2025  
**Status**: ⏳ AGUARDANDO TESTE MANUAL
