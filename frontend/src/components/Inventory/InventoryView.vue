<template>
  <div class="h-full flex flex-col app-page app-page-muted">
    <!-- Cabeçalho compacto numa linha (EV-0054): título · abas · ações -->
    <header class="app-surface border-b app-divider px-4 md:px-6 py-2 z-10">
      <div class="flex items-center gap-3 flex-wrap">
        <h1 class="text-base font-semibold app-text-primary mr-2">Inventário</h1>
        <nav class="flex items-center gap-1 flex-wrap" aria-label="Secções do inventário">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'px-2.5 py-1 rounded-md text-sm font-medium transition-colors app-tab',
              activeTab === tab.id ? 'is-active' : ''
            ]"
            :data-testid="`inventory-tab-${tab.id}`"
          >
            {{ tab.label }}
          </button>
        </nav>
        <div class="ml-auto flex gap-2">
          <template v-if="activeTab === 'sites'">
            <button
              @click="handleExport"
              class="px-2.5 py-1.5 rounded-md transition-colors flex items-center gap-2 text-sm app-btn"
            >
              <i class="fas fa-download"></i>
              <span class="hidden sm:inline">Exportar</span>
            </button>
            <button
              @click="triggerNewSite"
              class="px-2.5 py-1.5 rounded-md transition-colors flex items-center gap-2 text-sm app-btn-primary"
            >
              <i class="fas fa-plus"></i>
              <span>Novo site</span>
            </button>
          </template>
          <template v-else-if="activeTab === 'device-groups'">
            <button
              @click="triggerNewGroup"
              class="px-2.5 py-1.5 rounded-md transition-colors flex items-center gap-2 text-sm app-btn-primary"
            >
              <i class="fas fa-plus"></i>
              <span>Novo grupo</span>
            </button>
          </template>
        </div>
      </div>
    </header>

    <main class="flex-1 overflow-auto px-4 md:px-6 py-2 flex flex-col gap-2">
      <component
        :is="activeComponent"
        ref="managerRef"
        class="flex-1"
      />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import InventoryManager from '@/components/Inventory/InventoryManager.vue';
import DeviceGroupsList from '@/components/Inventory/Groups/DeviceGroupsManager.vue';
import DevicesList from '@/components/Inventory/DevicesList.vue';
import FiberCablesList from '@/components/Inventory/FiberCablesList.vue';
import PortsList from '@/components/Inventory/PortsList.vue';

const managerRef = ref(null);
const activeTab = ref('sites');
const tabs = [
  { id: 'sites', label: 'Sites' },
  { id: 'device-groups', label: 'Grupos' },
  { id: 'devices', label: 'Dispositivos' },
  { id: 'fiber-cables', label: 'Cabos' },
  { id: 'ports', label: 'Portas' },
];

const activeComponent = computed(() => {
  switch (activeTab.value) {
    case 'device-groups':
      return DeviceGroupsList;
    case 'devices':
      return DevicesList;
    case 'fiber-cables':
      return FiberCablesList;
    case 'ports':
      return PortsList;
    default:
      return InventoryManager;
  }
});

const triggerNewSite = () => {
  managerRef.value?.openCreateModal();
};

const triggerNewGroup = () => {
  managerRef.value?.openCreateModal();
};

const handleExport = () => {
  managerRef.value?.exportSites();
};
</script>
