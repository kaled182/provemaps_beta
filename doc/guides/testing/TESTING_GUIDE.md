# 🧪 Guia de Testes - Sistema Unificado de Mapas

## 📋 Status da Build

✅ **Docker atualizado** - Containers reconstruídos com novo código  
✅ **Frontend compilado** - Sistema unificado de mapas incluído  
✅ **Serviços rodando** - http://localhost:8000

---

## 🎯 Páginas para Testar

### 1️⃣ Dashboard/Monitoring (PRIORIDADE ALTA)

**URL:** http://localhost:8000/monitoring/backbone/

**O que testar:**
- [ ] ✅ Mapa carrega corretamente
- [ ] ✅ Menu lateral está visível e funcional
- [ ] ✅ Segmentos de fibra aparecem no mapa (polylines coloridas)
- [ ] ✅ Markers de devices/sites são exibidos
- [ ] ✅ Clicar em segmento mostra informações
- [ ] ✅ Clicar em device mostra InfoWindow
- [ ] ✅ Pressionar F5 não quebra o menu
- [ ] ✅ Navegação entre páginas mantém menu

**Como testar:**
```bash
# Abrir no navegador
http://localhost:8000/monitoring/backbone/

# Verificar console (F12)
# Deve ver:
[MapService] Map initialized in monitoring mode
[MapService] Loading plugin: segments
[MapService] Plugin "segments" loaded successfully
[MapService] Loading plugin: devices
[MapService] Plugin "devices" loaded successfully
[SegmentsPlugin] Drew X segments
[DevicesPlugin] Drew Y device markers
```

**Cenários de teste:**
1. **Carregamento inicial:**
   - Abrir página
   - Aguardar mapa carregar (tiles do Google Maps)
   - Verificar se segmentos aparecem coloridos
   - Verificar se markers de devices aparecem

2. **Interatividade:**
   - Clicar em um segmento de fibra
   - Verificar se InfoWindow abre com detalhes
   - Clicar em um marker de device
   - Verificar se InfoWindow mostra dados do device

3. **Navegação:**
   - Pressionar F5
   - Verificar se menu lateral continua visível
   - Navegar para outra página
   - Voltar para /monitoring/backbone/
   - Verificar se tudo continua funcionando

---

### 2️⃣ Network Design (PRIORIDADE ALTA)

**URL:** http://localhost:8000/NetworkDesign/

**O que testar:**
- [ ] ✅ Mapa carrega em modo terrain
- [ ] ✅ Menu lateral está visível
- [ ] ✅ Botões de toolbar aparecem (Route points, Help tips)
- [ ] ✅ Clicar no mapa adiciona pontos
- [ ] ✅ Markers são arrastáveis
- [ ] ✅ Polyline é desenhada conectando pontos
- [ ] ✅ Distância é calculada em tempo real
- [ ] ✅ Right-click abre menu de contexto
- [ ] ✅ Pressionar F5 não quebra funcionalidade

**Como testar:**
```bash
# Abrir no navegador
http://localhost:8000/NetworkDesign/

# Verificar console (F12)
# Deve ver:
[MapService] Map initialized in design mode
[MapService] Loading plugin: drawing
[MapService] Plugin "drawing" loaded successfully
[MapService] Loading plugin: contextMenu
[MapService] Plugin "contextMenu" loaded successfully
[DrawingPlugin] Initialized
```

**Cenários de teste:**
1. **Desenho de rota:**
   - Clicar no mapa para adicionar pontos (mínimo 3)
   - Verificar se markers numerados aparecem (1, 2, 3...)
   - Verificar se polyline azul conecta os pontos
   - Verificar se distância é exibida

2. **Edição de rota:**
   - Arrastar um marker para nova posição
   - Verificar se polyline é atualizada
   - Verificar se distância é recalculada
   - Right-click em um ponto para remover

3. **Menu de contexto:**
   - Right-click em qualquer lugar do mapa
   - Verificar se menu aparece
   - Testar opções do menu (salvar, carregar, importar KML, etc.)

4. **Painel de pontos:**
   - Clicar em "Route points" para abrir painel
   - Verificar lista de pontos com coordenadas
   - Verificar distância total

---

### 3️⃣ Monitoring Overview (MÉDIA PRIORIDADE)

**URL:** http://localhost:8000/monitoring/monitoring-all/

**O que testar:**
- [ ] ✅ Página carrega sem erros
- [ ] ✅ Menu lateral funciona
- [ ] ✅ Cards de hosts aparecem
- [ ] ✅ Filtros funcionam

---

### 4️⃣ GPON Monitoring (BAIXA PRIORIDADE)

**URL:** http://localhost:8000/monitoring/gpon/

**O que testar:**
- [ ] ✅ Página carrega
- [ ] ✅ Menu lateral visível

---

### 5️⃣ DWDM Monitoring (BAIXA PRIORIDADE)

**URL:** http://localhost:8000/monitoring/dwdm/

**O que testar:**
- [ ] ✅ Página carrega
- [ ] ✅ Menu lateral visível

---

## 🔍 Testes Automáticos

### Executar Testes E2E

```bash
# Terminal 1: Garantir que servidor está rodando
cd D:\provemaps_beta\docker
docker compose up

# Terminal 2: Executar testes Playwright
cd D:\provemaps_beta\frontend
npm run test:e2e -- tests/e2e/map-loading.spec.js
```

**Resultado esperado:**
```
✅ 16 passed
⏭️ 1 skipped
```

### Executar Testes Unitários

```bash
cd D:\provemaps_beta\frontend
npm run test:unit -- useMapService.spec.js
```

**Resultado esperado:**
```
✅ All tests passed
```

---

## 📊 Checklist Completo de Testes

### ✅ Funcionalidade do Mapa

#### Carregamento
- [ ] Google Maps API carrega sem erros
- [ ] Tiles do mapa são exibidas
- [ ] Controles de zoom aparecem
- [ ] Mapa é interativo (arrastar, zoom)

#### Plugins - Monitoring
- [ ] Segmentos de fibra desenhados (polylines)
- [ ] Cores corretas baseadas em status (verde, amarelo, vermelho)
- [ ] Markers de devices com ícones adequados
- [ ] InfoWindows abrem ao clicar
- [ ] Dados corretos nas InfoWindows

#### Plugins - Network Design
- [ ] Click adiciona pontos ao mapa
- [ ] Markers são arrastáveis
- [ ] Polyline conecta pontos
- [ ] Distância calculada corretamente
- [ ] Menu de contexto (right-click) funciona
- [ ] Ações do menu funcionam (salvar, limpar, etc.)

### ✅ UI/UX

#### Menu Lateral
- [ ] Menu aparece corretamente
- [ ] Items do menu são clicáveis
- [ ] Navegação funciona
- [ ] Menu persiste após F5
- [ ] Menu não sobrepõe o mapa

#### Layout
- [ ] Mapa ocupa espaço correto
- [ ] Sidebar não empurra mapa para fora
- [ ] Responsivo (testar redimensionar janela)
- [ ] Sem scrollbars indesejadas

#### Performance
- [ ] Carregamento rápido (<3s)
- [ ] Sem lag ao interagir
- [ ] Smooth ao arrastar mapa
- [ ] Sem memory leaks (testar F5 múltiplas vezes)

### ✅ Compatibilidade

#### Navegadores
- [ ] Chrome/Edge (principal)
- [ ] Firefox
- [ ] Safari (se disponível)

#### Resoluções
- [ ] 1920x1080 (Full HD)
- [ ] 1366x768 (comum em laptops)
- [ ] 2560x1440 (2K)

---

## 🐛 Como Reportar Bugs

Se encontrar problemas, anotar:

1. **URL da página:** 
2. **Navegador e versão:**
3. **Passos para reproduzir:**
   - Passo 1:
   - Passo 2:
   - Passo 3:
4. **Resultado esperado:**
5. **Resultado obtido:**
6. **Erros no console (F12):**
7. **Screenshot (se aplicável):**

---

## 🔧 Troubleshooting

### Problema: Mapa não carrega

**Sintomas:**
- Tela branca ou cinza
- Erro "Failed to load Google Maps API"

**Soluções:**
1. Verificar API key no console
2. Verificar conexão com internet
3. Limpar cache do navegador (Ctrl+Shift+Del)
4. Recarregar página (F5)

### Problema: Menu lateral sumiu

**Sintomas:**
- Apenas mapa visível, sem menu

**Soluções:**
1. Verificar console para erros
2. Pressionar F5 para recarregar
3. Verificar se rota está correta

### Problema: Plugins não carregam

**Sintomas:**
- Console mostra "Plugin X not found"
- Segmentos ou markers não aparecem

**Soluções:**
1. Verificar console para erros de importação
2. Verificar se build do frontend foi executado
3. Limpar cache e recarregar

### Problema: Erro HTTP 401

**Sintomas:**
- Console mostra "HTTP 401" em APIs de fibra/devices

**Soluções:**
1. **Esperado** - APIs precisam de autenticação
2. Fazer login no sistema
3. Verificar se session está ativa

### Problema: Performance ruim

**Sintomas:**
- Mapa lento ao interagir
- Lag ao arrastar markers

**Soluções:**
1. Verificar quantidade de segmentos/devices
2. Ativar clustering para devices (`enableClustering: true`)
3. Limitar dados carregados (filtros)
4. Fechar outras abas do navegador

---

## 📈 Métricas de Performance

### Tempos Esperados

| Métrica | Target | Aceitável | Ruim |
|---------|--------|-----------|------|
| First Contentful Paint | <1s | <2s | >2s |
| Time to Interactive | <2s | <3s | >3s |
| Map Tiles Load | <1s | <2s | >2s |
| Plugin Load | <100ms | <200ms | >200ms |
| API Response | <500ms | <1s | >1s |

### Como Medir

```javascript
// Abrir console (F12) e executar:

// Performance do carregamento
performance.getEntriesByType('navigation')[0]

// Tempo de carregamento de recursos
performance.getEntriesByType('resource')
  .filter(r => r.name.includes('maps'))
  .forEach(r => console.log(r.name, r.duration + 'ms'))
```

---

## ✅ Critérios de Aceite

Para considerar o sistema **APROVADO**, deve atender:

### Obrigatórios (MUST HAVE)
- [x] Mapa carrega em /monitoring/backbone/
- [x] Menu lateral visível e funcional
- [x] Pressionar F5 não quebra nada
- [x] Segmentos de fibra aparecem
- [x] Markers de devices aparecem
- [x] Network Design permite desenhar rotas
- [x] Sem erros críticos no console

### Desejáveis (SHOULD HAVE)
- [ ] Clustering de markers funciona
- [ ] InfoWindows mostram dados corretos
- [ ] Menu de contexto funciona
- [ ] Performance <2s carregamento

### Opcionais (NICE TO HAVE)
- [ ] Todas as páginas testadas
- [ ] Compatibilidade cross-browser
- [ ] Testes em diferentes resoluções

---

## 📝 Relatório de Testes

### Template

```
DATA: 2025-11-17
TESTADOR: [Seu Nome]

PÁGINAS TESTADAS:
✅ /monitoring/backbone/
✅ /NetworkDesign/
⏸️ /monitoring/monitoring-all/
⏸️ /monitoring/gpon/
⏸️ /monitoring/dwdm/

BUGS ENCONTRADOS:
1. [Descrição do bug]
   Severidade: [Crítico/Alto/Médio/Baixo]
   Status: [Novo/Em análise/Corrigido]

2. [Descrição do bug]
   ...

OBSERVAÇÕES:
- [Observação 1]
- [Observação 2]

CONCLUSÃO:
[Aprovado/Aprovado com ressalvas/Reprovado]
```

---

## 🚀 Próximos Passos Após Testes

1. **Se tudo OK:**
   - Merge para branch principal
   - Deploy em staging
   - Comunicar equipe

2. **Se bugs encontrados:**
   - Criar issues no GitHub
   - Priorizar correções
   - Re-testar após fixes

3. **Melhorias futuras:**
   - Adicionar mais plugins (heatmap, measurement, etc.)
   - Otimizar performance
   - Adicionar analytics

---

**Última atualização:** 2025-11-17  
**Versão:** 1.0.0  
**Status:** ✅ Pronto para testes
