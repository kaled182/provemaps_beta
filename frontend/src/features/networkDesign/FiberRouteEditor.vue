<template>
  <div class="flex h-screen overflow-hidden relative bg-gray-50">
    
    <!-- Área do Mapa (Esquerda - Expansível) -->
    <div class="flex-1 relative bg-gray-100 z-0">
      
      <UnifiedMapView
        ref="mapRef"
        :plugins="['drawing']"
        :plugin-options="pluginOptions"
        class="w-full h-full"
        @map-ready="onMapReady"
        @plugin-loaded="onPluginLoaded"
      />
      
      <!-- Toolbar Flutuante (Modo de Edição) -->
      <div class="absolute top-4 left-1/2 -translate-x-1/2 z-10 bg-white dark:bg-gray-800 rounded-full shadow-lg p-1.5 flex items-center gap-1 border border-gray-200 dark:border-gray-600 transition-transform duration-300 hover:scale-105">
        
        <button 
          @click="setMode('read')"
          class="px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-colors"
          :class="mode === 'read' ? 'bg-gray-800 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'"
        >
          <i class="fas fa-lock"></i> Visualizar
        </button>

        <button 
          @click="setMode('edit')"
          class="px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 transition-colors"
          :class="mode === 'edit' ? 'bg-indigo-600 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700'"
        >
          <i class="fas fa-pen"></i> Editar Traçado
        </button>

        <div class="w-px h-4 bg-gray-300 mx-1"></div>

        <label class="p-2 rounded-full text-gray-500 hover:bg-gray-100 hover:text-indigo-600 cursor-pointer" title="Importar KML">
          <input type="file" class="hidden" accept=".kml" @change="onKmlSelected" />
          <i class="fas fa-file-upload"></i>
        </label>
        
        <button class="p-2 rounded-full text-gray-500 hover:bg-gray-100 hover:text-indigo-600" title="Ferramentas de Medição">
          <i class="fas fa-ruler-combined"></i>
        </button>
      </div>

      <!-- Menu de Contexto (Right-Click) -->
      <transition name="fade">
        <div 
          v-if="contextMenu.show" 
          class="fixed z-50 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 w-56 py-1 overflow-hidden"
          :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
          @mouseleave="closeContextMenu"
        >
          <!-- Menu para Polyline (Adicionar Infraestrutura) -->
          <template v-if="contextMenu.type === 'polyline'">
            <div class="px-3 py-2 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
              <p class="text-[10px] font-bold text-gray-500 uppercase">Ações no Ponto</p>
            </div>
            
            <button class="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 flex items-center gap-3" @click="actionAddSlack">
              <i class="fas fa-infinity text-blue-500"></i> Adicionar Reserva
            </button>
            
            <button class="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 flex items-center gap-3" @click="actionAddSplice">
              <i class="fas fa-box text-orange-500"></i> Adicionar Caixa (CEO)
            </button>

            <div class="border-t border-gray-100 dark:border-gray-700 my-1"></div>
            
            <button class="w-full text-left px-4 py-2 text-xs hover:bg-red-50 text-red-600 flex items-center gap-3" @click="closeContextMenu">
              <i class="fas fa-times"></i> Cancelar
            </button>
          </template>

          <!-- Menu para Infrastructure (Gerenciar Ponto) -->
          <template v-else-if="contextMenu.type === 'infrastructure'">
            <div class="px-3 py-2 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
              <p class="text-[10px] font-bold text-gray-500 uppercase">{{ contextMenu.infrastructurePoint?.type_display }}</p>
              <p class="text-[10px] text-gray-400">{{ contextMenu.infrastructurePoint?.name || 'Sem nome' }}</p>
            </div>
            
            <button class="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 flex items-center gap-3" @click="actionViewInfraDetails">
              <i class="fas fa-info-circle text-blue-500"></i> Detalhes
            </button>
            
            <button class="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 flex items-center gap-3" @click="actionEditInfra">
              <i class="fas fa-edit text-indigo-500"></i> Alterar
            </button>
            
            <button 
              v-if="contextMenu.infrastructurePoint?.type === 'splice_box'"
              class="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 flex items-center gap-3" 
              @click="actionManageSplices"
            >
              <i class="fas fa-project-diagram text-purple-500"></i> Gerenciar Emendas
            </button>
            
            <button 
              v-if="contextMenu.infrastructurePoint?.type === 'slack'"
              class="w-full text-left px-4 py-2.5 text-sm hover:bg-indigo-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 flex items-center gap-3" 
              @click="actionConvertSlackToCEO"
            >
              <i class="fas fa-exchange-alt text-orange-500"></i> Converter em CEO
            </button>

            <div class="border-t border-gray-100 dark:border-gray-700 my-1"></div>
            
            <button class="w-full text-left px-4 py-2.5 text-sm hover:bg-red-50 dark:hover:bg-gray-700 text-red-600 flex items-center gap-3" @click="actionDeleteInfra">
              <i class="fas fa-trash"></i> Remover
            </button>
            
            <button class="w-full text-left px-4 py-2 text-xs hover:bg-gray-50 text-gray-500 flex items-center gap-3" @click="closeContextMenu">
              <i class="fas fa-times"></i> Cancelar
            </button>
          </template>
        </div>
      </transition>

      <!-- Loading Overlay -->
      <div v-if="loading" class="absolute inset-0 bg-white/90 dark:bg-gray-900/90 flex items-center justify-center z-20">
        <div class="text-center">
          <div class="animate-spin h-12 w-12 border-4 border-indigo-500 rounded-full border-t-transparent mx-auto mb-4"></div>
          <p class="text-gray-600 dark:text-gray-300">Carregando cabo...</p>
        </div>
      </div>

    </div>

    <!-- Sidebar Direito (Propriedades e Timeline) -->
    <EditorSidebar 
      :cable="cable" 
      :is-dirty="isDirty" 
      @save="saveChanges"
      @edit-infrastructure="openEditInfrastructureModal"
      @delete-infrastructure="confirmDeleteInfrastructure"
    />

    <!-- Modal de Edição de Infraestrutura -->
    <transition name="fade">
      <div v-if="editInfraModal.show" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="closeEditInfraModal">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
          <div class="p-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-gray-900 dark:to-gray-900">
            <h3 class="text-lg font-bold text-gray-900 dark:text-white">Editar Infraestrutura</h3>
            <p class="text-xs text-gray-500 mt-1">
              {{ editInfraModal.type === 'slack' ? 'Alterar tamanho da reserva técnica' : 'Alterar nome ou tipo do ponto' }}
            </p>
          </div>
          
          <div class="p-6 space-y-4">
            <!-- Nome (Não editável para Reserva Técnica) -->
            <div v-if="editInfraModal.type !== 'slack'">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Nome</label>
              <input 
                v-model="editInfraModal.name" 
                type="text" 
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white"
                placeholder="Ex: CEO-1234"
              />
            </div>
            
            <!-- Tamanho da Reserva (Apenas para slack) -->
            <div v-if="editInfraModal.type === 'slack'">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Tamanho da Reserva (metros)
              </label>
              <input 
                v-model.number="editInfraModal.slackLength" 
                type="number" 
                min="1"
                step="0.1"
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white"
                placeholder="Ex: 10"
              />
              <p class="text-xs text-gray-500 mt-1">
                Este valor será adicionado ao comprimento total do cabo
              </p>
            </div>
            
            <!-- Tipo (Não editável para Reserva Técnica - usar Converter) -->
            <div v-if="editInfraModal.type !== 'slack'">
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tipo</label>
              <select 
                v-model="editInfraModal.type" 
                class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white"
              >
                <option value="splice_box">Caixa de Emenda (CEO)</option>
                <option value="splitter_box">Caixa Splitter</option>
                <option value="transition">Transição</option>
              </select>
            </div>

            <div class="text-xs text-gray-500 bg-gray-50 dark:bg-gray-900 p-3 rounded-lg">
              <p><strong>Distância:</strong> {{ formatDistance(editInfraModal.distance) }}</p>
              <p class="mt-1 text-[10px] text-gray-400">A localização e distância não podem ser alteradas.</p>
            </div>
          </div>
          
          <div class="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3">
            <button 
              @click="closeEditInfraModal" 
              class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 font-medium"
            >
              Cancelar
            </button>
            <button 
              @click="saveInfrastructureChanges" 
              class="flex-1 px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 font-medium"
            >
              Salvar
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Modal de Notificação Padronizado -->
    <transition name="fade">
      <div v-if="notification.show" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" @click.self="closeNotification">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
          <!-- Header com cor baseada no tipo -->
          <div 
            class="p-6 border-b border-gray-200 dark:border-gray-700"
            :class="{
              'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30': notification.type === 'success',
              'bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/30 dark:to-rose-900/30': notification.type === 'error',
              'bg-gradient-to-r from-yellow-50 to-amber-50 dark:from-yellow-900/30 dark:to-amber-900/30': notification.type === 'warning',
              'bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30': notification.type === 'info'
            }"
          >
            <div class="flex items-center gap-3">
              <div 
                class="w-10 h-10 rounded-full flex items-center justify-center"
                :class="{
                  'bg-green-100 dark:bg-green-800': notification.type === 'success',
                  'bg-red-100 dark:bg-red-800': notification.type === 'error',
                  'bg-yellow-100 dark:bg-yellow-800': notification.type === 'warning',
                  'bg-blue-100 dark:bg-blue-800': notification.type === 'info'
                }"
              >
                <i 
                  class="text-lg"
                  :class="{
                    'fas fa-check-circle text-green-600 dark:text-green-400': notification.type === 'success',
                    'fas fa-exclamation-circle text-red-600 dark:text-red-400': notification.type === 'error',
                    'fas fa-exclamation-triangle text-yellow-600 dark:text-yellow-400': notification.type === 'warning',
                    'fas fa-info-circle text-blue-600 dark:text-blue-400': notification.type === 'info'
                  }"
                ></i>
              </div>
              <div class="flex-1">
                <h3 class="text-lg font-bold text-gray-900 dark:text-white">{{ notification.title }}</h3>
              </div>
            </div>
          </div>
          
          <div class="p-6">
            <p class="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-line">{{ notification.message }}</p>
          </div>
          
          <div class="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3">
            <button 
              v-if="notification.confirmAction"
              @click="closeNotification" 
              class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 font-medium"
            >
              Cancelar
            </button>
            <button 
              @click="notification.confirmAction ? executeConfirmAction() : closeNotification()" 
              class="px-4 py-2 rounded-lg font-medium"
              :class="{
                'flex-1': notification.confirmAction,
                'w-full': !notification.confirmAction,
                'bg-green-600 hover:bg-green-700 text-white': notification.type === 'success',
                'bg-red-600 hover:bg-red-700 text-white': notification.type === 'error' || notification.confirmAction,
                'bg-yellow-600 hover:bg-yellow-700 text-white': notification.type === 'warning',
                'bg-indigo-600 hover:bg-indigo-700 text-white': notification.type === 'info' && !notification.confirmAction
              }"
            >
              {{ notification.confirmAction ? 'Confirmar' : 'OK' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Modal de Input Genérico (para prompts) -->
    <transition name="fade">
      <div v-if="inputModal.show" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/50" @click.self="closeInputModal">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
          <div class="p-6 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-indigo-50 to-blue-50 dark:from-gray-900 dark:to-gray-900">
            <h3 class="text-lg font-bold text-gray-900 dark:text-white">{{ inputModal.title }}</h3>
          </div>
          
          <div class="p-6">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {{ inputModal.label }}
            </label>
            <input 
              v-model="inputModal.value"
              :type="inputModal.type"
              :placeholder="inputModal.placeholder"
              class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-indigo-500 dark:bg-gray-700 dark:text-white"
              @keyup.enter="executeInputAction"
            />
          </div>
          
          <div class="p-6 border-t border-gray-200 dark:border-gray-700 flex gap-3">
            <button 
              @click="closeInputModal" 
              class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 font-medium"
            >
              Cancelar
            </button>
            <button 
              @click="executeInputAction" 
              class="flex-1 px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 font-medium"
            >
              Confirmar
            </button>
          </div>
        </div>
      </div>
    </transition>

    <!-- Modal de Gerenciamento de Fusões -->
    <SpliceMatrixModal
      :show="spliceModal.show"
      :infra-point="spliceModal.infraPoint"
      @close="closeSpliceModal"
    />

  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue';
import { useRoute } from 'vue-router';
import { useApi } from '@/composables/useApi';
import UnifiedMapView from '@/components/Map/UnifiedMapView.vue';
import EditorSidebar from './components/EditorSidebar.vue';
import SpliceMatrixModal from '@/components/Fusion/SpliceMatrixModal.vue';

const route = useRoute();
const api = useApi();
const id = route.params.id;

// State
const loading = ref(true);
const cable = ref({});
const mapRef = ref(null);
const pathStats = ref(null);
const mapInstance = ref(null);
const drawingPlugin = ref(null);
const editInfraModal = reactive({
  show: false,
  id: null,
  name: '',
  type: '',
  distance: 0,
  slackLength: 0, // Tamanho da reserva técnica
  originalType: '' // Para detectar mudanças de tipo
});
const mode = ref('read'); // 'read' | 'edit'
const isDirty = ref(false);
const infrastructureMarkers = ref([]); // Marcadores de infraestrutura

// Notification System
const notification = reactive({
  show: false,
  title: '',
  message: '',
  type: 'info', // 'success' | 'error' | 'warning' | 'info'
  confirmAction: null // Para modais de confirmação
});

// Input Modal System
const inputModal = reactive({
  show: false,
  title: '',
  label: '',
  value: '',
  placeholder: '',
  type: 'text', // 'text' | 'number'
  submitAction: null
});

// Splice Matrix Modal
const spliceModal = reactive({
  show: false,
  infraPoint: null
});

// Context Menu (Polyline + Infrastructure)
const contextMenu = reactive({
  show: false,
  x: 0,
  y: 0,
  latlng: null,
  type: null, // 'polyline' | 'infrastructure'
  infrastructurePoint: null // Dados do ponto clicado
});

// Plugin Options
const pluginOptions = {
  drawing: {
    editable: true, // SEMPRE editável para permitir arrastar markers
    onPathChange: (coords, distance) => {
      pathStats.value = {
        points: coords.length,
        distance: (distance / 1000).toFixed(2)
      };
      
      // Atualiza cable.length em tempo real para sidebar
      cable.value.length = distance;
      isDirty.value = true;
    }
  }
};

const canSave = computed(() => {
  return pathStats.value && pathStats.value.points >= 2 && isDirty.value;
});

const getDrawing = () => drawingPlugin.value;

// Map Events
const onMapReady = (map) => {
  mapInstance.value = map;
  console.log('[FiberRouteEditor] Map ready');
  
  // NÃO adiciona listener no mapa - será adicionado na polyline
};

const onPluginLoaded = async (pluginName, plugin) => {
  if (pluginName === 'drawing') {
    drawingPlugin.value = plugin;
    console.log('[FiberRouteEditor] Drawing plugin loaded');
    await loadCableData();
  }
};

// Load Cable Data
const loadCableData = async () => {
  try {
    const data = await api.get(`/api/v1/fiber-cables/${id}/`);
    cable.value = data;
    console.log('[FiberRouteEditor] Cable data loaded', data);

    const drawing = getDrawing();
    if (!drawing) {
      console.warn('[FiberRouteEditor] Drawing plugin not available');
      return;
    }

    // Carregar path existente
    const path = Array.isArray(data.path_coordinates) ? data.path_coordinates : [];
    if (path.length >= 2) {
      console.log('[FiberRouteEditor] Loading existing path', path.length, 'points');
      drawing.setPath(path);
      drawing.fitBounds();
      
      // Adicionar listener de right-click na polyline
      const polyline = drawing.getPolyline();
      if (polyline) {
        polyline.addListener('rightclick', handlePolylineRightClick);
        console.log('[FiberRouteEditor] Right-click listener added to polyline');
      }
      
      // Inicializar stats
      pathStats.value = {
        points: path.length,
        distance: (drawing.getDistance() / 1000).toFixed(2)
      };
    } else {
      // Centralizar entre Site A e B
      const locA = data.site_a_location;
      const locB = data.site_b_location;
      if (locA && locB && mapInstance.value) {
        console.log('[FiberRouteEditor] Centering on sites', locA, locB);
        const bounds = new google.maps.LatLngBounds();
        bounds.extend(new google.maps.LatLng(locA.lat, locA.lng));
        bounds.extend(new google.maps.LatLng(locB.lat, locB.lng));
        mapInstance.value.fitBounds(bounds);
        
        // Desenhar linha guia tracejada
        new google.maps.Polyline({
          path: [locA, locB],
          map: mapInstance.value,
          strokeColor: '#9CA3AF',
          strokeOpacity: 0.6,
          strokeWeight: 2,
          geodesic: true,
          icons: [{
            icon: { path: 'M 0,-1 0,1', strokeOpacity: 1, scale: 2 },
            offset: '0',
            repeat: '20px'
          }]
        });
      }
    }
    
    // Renderizar pontos de infraestrutura existentes
    renderInfrastructureMarkers();
    
    // Inicia em modo read (seguro)
    setMode('read');
  } catch (err) {
    console.error('[FiberRouteEditor] Erro ao carregar cabo', err);
    showNotification(
      'Erro ao Carregar',
      err?.response?.data?.detail || err?.message || 'Erro ao carregar dados do cabo.',
      'error'
    );
  } finally {
    loading.value = false;
  }
};

// Renderizar marcadores de infraestrutura no mapa
const renderInfrastructureMarkers = () => {
  // Limpar marcadores antigos
  infrastructureMarkers.value.forEach(marker => marker.setMap(null));
  infrastructureMarkers.value = [];
  
  const points = cable.value.infrastructure_points || [];
  if (!mapInstance.value || points.length === 0) return;
  
  console.log('[FiberRouteEditor] Rendering', points.length, 'infrastructure markers');
  
  points.forEach(point => {
    if (!point.location || !point.location.coordinates) return;
    
    const [lng, lat] = point.location.coordinates;
    
    // Definir cor e ícone baseado no tipo
    let color, icon;
    switch(point.type) {
      case 'slack':
        color = '#3b82f6'; // azul
        icon = google.maps.SymbolPath.CIRCLE;
        break;
      case 'splice_box':
        color = '#f97316'; // laranja
        icon = google.maps.SymbolPath.BACKWARD_CLOSED_ARROW;
        break;
      case 'splitter_box':
        color = '#a855f7'; // roxo
        icon = google.maps.SymbolPath.FORWARD_CLOSED_ARROW;
        break;
      default:
        color = '#6b7280'; // cinza
        icon = google.maps.SymbolPath.CIRCLE;
    }
    
    const marker = new google.maps.Marker({
      position: { lat, lng },
      map: mapInstance.value,
      icon: {
        path: icon,
        fillColor: color,
        fillOpacity: 0.9,
        strokeColor: '#fff',
        strokeWeight: 2,
        scale: point.type === 'slack' ? 8 : 5,
        rotation: point.type === 'splice_box' ? 180 : 0
      },
      title: `${point.name || point.type_display} @ ${point.distance_from_origin?.toFixed(1)}m`,
      zIndex: 1000
    });
    
    // Adicionar listener de clique direito no marcador
    marker.addListener('rightclick', (event) => {
      if (mode.value !== 'edit') return;
      
      event.domEvent.preventDefault();
      
      contextMenu.x = event.domEvent.clientX;
      contextMenu.y = event.domEvent.clientY;
      contextMenu.latlng = event.latLng;
      contextMenu.type = 'infrastructure';
      contextMenu.infrastructurePoint = point;
      contextMenu.show = true;
      
      console.log('[FiberRouteEditor] Right-click on infrastructure', point);
    });
    
    infrastructureMarkers.value.push(marker);
  });
};

// Mode Control (Read/Edit)
const setMode = (newMode) => {
  mode.value = newMode;
  const drawing = getDrawing();
  
  if (!drawing) return;
  
  if (newMode === 'edit') {
    drawing.startDrawing();
    console.log('[FiberRouteEditor] Edit mode enabled');
  } else {
    drawing.stopDrawing();
    console.log('[FiberRouteEditor] Read mode (locked)');
  }
};

// Context Menu (Right-Click)
const handlePolylineRightClick = (event) => {
  if (mode.value !== 'edit') return; // Só abre menu se estiver editando
  
  event.domEvent.preventDefault();
  
  contextMenu.x = event.domEvent.clientX;
  contextMenu.y = event.domEvent.clientY;
  contextMenu.latlng = event.latLng;
  contextMenu.type = 'polyline';
  contextMenu.infrastructurePoint = null;
  contextMenu.show = true;
  
  console.log('[FiberRouteEditor] Right-click on polyline', event.latLng.lat(), event.latLng.lng());
};

const handleMapRightClick = (event) => {
  // Fallback caso o listener da polyline não funcione
  if (mode.value !== 'edit') return;
  
  event.domEvent.preventDefault();
  
  contextMenu.x = event.domEvent.clientX;
  contextMenu.y = event.domEvent.clientY;
  contextMenu.latlng = event.latLng;
  contextMenu.type = 'polyline';
  contextMenu.infrastructurePoint = null;
  contextMenu.show = true;
};

const closeContextMenu = () => {
  contextMenu.show = false;
  contextMenu.type = null;
  contextMenu.infrastructurePoint = null;
};

// Context Menu Actions - Criar Infraestrutura
const actionAddSlack = async () => {
  const lat = contextMenu.latlng.lat();
  const lng = contextMenu.latlng.lng();
  console.log('[FiberRouteEditor] Add Slack at', lat, lng);
  
  const createSlackAction = async (slackLengthStr) => {
    const slackLength = parseFloat(slackLengthStr);
    if (isNaN(slackLength) || slackLength <= 0) {
      showNotification(
        'Tamanho Inválido',
        'Informe um número positivo para o tamanho da reserva.',
        'error'
      );
      return;
    }
    
    try {
      const result = await api.post('/api/v1/inventory/infrastructure/', {
        cable: id,
        type: 'slack',
        name: '',
        lat,
        lng,
        metadata: { slack_length: slackLength }
      });
      
      console.log('[FiberRouteEditor] Infrastructure created', result);
      
      // Recarregar dados do cabo para atualizar sidebar e marcadores
      await loadCableData();
      
      showNotification(
        'Reserva Técnica Criada!',
        `Tamanho: ${slackLength}m\nMetragem: ${result.distance_from_origin?.toFixed(1)}m`,
        'success'
      );
    } catch (err) {
      console.error('[FiberRouteEditor] Erro ao criar infraestrutura', err);
      showNotification(
        'Erro ao Criar',
        err?.response?.data?.detail || err?.message || 'Erro ao criar ponto de infraestrutura.',
        'error'
      );
    }
  };
  
  closeContextMenu();
  showInputModal(
    'Criar Reserva Técnica',
    'Tamanho da Reserva (metros)',
    'Ex: 10',
    '10',
    'number',
    createSlackAction
  );
};

const actionAddSplice = async () => {
  const lat = contextMenu.latlng.lat();
  const lng = contextMenu.latlng.lng();
  console.log('[FiberRouteEditor] Add Splice Box at', lat, lng);
  
  const createCEOAction = async (name) => {
    if (!name || !name.trim()) {
      showNotification(
        'Nome Obrigatório',
        'Informe um nome para a Caixa de Emenda.',
        'error'
      );
      return;
    }
    
    try {
      const result = await api.post('/api/v1/inventory/infrastructure/', {
        cable: id,
        type: 'splice_box',
        name: name.trim(),
        lat,
        lng,
        metadata: {}
      });
      
      console.log('[FiberRouteEditor] Infrastructure created', result);
      
      await loadCableData();
      
      showNotification(
        'Caixa de Emenda Criada!',
        `${name}\nMetragem: ${result.distance_from_origin?.toFixed(1)}m\n(+20m adicionados ao cabo)`,
        'success'
      );
    } catch (err) {
      console.error('[FiberRouteEditor] Erro ao criar infraestrutura', err);
      showNotification(
        'Erro ao Criar',
        err?.response?.data?.detail || err?.message || 'Erro ao criar ponto de infraestrutura.',
        'error'
      );
    }
  };
  
  closeContextMenu();
  showInputModal(
    'Criar Caixa de Emenda (CEO)',
    'Nome da Caixa',
    'Ex: CEO-1234',
    'CEO-' + Date.now().toString().slice(-4),
    'text',
    createCEOAction
  );
};

// Save Changes
const saveChanges = async () => {
  const drawing = getDrawing();
  if (!drawing) {
    showNotification(
      'Plugin Indisponível',
      'O plugin de desenho não está disponível.',
      'error'
    );
    return;
  }
  
  const path = drawing.getPathCoordinates() || [];
  if (path.length < 2) {
    showNotification(
      'Traçado Incompleto',
      'É necessário desenhar pelo menos 2 pontos.',
      'warning'
    );
    return;
  }
  
  try {
    console.log('[FiberRouteEditor] Saving path', path.length, 'points');
    const result = await api.post(`/api/v1/fiber-cables/${id}/update-path/`, { path });
    console.log('[FiberRouteEditor] Path saved', result);
    
    // Atualizar dados locais
    cable.value.length_km = result.length_km;
    cable.value.path_coordinates = result.path;
    isDirty.value = false;
    
    // Voltar para modo read (seguro)
    setMode('read');
    
    showNotification(
      'Traçado Salvo!',
      `${result.points} pontos\n${result.length_km} km`,
      'success'
    );
  } catch (err) {
    console.error('[FiberRouteEditor] Erro ao salvar traçado', err);
    showNotification(
      'Erro ao Salvar',
      err?.response?.data?.detail || err?.message || 'Erro ao salvar traçado.',
      'error'
    );
  }
};

// Notification System
const showNotification = (title, message, type = 'info', confirmAction = null) => {
  notification.title = title;
  notification.message = message;
  notification.type = type;
  notification.confirmAction = confirmAction;
  notification.show = true;
};

const closeNotification = () => {
  notification.show = false;
  notification.confirmAction = null;
};

const executeConfirmAction = async () => {
  if (notification.confirmAction) {
    await notification.confirmAction();
  }
  closeNotification();
};

// Input Modal System
const showInputModal = (title, label, placeholder = '', defaultValue = '', type = 'text', submitAction = null) => {
  inputModal.title = title;
  inputModal.label = label;
  inputModal.placeholder = placeholder;
  inputModal.value = defaultValue;
  inputModal.type = type;
  inputModal.submitAction = submitAction;
  inputModal.show = true;
};

const closeInputModal = () => {
  inputModal.show = false;
  inputModal.submitAction = null;
  inputModal.value = '';
};

const executeInputAction = async () => {
  if (inputModal.submitAction) {
    await inputModal.submitAction(inputModal.value);
  }
  closeInputModal();
};

// Infrastructure Management
const openEditInfrastructureModal = (point) => {
  editInfraModal.show = true;
  editInfraModal.id = point.id;
  editInfraModal.name = point.name || '';
  editInfraModal.type = point.type;
  editInfraModal.originalType = point.type;
  editInfraModal.distance = point.distance_from_origin;
  editInfraModal.slackLength = point.metadata?.slack_length || 0;
};

const closeEditInfraModal = () => {
  editInfraModal.show = false;
  editInfraModal.id = null;
  editInfraModal.name = '';
  editInfraModal.type = '';
  editInfraModal.originalType = '';
  editInfraModal.distance = 0;
  editInfraModal.slackLength = 0;
};

const saveInfrastructureChanges = async () => {
  try {
    let payload = {};
    
    // Se for Reserva Técnica, atualizar apenas slack_length
    if (editInfraModal.type === 'slack') {
      if (!editInfraModal.slackLength || editInfraModal.slackLength <= 0) {
        showNotification(
          'Tamanho Inválido',
          'O tamanho da reserva técnica deve ser maior que zero.',
          'error'
        );
        return;
      }
      payload = {
        metadata: { slack_length: editInfraModal.slackLength }
      };
    } else {
      // Para outros tipos, atualizar nome e tipo
      payload = {
        name: editInfraModal.name,
        type: editInfraModal.type
      };
    }
    
    const result = await api.patch(`/api/v1/inventory/infrastructure/${editInfraModal.id}/`, payload);
    
    console.log('[FiberRouteEditor] Infrastructure updated', result);
    
    // Recarregar dados para atualizar sidebar e mapa
    await loadCableData();
    closeEditInfraModal();
    
    showNotification(
      'Sucesso!',
      'Infraestrutura atualizada com sucesso.',
      'success'
    );
  } catch (err) {
    console.error('[FiberRouteEditor] Erro ao atualizar infraestrutura', err);
    showNotification(
      'Erro ao Atualizar',
      err?.response?.data?.detail || err?.message || 'Erro ao atualizar infraestrutura.',
      'error'
    );
  }
};

const confirmDeleteInfrastructure = async (point) => {
  const deleteAction = async () => {
    try {
      await api.delete(`/api/v1/inventory/infrastructure/${point.id}/delete/`);
      
      console.log('[FiberRouteEditor] Infrastructure deleted', point.id);
      
      // Recarregar dados para atualizar sidebar e mapa
      await loadCableData();
      
      showNotification(
        'Sucesso!',
        'Infraestrutura removida com sucesso.',
        'success'
      );
    } catch (err) {
      console.error('[FiberRouteEditor] Erro ao excluir infraestrutura', err);
      showNotification(
        'Erro ao Remover',
        err?.response?.data?.detail || err?.message || 'Erro ao excluir infraestrutura.',
        'error'
      );
    }
  };
  
  showNotification(
    'Confirmar Exclusão',
    `Tem certeza que deseja excluir "${point.name || point.type_display}"?\n\nEsta ação não pode ser desfeita.`,
    'warning',
    deleteAction
  );
};

// Helper para formatar distância
const formatDistance = (meters) => {
  if (!meters && meters !== 0) return '?';
  return meters >= 1000 ? `${(meters/1000).toFixed(2)}km` : `${Math.round(meters)}m`;
};

// Infrastructure Context Menu Actions
const actionViewInfraDetails = () => {
  const point = contextMenu.infrastructurePoint;
  if (!point) return;
  
  const details = [
    `Tipo: ${point.type_display}`,
    `Nome: ${point.name || '(sem nome)'}`,
    `Metragem: ${formatDistance(point.distance_from_origin)}`,
  ];
  
  if (point.type === 'slack' && point.metadata?.slack_length) {
    details.push(`Tamanho Reserva: ${point.metadata.slack_length}m`);
  }
  
  if (point.type === 'splice_box') {
    details.push(`CEO adiciona 20m ao cabo`);
  }
  
  closeContextMenu();
  showNotification(
    point.type_display,
    details.join('\n'),
    'info'
  );
};

const actionEditInfra = () => {
  const point = contextMenu.infrastructurePoint;
  if (!point) return;
  
  openEditInfrastructureModal(point);
  closeContextMenu();
};

const actionDeleteInfra = async () => {
  const point = contextMenu.infrastructurePoint;
  if (!point) return;
  
  closeContextMenu();
  await confirmDeleteInfrastructure(point);
};

const actionConvertSlackToCEO = async () => {
  const point = contextMenu.infrastructurePoint;
  if (!point || point.type !== 'slack') return;
  
  const convertAction = async () => {
    try {
      const result = await api.patch(`/api/v1/inventory/infrastructure/${point.id}/`, {
        type: 'splice_box'
      });
      
      console.log('[FiberRouteEditor] Converted slack to CEO', result);
      
      await loadCableData();
      
      showNotification(
        'Conversão Concluída!',
        'Reserva Técnica convertida em CEO com sucesso.',
        'success'
      );
    } catch (err) {
      console.error('[FiberRouteEditor] Erro ao converter', err);
      showNotification(
        'Erro na Conversão',
        err?.response?.data?.detail || err?.message || 'Erro ao converter infraestrutura.',
        'error'
      );
    }
  };
  
  closeContextMenu();
  
  const confirmMsg = `Converter "${point.name || 'Reserva Técnica'}" em Caixa de Emenda (CEO)?\n\n` +
    `- Remove o tamanho da reserva\n` +
    `- Adiciona 20m padrão de CEO ao cabo\n` +
    `- Permite gerenciar emendas/fusões`;
  
  showNotification(
    'Confirmar Conversão',
    confirmMsg,
    'warning',
    convertAction
  );
};

const actionManageSplices = () => {
  const point = contextMenu.infrastructurePoint;
  if (!point || point.type !== 'splice_box') return;
  
  closeContextMenu();
  
  // Abrir modal de gerenciamento de fusões
  console.debug('[FiberRouteEditor] Abrindo modal de emendas para infraestrutura id:', point.id, 'nome:', point.name);
  spliceModal.infraPoint = point;
  spliceModal.show = true;
  // Forçar re-render debug
  setTimeout(() => {
    console.debug('[FiberRouteEditor] Modal estado show:', spliceModal.show, 'infraPoint.id:', spliceModal.infraPoint?.id)
  }, 50)
};

const closeSpliceModal = () => {
  spliceModal.show = false;
  spliceModal.infraPoint = null;
};

// KML Import
const onKmlSelected = async (evt) => {
  const file = evt.target.files?.[0];
  if (!file) return;
  
  evt.target.value = ''; // Reset input
  
  try {
    console.log('[FiberRouteEditor] Importing KML', file.name);
    const formData = new FormData();
    formData.append('kml', file);
    
    const result = await api.postFormData(`/api/v1/fiber-cables/${id}/import-kml/`, formData);
    console.log('[FiberRouteEditor] KML imported', result);
    
    const drawing = getDrawing();
    if (drawing && result.path && result.path.length > 0) {
      drawing.clearPath();
      drawing.setPath(result.path);
      drawing.fitBounds();
      
      // Atualizar stats
      pathStats.value = {
        points: result.points,
        distance: result.length_km
      };
      cable.value.length = result.length_km * 1000; // metros
      isDirty.value = true;
      
      showNotification(
        'KML Importado!',
        `${result.points} pontos\n${result.length_km} km`,
        'success'
      );
    } else {
      showNotification(
        'Aviso',
        'KML importado mas sem coordenadas válidas.',
        'warning'
      );
    }
  } catch (err) {
    console.error('[FiberRouteEditor] Falha ao importar KML', err);
    showNotification(
      'Erro ao Importar KML',
      err?.response?.data?.detail || err?.message || 'Falha ao importar KML.',
      'error'
    );
  }
};
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { 
  transition: opacity 0.2s; 
}
.fade-enter-from, .fade-leave-to { 
  opacity: 0; 
}
</style>
