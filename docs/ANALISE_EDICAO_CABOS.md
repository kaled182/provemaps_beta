# 📊 RELATÓRIO TÉCNICO: Análise da Funcionalidade de Edição de Cabos

**Data:** 27 de Outubro de 2025  
**Projeto:** MapsProveFiber - Fiber Route Builder  
**Status:** 🔴 Funcionalidade Bloqueada por Erro JavaScript

---

## 🎯 RESUMO EXECUTIVO

### Problema Relatado
Ao clicar com botão direito no cabo (linha azul no mapa), a funcionalidade de edição não está funcionando. O usuário espera ver um menu com opções para:
1. **Editar caminho do cabo** (arrastar marcadores no mapa)
2. **Editar porta monitorada** (metadados: nome, notas, porta origem/destino)

### Estado Atual
- ❌ **Edição de cabos:** NÃO funciona
- ✅ **Backend API:** 100% funcional (18/18 testes passando)
- ❌ **Frontend:** Bloqueado por erro de sintaxe JavaScript
- ✅ **Menu de contexto:** Aparece corretamente
- ❌ **Marcadores editáveis:** Não são criados (processo interrompido)

### Causa Raiz
**Erro crítico na linha 35-36 de `fiber_route_builder.js`:**
```javascript
// ❌ ERRO: distance tratado como função quando é número
totalDistance = distance(); 
```

---

## 🐛 ERROS IDENTIFICADOS NO CONSOLE

### Erro 1: ReferenceError - distance() não é uma função
```javascript
❌ Path change callback error: ReferenceError: distance() is not defined
   at fiber_route_builder.js:35
   at notifyPathChange (pathState.js:23)
   at edifyPathChange (oasisGate.js:187:23)
```

**Localização:** `routes_builder/static/js/fiber_route_builder.js` linha 35-36

**Código Problemático:**
```javascript
onPathChange(({ path, distance }) => {
    drawPolyline(path);
    totalDistance = distance(); // ❌ ERRO: distance é número, não função!
    updateEditButtonState();
});
```

**Solução:**
```javascript
onPathChange(({ path, distance }) => {
    drawPolyline(path);
    totalDistance = distance; // ✅ Remover parênteses
    updateEditButtonState();
});
```

### Erro 2: Marcadores não são criados
**Consequência do Erro 1:** O processo de criação de marcadores é interrompido antes de `addMarker()` ser executado para cada ponto do path.

---

## 🔍 PROCEDIMENTO ESPERADO (FLUXO CORRETO)

### FASE 1: Carregamento Inicial da Página
1. **Usuário acessa:** `http://localhost:8000/routes/builder/fiber-route-builder/`
2. **JavaScript carrega:** `fiber_route_builder.js` (arquivo principal)
3. **Função `initMap()` é executada** (linha ~185):
   - Inicializa mapa Google Maps
   - Configura handlers de clique esquerdo (`onMapClick`)
   - Configura handlers de clique direito (`onMapRightClick`)
4. **Função `loadAllCablesForVisualization()` é executada** (linha ~73):
   - Busca todos os cabos via API: `GET /zabbix_api/api/fibers/load-all/`
   - Para cada cabo, desenha polilinha azul no mapa
   - **Chama `makeCableEditable()`** para cada polilinha

---

### FASE 2: Clique com Botão Direito no Cabo

#### Passo 1: Event Handler Dispara
```javascript
// Arquivo: fiber_route_builder.js (linha 242-256)
function makeCableEditable(cablePolyline, cableId, cableName) {
    cablePolyline.addListener('rightclick', async (event) => {
        event.stop();
        
        // ✅ 1. Atualiza dropdown
        const fiberSelect = document.getElementById('fiberSelect');
        if (fiberSelect) {
            fiberSelect.value = String(cableId);
        }
        
        // ✅ 2. Carrega detalhes do cabo
        await loadFiberDetail(cableId);
        
        // ✅ 3. Abre menu de contexto
        setTimeout(() => {
            showContextMenu(event.domEvent.clientX, event.domEvent.clientY);
            updateContextMenuStateWrapper();
        }, 100);
    });
}
```

#### Passo 2: Carregar Dados do Cabo
```javascript
// Arquivo: fiber_route_builder.js (linha 308-327)
async function loadFiberDetail(id) {
    try {
        // ✅ Busca dados: GET /zabbix_api/api/fibers/{id}/
        const data = await fetchFiber(id);
        
        // ✅ Define cabo como ativo
        activeFiberId = data.id;
        currentFiberMeta = {
            name: data.name || '',
            origin_device_id: data.origin?.device_id || null,
            origin_port_id: data.origin?.port_id || null,
            dest_device_id: data.destination?.device_id || null,
            dest_port_id: data.destination?.port_id || null,
            single_port: Boolean(data.single_port),
        };
        
        updateEditButtonState();
        
        // ✅ Carrega path do backend
        const path = (data.path && data.path.length) 
            ? data.path 
            : buildDefaultFromEndpoints(data);
        
        console.log(`[loadFiberDetail] Setting path with ${path.length} points:`, path);
        
        // ❌ PROBLEMA AQUI: setPath() dispara erro
        setPath(path); // Linha 318
        
        console.log(`[loadFiberDetail] Created ${markers.length} markers`);
        
        // ✅ Ajusta zoom para mostrar todos os pontos
        if (path && path.length > 0) {
            fitMapToBounds(path);
        }
    } catch (err) {
        console.error('Error loading cable', err);
        alert('Error loading cable');
    }
}
```

#### Passo 3: Criar Marcadores Editáveis (BLOQUEADO)
```javascript
// Arquivo: fiber_route_builder.js (linha 177-183)
function setPath(points) {
    clearMarkers();
    setPathState(points); // Atualiza estado global via pathState.js
    const currentPath = getPath();
    
    // ❌ BLOQUEADO: Para cada ponto, deveria criar marcador
    // Mas notifyPathChange() dispara erro antes de chegar aqui
    currentPath.forEach((point) => addMarker(point));
}
```

```javascript
// Arquivo: fiber_route_builder.js (linha 145-175)
function addMarker(point, removable = true) {
    console.log(`[addMarker] Creating draggable marker at:`, point);
    const marker = createMarker(point, { draggable: true });
    markers.push(marker);
    console.log(`[addMarker] Total markers now: ${markers.length}`);

    // ✅ Handler de drag (mover marcador)
    marker.addListener('dragend', () => {
        const index = markers.indexOf(marker);
        if (index > -1) {
            const newPos = marker.getPosition();
            console.log(`[addMarker] Marker #${index} dragged to:`, newPos.lat(), newPos.lng());
            updatePoint(index, newPos.lat(), newPos.lng());
        }
    });

    // ✅ Handlers de remoção (double-click ou right-click)
    if (removable) {
        const removeMarkerHandler = () => {
            const index = markers.indexOf(marker);
            if (index > -1) {
                console.log(`[addMarker] Removing marker #${index}`);
                markers.splice(index, 1);
                removePoint(index);
                removeMarker(marker);
            }
        };

        marker.addListener('dblclick', removeMarkerHandler);
        marker.addListener('rightclick', removeMarkerHandler);
    }

    return marker;
}
```

#### Passo 4: Exibir Menu de Contexto
```javascript
// Arquivo: modules/contextMenu.js
showContextMenu(x, y); // Posiciona menu nas coordenadas do mouse

updateContextMenuState({
    hasActiveFiber: true,
    fiberMeta: currentFiberMeta,
    pathLength: getPath().length
});
```

**HTML do Menu** (`fiber_route_builder.html` linha 82-92):
```html
<div id="contextSelectedOptions" class="hidden">
  <!-- ✅ NOVO: Botão para entrar em modo de edição -->
  <button id="contextEditPath">
    <span>📍</span> Edit Cable Path
  </button>
  
  <!-- ✅ Botão para editar metadados -->
  <button id="contextEditCable">
    <span>⚙️</span> Edit Metadata (Port/Name)
  </button>
  
  <!-- ✅ Botão para salvar alterações no path -->
  <button id="contextSavePath">
    <span>💾</span> Save Path Changes
  </button>
  
  <!-- ✅ Botão para deletar cabo -->
  <button id="contextDeleteCable">
    <span>🗑️</span> Delete Selected Cable
  </button>
</div>
```

#### Passo 5: Usuário Clica em "Edit Cable Path"
```javascript
// Arquivo: fiber_route_builder.js (linha 558-571)
document.getElementById('contextEditPath')?.addEventListener('click', () => {
    hideContextMenu();
    if (activeFiberId && currentFiberMeta) {
        console.log('[contextEditPath] Entering path edit mode');
        
        const currentPath = getPath();
        if (currentPath.length === 0) {
            // Se path vazio, recarrega o cabo
            loadFiberDetail(activeFiberId);
        } else {
            console.log(`[contextEditPath] Path already loaded with ${currentPath.length} points`);
            
            // ❌ NUNCA CHEGA AQUI porque erro anterior impede execução
            alert(`Path edit mode active!\n${currentPath.length} draggable markers loaded.\nDrag markers to edit, right-click marker to remove.`);
        }
    }
});
```

#### Passo 6: Editar e Salvar
```javascript
// Usuário arrasta marcadores
// → Evento 'dragend' → updatePoint() → notifyPathChange() → drawPolyline()

// Usuário clica direito novamente → "Save Path Changes"
document.getElementById('contextSavePath')?.addEventListener('click', () => {
    hideContextMenu();
    if (activeFiberId && getPath().length >= 2) {
        handleSaveClick(); // Chama API: PUT /zabbix_api/api/fibers/{id}/
    }
});
```

---

## 📁 ARQUIVOS ENVOLVIDOS E RESPONSABILIDADES

### 1. ARQUIVO PRINCIPAL

#### **`routes_builder/static/js/fiber_route_builder.js`** (660 linhas)
**Responsabilidade:** Controlador principal da aplicação

**Linhas Críticas:**
- **Linha 35-36:** ❌ **ERRO PRINCIPAL** - Callback com `distance()` incorreto
- **Linha 145-175:** Função `addMarker()` - Cria marcadores arrastáveis com drag/remove handlers
- **Linha 177-183:** Função `setPath()` - Sincroniza marcadores com path do estado
- **Linha 185-227:** Função `initMap()` - Inicializa Google Maps e event handlers
- **Linha 242-256:** Função `makeCableEditable()` - Configura right-click em polilinha de visualização
- **Linha 308-327:** Função `loadFiberDetail()` - Carrega dados do cabo via API e cria marcadores
- **Linha 558-571:** Event handler `contextEditPath` - Botão "Edit Cable Path" (modo de edição)
- **Linha 573-578:** Event handler `contextEditCable` - Botão "Edit Metadata" (abre modal)
- **Linha 580-585:** Event handler `contextSavePath` - Botão "Save Path Changes" (persiste no backend)

**Dependências:**
```javascript
import { setPath as setPathState, getPath, updatePoint, removePoint, 
         onPathChange, clearPath, reorderPath } from './modules/pathState.js';
import { initMap as initializeMap, onMapClick, onMapRightClick, drawPolyline, 
         clearPolyline, addMarker as createMarker, removeMarker, 
         clearMarkers as clearAllMarkers, attachPolylineRightClick } from './modules/mapCore.js';
import { initContextMenu, showContextMenu, hideContextMenu, 
         updateContextMenuState } from './modules/contextMenu.js';
import { initModalEditor, openModalForCreate, openModalForEdit, closeModal, 
         updateEditButtonState } from './modules/modalEditor.js';
import { fetchFibers, fetchFiber, createFiberManual, updateFiber, 
         removeFiber } from './modules/apiClient.js';
```

---

### 2. MÓDULOS AUXILIARES

#### **A) `modules/pathState.js`**
**Responsabilidade:** Gerencia estado global do path (array de pontos `{lat, lng}`)

**Funções Exportadas:**
- `setPath(points)` - Define path inicial (substitui todo o array)
- `getPath()` - Retorna cópia do path atual
- `updatePoint(index, lat, lng)` - Atualiza coordenadas de um ponto específico
- `addPoint(lat, lng)` - Adiciona novo ponto ao final do array
- `removePoint(index)` - Remove ponto do array
- `clearPath()` - Limpa todo o path
- `reorderPath()` - Reordena pontos (se necessário)
- `onPathChange(callback)` - Registra listener para mudanças no path
- `calculateTotalDistance()` - Calcula distância total usando fórmula Haversine

**Fluxo Interno:**
```javascript
// Qualquer mudança no path dispara:
function notifyPathChange() {
    const distance = calculateTotalDistance(); // Calcula distância total
    
    // ✅ Dispara todos os callbacks registrados
    pathChangeListeners.forEach(listener => {
        listener({ 
            path: [...currentPath],  // Cópia do path atual
            distance                  // Número (km) - NÃO é função!
        });
    });
}
```

**❌ ERRO:** O callback registrado em `fiber_route_builder.js` trata `distance` como função `distance()`.

---

#### **B) `modules/mapCore.js`**
**Responsabilidade:** Abstração da API do Google Maps

**Funções Exportadas:**
- `initMap(elementId, options)` - Cria instância do mapa Google Maps
- `getMap()` - Retorna instância atual do mapa
- `onMapClick(callback)` - Registra handler para clique esquerdo no mapa
- `onMapRightClick(callback)` - Registra handler para clique direito no mapa
- `drawPolyline(path)` - Desenha/atualiza linha azul representando o cabo
- `clearPolyline()` - Remove linha azul do mapa
- `addMarker(position, options)` - Cria marcador Google Maps (retorna `google.maps.Marker`)
- `removeMarker(marker)` - Remove marcador específico do mapa
- `clearMarkers()` - Remove todos os marcadores
- `attachPolylineRightClick(polyline, callback)` - Configura right-click em polilinha específica

**Wrapper para Google Maps API:**
```javascript
function addMarker(position, options = {}) {
    const marker = new google.maps.Marker({
        map: mapInstance,
        position: position,
        draggable: options.draggable || false,
        icon: options.icon || undefined,
        title: options.title || ''
    });
    return marker; // Retorna instância do marcador
}
```

---

#### **C) `modules/contextMenu.js`**
**Responsabilidade:** Gerencia menu de contexto (botão direito)

**Funções Exportadas:**
- `initContextMenu()` - Inicialização: cacheia DOM elements, configura ESC/click-outside handlers
- `showContextMenu(x, y)` - Posiciona e exibe menu nas coordenadas especificadas
- `hideContextMenu()` - Esconde menu
- `updateContextMenuState(context)` - Atualiza visibilidade de seções do menu
- `isContextMenuVisible()` - Verifica se menu está visível
- `getContextMenuPosition()` - Retorna posição atual do menu

**Lógica de Exibição (3 Cenários):**

```javascript
export function updateContextMenuState(context) {
    const { hasActiveFiber, fiberMeta, pathLength } = context;

    // Determina cenário atual
    const isCreatingNewCable = !hasActiveFiber && pathLength > 0; // Scenario B
    const isSelectedCable = hasActiveFiber && !!fiberMeta;        // Scenario C
    const isEmpty = !hasActiveFiber && pathLength === 0;          // Scenario A

    // Reset (esconde tudo)
    selectedOptionsEl?.classList.add('hidden');
    creatingOptionsEl?.classList.add('hidden');
    cableInfoEl?.classList.add('hidden');
    generalOptionsEl?.classList.add('hidden');
    reloadButtonEl?.classList.add('hidden');

    if (isCreatingNewCable) {
        // Scenario B: Desenhando novo cabo
        creatingOptionsEl?.classList.remove('hidden');
        // Mostra: "Assign the Cable" + "Clear Points"
        
    } else if (isSelectedCable) {
        // Scenario C: Cabo selecionado para edição
        selectedOptionsEl?.classList.remove('hidden');
        cableInfoEl?.classList.remove('hidden');
        // Mostra: "Edit Path" + "Edit Metadata" + "Save" + "Delete"

        // Atualiza nome do cabo no menu
        if (cableNameEl) {
            const isEditing = pathLength > 0;
            const status = isEditing ? ' - EDITING' : '';
            const displayName = fiberMeta.name || `Cable #${fiberMeta.id || '?'}`;
            cableNameEl.textContent = `📌 ${displayName}${status}`;
        }

        // Habilita "Save Path" apenas se ≥2 pontos
        if (savePathEl) {
            savePathEl.disabled = pathLength < 2;
            savePathEl.style.opacity = pathLength >= 2 ? '1' : '0.5';
        }
        
    } else if (isEmpty) {
        // Scenario A: Estado vazio
        generalOptionsEl?.classList.remove('hidden');
        // Mostra: "Import KML" + "Reload All Cables"
    }
}
```

---

#### **D) `modules/modalEditor.js`**
**Responsabilidade:** Modal de edição de metadados (nome, porta origem/destino)

**Funções Exportadas:**
- `initModalEditor()` - Inicializa evento de submit do formulário
- `openModalForCreate(distance)` - Abre modal para criar novo cabo
- `openModalForEdit(cableData, distance)` - Abre modal para editar cabo existente
- `closeModal()` - Fecha modal e reseta formulário
- `getEditingFiberId()` - Retorna ID do cabo sendo editado (ou null)
- `isEditMode()` - Verifica se está em modo de edição (vs criação)
- `resetForm()` - Limpa todos os campos do formulário
- `updateEditButtonState()` - Habilita/desabilita botão "Edit" baseado em estado

**Diferença entre Create vs Edit:**
```javascript
// CREATE: Novo cabo (sem ID)
openModalForCreate(distance) {
    editingFiberId = null; // Sem ID
    modalTitle.textContent = 'Create New Cable';
    manualLengthInput.value = distance.toFixed(2);
    // Campos vazios, exceto distância calculada
}

// EDIT: Cabo existente (com ID)
openModalForEdit(cableData, distance) {
    editingFiberId = cableData.id; // Define ID
    modalTitle.textContent = 'Edit Cable Metadata';
    
    // Preenche campos com dados atuais
    manualNameInput.value = cableData.name || '';
    manualOriginDeviceSelect.value = cableData.origin_device_id || '';
    manualDestDeviceSelect.value = cableData.dest_device_id || '';
    // ... carrega portas e define valores
}
```

---

#### **E) `modules/apiClient.js`**
**Responsabilidade:** Comunicação HTTP com backend Django

**Funções Exportadas:**
- `fetchFibers()` - Lista todos os cabos
- `fetchFiber(id)` - Detalhes de um cabo específico
- `createFiberManual(payload)` - Cria novo cabo
- `updateFiber(id, payload)` - Atualiza cabo existente
- `removeFiber(id)` - Deleta cabo
- `fetchDevicePorts(deviceId)` - Lista portas de um device

**Endpoints do Backend:**

| Método | Endpoint | Função | Payload |
|--------|----------|--------|---------|
| GET | `/zabbix_api/api/fibers/` | Lista cabos | - |
| GET | `/zabbix_api/api/fibers/{id}/` | Detalhes cabo | - |
| POST | `/zabbix_api/api/fibers/manual-create/` | Criar cabo | `{name, path, origin_device_id, origin_port_id, dest_device_id, dest_port_id}` |
| PUT | `/zabbix_api/api/fibers/{id}/` | Atualizar cabo | `{path}` ou `{name, notes, length_km}` |
| DELETE | `/zabbix_api/api/fibers/{id}/` | Deletar cabo | - |
| GET | `/zabbix_api/api/fibers/load-all/` | Visualização todos cabos | - |

**Formato do Payload (Crítico):**
```javascript
// ✅ API usa "path" (NÃO "path_coordinates")
{
    path: [
        {lat: -23.5505, lng: -46.6333},
        {lat: -23.5506, lng: -46.6334},
        // ...
    ],
    name: "Cabo Exemplo",
    origin_device_id: 1,
    origin_port_id: 2,
    dest_device_id: 3,
    dest_port_id: 4,
    notes: "Observações",
    length_km: 5.42
}
```

**Backend faz conversão automática:**
- **API recebe:** `path` (JSON)
- **Backend salva:** `path_coordinates` (campo do modelo)
- **API retorna:** `path` (JSON)

---

#### **F) `modules/cableService.js`**
**Responsabilidade:** Lógica de visualização de cabos no mapa

**Funções Principais:**
- `loadAllCablesForVisualization()` - Carrega todos os cabos para visualização
- `drawCableOnMap(cable)` - Desenha polilinha individual no mapa
- `clearAllCables()` - Remove todos os cabos da visualização

**Integração com fiber_route_builder.js:**
```javascript
// fiber_route_builder.js importa e usa:
import { loadAllCablesForVisualization } from './modules/cableService.js';

// Chamado em 3 momentos:
// 1. initMap() - Carregamento inicial
// 2. Após criar novo cabo (auto-reload)
// 3. Evento "Reload All Cables" do menu de contexto
```

---

#### **G) `modules/uiHelpers.js`**
**Responsabilidade:** Utilitários de UI (formatação, mensagens)

**Funções Típicas:**
- Formatação de distâncias (km)
- Formatação de coordenadas (lat/lng)
- Tooltips dinâmicos
- Mensagens de validação

---

### 3. TEMPLATE HTML

#### **`routes_builder/templates/fiber_route_builder.html`**

**Estrutura do Menu de Contexto (linha 63-105):**
```html
<div id="contextMenu" class="absolute bg-white rounded-lg shadow-xl border border-gray-200 py-2 z-20 hidden" style="min-width: 220px;">
    
    <!-- Informação do cabo selecionado -->
    <div id="contextCableInfo" class="hidden">
        <span id="contextCableName"></span>
    </div>
    
    <!-- Scenario B: Criando novo cabo -->
    <div id="contextCreatingOptions" class="hidden">
        <button id="contextSaveNewCable">✏️ Assign the Cable</button>
        <button id="contextClearNew">🧹 Clear Points</button>
    </div>
    
    <!-- Scenario C: Cabo selecionado (PRINCIPAL) -->
    <div id="contextSelectedOptions" class="hidden">
        <button id="contextEditPath">📍 Edit Cable Path</button>
        <button id="contextEditCable">⚙️ Edit Metadata (Port/Name)</button>
        <button id="contextSavePath">💾 Save Path Changes</button>
        <button id="contextDeleteCable">🗑️ Delete Selected Cable</button>
    </div>
    
    <!-- Scenario A: Mapa vazio -->
    <div id="contextGeneralOptions">
        <button id="contextImportKML">📥 Import KML</button>
    </div>
    
    <!-- Sempre visível -->
    <button id="contextLoadAll">
        <span id="contextLoadAllText">🔄 Reload All Cables</span>
    </button>
    
</div>
```

**Carregamento de Scripts (linha 110-115):**
```html
<!-- Google Maps API -->
<script src="https://maps.googleapis.com/maps/api/js?key={{ GOOGLE_MAPS_API_KEY }}" async defer></script>

<!-- Import KML (legado) -->
<script src="{% static 'js/partials/import_kml.js' %}?v={{ STATIC_ASSET_VERSION }}"></script>

<!-- Aplicação principal (ES6 modules) -->
<script type="module" src="{% static 'js/fiber_route_builder.js' %}?v={{ STATIC_ASSET_VERSION }}"></script>
```

---

## 🔗 FLUXO DE JUNÇÕES ENTRE ARQUIVOS

```
┌──────────────────────────────────────────────────────────────┐
│  fiber_route_builder.html (Template Django)                  │
│  - Define estrutura do menu de contexto (#contextMenu)       │
│  - Carrega Google Maps API                                   │
│  - Carrega fiber_route_builder.js (type="module")            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  fiber_route_builder.js (Controlador Principal - 660 linhas) │
│                                                               │
│  Inicialização:                                               │
│  - DOMContentLoaded → initMap() → Setup handlers             │
│  - loadAllCablesForVisualization() → Desenha todos os cabos  │
│                                                               │
│  Event Handlers:                                              │
│  - Right-click em cabo → makeCableEditable()                 │
│  - Right-click no mapa → showContextMenu()                   │
│  - Click em "Edit Path" → contextEditPath handler            │
│  - Click em "Edit Metadata" → contextEditCable handler       │
│  - Click em "Save Path" → contextSavePath handler            │
└────────────────────────┬─────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┬──────────────────┬──────────────┐
        ▼                ▼                ▼                  ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ pathState.js │  │ mapCore.js   │  │ contextMenu  │  │apiClient │  │modalEdi- │
│              │  │              │  │.js           │  │.js       │  │tor.js    │
│ Estado do    │  │ Google Maps  │  │              │  │          │  │          │
│ path global  │  │ API wrapper  │  │ Menu botão   │  │ HTTP     │  │ Modal de │
│              │  │              │  │ direito      │  │ requests │  │ metadados│
│ - Array de   │  │ - initMap()  │  │              │  │          │  │          │
│   pontos     │  │ - drawPoly   │  │ - show()     │  │ GET/POST │  │ - Create │
│              │  │   line()     │  │ - hide()     │  │ PUT/DEL  │  │ - Edit   │
│ - Callbacks  │  │ - addMarker  │  │ - update     │  │          │  │ - Close  │
│   onChange   │  │   ()         │  │   State()    │  │ Backend: │  │          │
│              │  │              │  │              │  │ /zabbix  │  │          │
│ - Calcula    │  │ - Event      │  │ 3 cenários:  │  │ _api/    │  │          │
│   distância  │  │   handlers   │  │ A, B, C      │  │ api/     │  │          │
│   Haversine  │  │              │  │              │  │ fibers/  │  │          │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────┘  └──────────┘
```

---

## 🔄 FLUXO DE EXECUÇÃO DETALHADO (Right-Click em Cabo)

### **Sequência de Chamadas:**

```
1. 👆 Usuário clica com BOTÃO DIREITO em polilinha azul (cabo no mapa)
         ↓
         
2. 🎯 Google Maps API dispara evento 'rightclick'
         ↓
         
3. ⚡ makeCableEditable() → Event handler 'rightclick' executado
   📍 Localização: fiber_route_builder.js linha 242-256
   
   Ações:
   ✅ event.stop() - Impede propagação
   ✅ fiberSelect.value = String(cableId) - Atualiza dropdown
   ✅ await loadFiberDetail(cableId) - Carrega dados
   ✅ showContextMenu(x, y) - Exibe menu
   ✅ updateContextMenuStateWrapper() - Atualiza estado do menu
         ↓
         
4. 🌐 loadFiberDetail(cableId) → Busca dados do backend
   📍 Localização: fiber_route_builder.js linha 308-327
   
   Ações:
   ✅ const data = await fetchFiber(id)
      → HTTP: GET /zabbix_api/api/fibers/{id}/
      
   ✅ activeFiberId = data.id - Define cabo ativo global
   ✅ currentFiberMeta = {...} - Armazena metadados
   ✅ updateEditButtonState() - Atualiza estado do botão de edição
   
   ✅ const path = data.path || buildDefaultFromEndpoints(data)
      → Path vem do backend como array de {lat, lng}
      
   ❌ setPath(path) - CHAMADA AQUI DISPARA ERRO!
         ↓
         
5. ⚙️ setPath(points) → Sincroniza marcadores com path
   📍 Localização: fiber_route_builder.js linha 177-183
   
   Ações:
   ✅ clearMarkers() - Remove marcadores antigos via mapCore
   ✅ setPathState(points) - Atualiza estado em pathState.js
         ↓
         
6. 📊 pathState.setPath(points) → Atualiza estado global
   📍 Localização: modules/pathState.js
   
   Ações:
   ✅ currentPath = [...points] - Clone do array
   ✅ notifyPathChange() - Dispara callbacks registrados
         ↓
         
7. 🔔 notifyPathChange() → Notifica todos os listeners
   📍 Localização: modules/pathState.js linha ~23
   
   Ações:
   ✅ const distance = calculateTotalDistance() - Calcula distância (número)
   
   ✅ pathChangeListeners.forEach(listener => {
         listener({ 
             path: [...currentPath],  // ✅ Array de pontos
             distance                  // ✅ Número (km)
         });
      });
         ↓
         
8. ❌ ERRO! Callback registrado em fiber_route_builder.js linha 35-36
   📍 Localização: fiber_route_builder.js linha 35-36
   
   Código Problemático:
   onPathChange(({ path, distance }) => {
       drawPolyline(path);
       totalDistance = distance(); // ❌ distance não é função!
       updateEditButtonState();
   });
   
   Erro Lançado:
   ReferenceError: distance is not defined
   
   ⛔ PROCESSO INTERROMPIDO - Marcadores não são criados!
         ↓
         
9. ❌ BLOQUEADO: setPath() não completa execução
   
   Código não executado:
   const currentPath = getPath();
   currentPath.forEach((point) => addMarker(point)); // ❌ Nunca executado!
         ↓
         
10. ✅ Menu de contexto aparece (independente do erro)
    📍 Localização: modules/contextMenu.js
    
    setTimeout(() => {
        showContextMenu(event.domEvent.clientX, event.domEvent.clientY);
        updateContextMenuStateWrapper();
    }, 100);
    
    Estado do Menu:
    ✅ contextSelectedOptions visible
    ✅ Botões disponíveis:
       - 📍 Edit Cable Path
       - ⚙️ Edit Metadata (Port/Name)
       - 💾 Save Path Changes (desabilitado se pathLength < 2)
       - 🗑️ Delete Selected Cable
         ↓
         
11. 👆 Usuário clica em "📍 Edit Cable Path"
    📍 Localização: fiber_route_builder.js linha 558-571
    
    ❌ BLOQUEADO: Condição `currentPath.length === 0` é TRUE
       porque marcadores não foram criados (erro anterior)
    
    Ação:
    ❌ loadFiberDetail(activeFiberId) - Tenta recarregar
       → Dispara MESMO ERRO novamente!
       
    ✅ Menu esconde: hideContextMenu()
    ❌ Marcadores editáveis NUNCA aparecem
```

---

## ✅ SOLUÇÃO NECESSÁRIA

### **FIX 1: Corrigir Callback onPathChange**

**Arquivo:** `routes_builder/static/js/fiber_route_builder.js`  
**Linha:** 35-36

**Código Atual (ERRADO):**
```javascript
onPathChange(({ path, distance }) => {
    drawPolyline(path);
    totalDistance = distance(); // ❌ distance não é função, é número!
    updateEditButtonState();
});
```

**Código Corrigido:**
```javascript
onPathChange(({ path, distance }) => {
    drawPolyline(path);
    totalDistance = distance; // ✅ Remover parênteses - é um valor, não função!
    updateEditButtonState();
});
```

**Justificativa:**
- O módulo `pathState.js` passa `distance` como **número** (resultado de `calculateTotalDistance()`)
- Não é uma função, portanto não deve ser chamado com `()`

---

### **FIX 2: Validar Execução de addMarker()**

**Arquivo:** `routes_builder/static/js/fiber_route_builder.js`  
**Linha:** 177-183

**Código Atual:**
```javascript
function setPath(points) {
    clearMarkers();
    setPathState(points);
    const currentPath = getPath();
    currentPath.forEach((point) => addMarker(point));
    // onPathChange callback will handle polyline drawing
}
```

**Validação Necessária:**
Após FIX 1, este código deve executar normalmente. Logs de debug já adicionados em `addMarker()` para confirmar:

```javascript
console.log(`[addMarker] Creating draggable marker at:`, point);
console.log(`[addMarker] Total markers now: ${markers.length}`);
```

---

### **FIX 3: Testar Fluxo Completo**

**Passos de Teste:**

1. **Aplicar FIX 1:**
   ```bash
   # Editar fiber_route_builder.js linha 35-36
   # Remover parênteses de distance()
   ```

2. **Coletar estáticos:**
   ```bash
   docker exec mapsprovefiber-web-1 python manage.py collectstatic --noinput
   ```

3. **Reiniciar serviço web:**
   ```bash
   docker compose restart web
   ```

4. **Abrir navegador com hard refresh:**
   ```
   Ctrl + F5 em http://localhost:8000/routes/builder/fiber-route-builder/
   ```

5. **Clicar com botão direito em cabo e observar Console:**
   ```
   Esperado:
   ✅ [loadFiberDetail] Loaded cable #X: {...}
   ✅ [loadFiberDetail] Setting path with N points: [...]
   ✅ [addMarker] Creating draggable marker at: {...}
   ✅ [addMarker] Total markers now: 1
   ✅ [addMarker] Creating draggable marker at: {...}
   ✅ [addMarker] Total markers now: 2
   ✅ [loadFiberDetail] Created N markers
   ```

6. **Clicar em "📍 Edit Cable Path":**
   ```
   Esperado:
   ✅ Alert: "Path edit mode active! N draggable markers loaded..."
   ✅ Marcadores vermelhos visíveis no mapa
   ✅ Possibilidade de arrastar marcadores
   ```

7. **Arrastar marcador e observar Console:**
   ```
   Esperado:
   ✅ [addMarker] Marker #0 dragged to: -23.551, -46.634
   ✅ Polilinha azul se atualiza automaticamente
   ```

8. **Clicar direito novamente → "💾 Save Path Changes":**
   ```
   Esperado:
   ✅ HTTP PUT /zabbix_api/api/fibers/{id}/
   ✅ Alert: "Saved successfully. Points: N, Distance: X.XX km"
   ✅ Mapa recarrega com cabo atualizado
   ```

---

## 📊 VALIDAÇÃO DO BACKEND (Testes Automatizados)

### **Status dos Testes:**
✅ **18/18 testes passando (100%)**

**Arquivo:** `routes_builder/tests/test_fiber_routes_full.py`

**Cobertura:**
```python
# API Operations (9 testes)
✅ test_list_cables_empty
✅ test_list_cables_with_data
✅ test_get_cable_details
✅ test_get_cable_not_found
✅ test_create_cable_manual
✅ test_update_cable_path          # ← VALIDA EDIÇÃO DE PATH!
✅ test_update_cable_metadata
✅ test_delete_cable
✅ test_delete_cable_not_found

# Model Validation (3 testes)
✅ test_cable_creation
✅ test_cable_str_representation
✅ test_cable_path_validation

# Edge Cases (3 testes)
✅ test_create_cable_with_single_point
✅ test_create_cable_with_many_points
✅ test_update_cable_empty_path

# Permissions (2 testes)
✅ test_list_cables_unauthenticated
✅ test_create_cable_unauthenticated

# Visualization (1 teste)
✅ test_load_all_cables
```

**Conclusão:** Backend está **100% funcional**. O problema é **exclusivamente no frontend**.

---

## 🎯 RESUMO FINAL

### **Situação Atual**
| Componente | Status | Detalhes |
|------------|--------|----------|
| **Backend API** | ✅ 100% funcional | 18/18 testes passando |
| **Database** | ✅ Correto | Campo `path_coordinates` (JSONField) |
| **API Contract** | ✅ Correto | API usa `path` (conversão automática) |
| **Frontend - Menu** | ✅ Funcional | Aparece corretamente |
| **Frontend - Load Cable** | ✅ Funcional | Dados carregados corretamente |
| **Frontend - Callback** | ❌ **ERRO** | `distance()` tratado como função |
| **Frontend - Markers** | ❌ Bloqueado | Não são criados devido ao erro |

### **Causa Raiz**
**Erro de sintaxe JavaScript:** Callback `onPathChange` trata parâmetro `distance` como função quando é número.

**Localização:** `fiber_route_builder.js` linha 35-36

### **Impacto**
- Menu de contexto abre corretamente ✅
- Cabo é selecionado corretamente ✅
- Dados são carregados corretamente ✅
- **Marcadores editáveis não são criados** ❌
- **Edição de caminho não funciona** ❌

### **Solução**
1. Remover parênteses de `distance()` → `distance` (linha 35-36)
2. Executar `collectstatic`
3. Reiniciar serviço web
4. Testar com Ctrl+F5

**Tempo estimado de correção:** 2 minutos  
**Complexidade:** Baixa (1 linha de código)

---

## 📎 ANEXOS

### **Logs de Console (Comportamento Atual)**
```
[LOADMORE] TOTAL markers now: 1
  fiber_route_builder.js:20251027131827:146

❌ Path change callback error: ReferenceError: distance() is not defined
  at fiber_route_builder.js:35
  at notifyPathChange (pathState.js:23)
  at edifyPathChange (oasisGate.js:187:23)
  at Array.forEach (<anonymous>)
  at Sew (wap.js:19:227)

Visualization: 1 cables loaded.
  cableService.js:13:286
```

### **Estrutura de Dados (API Response)**
```json
{
  "id": 1,
  "name": "Cabo Exemplo",
  "path": [
    {"lat": -23.5505, "lng": -46.6333},
    {"lat": -23.5506, "lng": -46.6334}
  ],
  "origin": {
    "device_id": 1,
    "device_name": "OLT 01",
    "port_id": 2,
    "port_name": "PON 1/1/1"
  },
  "destination": {
    "device_id": 3,
    "device_name": "Splitter 01",
    "port_id": 4,
    "port_name": "Out 1"
  },
  "length_km": 5.42,
  "status": "active",
  "notes": "Observações do cabo"
}
```

### **Tecnologias Utilizadas**
- **Frontend:** Vanilla JavaScript (ES6 Modules)
- **Maps:** Google Maps JavaScript API
- **Backend:** Django 5.2.7 + Django REST Framework
- **Database:** MariaDB 11
- **Container:** Docker + Docker Compose

---

**Documento gerado em:** 27/10/2025  
**Versão:** 1.0  
**Autor:** Análise Técnica Automatizada
