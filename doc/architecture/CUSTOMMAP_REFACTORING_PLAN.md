# Plano de Refatoração: CustomMapViewer.vue

## 📊 Análise Atual

### Tamanho do Arquivo
- **Arquivo fonte**: `CustomMapViewer.vue` - **3.471 linhas**
- **Build gerado**: `CustomMapViewer-DLSJHCcj.js` - **3.610,71 KB** (767.26 KB gzipped)
- **Problema**: Arquivo monolítico gigante afeta performance de carregamento e manutenção

### Imports Pesados Identificados
```javascript
// Bibliotecas de mapas (TODAS carregadas mesmo usando apenas 1)
import { MarkerClusterer } from '@googlemaps/markerclusterer'  // ~50KB
import mapboxgl from 'mapbox-gl'                               // ~500KB
import 'mapbox-gl/dist/mapbox-gl.css'                          // ~50KB
import L from 'leaflet'                                        // ~150KB
import 'leaflet/dist/leaflet.css'                              // ~20KB
```

**🔴 PROBLEMA CRÍTICO**: O arquivo carrega **3 bibliotecas de mapas diferentes** (Google Maps, Mapbox, Leaflet) mesmo que o usuário só use **uma** delas!

---

## 🎯 Objetivos da Refatoração

1. **Reduzir tamanho do bundle em 60-70%** (de 3.6MB para ~1.2MB)
2. **Code splitting** - carregar apenas o que é necessário
3. **Lazy loading** - bibliotecas de mapas carregadas sob demanda
4. **Componentização** - extrair lógica em componentes reutilizáveis
5. **Manutenibilidade** - código mais organizado e testável

---

## 📋 Plano de Ação

### FASE 1: Lazy Loading de Provedores de Mapa ✅ **CONCLUÍDA**
**Impacto**: Redução de ~2.8MB no bundle inicial (77% de redução)

**Status**: ✅ IMPLEMENTADO
**Branch**: `refactor/lazy-load-map-providers`
**Commit**: Implementação lazy loading para Mapbox e Leaflet

**Resultados**:
- Bundle CustomMapViewer: **3,610KB → 818KB** (redução de 77.9%)
- Gzipped: **767KB → 163KB** (redução de 78.7%)
- Mapbox chunk lazy: **2,406KB** (carregado apenas quando necessário)
- Leaflet chunk lazy: **388KB** (carregado apenas quando necessário)

**Arquivos criados**:
1. `composables/map/providers/useMapbox.js` - Lazy load Mapbox GL
2. `composables/map/providers/useLeaflet.js` - Lazy load Leaflet
3. `composables/map/providers/useMarkerClusterer.js` - Lazy load clusterer

**Implementação**:
```javascript
// useMapbox.js
export async function loadMapbox() {
  const [mapboxModule, cssModule] = await Promise.all([
    import('mapbox-gl'),
    import('mapbox-gl/dist/mapbox-gl.css')
  ])
  mapboxgl = mapboxModule.default
  mapboxLoaded = true
  return mapboxgl
}

// useLeaflet.js  
export async function loadLeaflet() {
  const [leafletModule, cssModule] = await Promise.all([
    import('leaflet'),
    import('leaflet/dist/leaflet.css')
  ])
  L = leafletModule.default
  leafletLoaded = true
  return L
}
```

**Modificações em CustomMapViewer.vue**:
- Removidos imports estáticos de mapbox-gl e leaflet
- `initMapboxMap()` chama `await loadMapbox()` antes de usar
- `initOpenStreetMap()` chama `await loadLeaflet()` antes de usar

**Validação**:
- ✅ Build reduzido de 3.6MB para 818KB
- ✅ Mapbox carrega dinamicamente apenas quando selecionado
- ✅ Leaflet carrega dinamicamente apenas quando selecionado  
- ✅ Google Maps continua funcionando via CDN
- ✅ Todos os 3 provedores testados e funcionais

---

### FASE 2: Extrair Componentes ✅ **CONCLUÍDA**
**Impacto**: Organização do código, reutilização, facilita manutenção

**Status**: ✅ 75% COMPLETO (3/4 componentes criados)

**Componentes criados**:
1. ✅ **`MapToolbar.vue`** - Criado e integrado
   - Props: mapName, mapCategory, isFullscreen
   - Emits: toggle-inventory, toggle-fullscreen
   - Resultado: ~70 linhas de código extraídas

2. ✅ **`MapLegend.vue`** - Criado e integrado
   - Props: statusLegend (array)
   - Resultado: ~60 linhas de código extraídas + CSS isolado

3. ✅ **`MapInventoryPanel.vue`** - Criado e integrado (grande conquista!)
   - Props: 11 props incluindo isVisible, activeCategory, searchQuery, categories, availableItems, selectedItems, expandedSites, expandedCameraSites, devicesBySite, camerasBySite, filteredItems
   - Emits: 11 eventos incluindo close, update:activeCategory, update:searchQuery, toggle-site-expansion, toggle-camera-site-expansion, toggle-site, toggle-camera-site, toggle-item, focus-item, highlight-cable, unhighlight-cable, select-all, save
   - Componente complexo com hierarquia de sites para devices e câmeras
   - Resultado: **~230 linhas de template + ~530 linhas de CSS** extraídas

4. ⏳ **`MapProviderWrapper.vue`** (100 linhas) - PENDENTE (opcional)
   - Container do mapa com abstração de provedor
   - Gerencia inicialização Google/Mapbox/Leaflet
   - Nota: Pode não ser necessário após extrações atuais

**Resultados FASE 2 (completa)**:
- CustomMapViewer JS: **818KB → 803KB** (redução de 1.8%)
- CustomMapViewer CSS: **122KB → 133KB** (aumento devido ao componente MapInventoryPanel incluído no bundle)
- Código fonte CustomMapViewer: **3,484 linhas → ~2,700 linhas** (~784 linhas extraídas)
- Total de componentes: **3 novos arquivos** (MapToolbar, MapLegend, MapInventoryPanel)
- Total de linhas de código modularizadas: **~850 linhas**

**Observação sobre CSS**: O CSS total aumentou ligeiramente porque o MapInventoryPanel.vue agora está no bundle (mesmo estando em arquivo separado com scoped CSS). Isso é esperado e não é um problema - o benefício é a organização e manutenibilidade, não redução de CSS.

**Estrutura final de componentes**:
```
frontend/src/views/monitoring/components/
├── MapToolbar.vue           ✅ 95 linhas
├── MapLegend.vue            ✅ 100 linhas  
├── MapInventoryPanel.vue    ✅ 753 linhas
└── MapProviderWrapper.vue   ⏳ Opcional
```

---

### FASE 3: Extrair Lógica em Composables (PRIORIDADE MÉDIA)
**Impacto**: Reutilização, testabilidade, separação de concerns

**Composables a criar**:

1. **`useMapMarkers.js`** (~400 linhas)
   - Funções: `createMarker()`, `updateMapMarkers()`, `getMarkerIcon()`
   - Gerenciamento de `activeMarkers` Map

2. **`useMapPolylines.js`** (~300 linhas)
   - Funções: `createPolyline()`, `updateCablePolylines()`
   - Gerenciamento de `activePolylines` Map

3. **`useMapSelection.js`** (~200 linhas)
   - Gerencia `selectedItems`, `availableItems`
   - Funções: `toggleItem()`, `selectAll()`, `deselectAll()`

4. **`useMapConfig.js`** (~150 linhas)
   - Carrega configurações do sistema
   - Gerencia `configForm`

5. **`useMapData.js`** (~200 linhas)
   - `loadInventoryItems()`, `loadMapData()`
   - Cache de dados

---

### FASE 4: Remover Código Morto (PRIORIDADE BAIXA)
**Impacto**: Redução de ~200-300 linhas

**Identificar e remover**:
1. Funções não utilizadas (grep por referências)
2. Variáveis declaradas mas não usadas
3. Logs de debug excessivos
4. Código comentado antigo

**Script de verificação**:
```bash
# Encontrar funções definidas
grep -E "^const [a-zA-Z]+ = " CustomMapViewer.vue

# Verificar se cada função é usada
# Manualmente ou com ferramenta de análise estática
```

---

### FASE 5: Tree Shaking de Bibliotecas (PRIORIDADE MÉDIA)
**Impacto**: Redução de ~100-200KB

**Ações**:
1. **MarkerClusterer**: Carregar apenas quando clustering ativado
```javascript
let MarkerClusterer
if (enableClustering) {
  const module = await import('@googlemaps/markerclusterer')
  MarkerClusterer = module.MarkerClusterer
}
```

2. **Modals**: Lazy load de modais (só carregar quando abrir)
```javascript
const SiteDetailsModal = defineAsyncComponent(() =>
  import('@/components/SiteDetailsModal.vue')
)
```

---

## 🏗️ Estrutura de Arquivos Proposta

```
frontend/src/views/monitoring/
├── CustomMapViewer.vue                  (500 linhas - orquestra tudo)
│
├── components/
│   ├── MapToolbar.vue                   (50 linhas)
│   ├── MapInventoryPanel.vue            (300 linhas)
│   ├── MapLegend.vue                    (50 linhas)
│   └── MapProviderWrapper.vue           (100 linhas)
│
└── composables/map/
    ├── useMapMarkers.js                 (400 linhas)
    ├── useMapPolylines.js               (300 linhas)
    ├── useMapSelection.js               (200 linhas)
    ├── useMapConfig.js                  (150 linhas)
    ├── useMapData.js                    (200 linhas)
    ├── providers/
    │   ├── useGoogleMaps.js             (400 linhas)
    │   ├── useMapbox.js                 (400 linhas)
    │   └── useLeaflet.js                (300 linhas)
```

---

## 📈 Estimativa de Resultados

### Bundle Size (atual → depois)
- **Inicial**: 3.610 KB → **~1.200 KB** (-67%)
- **Mapbox chunk**: 0 KB → **~500 KB** (lazy loaded)
- **Leaflet chunk**: 0 KB → **~150 KB** (lazy loaded)
- **Google Maps**: Já lazy (CDN)

### Performance
- **Tempo de carregamento inicial**: -60%
- **First Contentful Paint (FCP)**: -50%
- **Time to Interactive (TTI)**: -55%

### Manutenibilidade
- **Linhas por arquivo**: 3.471 → média de **200-400 linhas**
- **Testabilidade**: Composables podem ser testados isoladamente
- **Reusabilidade**: Componentes reutilizáveis em outros mapas

---

## 🚀 Cronograma Sugerido

| Fase | Esforço | Prazo | Prioridade |
|------|---------|-------|------------|
| **FASE 1**: Lazy Loading Mapas | 8h | 2 dias | 🔴 ALTA |
| **FASE 2**: Componentização | 12h | 3 dias | 🟡 MÉDIA |
| **FASE 3**: Composables | 16h | 4 dias | 🟡 MÉDIA |
| **FASE 4**: Código Morto | 4h | 1 dia | 🟢 BAIXA |
| **FASE 5**: Tree Shaking | 4h | 1 dia | 🟡 MÉDIA |
| **Testes & QA** | 8h | 2 dias | 🔴 ALTA |
| **TOTAL** | 52h | 13 dias | |

---

## ✅ Checklist de Validação

Após cada fase, validar:

- [ ] Bundle size reduziu conforme esperado
- [ ] Todas as funcionalidades continuam funcionando
- [ ] Google Maps funciona
- [ ] Mapbox funciona
- [ ] Leaflet/OSM funciona
- [ ] Markers aparecem corretamente
- [ ] Polylines aparecem corretamente
- [ ] Seleção de items funciona
- [ ] Modais abrem corretamente
- [ ] Zoom e centralização funcionam
- [ ] Performance melhorou (Lighthouse)
- [ ] Sem erros no console
- [ ] Testes unitários passam

---

## 🎬 Primeiros Passos (Quick Wins)

**Para começar HOJE**:

1. **Criar branch de refatoração**:
```bash
git checkout -b refactor/split-custom-map-viewer
```

2. **Implementar lazy loading de Mapbox/Leaflet** (FASE 1):
   - Maior impacto com menor risco
   - ~700KB de redução imediata
   - Sem alterar lógica existente

3. **Extrair MapToolbar.vue** (FASE 2):
   - Componente simples, baixo risco
   - Valida pipeline de componentização

---

## 📝 Notas Importantes

1. **Não quebrar funcionalidade**: Refatorar incrementalmente, validar a cada passo
2. **Testes**: Criar testes E2E para fluxos críticos antes de refatorar
3. **Rollback**: Manter branch original como backup
4. **Documentação**: Atualizar docs de cada componente/composable criado
5. **Code Review**: Revisões menores e frequentes (PR por fase)

---

## 🤔 Decisões Pendentes

- [ ] **Clustering**: Manter MarkerClusterer ou implementar solução custom?
- [ ] **CSS**: Manter em `<style>` ou migrar para CSS Modules/Tailwind?
- [ ] **State Management**: Considerar Pinia store para estado do mapa?
- [ ] **TypeScript**: Converter para TS durante refatoração?

---

## 📚 Referências

- [Vite Code Splitting](https://vitejs.dev/guide/features.html#code-splitting)
- [Vue Dynamic Imports](https://vuejs.org/guide/components/async.html)
- [Composables Pattern](https://vuejs.org/guide/reusability/composables.html)
- [Tree Shaking Guide](https://webpack.js.org/guides/tree-shaking/)
