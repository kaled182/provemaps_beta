<template>
  <div class="network-design-page">
    <div class="map-container">
      <div id="builderMap" class="map-canvas" role="presentation"></div>
    </div>

    <section
      id="routePointsPanel"
      class="floating-panel"
      aria-labelledby="routePointsPanelTitle"
    >
      <div class="floating-panel__header">
        <div class="floating-panel__header-main">
          <h3 id="routePointsPanelTitle">Route points</h3>
          <div class="floating-panel__metric">
            Total distance: <span id="distanceKm">0.000</span> km
          </div>
        </div>
        <button
          id="toggleRoutePoints"
          type="button"
          class="panel-toggle-btn"
          aria-expanded="true"
          aria-controls="routePointsPanelBody"
        >
          <svg class="panel-toggle-icon" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M5.5 7.5L10 12l4.5-4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="sr-only">Collapse route points</span>
        </button>
      </div>
      <div id="routePointsPanelBody" class="floating-panel__body" aria-hidden="false">
        <p class="floating-panel__description">
          Drag points to reorder them or right-click the map to access additional options.
        </p>
        <ul id="pointsList" class="route-points-list"></ul>
        <div class="floating-panel__footer">
          <button
            id="manualCancelButton"
            type="button"
            class="footer-btn"
          >
            Cancel editing
          </button>
        </div>
      </div>
    </section>

    <section
      id="helpPanel"
      class="floating-panel help-panel"
      aria-labelledby="helpPanelTitle"
    >
      <div class="floating-panel__header">
        <h3 id="helpPanelTitle">Tips</h3>
        <button
          id="toggleHelp"
          type="button"
          class="panel-toggle-btn"
          aria-expanded="true"
          aria-controls="helpPanelBody"
        >
          <svg class="panel-toggle-icon" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M5.5 7.5L10 12l4.5-4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
          <span class="sr-only">Collapse tips</span>
        </button>
      </div>
      <div id="helpPanelBody" class="floating-panel__body" aria-hidden="false">
        <ul class="help-list">
          <li>
            <span class="help-index">1.</span>
            Click the map to add points. Drag markers to adjust their position or reorder them in the list.
          </li>
          <li>
            <span class="help-index">2.</span>
            Use the <span class="help-emphasis">context menu</span> (right-click) to save, edit, import from KML, or delete cables.
          </li>
          <li>
            <span class="help-index">3.</span>
            When editing, the selected cable is highlighted while the remaining cables stay visible with lower opacity.
          </li>
          <li>
            <span class="help-index">4.</span>
            Press
            <kbd class="help-shortcut">Esc</kbd>
            to quickly exit the current edit session.
          </li>
        </ul>
      </div>
    </section>

    <div id="contextMenu" class="hidden">
      <div id="contextCableInfo" class="hidden">
        <h3 class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Selected cable</h3>
        <p id="contextCableName">&mdash;</p>
      </div>

      <div id="contextGeneralOptions" class="space-y-2">
        <h3>Map actions</h3>
        <button id="contextLoadAll" type="button">
          <span id="contextLoadAllText">Reload all cables</span>
        </button>
        <button id="contextImportKML" type="button">Import route from KML</button>
      </div>

      <div id="contextSelectedOptions" class="hidden space-y-2 mt-3">
        <h3>Editing cable</h3>
        <button id="contextEditCable" type="button">Edit cable metadata</button>
        <button id="contextSavePath" type="button">Save updated path</button>
        <button id="contextCancelEdit" type="button">Cancel editing</button>
        <button id="contextDeleteCable" type="button" data-variant="danger">Delete cable</button>
      </div>

      <div id="contextCreatingOptions" class="hidden space-y-2 mt-3">
        <h3>New route</h3>
        <button id="contextSaveNewCable" type="button">Save as new cable</button>
        <button id="contextClearNew" type="button">Clear drawn points</button>
      </div>
    </div>

    <div id="toastHost" class="toast-host hidden"></div>
    <div id="confirmHost" class="confirm-host hidden"></div>

    <div id="manualSaveModal" class="modal-overlay opacity-0 pointer-events-none">
      <div id="manualSaveModalContent" class="modal-card opacity-0 scale-95">
        <button
          type="button"
          class="absolute top-4 right-4 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 text-2xl leading-none"
          @click="closeManualModal"
        >
          &times;
        </button>
        <h2 class="mb-1">Save cable manually</h2>
        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Link the drawn path to inventory devices and their monitored ports.
        </p>

        <div class="mb-4 rounded-lg bg-blue-50 border border-blue-100 px-4 py-3 text-sm text-blue-700">
          Current route distance: <span id="manualRouteDistance" class="font-semibold">0.000 km</span>
        </div>

        <form id="manualSaveForm" class="space-y-4">
          <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />

          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" for="manualRouteName">Cable name</label>
            <input
              id="manualRouteName"
              name="name"
              type="text"
              required
              placeholder="e.g. Confresa backbone"
              class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" for="manualOriginDeviceSelect">Origin device</label>
              <select
                id="manualOriginDeviceSelect"
                name="origin_device_id"
                required
                data-placeholder="Select..."
                class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select...</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" for="manualOriginPortSelect">Origin port</label>
              <select
                id="manualOriginPortSelect"
                name="origin_port_id"
                required
                class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select...</option>
              </select>
            </div>
          </div>

          <div class="flex items-center justify-between gap-3">
            <label for="manualSinglePortOnly" class="text-sm text-gray-700 dark:text-gray-300 select-none">Monitor origin port only</label>
            <input
              id="manualSinglePortOnly"
              name="single_port"
              type="checkbox"
              value="true"
              class="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
          </div>

          <div
            id="manualDestNotice"
            class="hidden rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-700"
          >
            Destination fields are disabled because only the origin port will be monitored.
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" for="manualDestDeviceSelect">Destination device</label>
              <select
                id="manualDestDeviceSelect"
                name="dest_device_id"
                required
                data-placeholder="Select..."
                class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select...</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1" for="manualDestPortSelect">Destination port</label>
              <select
                id="manualDestPortSelect"
                name="dest_port_id"
                required
                class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="">Select...</option>
              </select>
            </div>
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition" @click="closeManualModal">
              Cancel
            </button>
            <button type="submit" class="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition">
              Save
            </button>
          </div>
        </form>
      </div>
    </div>

    <div
      id="importKmlModal"
      class="fixed inset-0 flex items-center justify-center bg-black/50 opacity-0 pointer-events-none transition-opacity duration-300 z-50"
    >
      <div
        id="importKmlModalContent"
        class="modal-card rounded-lg shadow-lg w-full max-w-md p-6 relative transform scale-95 opacity-0 transition-all duration-300"
      >
        <button
          type="button"
          class="absolute top-2 right-2 text-gray-600 hover:text-black text-xl"
          @click="closeKmlModal"
        >
          &times;
        </button>

        <h2 class="text-xl font-semibold mb-4 text-gray-800 dark:text-white">Import route via KML</h2>

        <p class="text-sm text-gray-500 dark:text-gray-400 mb-4">
          Link the <span class="font-medium">.kml</span> file to monitored devices. You may monitor only the source port (one-way) or set different source and destination devices.
        </p>

        <div class="bg-gray-100 dark:bg-gray-800 rounded-md px-3 py-2 text-xs text-gray-600 dark:text-gray-400 mb-4">
          The file must include a <em>LineString</em> with the sequence of points (source -> destination) that represents the physical cable.
        </div>

        <form id="importKmlForm" enctype="multipart/form-data" class="space-y-3">
          <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />

          <div>
            <label class="block text-sm font-medium text-gray-700">Route name</label>
            <input
              type="text"
              name="name"
              required
              placeholder="Example: Backbone GYN -> BSB"
              class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring focus:ring-blue-300"
            />
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Source device</label>
            <select
              name="origin_device_id"
              id="kmlOriginDeviceSelect"
              required
              data-placeholder="Select..."
              class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring focus:ring-blue-300"
            >
              <option value="">Select...</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Source port</label>
            <select
              name="origin_port_id"
              id="kmlOriginPortSelect"
              required
              class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring focus:ring-blue-300"
            >
              <option value="">Select...</option>
            </select>
          </div>

          <div class="flex items-center justify-between gap-2">
            <label for="kmlSinglePortOnly" class="text-sm text-gray-700 select-none">Monitor source port only</label>
            <input
              type="checkbox"
              id="kmlSinglePortOnly"
              name="single_port"
              value="true"
              class="h-4 w-4 text-blue-600 border-gray-300 rounded"
            />
          </div>

          <div
            id="kmlDestNotice"
            class="hidden text-xs text-blue-700 bg-blue-50 border border-blue-200 rounded px-3 py-2"
          >
            Destination disabled: the route will only track the source port.
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Destination device</label>
            <select
              name="dest_device_id"
              id="kmlDestDeviceSelect"
              required
              data-placeholder="Select..."
              class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring focus:ring-blue-300"
            >
              <option value="">Select...</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">Destination port</label>
            <select
              name="dest_port_id"
              id="kmlDestPortSelect"
              required
              class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring focus:ring-blue-300"
            >
              <option value="">Select...</option>
            </select>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">KML file</label>
            <input
              type="file"
              name="kml_file"
              accept=".kml"
              required
              class="w-full border rounded-md px-3 py-2 focus:outline-none focus:ring focus:ring-blue-300"
            />
          </div>

          <div class="flex justify-end gap-2 pt-2">
            <button type="button" class="px-4 py-2 rounded-md bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition" @click="closeKmlModal">
              Cancel
            </button>
            <button type="submit" class="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 transition">
              Import route
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue';
import { initializeNetworkDesignApp } from '@/features/networkDesign/fiberRouteBuilder.js';
import { initializeKmlModal, cleanupKmlModal } from '@/features/networkDesign/partials/import_kml.js';

const csrfToken = ref(window.CSRF_TOKEN || '');

const ensureFiberGlobals = () => {
  if (!Array.isArray(window.__FIBER_DEVICE_OPTIONS)) {
    window.__FIBER_DEVICE_OPTIONS = [];
  }
};

const waitForKmlModal = async (retries = 5) => {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    const ready = await initializeKmlModal(attempt > 0);
    if (ready) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 120 * (attempt + 1)));
  }
  console.warn('[NetworkDesign] KML modal could not be initialized.');
  return false;
};

const closeManualModal = () => {
  if (typeof window.closeManualSaveModal === 'function') {
    window.closeManualSaveModal();
  }
};

const closeKmlModal = () => {
  if (typeof window.closeKmlModal === 'function') {
    window.closeKmlModal();
  }
};

onMounted(async () => {
  console.log('[NetworkDesignView] Component mounting...');
  document.title = 'Network Design | ProveMaps';

  // IMPORTANTE: Limpar elementos órfãos de reloads anteriores (F5)
  const orphanedElements = [
    'toastHost',
    'confirmHost',
    'contextMenu',
    'manualSaveModal',
    'importKmlModal'
  ];
  
  orphanedElements.forEach(id => {
    const bodyElement = document.body.querySelector(`#${id}`);
    if (bodyElement && bodyElement.parentElement === document.body) {
      console.log(`[NetworkDesignView] Removing orphaned element #${id} from document.body`);
      bodyElement.remove();
    }
  });

  ensureFiberGlobals();

  // IMPORTANTE: NetworkDesign refatorado para usar Provider Pattern
  // Funciona com qualquer provider configurado (Mapbox, Google Maps, etc.)
  try {
    console.log('[NetworkDesignView] Initializing map provider system...');
    
    // Pre-load provider antes de inicializar NetworkDesign
    const { getMapProvider, getCurrentProviderName } = await import('@/providers/maps/MapProviderFactory.js');
    
    const providerName = await getCurrentProviderName();
    console.log(`[NetworkDesignView] 🗺️ Configured provider: ${providerName}`);
    
    // Carregar provider (Google, Mapbox, etc.)
    const provider = await getMapProvider();
    
    if (!provider.isLoaded()) {
      throw new Error(`Provider ${providerName} failed to load`);
    }
    
    console.log(`[NetworkDesignView] ✅ ${providerName} provider ready`);
    
  } catch (error) {
    console.error('[NetworkDesignView] ❌ Failed to initialize map provider:', error);
    
    alert(
      `Erro ao inicializar sistema de mapas.\n\n` +
      `Detalhes: ${error.message}\n\n` +
      `Possíveis causas:\n` +
      `- Chave/token da API não configurado no sistema\n` +
      `- Problema de conexão com o serviço de mapas\n` +
      `- Provider de mapas não suportado\n\n` +
      `Configure em: Sistema > Configuração > Mapas\n\n` +
      `Por favor, recarregue a página (F5).`
    );
    return;
  }

  await nextTick();

  await waitForKmlModal();
  initializeNetworkDesignApp({ force: true });

  if (!csrfToken.value && window.CSRF_TOKEN) {
    csrfToken.value = window.CSRF_TOKEN;
  }
  
  console.log('[NetworkDesignView] Component mounted successfully');
});

onUnmounted(() => {
  console.log('[NetworkDesignView] Component unmounting, cleaning up...');
  
  closeKmlModal();
  cleanupKmlModal();
  
  // Call the comprehensive cleanup function
  if (typeof window.destroyNetworkDesignApp === 'function') {
    window.destroyNetworkDesignApp();
  } else if (typeof window.clearMapAndResetState === 'function') {
    window.clearMapAndResetState();
  }
  
  console.log('[NetworkDesignView] Cleanup complete.');
});
</script>

<style scoped>
:global(:root) {
  --nd-bg: #f9fafb;
  --nd-text: #111827;
  --nd-muted: #6b7280;
  --nd-panel-bg: #ffffff;
  --nd-panel-border: #e5e7eb;
  --nd-panel-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  --nd-panel-text: #111827;
  --nd-panel-muted: #6b7280;
  --nd-chip-bg: #dbeafe;
  --nd-chip-text: #1e40af;
  --nd-list-bg: #f9fafb;
  --nd-list-border: #e5e7eb;
  --nd-list-item-hover: #f3f4f6;
  --nd-btn-bg: #fef2f2;
  --nd-btn-border: #fecaca;
  --nd-btn-text: #b91c1c;
  --nd-help-emphasis: #b45309;
  --nd-shortcut-bg: #f3f4f6;
  --nd-shortcut-border: #d1d5db;
  --nd-context-bg: #ffffff;
  --nd-context-border: #e5e7eb;
  --nd-context-text: #111827;
  --nd-context-hover: #f3f4f6;
  --nd-modal-bg: #ffffff;
  --nd-modal-text: #111827;
  --nd-modal-muted: #6b7280;
  --nd-input-bg: #ffffff;
  --nd-input-border: #d1d5db;
}

.network-design-page {
  position: relative;
  height: 100%;
  width: 100%;
  overflow: hidden;
  color: var(--nd-text);
  background: var(--nd-bg);
}

:global(.dark),
:global([data-theme='dark']) {
  --nd-bg: #111827;
  --nd-text: #f9fafb;
  --nd-muted: #9ca3af;
  --nd-panel-bg: #1f2937;
  --nd-panel-border: #374151;
  --nd-panel-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
  --nd-panel-text: #f9fafb;
  --nd-panel-muted: #9ca3af;
  --nd-chip-bg: #1e3a8a;
  --nd-chip-text: #93c5fd;
  --nd-list-bg: #111827;
  --nd-list-border: #374151;
  --nd-list-item-hover: #374151;
  --nd-btn-bg: #7f1d1d;
  --nd-btn-border: #991b1b;
  --nd-btn-text: #fecaca;
  --nd-help-emphasis: #fbbf24;
  --nd-shortcut-bg: #374151;
  --nd-shortcut-border: #4b5563;
  --nd-context-bg: #1f2937;
  --nd-context-border: #374151;
  --nd-context-text: #f9fafb;
  --nd-context-hover: #374151;
  --nd-modal-bg: #1f2937;
  --nd-modal-text: #f9fafb;
  --nd-modal-muted: #9ca3af;
  --nd-input-bg: #111827;
  --nd-input-border: #374151;
}

.map-container {
  position: relative;
  height: 100%;
  width: 100%;
}

.map-canvas {
  height: 100%;
  width: 100%;
}

.floating-panel {
  position: absolute;
  right: 24px;
  width: min(360px, calc(100% - 48px));
  max-height: calc(100% - 160px);
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1.4rem;
  background: var(--nd-panel-bg);
  border-radius: 12px;
  border: 1px solid var(--nd-panel-border);
  box-shadow: var(--nd-panel-shadow);
  z-index: 35;
  color: var(--nd-panel-text);
  overflow: hidden;
  overflow-y: auto;
}

.floating-panel.collapsed {
  gap: 0;
  padding-bottom: 1rem;
}

#routePointsPanel {
  top: 104px;
}

.help-panel {
  top: auto;
  bottom: 32px;
}

.floating-panel h3 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--nd-panel-text);
  letter-spacing: 0.01em;
}

.floating-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.floating-panel__header-main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.floating-panel__metric {
  font-size: 0.82rem;
  color: var(--nd-panel-muted);
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  border: 1px solid var(--nd-panel-border);
  background: var(--nd-list-bg);
}

.panel-toggle-btn {
  border: 1px solid var(--nd-panel-border);
  background: var(--nd-chip-bg);
  color: var(--nd-panel-text);
  border-radius: 999px;
  height: 32px;
  width: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.panel-toggle-btn:hover {
  background: var(--nd-list-item-hover);
}

.panel-toggle-icon {
  width: 18px;
  height: 18px;
  transition: transform 0.2s ease;
}

.floating-panel.collapsed .panel-toggle-icon {
  transform: rotate(-90deg);
}

.floating-panel__body {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.floating-panel.collapsed .floating-panel__body {
  display: none;
}

.floating-panel__description {
  margin: 0;
  font-size: 0.85rem;
  color: var(--nd-panel-muted);
}

.route-points-list {
  list-style: none;
  margin: 0;
  padding: 0.75rem;
  border: 1px dashed var(--nd-list-border);
  border-radius: 16px;
  background: var(--nd-list-bg);
  flex: 1;
  overflow-y: auto;
}

.route-points-list li {
  padding: 0.45rem 0.6rem;
  border-radius: 0.65rem;
  font-size: 0.85rem;
  color: var(--nd-panel-text);
  cursor: grab;
  transition: background 0.2s ease, transform 0.2s ease;
}

.route-points-list li + li {
  margin-top: 0.45rem;
}

.route-points-list li.bg-blue-100 {
  background: rgba(37, 99, 235, 0.18);
}

.route-points-list li.bg-blue-50 {
  background: rgba(191, 219, 254, 0.4);
}

:global(.dark .network-design-page .route-points-list li.bg-blue-100),
:global([data-theme='dark'] .network-design-page .route-points-list li.bg-blue-100) {
  background: rgba(59, 130, 246, 0.35);
  color: #f8fafc;
}

:global(.dark .network-design-page .route-points-list li.bg-blue-50),
:global([data-theme='dark'] .network-design-page .route-points-list li.bg-blue-50) {
  background: rgba(191, 219, 254, 0.18);
  color: #f8fafc;
}

.floating-panel__footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}

.footer-btn {
  background: var(--nd-btn-bg);
  color: var(--nd-btn-text);
  border: 1px solid var(--nd-btn-border);
  border-radius: 999px;
  padding: 0.45rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.footer-btn:hover {
  background: rgba(248, 113, 113, 0.22);
  border-color: rgba(248, 113, 113, 0.45);
}

.help-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  font-size: 0.85rem;
  color: var(--nd-panel-muted);
}

.help-index {
  font-weight: 600;
  color: var(--nd-panel-text);
  margin-right: 0.5rem;
}

.help-emphasis {
  font-weight: 600;
  color: var(--nd-help-emphasis);
}

.help-shortcut {
  border: 1px solid var(--nd-shortcut-border);
  border-radius: 8px;
  padding: 0.15rem 0.4rem;
  background: var(--nd-shortcut-bg);
  color: var(--nd-panel-text);
  font-size: 0.75rem;
}

@media (max-width: 1024px) {
  .floating-panel {
    left: 24px;
    right: 24px;
    width: auto;
    max-height: 60vh;
  }

  #routePointsPanel {
    top: auto;
    bottom: calc(32px + 18vh);
  }

  .help-panel {
    bottom: 24px;
  }
}

.toast-host {
  position: fixed;
  top: 1.25rem;
  right: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  z-index: 60;
  pointer-events: none;
}

.toast-card {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  background: #111827;
  color: #f9fafb;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  box-shadow: 0 18px 48px rgba(15, 23, 42, 0.35);
  transition: opacity 0.16s ease;
  pointer-events: auto;
}

.toast-card.toast-success {
  border-left: 4px solid #22c55e;
}

.toast-card.toast-error {
  border-left: 4px solid #ef4444;
}

.toast-card.toast-warning {
  border-left: 4px solid #f97316;
}

.toast-card.toast-info {
  border-left: 4px solid #3b82f6;
}

.confirm-host {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 55;
  pointer-events: none;
}

.confirm-backdrop {
  position: absolute;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  pointer-events: auto;
}

.confirm-card {
  position: relative;
  background: var(--nd-modal-bg);
  padding: 1.5rem;
  border-radius: 1rem;
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.25);
  max-width: 420px;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  z-index: 1;
  pointer-events: auto;
  color: var(--nd-modal-text);
}

#contextMenu {
  width: 260px;
  background: var(--nd-context-bg);
  border-radius: 12px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
  padding: 1rem;
  color: var(--nd-context-text);
  border: 1px solid var(--nd-context-border);
}

#contextMenu.hidden {
  display: none;
}

#contextMenu h3 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--nd-context-text);
}

#contextMenu button {
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-radius: 0.6rem;
  transition: background-color 0.2s ease;
  font-size: 0.875rem;
  color: var(--nd-context-text);
}

#contextMenu button:hover {
  background-color: var(--nd-context-hover);
}

#contextMenu button[data-variant='danger'] {
  color: #dc2626;
}

:global(.dark) #contextMenu button[data-variant='danger'],
:global([data-theme='dark']) #contextMenu button[data-variant='danger'] {
  color: #f87171;
}

#contextMenu button[data-variant='danger']:hover {
  background-color: #fef2f2;
}

:global(.dark) #contextMenu button[data-variant='danger']:hover,
:global([data-theme='dark']) #contextMenu button[data-variant='danger']:hover {
  background-color: #7f1d1d;
}

#contextCableInfo {
  margin-bottom: 0.75rem;
  border-bottom: 1px solid var(--nd-context-border);
  padding-bottom: 0.75rem;
}

#contextCableName {
  font-weight: 600;
  font-size: 0.95rem;
  color: var(--nd-context-text);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(17, 24, 39, 0.75);
  z-index: 52;
  transition: opacity 0.3s ease;
}

:global(.dark) .modal-overlay,
:global([data-theme='dark']) .modal-overlay {
  background: rgba(0, 0, 0, 0.85);
}

.modal-card {
  background: var(--nd-modal-bg);
  border-radius: 0.75rem;
  width: 100%;
  max-width: 540px;
  padding: 1.5rem;
  position: relative;
  transition: opacity 0.3s ease, transform 0.3s ease;
  color: var(--nd-modal-text);
  border: 1px solid var(--nd-panel-border);
  box-shadow: var(--nd-panel-shadow);
}

.network-design-page .modal-card label {
  color: var(--nd-modal-text);
}

.network-design-page .modal-card p,
.network-design-page .modal-card .text-slate-500,
.network-design-page .modal-card .text-gray-500,
.network-design-page .modal-card .text-gray-600 {
  color: var(--nd-modal-muted);
}

.network-design-page .modal-card input,
.network-design-page .modal-card select,
.network-design-page .modal-card textarea {
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  border-color: var(--nd-input-border);
}

.network-design-page #importKmlModalContent {
  color: var(--nd-modal-text);
}

.network-design-page #importKmlModalContent h2 {
  color: var(--nd-modal-text);
}

.network-design-page #importKmlModalContent p,
.network-design-page #importKmlModalContent .text-gray-500,
.network-design-page #importKmlModalContent .text-gray-600,
.network-design-page #importKmlModalContent .text-gray-700 {
  color: var(--nd-modal-muted);
}

.network-design-page #importKmlModalContent input,
.network-design-page #importKmlModalContent select,
.network-design-page #importKmlModalContent textarea {
  background: var(--nd-input-bg);
  color: var(--nd-modal-text);
  border-color: var(--nd-input-border);
}

.network-design-page #importKmlModalContent .bg-gray-100 {
  background: var(--nd-list-bg);
}

.network-design-page .modal-card .bg-blue-50 {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1e40af;
}

:global(.dark) .network-design-page .modal-card .bg-blue-50,
:global([data-theme='dark']) .network-design-page .modal-card .bg-blue-50 {
  background: #1e3a8a;
  border-color: #1e40af;
  color: #93c5fd;
}

.opacity-0 {
  opacity: 0;
}

.opacity-100 {
  opacity: 1;
}

.pointer-events-none {
  pointer-events: none;
}

.scale-95 {
  transform: scale(0.95);
}

.scale-100 {
  transform: scale(1);
}
</style>
