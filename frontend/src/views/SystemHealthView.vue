<template>
  <div class="h-full overflow-y-auto bg-gray-50 dark:bg-gray-900">
    <div class="max-w-7xl mx-auto p-6 space-y-6">
      <!-- Header com Toggle -->
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-3xl font-bold text-gray-900 dark:text-gray-100">
            System Health Dashboard
          </h1>
          <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Real-time monitoring and metrics visualization
          </p>
        </div>
        
        <div class="flex items-center gap-4">
          <!-- Auto-refresh Toggle -->
          <label class="flex items-center gap-2 cursor-pointer">
            <input
              v-model="autoRefresh"
              type="checkbox"
              class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            />
            <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
              Auto-refresh (10s)
            </span>
          </label>

          <!-- View Toggle -->
          <div class="flex gap-2 bg-gray-200 dark:bg-gray-700 p-1 rounded-lg">
            <button
              @click="viewMode = 'visual'"
              :class="[
                'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                viewMode === 'visual'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
              ]"
            >
              📊 Visual
            </button>
            <button
              @click="viewMode = 'raw'"
              :class="[
                'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                viewMode === 'raw'
                  ? 'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100'
              ]"
            >
              📄 Raw Metrics
            </button>
          </div>
        </div>
      </div>

      <!-- Visual Mode -->
      <div v-if="viewMode === 'visual'" class="space-y-6">
        <!-- Overall Status Banner -->
        <div
          :class="[
            'rounded-lg p-4 border-2',
            allServicesHealthy
              ? 'bg-green-50 dark:bg-green-900/20 border-green-500 dark:border-green-700'
              : 'bg-red-50 dark:bg-red-900/20 border-red-500 dark:border-red-700'
          ]"
        >
          <div class="flex items-center gap-3">
            <span class="text-3xl">{{ allServicesHealthy ? '✅' : '⚠️' }}</span>
            <div>
              <h2
                :class="[
                  'text-lg font-semibold',
                  allServicesHealthy
                    ? 'text-green-800 dark:text-green-300'
                    : 'text-red-800 dark:text-red-300'
                ]"
              >
                {{ allServicesHealthy ? 'All Systems Operational' : 'Some Services Are Down' }}
              </h2>
              <p
                :class="[
                  'text-sm',
                  allServicesHealthy
                    ? 'text-green-700 dark:text-green-400'
                    : 'text-red-700 dark:text-red-400'
                ]"
              >
                Last updated: {{ lastUpdate }}
              </p>
            </div>
          </div>
        </div>

        <!-- Service Status Cards -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <ServiceStatusCard
            v-for="(service, key) in metrics.services"
            :key="key"
            :name="key"
            :data="service"
          />
        </div>

        <!-- System Metrics Charts -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SystemMetricsCard
            title="CPU Usage"
            :value="metrics.system?.cpu_percent"
            unit="%"
            icon="💻"
            :threshold="80"
          />
          <SystemMetricsCard
            title="Memory Usage"
            :value="metrics.system?.memory_percent"
            unit="%"
            icon="🧠"
            :threshold="85"
            :details="`${metrics.system?.memory_used_gb || 0}GB / ${metrics.system?.memory_total_gb || 0}GB`"
          />
          <SystemMetricsCard
            title="Disk Usage"
            :value="metrics.system?.disk_percent"
            unit="%"
            icon="💾"
            :threshold="90"
            :details="`${metrics.system?.disk_used_gb || 0}GB / ${metrics.system?.disk_total_gb || 0}GB`"
          />
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
              📈 Service Response Times
            </h3>
            <div class="space-y-3">
              <ResponseTimeBar
                v-for="(service, key) in servicesWithResponseTime"
                :key="key"
                :name="key"
                :responseTime="service.response_time_ms"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Raw Metrics Mode -->
      <div v-else class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div class="border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
              Prometheus Metrics (Raw)
            </h2>
            <p class="mt-1 text-sm text-gray-600 dark:text-gray-400">
              Native Prometheus format metrics
            </p>
          </div>
          <a
            href="/metrics/"
            target="_blank"
            class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            </svg>
            Open in New Tab
          </a>
        </div>
        <div class="p-6">
          <div v-if="loadingRawMetrics" class="flex items-center justify-center py-12">
            <ph-spinner class="h-8 w-8 animate-spin text-blue-600" />
          </div>
          <pre v-else class="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg overflow-x-auto text-xs font-mono text-gray-800 dark:text-gray-200 max-h-[600px] overflow-y-auto">{{ rawMetrics }}</pre>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <ph-spinner class="h-8 w-8 animate-spin text-blue-600" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { PhSpinner } from '@phosphor-icons/vue';
import ServiceStatusCard from '../components/Health/ServiceStatusCard.vue';
import SystemMetricsCard from '../components/Health/SystemMetricsCard.vue';
import ResponseTimeBar from '../components/Health/ResponseTimeBar.vue';

const viewMode = ref('visual'); // 'visual' | 'raw'
const autoRefresh = ref(true);
const loading = ref(false);
const loadingRawMetrics = ref(false);
const rawMetrics = ref('');
const metrics = ref({
  timestamp: null,
  services: {},
  system: {},
});

let refreshInterval = null;

const lastUpdate = computed(() => {
  if (!metrics.value.timestamp) return 'Never';
  const date = new Date(metrics.value.timestamp);
  return date.toLocaleTimeString();
});

const allServicesHealthy = computed(() => {
  const services = metrics.value.services || {};
  return Object.values(services).every(
    (s) => s.status === 'online' || s.status === 'not_configured'
  );
});

const servicesWithResponseTime = computed(() => {
  const services = metrics.value.services || {};
  return Object.fromEntries(
    Object.entries(services).filter(
      ([_, service]) => service.response_time_ms !== undefined
    )
  );
});

const fetchMetrics = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/metrics/health/');
    const data = await response.json();
    metrics.value = data;
  } catch (error) {
    console.error('Failed to fetch metrics:', error);
  } finally {
    loading.value = false;
  }
};

const fetchRawMetrics = async () => {
  loadingRawMetrics.value = true;
  try {
    const response = await fetch('/metrics/metrics');
    const text = await response.text();
    rawMetrics.value = text;
  } catch (error) {
    console.error('Failed to fetch raw metrics:', error);
    rawMetrics.value = 'Error loading metrics. Please try again.';
  } finally {
    loadingRawMetrics.value = false;
  }
};

const startAutoRefresh = () => {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(() => {
    if (autoRefresh.value) {
      fetchMetrics();
    }
  }, 10000); // 10 seconds
};

// Watch for viewMode changes to load raw metrics when switching to raw mode
watch(viewMode, (newMode) => {
  if (newMode === 'raw' && !rawMetrics.value) {
    fetchRawMetrics();
  }
});

onMounted(() => {
  fetchMetrics();
  startAutoRefresh();
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
});
</script>
