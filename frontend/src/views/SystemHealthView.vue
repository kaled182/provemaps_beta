<template>
  <div class="health-page relative min-h-full overflow-hidden">
    <div class="metrics-bg absolute inset-0 opacity-70"></div>
    <div class="relative max-w-7xl mx-auto px-6 py-6 space-y-8">
      <!-- Header -->
      <div class="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div class="flex items-start gap-4">
          <div class="h-12 w-12 rounded-2xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center text-xl shadow-inner">
            ⚡
          </div>
          <div>
            <h1 class="text-3xl font-semibold health-title">
              Métricas do Sistema
            </h1>
            <p class="mt-1 text-sm health-muted">
              Monitoramento de alta disponibilidade, performance e saúde operacional.
            </p>
            <div class="mt-4 flex flex-wrap items-center gap-3 text-xs health-muted">
              <span class="health-badge inline-flex items-center gap-2 rounded-full px-3 py-1">
                <span class="h-2 w-2 rounded-full" :class="allServicesHealthy ? 'bg-emerald-400' : 'bg-rose-400'"></span>
                {{ allServicesHealthy ? 'Tudo operacional' : 'Atencao necessaria' }}
              </span>
              <span class="health-badge inline-flex items-center gap-2 rounded-full px-3 py-1">
                Atualizado: {{ lastUpdate }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-4">
          <div class="health-card-sm rounded-2xl px-4 py-3 text-right">
            <div class="text-xs uppercase tracking-wide health-muted">Hora local</div>
            <div class="text-lg font-semibold health-title">{{ currentTime }}</div>
          </div>
          <label class="flex items-center gap-2 cursor-pointer text-sm health-muted">
            <input
              v-model="autoRefresh"
              type="checkbox"
              class="w-4 h-4 text-emerald-500 rounded"
            />
            Auto-refresh (10s)
          </label>
          <div class="health-toggle flex gap-2 p-1 rounded-lg">
            <button
              @click="viewMode = 'visual'"
              class="px-4 py-2 rounded-md text-xs font-semibold transition-colors"
              :class="viewMode === 'visual' ? 'health-toggle-active' : 'health-toggle-inactive'"
            >
              📊 Visual
            </button>
            <button
              @click="viewMode = 'raw'"
              class="px-4 py-2 rounded-md text-xs font-semibold transition-colors"
              :class="viewMode === 'raw' ? 'health-toggle-active' : 'health-toggle-inactive'"
            >
              📄 Raw Metrics
            </button>
          </div>
        </div>
      </div>

      <!-- Visual Mode -->
      <div v-if="viewMode === 'visual'" class="space-y-8">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div class="health-stat-card rounded-xl px-4 py-3 shadow-sm">
            <p class="text-xs uppercase tracking-wide health-muted">Servicos</p>
            <p class="mt-2 text-2xl font-semibold health-title">{{ serviceSummary.total }}</p>
            <p class="text-xs health-dim">Total monitorados</p>
          </div>
          <div class="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 shadow-sm">
            <p class="text-xs uppercase tracking-wide text-emerald-600 dark:text-emerald-200">Online</p>
            <p class="mt-2 text-2xl font-semibold text-emerald-700 dark:text-emerald-100">{{ serviceSummary.online }}</p>
            <p class="text-xs text-emerald-600/80 dark:text-emerald-200/80">Operando normal</p>
          </div>
          <div class="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 shadow-sm">
            <p class="text-xs uppercase tracking-wide text-rose-600 dark:text-rose-200">Offline</p>
            <p class="mt-2 text-2xl font-semibold text-rose-700 dark:text-rose-100">{{ serviceSummary.offline }}</p>
            <p class="text-xs text-rose-600/80 dark:text-rose-200/80">Requer acao</p>
          </div>
          <div class="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 shadow-sm">
            <p class="text-xs uppercase tracking-wide text-amber-600 dark:text-amber-200">Pendente</p>
            <p class="mt-2 text-2xl font-semibold text-amber-700 dark:text-amber-100">{{ serviceSummary.pending }}</p>
            <p class="text-xs text-amber-600/80 dark:text-amber-200/80">Nao configurado</p>
          </div>
        </div>

        <div class="health-section rounded-2xl p-6 shadow-sm">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-lg font-semibold health-title">Operational Overview</h2>
              <p class="text-xs health-muted">Servicos centrais e configuracoes criticas.</p>
            </div>
            <span class="text-xs health-dim">Status central</span>
          </div>
          <div class="mt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div class="health-inner-card rounded-xl p-4">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wide health-muted">Zabbix API</span>
                <span class="health-dim">⚡</span>
              </div>
              <div class="mt-3 text-lg font-semibold health-title">
                {{ configStatus.zabbixApi ? 'Conectado' : 'Pendente' }}
              </div>
              <div class="mt-1 text-xs health-dim truncate">
                {{ configStatus.zabbixApi || '--' }}
              </div>
            </div>
            <div class="health-inner-card rounded-xl p-4">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wide health-muted">Banco de Dados</span>
                <span class="health-dim">🗄️</span>
              </div>
              <div class="mt-3 text-lg font-semibold health-title">
                {{ configStatus.dbHost || 'localhost' }}
              </div>
              <div class="mt-1 text-xs health-dim">PostgreSQL / PostGIS</div>
            </div>
            <div class="health-inner-card rounded-xl p-4">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wide health-muted">Mapas</span>
                <span class="health-dim">🗺️</span>
              </div>
              <div class="mt-3 text-lg font-semibold health-title uppercase">
                {{ configStatus.mapProvider || 'Google' }}
              </div>
              <div class="mt-1 text-xs health-dim">Provedor ativo</div>
            </div>
            <div class="health-inner-card rounded-xl p-4">
              <div class="flex items-center justify-between">
                <span class="text-xs uppercase tracking-wide health-muted">Snapshots</span>
                <span class="health-dim">📦</span>
              </div>
              <div class="mt-3 text-lg font-semibold health-title">
                {{ configStatus.backupCount }}
              </div>
              <div class="mt-1 text-xs health-dim">Arquivos salvos</div>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 xl:grid-cols-[1fr_1.35fr] gap-6">
          <div class="space-y-4">
            <div class="health-section rounded-2xl p-5">
              <h3 class="text-sm font-semibold health-title">Estado da Placa</h3>
              <p class="text-xs health-muted">CPU, memoria e armazenamento.</p>
              <div class="mt-4 space-y-3">
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
              </div>
            </div>
            <div class="health-section rounded-2xl p-5">
              <h3 class="text-sm font-semibold health-title">Latencia de Servicos</h3>
              <p class="text-xs health-muted">Tempo de resposta das integracoes.</p>
              <div class="mt-4 space-y-3">
                <ResponseTimeBar
                  v-for="(service, key) in servicesWithResponseTime"
                  :key="key"
                  :name="key"
                  :responseTime="service.response_time_ms"
                />
              </div>
            </div>
          </div>
          <div class="health-section rounded-2xl p-5">
            <div class="flex items-center justify-between">
              <div>
                <h3 class="text-sm font-semibold health-title">Status dos Servicos</h3>
                <p class="text-xs health-muted">Camadas monitoradas em tempo real.</p>
              </div>
              <span class="text-xs health-dim">Atualizado {{ lastUpdate }}</span>
            </div>
            <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
              <ServiceStatusCard
                v-for="(service, key) in metrics.services"
                :key="key"
                :name="key"
                :data="service"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Raw Metrics Mode -->
      <div v-else class="health-section rounded-2xl overflow-hidden">
        <div class="health-inner-card border-b px-6 py-4 flex items-center justify-between" style="border-radius: 0;">
          <div>
            <h2 class="text-lg font-semibold health-title">
              Prometheus Metrics (Raw)
            </h2>
            <p class="mt-1 text-sm health-muted">
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
          <pre class="health-pre p-4 rounded-lg overflow-x-auto text-xs font-mono max-h-[600px] overflow-y-auto">{{ rawMetrics }}</pre>
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
const configStatus = ref({
  zabbixApi: null,
  dbHost: null,
  mapProvider: null,
  backupCount: 0,
});

let refreshInterval = null;
let clockInterval = null;

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

const serviceSummary = computed(() => {
  const services = metrics.value.services || {};
  let total = 0;
  let online = 0;
  let offline = 0;
  let pending = 0;
  Object.values(services).forEach((service) => {
    total += 1;
    if (service.status === 'online') {
      online += 1;
    } else if (service.status === 'offline') {
      offline += 1;
    } else {
      pending += 1;
    }
  });
  return { total, online, offline, pending };
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

const fetchOperationalOverview = async () => {
  try {
    const [configRes, backupsRes] = await Promise.all([
      fetch('/setup_app/api/config/'),
      fetch('/setup_app/api/backups/'),
    ]);
    const configData = configRes.ok ? await configRes.json() : null;
    const backupsData = backupsRes.ok ? await backupsRes.json() : null;
    const configuration = configData?.configuration || {};
    configStatus.value = {
      zabbixApi: configuration.ZABBIX_API_URL || null,
      dbHost: configuration.DB_HOST || null,
      mapProvider: configuration.MAP_PROVIDER || null,
      backupCount: Array.isArray(backupsData?.backups) ? backupsData.backups.length : 0,
    };
  } catch (error) {
    console.error('Failed to fetch config status:', error);
  }
};

const loadData = async () => {
  await Promise.all([fetchMetrics(), fetchOperationalOverview()]);
};

const now = ref(new Date());
const currentTime = computed(() => now.value.toLocaleTimeString());

const startAutoRefresh = () => {
  if (refreshInterval) clearInterval(refreshInterval);
  refreshInterval = setInterval(() => {
    if (autoRefresh.value) {
      loadData();
    }
  }, 10000);
};

watch(viewMode, (newMode) => {
  if (newMode === 'raw' && !rawMetrics.value) {
    fetchRawMetrics();
  }
});

onMounted(() => {
  loadData();
  startAutoRefresh();
  clockInterval = setInterval(() => {
    now.value = new Date();
  }, 1000);
});

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval);
  if (clockInterval) clearInterval(clockInterval);
});
</script>

<style scoped>
.health-page {
  background: var(--bg-primary);
  color: var(--text-primary);
}

.health-title { color: var(--text-primary); }
.health-muted { color: var(--text-tertiary); }
.health-dim   { color: var(--text-disabled); }

.health-badge {
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
  color: var(--text-tertiary);
}

.health-card-sm {
  border: 1px solid var(--border-primary);
  background: var(--bg-secondary);
}

.health-section {
  border: 1px solid var(--border-primary);
  background: var(--surface-card);
}

.health-stat-card {
  border: 1px solid var(--border-primary);
  background: var(--surface-card);
}

.health-inner-card {
  border: 1px solid var(--border-secondary);
  background: var(--bg-secondary);
}

.health-toggle {
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
}

.health-toggle-active {
  background: var(--bg-primary);
  color: var(--text-primary);
  box-shadow: var(--shadow-sm);
}

.health-toggle-inactive {
  background: transparent;
  color: var(--text-tertiary);
}

.health-toggle-inactive:hover {
  color: var(--text-primary);
}

.health-pre {
  background: var(--bg-primary);
  color: var(--text-secondary);
  border: 1px solid var(--border-secondary);
}

.metrics-bg {
  background:
    radial-gradient(circle at top left, rgba(16, 185, 129, 0.08), transparent 45%),
    radial-gradient(circle at 20% 40%, rgba(59, 130, 246, 0.08), transparent 45%),
    radial-gradient(circle at 80% 30%, rgba(249, 115, 22, 0.06), transparent 40%),
    repeating-linear-gradient(
      120deg,
      rgba(148, 163, 184, 0.06) 0px,
      rgba(148, 163, 184, 0.06) 1px,
      transparent 1px,
      transparent 22px
    );
}
</style>
