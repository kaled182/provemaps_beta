<template>
  <div class="dashboard-container">
    <!-- Header (removido status de conexão, agora no navbar) -->
    <header class="dashboard-header">
      <div class="header-actions">
        <!-- Mobile sidebar toggle -->
        <button 
          class="sidebar-toggle" 
          @click="sidebarOpen = !sidebarOpen"
          aria-label="Toggle sidebar"
        >
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
      </div>
    </header>

    <!-- Main content area: sidebar + map -->
    <div class="dashboard-main" :class="{ 'sidebar-right': sidebarPosition === 'right' }">
      <!-- Left sidebar with host cards and charts -->
      <aside 
        class="dashboard-sidebar" 
        :class="{ 
          'sidebar-open': sidebarOpen,
          'sidebar-collapsed': sidebarCollapsed,
          'sidebar-right': sidebarPosition === 'right'
        }"
      >
        <!-- Botão de expandir quando colapsado -->
        <div v-if="sidebarCollapsed" class="collapsed-sidebar-controls">
          <button 
            @click="toggleSidebar"
            class="expand-btn"
            title="Expandir sidebar"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 5l7 7-7 7M5 5l7 7-7 7" />
            </svg>
          </button>
          <button 
            @click="toggleSidebarPosition"
            class="swap-btn-collapsed"
            title="Trocar lado"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12M8 12h12m-12 5h12M3 7h.01M3 12h.01M3 17h.01" />
            </svg>
          </button>
        </div>
        
        <!-- Mobile close button -->
        <button class="sidebar-close" @click="sidebarOpen = false" aria-label="Close sidebar">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <!-- Status summary -->
        <div class="status-summary">
          <StatusChart 
            :distribution="dashboard.statusDistribution"
            @toggle-sidebar="toggleSidebar"
            @toggle-position="toggleSidebarPosition"
          />
        </div>

        <!-- Filter Bar -->
        <FilterBar />

        <!-- Host cards list -->
        <div class="host-cards-container">
          <div class="section-header">
            <h2>Hosts</h2>
            <span class="host-count">
              {{ dashboard.filteredHosts.length }}
              <span v-if="filtersStore.hasActiveFilters" class="filter-indicator">
                of {{ dashboard.totalHosts }}
              </span>
            </span>
          </div>
          
          <div v-if="dashboard.loading" class="loading-state">
            Carregando hosts...
          </div>
          
          <div v-else-if="dashboard.error" class="error-state">
            Erro: {{ dashboard.error }}
          </div>
          
          <!-- Virtualized list for performance with 100+ hosts -->
          <VirtualList
            v-else-if="dashboard.filteredHosts.length > 20"
            :items="dashboard.filteredHosts"
            :item-height="92"
            :container-height="containerHeight"
            :buffer="3"
            class="host-cards-list-virtual"
          >
            <template #default="{ item }">
              <HostCard :host="item" :key="item.id" />
            </template>
          </VirtualList>
          
          <!-- Standard list for small number of hosts -->
          <div v-else-if="dashboard.filteredHosts.length > 0" class="host-cards-list">
            <HostCard 
              v-for="host in dashboard.filteredHosts" 
              :key="host.id"
              :host="host"
            />
          </div>
          
          <!-- Empty state when filters applied but no results -->
          <div v-if="!dashboard.loading && dashboard.filteredHosts.length === 0 && dashboard.totalHosts > 0" class="empty-state">
            <p>No devices match current filters</p>
            <button @click="filtersStore.clearAllFilters()" class="btn-link">
              Clear all filters
            </button>
          </div>
          
          <!-- Empty state when no hosts at all -->
          <div v-if="!dashboard.loading && dashboard.totalHosts === 0" class="empty-state">
            Nenhum host encontrado
          </div>
        </div>
      </aside>

      <!-- Map area -->
      <main class="dashboard-map">
        <MapView />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { useDashboardStore } from '@/stores/dashboard';
import { useFiltersStore } from '@/stores/filters';
import { useWebSocket } from '@/composables/useWebSocket';
import { useUrlSync } from '@/composables/useUrlSync';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { throttle } from '@/composables/usePerformance';
import { defineAsyncComponent } from 'vue';
import HostCard from '@/components/Dashboard/HostCard.vue';
import StatusChart from '@/components/Dashboard/StatusChart.vue';
import VirtualList from '@/components/Common/VirtualList.vue';
import FilterBar from '@/components/filters/FilterBar.vue';

// Lazy load MapView for better initial load performance
const MapView = defineAsyncComponent(() => 
  import('@/components/MapView.vue')
);

const dashboard = useDashboardStore();
const filtersStore = useFiltersStore();
const router = useRouter();
const route = useRoute();
const { handleAsync } = useErrorHandler();
const sidebarOpen = ref(false);
const sidebarCollapsed = ref(false);
const sidebarPosition = ref(localStorage.getItem('sidebarPosition') || 'left');

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem('sidebarCollapsed', sidebarCollapsed.value);
}

function toggleSidebarPosition() {
  sidebarPosition.value = sidebarPosition.value === 'left' ? 'right' : 'left';
  localStorage.setItem('sidebarPosition', sidebarPosition.value);
}

// Carregar estado salvo
onMounted(() => {
  const savedCollapsed = localStorage.getItem('sidebarCollapsed');
  if (savedCollapsed !== null) {
    sidebarCollapsed.value = savedCollapsed === 'true';
  }
});

// Initialize URL sync for filter persistence
useUrlSync(filtersStore, router, route);

// Calculate container height for virtual scroll (viewport - header - summary - section header)
const containerHeight = computed(() => {
  return window.innerHeight - 60 - 120 - 60; // Approximate heights
});

// WebSocket connection to real-time updates
const wsUrl = computed(() => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws/dashboard/status/`;
});

const { connected: wsConnected, connecting: wsConnecting, lastMessage } = useWebSocket(
  wsUrl.value,
  { autoConnect: true }
);

// Throttle WebSocket message processing to avoid excessive re-renders
const throttledHandleMessage = throttle((message) => {
  handleAsync(
    () => dashboard.handleWebSocketMessage(message),
    { errorMessage: 'Failed to process WebSocket message', silent: true }
  );
}, 300); // Max 3 updates per second

// Watch for WebSocket messages and update dashboard
watch(lastMessage, (message) => {
  if (message) {
    throttledHandleMessage(message);
  }
});

// Fetch initial dashboard data on mount with error handling
onMounted(async () => {
  await handleAsync(
    () => dashboard.fetchDashboard(),
    { errorMessage: 'Failed to load dashboard data' }
  );
});
</script>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 24px;
  background: #1f2937;
  color: #fff;
  border-bottom: 1px solid #374151;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.sidebar-controls {
  display: flex;
  gap: 8px;
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px;
  background: #374151;
  border: 1px solid #4b5563;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.control-btn:hover {
  background: #4b5563;
  transform: translateY(-1px);
}

.control-btn svg {
  width: 20px;
  height: 20px;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #6b7280;
}

.status-indicator.connected {
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.status-indicator.connecting {
  background: #f59e0b;
  animation: pulse 1.5s infinite;
}

.status-indicator.disconnected {
  background: #ef4444;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.dashboard-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.dashboard-main.sidebar-right {
  flex-direction: row-reverse;
}

.dashboard-sidebar {
  width: 350px;
  background: #f9fafb;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s ease-in-out;
}

.dashboard-sidebar.sidebar-collapsed {
  width: 15px;
  min-width: 15px;
}

.dashboard-sidebar.sidebar-collapsed .status-summary,
.dashboard-sidebar.sidebar-collapsed .host-cards-container,
.dashboard-sidebar.sidebar-collapsed .section-header h2,
.dashboard-sidebar.sidebar-collapsed .host-count,
.dashboard-sidebar.sidebar-collapsed .filter-indicator,
.dashboard-sidebar.sidebar-collapsed .sidebar-close {
  display: none;
}

.dashboard-sidebar.sidebar-right {
  border-right: none;
  border-left: 1px solid #e5e7eb;
}

.collapsed-sidebar-controls {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 2px;
  background: #2563eb;
  border-bottom: 1px solid #1d4ed8;
  align-items: center;
  width: 15px;
}

.expand-btn,
.swap-btn-collapsed {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 11px;
  height: 32px;
  padding: 0;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  cursor: pointer;
  transition: all 0.2s;
  writing-mode: vertical-lr;
}

.expand-btn:hover,
.swap-btn-collapsed:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  width: 13px;
}

.expand-btn svg,
.swap-btn-collapsed svg {
  width: 10px;
  height: 10px;
  color: white;
  transform: rotate(90deg);
}

.dashboard-sidebar.sidebar-collapsed .collapsed-sidebar-controls {
  display: flex;
}


.status-summary {
  padding: 16px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.host-cards-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fff;
  border-bottom: 2px solid #e5e7eb;
}

.section-header h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.host-count {
  background: #3b82f6;
  color: #fff;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.host-cards-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.host-cards-list-virtual {
  flex: 1;
  padding: 8px;
}

.host-cards-list-virtual :deep(.virtual-list-container) {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #f9fafb;
}

.host-cards-list-virtual :deep(.virtual-list-container)::-webkit-scrollbar {
  width: 8px;
}

.host-cards-list-virtual :deep(.virtual-list-container)::-webkit-scrollbar-track {
  background: #f9fafb;
}

.host-cards-list-virtual :deep(.virtual-list-container)::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.host-cards-list-virtual :deep(.virtual-list-container)::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.loading-state,
.error-state,
.empty-state {
  padding: 24px;
  text-align: center;
  color: #6b7280;
  font-size: 14px;
}

.error-state {
  color: #ef4444;
}

.dashboard-map {
  flex: 1;
  position: relative;
}

/* Mobile Responsive Styles */
@media (max-width: 768px) {
  .dashboard-header {
    padding: 10px 16px;
  }

  .dashboard-header h1 {
    font-size: 16px;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .sidebar-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: transparent;
    border: 1px solid #374151;
    border-radius: 6px;
    color: #fff;
    cursor: pointer;
    transition: background 0.2s;
  }

  .sidebar-toggle:hover {
    background: #374151;
  }

  .sidebar-toggle svg {
    width: 20px;
    height: 20px;
  }

  .connection-status .status-text {
    display: none;
  }

  .dashboard-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 80%;
    max-width: 320px;
    height: 100vh;
    z-index: 1000;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
    box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  }

  .dashboard-sidebar.sidebar-open {
    transform: translateX(0);
  }

  .sidebar-close {
    display: flex;
    align-items: center;
    justify-content: center;
    position: absolute;
    top: 12px;
    right: 12px;
    width: 32px;
    height: 32px;
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    color: #6b7280;
    cursor: pointer;
    z-index: 10;
    transition: all 0.2s;
  }

  .sidebar-close:hover {
    background: #f9fafb;
    border-color: #d1d5db;
    color: #111827;
  }

  .sidebar-close svg {
    width: 18px;
    height: 18px;
  }

  .host-cards-list {
    max-height: calc(100vh - 350px);
  }
}

@media (min-width: 769px) {
  .sidebar-toggle,
  .sidebar-close {
    display: none;
  }

  .header-actions {
    display: flex;
    align-items: center;
  }
}

/* Phase 13 Sprint 1 Day 2: Filter indicator styles */
.filter-indicator {
  color: #6b7280;
  font-weight: normal;
  font-size: 0.875rem;
}

.btn-link {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  text-decoration: underline;
  padding: 0.5rem 1rem;
  margin-top: 0.5rem;
  font-size: 0.875rem;
  transition: color 0.2s;
}

.btn-link:hover {
  color: #2563eb;
}

.empty-state {
  text-align: center;
  padding: 2rem 1rem;
}

.empty-state p {
  margin-bottom: 0.5rem;
  color: #6b7280;
}

/* Touch-friendly controls */
@media (hover: none) and (pointer: coarse) {
  .host-card {
    padding: 14px;
  }

  .map-controls button {
    width: 44px;
    height: 44px;
  }

  .info-window-content {
    font-size: 15px;
  }
}
</style>
