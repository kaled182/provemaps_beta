<template>
  <div class="network-design-page">
    <div class="map-container">
      <div class="map-toolbar" aria-label="Network design tools">
        <button id="toggleRoutePoints" type="button" class="toolbar-btn">Route points</button>
        <button id="toggleHelp" type="button" class="toolbar-btn">Help tips</button>
      </div>
      <div id="builderMap" class="map-canvas" role="presentation"></div>
    </div>

    <section
      id="routePointsPanel"
      class="floating-panel hidden"
      aria-labelledby="routePointsPanelTitle"
    >
      <div class="floating-panel__header">
        <h3 id="routePointsPanelTitle">Route points</h3>
        <div class="floating-panel__metric">
          Total distance: <span id="distanceKm">0.000</span> km
        </div>
      </div>
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
    </section>

    <section
      id="helpPanel"
      class="floating-panel hidden help-panel"
      aria-labelledby="helpPanelTitle"
    >
      <h3 id="helpPanelTitle">Tips</h3>
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
    </section>

    <div id="contextMenu" class="hidden">
      <div id="contextCableInfo" class="hidden">
        <h3 class="text-xs uppercase tracking-wide text-slate-500">Selected cable</h3>
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
          class="absolute top-4 right-4 text-slate-400 hover:text-slate-600 text-2xl leading-none"
          @click="closeManualModal"
        >
          &times;
        </button>
        <h2 class="mb-1">Save cable manually</h2>
        <p class="text-sm text-slate-500 mb-4">
          Link the drawn path to inventory devices and their monitored ports.
        </p>

        <div class="mb-4 rounded-lg bg-blue-50 border border-blue-100 px-4 py-3 text-sm text-blue-700">
          Current route distance: <span id="manualRouteDistance" class="font-semibold">0.000 km</span>
        </div>

        <form id="manualSaveForm" class="space-y-4">
          <input type="hidden" name="csrfmiddlewaretoken" :value="csrfToken" />

          <div>
            <label class="block text-sm font-medium text-slate-700 mb-1" for="manualRouteName">Cable name</label>
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
              <label class="block text-sm font-medium text-slate-700 mb-1" for="manualOriginDeviceSelect">Origin device</label>
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
              <label class="block text-sm font-medium text-slate-700 mb-1" for="manualOriginPortSelect">Origin port</label>
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
            <label for="manualSinglePortOnly" class="text-sm text-slate-700 select-none">Monitor origin port only</label>
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
              <label class="block text-sm font-medium text-slate-700 mb-1" for="manualDestDeviceSelect">Destination device</label>
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
              <label class="block text-sm font-medium text-slate-700 mb-1" for="manualDestPortSelect">Destination port</label>
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
            <button type="button" class="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 transition" @click="closeManualModal">
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
        class="bg-white rounded-lg shadow-lg w-full max-w-md p-6 relative transform scale-95 opacity-0 transition-all duration-300"
      >
        <button
          type="button"
          class="absolute top-2 right-2 text-gray-600 hover:text-black text-xl"
          @click="closeKmlModal"
        >
          &times;
        </button>

        <h2 class="text-xl font-semibold mb-4 text-gray-800">Import route via KML</h2>

        <p class="text-sm text-gray-500 mb-4">
          Link the <span class="font-medium">.kml</span> file to monitored devices. You may monitor only the source port (one-way) or set different source and destination devices.
        </p>

        <div class="bg-gray-100 rounded-md px-3 py-2 text-xs text-gray-600 mb-4">
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
            <button type="button" class="px-4 py-2 rounded-md bg-gray-200 hover:bg-gray-300 transition" @click="closeKmlModal">
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
import { waitForGoogleMaps } from '@/utils/googleMapsLoader';

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

  // Aguarda Google Maps estar disponível
  // Tenta carregar se ainda não foi carregado (fallback do router guard)
  try {
    console.log('[NetworkDesignView] Checking Google Maps availability...');
    
    // Se Google Maps já está disponível, usa imediatamente
    if (window.google?.maps) {
      console.log('[NetworkDesignView] ✅ Google Maps already available!');
    } else {
      // Tenta carregar (pode ser que o router guard tenha falhado)
      console.log('[NetworkDesignView] Google Maps not loaded, attempting to load...');
      await waitForGoogleMaps(30000); // 30 segundos de timeout
      console.log('[NetworkDesignView] ✅ Google Maps loaded successfully!');
    }
  } catch (error) {
    console.error('[NetworkDesignView] ❌ Failed to load Google Maps API', error);
    alert('Erro ao carregar Google Maps.\n\nPossíveis causas:\n- Chave da API não configurada\n- Problema de conexão\n\nPor favor, recarregue a página (F5).');
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
.network-design-page {
  position: relative;
  height: 100%;
  width: 100%;
  overflow: hidden;
  color: #e2e8f0;
  background: radial-gradient(140% 140% at 10% 10%, rgba(59, 130, 246, 0.14) 0%, rgba(30, 41, 59, 0.85) 42%, rgba(10, 12, 26, 0.95) 100%);
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

.map-toolbar {
  position: absolute;
  top: 24px;
  left: 24px;
  display: flex;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(15, 23, 42, 0.85);
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.45);
  z-index: 40;
  backdrop-filter: blur(18px);
}

.toolbar-btn {
  background: rgba(226, 232, 240, 0.08);
  color: #f8fafc;
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 999px;
  padding: 0.55rem 1.35rem;
  font-size: 0.875rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.toolbar-btn:hover {
  background: rgba(241, 245, 249, 0.2);
  border-color: rgba(226, 232, 240, 0.6);
}

.toolbar-btn:active {
  background: rgba(148, 163, 184, 0.35);
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
  background: rgba(15, 23, 42, 0.92);
  border-radius: 24px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(22px);
  z-index: 35;
  color: #e2e8f0;
  overflow: hidden;
  overflow-y: auto;
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
  color: #f8fafc;
  letter-spacing: 0.01em;
}

.floating-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.floating-panel__metric {
  font-size: 0.82rem;
  color: #cbd5f5;
  padding: 0.35rem 0.85rem;
  border-radius: 999px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: rgba(15, 23, 42, 0.6);
}

.floating-panel__description {
  margin: 0;
  font-size: 0.85rem;
  color: #c5d2f7;
}

.route-points-list {
  list-style: none;
  margin: 0;
  padding: 0.75rem;
  border: 1px dashed rgba(148, 163, 184, 0.35);
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.45);
  flex: 1;
  overflow-y: auto;
}

.route-points-list li {
  padding: 0.45rem 0.6rem;
  border-radius: 0.65rem;
  font-size: 0.85rem;
  color: #f8fafc;
  cursor: grab;
  transition: background 0.2s ease, transform 0.2s ease;
}

.route-points-list li + li {
  margin-top: 0.45rem;
}

.route-points-list li.bg-blue-100 {
  background: rgba(59, 130, 246, 0.35);
}

.route-points-list li.bg-blue-50 {
  background: rgba(191, 219, 254, 0.25);
  color: #0f172a;
}

.floating-panel__footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.5rem;
}

.footer-btn {
  background: rgba(248, 113, 113, 0.15);
  color: #fee2e2;
  border: 1px solid rgba(248, 113, 113, 0.35);
  border-radius: 999px;
  padding: 0.45rem 1.25rem;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;
}

.footer-btn:hover {
  background: rgba(248, 113, 113, 0.26);
  border-color: rgba(254, 202, 202, 0.6);
}

.help-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  font-size: 0.85rem;
  color: #d7dcff;
}

.help-index {
  font-weight: 600;
  color: #ffffff;
  margin-right: 0.5rem;
}

.help-emphasis {
  font-weight: 600;
  color: #facc15;
}

.help-shortcut {
  border: 1px solid rgba(148, 163, 184, 0.4);
  border-radius: 8px;
  padding: 0.15rem 0.4rem;
  background: rgba(241, 245, 249, 0.12);
  color: #f8fafc;
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

@media (max-width: 640px) {
  .map-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-btn {
    width: 100%;
    text-align: center;
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
  background: #ffffff;
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
}

#contextMenu {
  width: 260px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.18);
  padding: 1rem;
  color: #111827;
}

#contextMenu.hidden {
  display: none;
}

#contextMenu h3 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #111827;
}

#contextMenu button {
  width: 100%;
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-radius: 0.6rem;
  transition: background-color 0.2s ease;
  font-size: 0.875rem;
  color: #1f2937;
}

#contextMenu button:hover {
  background-color: #eff6ff;
}

#contextMenu button[data-variant='danger'] {
  color: #b91c1c;
}

#contextMenu button[data-variant='danger']:hover {
  background-color: #fee2e2;
}

#contextCableInfo {
  margin-bottom: 0.75rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.75rem;
}

#contextCableName {
  font-weight: 600;
  font-size: 0.95rem;
  color: #1f2937;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(17, 24, 39, 0.55);
  z-index: 52;
  transition: opacity 0.3s ease;
}

.modal-card {
  background: #ffffff;
  border-radius: 1rem;
  width: 100%;
  max-width: 540px;
  padding: 1.5rem;
  position: relative;
  transition: opacity 0.3s ease, transform 0.3s ease;
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
