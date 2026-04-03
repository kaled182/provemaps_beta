<template>
  <div class="h-full flex flex-col app-page app-page-muted">
    <header class="app-surface shadow-sm border-b app-divider py-3 px-4 md:px-6 z-10">
      <div class="flex flex-col gap-3">
        <div class="flex items-start gap-3 justify-between">
          <div class="leading-tight">
            <h1 class="text-xl font-bold app-text-primary">Inventário</h1>
            <p class="text-xs app-text-tertiary mt-0.5">
              Sites, POPs e infraestrutura
            </p>
          </div>
        </div>

        <div class="app-surface rounded-xl p-2 flex items-center gap-2 justify-between">
          <div class="flex items-center gap-2 flex-wrap">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              :class="[
                'px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors app-tab',
                activeTab === tab.id ? 'is-active' : ''
              ]"
            >
              {{ tab.label }}
            </button>
          </div>
          <div class="flex gap-2">
            <template v-if="activeTab === 'sites'">
              <button
                @click="handleExport"
                class="px-3 py-2 rounded-lg transition-colors flex items-center gap-2 shadow-sm text-sm app-btn"
              >
                <i class="fas fa-download"></i>
                <span class="hidden sm:inline">Exportar</span>
              </button>
              <button
                @click="triggerNewSite"
                class="px-3 py-2 rounded-lg shadow-md transition-colors flex items-center gap-2 text-sm app-btn-primary"
              >
                <i class="fas fa-plus"></i>
                <span>Novo Site</span>
              </button>
            </template>
            <template v-else-if="activeTab === 'device-groups'">
              <button
                @click="triggerNewGroup"
                class="px-3 py-2 rounded-lg shadow-md transition-colors flex items-center gap-2 text-sm app-btn-primary"
              >
                <i class="fas fa-plus"></i>
                <span>Novo Grupo</span>
              </button>
            </template>
          </div>
        </div>
      </div>
    </header>

    <main class="flex-1 overflow-auto px-4 md:px-6 py-3 flex flex-col gap-3">
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
  { id: 'device-groups', label: 'Device Groups' },
  { id: 'devices', label: 'Devices' },
  { id: 'fiber-cables', label: 'Fiber Cables' },
  { id: 'ports', label: 'Ports' },
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
