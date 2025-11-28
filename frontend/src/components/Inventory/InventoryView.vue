<template>
  <div class="h-full flex flex-col bg-gray-50 dark:bg-gray-900">
    <header class="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700 py-3 px-4 md:px-6 z-10">
      <div class="flex flex-col gap-3">
        <div class="flex items-start gap-3 justify-between">
          <div class="leading-tight">
            <h1 class="text-xl font-bold text-gray-900 dark:text-white">Inventário</h1>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Sites, POPs e infraestrutura
            </p>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-sm p-2 flex items-center gap-2 justify-between">
          <div class="flex items-center gap-2 flex-wrap">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              @click="activeTab = tab.id"
              :class="[
                'px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors',
                activeTab === tab.id
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
              ]"
            >
              {{ tab.label }}
            </button>
          </div>
          <div class="flex gap-2">
            <template v-if="activeTab === 'sites'">
              <button
                @click="handleExport"
                class="px-3 py-2 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors flex items-center gap-2 shadow-sm text-sm"
              >
                <i class="fas fa-download"></i>
                <span class="hidden sm:inline">Exportar</span>
              </button>
              <button
                @click="triggerNewSite"
                class="px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-md transition-colors flex items-center gap-2 text-sm"
              >
                <i class="fas fa-plus"></i>
                <span>Novo Site</span>
              </button>
            </template>
            <template v-else-if="activeTab === 'device-groups'">
              <button
                @click="triggerNewGroup"
                class="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-md transition-colors flex items-center gap-2 text-sm"
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
