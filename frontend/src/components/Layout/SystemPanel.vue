<template>
  <Teleport to="body">
    <Transition name="sp-fade">
      <div v-if="show" class="sp-overlay" @click.self="$emit('close')">
        <Transition name="sp-slide">
          <div v-if="show" class="sp-panel">

            <!-- Header -->
            <div class="sp-header">
              <div class="sp-header-left">
                <div class="sp-header-icon">
                  <PhHardDrives :size="22" weight="duotone" />
                </div>
                <div>
                  <h2 class="sp-title">Painel do Sistema</h2>
                  <p class="sp-subtitle">Versão e administração de servidores</p>
                </div>
              </div>
              <button class="sp-close" @click="$emit('close')" title="Fechar">
                <PhX :size="18" weight="bold" />
              </button>
            </div>

            <!-- Tabs -->
            <div class="sp-tabs">
              <button
                v-for="tab in tabs"
                :key="tab.id"
                class="sp-tab"
                :class="{ active: activeTab === tab.id }"
                @click="activeTab = tab.id"
              >
                <component :is="tab.icon" :size="16" weight="regular" />
                {{ tab.label }}
                <span v-if="tab.badge" class="sp-tab-badge">{{ tab.badge }}</span>
              </button>
            </div>

            <!-- Body -->
            <div class="sp-body">

              <!-- ── Tab: Sistema ── -->
              <div v-if="activeTab === 'system'" class="sp-section-list">

                <!-- Version card -->
                <div class="sp-card">
                  <div class="sp-card-header">
                    <PhTag :size="16" weight="regular" />
                    Versão Instalada
                  </div>
                  <div class="sp-version-row">
                    <span class="sp-version-number">
                      v{{ sysInfo?.version ?? '—' }}
                    </span>
                    <span
                      class="sp-version-status"
                      :class="updateState"
                    >
                      <PhCheckCircle v-if="updateState === 'latest'" :size="14" />
                      <PhArrowCircleUp v-else-if="updateState === 'available'" :size="14" />
                      <PhCircleNotch v-else-if="updateState === 'checking'" :size="14" class="spin" />
                      <PhMinus v-else :size="14" />
                      {{ updateLabel }}
                    </span>
                  </div>

                  <button class="sp-btn sp-btn-check" :disabled="updateState === 'checking'" @click="checkForUpdates">
                    <PhArrowsClockwise :size="15" weight="regular" :class="{ spin: updateState === 'checking' }" />
                    Verificar atualizações
                  </button>

                  <div v-if="updateState === 'available'" class="sp-update-notice">
                    <PhWarning :size="14" weight="fill" />
                    Nova versão disponível. Contate o administrador para realizar o update.
                  </div>
                </div>

                <!-- Environment card -->
                <div class="sp-card">
                  <div class="sp-card-header">
                    <PhInfo :size="16" weight="regular" />
                    Ambiente
                  </div>
                  <div v-if="loading" class="sp-loading-row">
                    <PhCircleNotch :size="18" class="spin" />
                    Carregando…
                  </div>
                  <template v-else-if="sysInfo">
                    <div class="sp-info-grid">
                      <div class="sp-info-item">
                        <span class="sp-info-label">Python</span>
                        <span class="sp-info-value">{{ sysInfo.python_version }}</span>
                      </div>
                      <div class="sp-info-item">
                        <span class="sp-info-label">Django</span>
                        <span class="sp-info-value">{{ sysInfo.django_version }}</span>
                      </div>
                      <div class="sp-info-item">
                        <span class="sp-info-label">Plataforma</span>
                        <span class="sp-info-value">{{ sysInfo.platform }}</span>
                      </div>
                      <div class="sp-info-item">
                        <span class="sp-info-label">Ambiente</span>
                        <span class="sp-info-value sp-env-badge" :class="sysInfo.environment">
                          {{ sysInfo.environment }}
                        </span>
                      </div>
                      <div class="sp-info-item">
                        <span class="sp-info-label">Host</span>
                        <span class="sp-info-value">{{ sysInfo.hostname }}</span>
                      </div>
                    </div>
                  </template>
                  <div v-else class="sp-error-row">
                    <PhWarningCircle :size="16" /> Não foi possível carregar informações.
                  </div>
                </div>

                <!-- Telemetry stats card -->
                <div class="sp-card">
                  <div class="sp-card-header">
                    <PhGlobeHemisphereWest :size="16" weight="regular" />
                    Instalações Ativas
                  </div>
                  <div v-if="statsLoading" class="sp-loading-row">
                    <PhCircleNotch :size="18" class="spin" /> Carregando…
                  </div>
                  <template v-else-if="stats">
                    <div class="sp-stat-grid">
                      <div class="sp-stat-item">
                        <span class="sp-stat-number">{{ stats.total }}</span>
                        <span class="sp-stat-label">Total</span>
                      </div>
                      <div class="sp-stat-item">
                        <span class="sp-stat-number accent">{{ stats.active_30d }}</span>
                        <span class="sp-stat-label">Ativas 30d</span>
                      </div>
                      <div class="sp-stat-item">
                        <span class="sp-stat-number">{{ stats.active_7d }}</span>
                        <span class="sp-stat-label">Ativas 7d</span>
                      </div>
                    </div>
                    <div v-if="stats.versions?.length" class="sp-version-dist">
                      <div class="sp-version-dist-label">Distribuição por versão</div>
                      <div
                        v-for="v in stats.versions"
                        :key="v.version"
                        class="sp-version-bar-row"
                      >
                        <span class="sp-version-bar-label">v{{ v.version }}</span>
                        <div class="sp-version-bar-track">
                          <div
                            class="sp-version-bar-fill"
                            :style="{ width: Math.round((v.count / stats.active_30d) * 100) + '%' }"
                          ></div>
                        </div>
                        <span class="sp-version-bar-count">{{ v.count }}</span>
                      </div>
                    </div>
                  </template>
                  <div v-else class="sp-error-row">
                    <PhWarningCircle :size="16" /> Dados não disponíveis — configure TELEMETRY_ENDPOINT.
                  </div>
                </div>

              </div>

              <!-- ── Tab: Servidores ── -->
              <div v-if="activeTab === 'servers'" class="sp-section-list">

                <!-- Loading -->
                <div v-if="statsLoading" class="sp-loading-row">
                  <PhCircleNotch :size="18" class="spin" /> Carregando recursos…
                </div>

                <template v-else-if="serverStats">
                  <!-- CPU -->
                  <div class="sp-card">
                    <div class="sp-card-header"><PhCpu :size="16" weight="regular" /> CPU</div>
                    <div class="sp-gauge-row">
                      <span class="sp-gauge-label">{{ serverStats.cpu.percent }}%</span>
                      <div class="sp-gauge-track">
                        <div class="sp-gauge-fill" :class="gaugeClass(serverStats.cpu.percent)"
                          :style="{ width: serverStats.cpu.percent + '%' }" />
                      </div>
                      <span class="sp-gauge-sub">{{ serverStats.cpu.count }} cores</span>
                    </div>
                  </div>

                  <!-- Memória -->
                  <div class="sp-card">
                    <div class="sp-card-header"><PhMemory :size="16" weight="regular" /> Memória RAM</div>
                    <div class="sp-gauge-row">
                      <span class="sp-gauge-label">{{ serverStats.memory.percent }}%</span>
                      <div class="sp-gauge-track">
                        <div class="sp-gauge-fill" :class="gaugeClass(serverStats.memory.percent)"
                          :style="{ width: serverStats.memory.percent + '%' }" />
                      </div>
                      <span class="sp-gauge-sub">{{ serverStats.memory.used_gb }} / {{ serverStats.memory.total_gb }} GB</span>
                    </div>
                  </div>

                  <!-- Disco -->
                  <div class="sp-card">
                    <div class="sp-card-header"><PhHardDrive :size="16" weight="regular" /> Disco</div>
                    <div class="sp-gauge-row">
                      <span class="sp-gauge-label">{{ serverStats.disk.percent }}%</span>
                      <div class="sp-gauge-track">
                        <div class="sp-gauge-fill" :class="gaugeClass(serverStats.disk.percent)"
                          :style="{ width: serverStats.disk.percent + '%' }" />
                      </div>
                      <span class="sp-gauge-sub">{{ serverStats.disk.used_gb }} / {{ serverStats.disk.total_gb }} GB</span>
                    </div>
                  </div>

                  <!-- Serviços -->
                  <div class="sp-card">
                    <div class="sp-card-header"><PhActivity :size="16" weight="regular" /> Serviços</div>
                    <div class="sp-services-grid">
                      <div v-for="svc in serverStats.services" :key="svc.name" class="sp-svc-item">
                        <span class="sp-svc-dot" :class="svc.online ? 'online' : 'offline'" />
                        <span class="sp-svc-name">{{ svc.name }}</span>
                        <span class="sp-svc-status" :class="svc.online ? 'online' : 'offline'">
                          {{ svc.online ? 'Online' : 'Offline' }}
                        </span>
                      </div>
                    </div>
                  </div>

                  <!-- Atualizar -->
                  <button class="sp-btn sp-btn-check" @click="fetchServerStats">
                    <PhArrowsClockwise :size="15" /> Atualizar
                  </button>
                </template>

                <div v-else class="sp-error-row">
                  <PhWarningCircle :size="16" /> Não foi possível carregar recursos do servidor.
                </div>
              </div>

            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import {
  PhHardDrives, PhX, PhTag, PhInfo, PhArrowsClockwise,
  PhCheckCircle, PhArrowCircleUp, PhCircleNotch, PhMinus,
  PhWarning, PhWarningCircle, PhGlobeHemisphereWest,
  PhCpu, PhMemory, PhHardDrive, PhActivity,
} from '@phosphor-icons/vue';
import { useApi } from '@/composables/useApi';

const props = defineProps({ show: { type: Boolean, default: false } });
defineEmits(['close']);

const api = useApi();

const activeTab = ref('system');
const loading = ref(false);
const sysInfo = ref(null);
const updateState = ref('idle'); // idle | checking | latest | available
const stats = ref(null);
const statsLoading = ref(false);
const serverStats = ref(null);
const serverStatsLoading = ref(false);

const tabs = [
  { id: 'system',  label: 'Sistema',    icon: PhInfo },
  { id: 'servers', label: 'Servidores', icon: PhHardDrives },
];

function gaugeClass(percent) {
  if (percent >= 90) return 'danger';
  if (percent >= 70) return 'warning';
  return 'ok';
}

const updateLabel = computed(() => ({
  idle:      'Não verificado',
  checking:  'Verificando…',
  latest:    'Versão mais recente',
  available: 'Atualização disponível',
}[updateState.value] ?? 'Não verificado'));

async function fetchSystemInfo() {
  loading.value = true;
  console.log('[SystemPanel] fetchSystemInfo iniciado');
  try {
    const data = await api.get('/api/v1/inventory/system/info/');
    console.log('[SystemPanel] system/info resposta:', data);
    sysInfo.value = data;
  } catch (err) {
    console.error('[SystemPanel] system/info erro:', err);
    sysInfo.value = null;
  } finally {
    loading.value = false;
  }
}

async function fetchStats() {
  statsLoading.value = true;
  try {
    stats.value = await api.get('/api/v1/telemetry/stats/');
  } catch {
    stats.value = null;
  } finally {
    statsLoading.value = false;
  }
}

async function checkForUpdates() {
  console.log('[SystemPanel] checkForUpdates clicado');
  updateState.value = 'checking';
  try {
    const data = await api.get('/api/v1/inventory/system/info/');
    console.log('[SystemPanel] checkForUpdates resposta:', data);
    sysInfo.value = data;
    updateState.value = 'latest';
  } catch (err) {
    console.error('[SystemPanel] checkForUpdates erro:', err);
    updateState.value = 'idle';
  }
}

async function fetchServerStats() {
  serverStatsLoading.value = true;
  try {
    serverStats.value = await api.get('/api/v1/inventory/system/stats/');
  } catch {
    serverStats.value = null;
  } finally {
    serverStatsLoading.value = false;
  }
}

watch(() => props.show, (val) => {
  if (val) {
    activeTab.value = 'system';
    if (!sysInfo.value) fetchSystemInfo();
    if (!stats.value) fetchStats();
    if (!serverStats.value) fetchServerStats();
  }
});
</script>

<style scoped>
/* ── Overlay ── */
.sp-overlay {
  position: fixed;
  inset: 0;
  z-index: 9000;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ── Panel ── */
.sp-panel {
  width: 480px;
  max-width: calc(100vw - 2rem);
  max-height: 82vh;
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: 16px;
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ── Header ── */
.sp-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.25rem 1.5rem 1rem;
  border-bottom: 1px solid var(--border-secondary);
  flex-shrink: 0;
}

.sp-header-left {
  display: flex;
  align-items: center;
  gap: 0.875rem;
}

.sp-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: var(--accent-info-light);
  color: var(--accent-info);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sp-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.sp-subtitle {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin: 0;
}

.sp-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-secondary);
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s, color 0.15s;
}

.sp-close:hover {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

/* ── Tabs ── */
.sp-tabs {
  display: flex;
  gap: 4px;
  padding: 0.75rem 1.5rem 0;
  border-bottom: 1px solid var(--border-secondary);
  flex-shrink: 0;
}

.sp-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.5rem 0.875rem;
  border-radius: 8px 8px 0 0;
  border: none;
  background: transparent;
  color: var(--text-tertiary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
  position: relative;
  bottom: -1px;
}

.sp-tab:hover {
  color: var(--text-primary);
  background: var(--menu-item-hover);
}

.sp-tab.active {
  color: var(--accent-info);
  border-bottom: 2px solid var(--accent-info);
  background: transparent;
}

.sp-tab-badge {
  font-size: 0.65rem;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--badge-neutral-bg);
  color: var(--text-tertiary);
}

/* ── Body ── */
.sp-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.25rem 1.5rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.sp-section-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ── Card ── */
.sp-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-secondary);
  border-radius: 12px;
  padding: 1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sp-card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ── Version ── */
.sp-version-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.sp-version-number {
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.02em;
}

.sp-version-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid transparent;
}

.sp-version-status.latest {
  background: var(--status-online-light);
  color: var(--status-online);
  border-color: var(--status-online-light);
}

.sp-version-status.available {
  background: var(--status-warning-light);
  color: var(--status-warning);
  border-color: var(--status-warning-light);
}

.sp-version-status.checking,
.sp-version-status.idle {
  background: var(--badge-neutral-bg);
  color: var(--text-tertiary);
}

/* ── Check button ── */
.sp-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  border: 1px solid var(--border-primary);
  background: var(--menu-item-base);
  color: var(--text-secondary);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  align-self: flex-start;
}

.sp-btn:hover:not(:disabled) {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

.sp-btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.sp-btn-check {
  border-color: var(--accent-info);
  color: var(--accent-info);
}

.sp-btn-check:hover:not(:disabled) {
  background: var(--accent-info-light);
  color: var(--accent-info);
}

.sp-update-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--status-warning);
  background: var(--status-warning-light);
  border: 1px solid var(--status-warning-light);
  border-radius: 8px;
  padding: 0.5rem 0.75rem;
}

/* ── Info grid ── */
.sp-info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem 1rem;
}

.sp-info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sp-info-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sp-info-value {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
  font-family: monospace;
}

.sp-env-badge.production {
  color: var(--status-online);
}

.sp-env-badge.development {
  color: var(--status-warning);
}

/* ── States ── */
.sp-loading-row,
.sp-error-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--text-tertiary);
  padding: 0.25rem 0;
}

.sp-error-row {
  color: var(--status-offline);
}

/* ── Coming soon ── */
.sp-coming-soon {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 2rem 1rem;
  gap: 0.75rem;
}

.sp-coming-icon {
  width: 72px;
  height: 72px;
  border-radius: 20px;
  background: var(--accent-info-light);
  color: var(--accent-info);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.25rem;
}

.sp-coming-soon h3 {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.sp-coming-soon p {
  font-size: 0.8125rem;
  color: var(--text-tertiary);
  max-width: 340px;
  line-height: 1.6;
  margin: 0;
}

.sp-coming-features {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
  margin-top: 0.5rem;
  text-align: left;
  width: 100%;
  max-width: 320px;
}

.sp-coming-feature {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--text-secondary);
}

.sp-coming-feature svg {
  color: var(--accent-info);
  flex-shrink: 0;
}

/* ── Gauge ── */
.sp-gauge-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sp-gauge-label {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-primary);
  width: 42px;
  flex-shrink: 0;
}

.sp-gauge-track {
  flex: 1;
  height: 8px;
  background: var(--border-secondary);
  border-radius: 999px;
  overflow: hidden;
}

.sp-gauge-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s ease;
}

.sp-gauge-fill.ok      { background: var(--status-online); }
.sp-gauge-fill.warning { background: var(--status-warning); }
.sp-gauge-fill.danger  { background: var(--status-offline); }

.sp-gauge-sub {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  width: 90px;
  text-align: right;
  flex-shrink: 0;
}

/* ── Services ── */
.sp-services-grid {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.sp-svc-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.sp-svc-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sp-svc-dot.online  { background: var(--status-online); }
.sp-svc-dot.offline { background: var(--status-offline); }

.sp-svc-name {
  flex: 1;
  font-size: 0.8125rem;
  color: var(--text-primary);
}

.sp-svc-status {
  font-size: 0.75rem;
  font-weight: 600;
}

.sp-svc-status.online  { color: var(--status-online); }
.sp-svc-status.offline { color: var(--status-offline); }

/* ── Spinner ── */
.spin {
  animation: sp-spin 0.9s linear infinite;
}

@keyframes sp-spin {
  to { transform: rotate(360deg); }
}

/* ── Transitions ── */
.sp-fade-enter-active,
.sp-fade-leave-active {
  transition: opacity 0.2s ease;
}

.sp-fade-enter-from,
.sp-fade-leave-to {
  opacity: 0;
}

.sp-slide-enter-active,
.sp-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.sp-slide-enter-from,
.sp-slide-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.98);
}

/* ── Telemetry stats ── */
.sp-stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.sp-stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem 0.5rem;
  background: var(--surface-highlight);
  border-radius: 10px;
  gap: 4px;
}

.sp-stat-number {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1;
}

.sp-stat-number.accent {
  color: var(--accent-info);
}

.sp-stat-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.sp-version-dist {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sp-version-dist-label {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 2px;
}

.sp-version-bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sp-version-bar-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
  width: 52px;
  font-family: monospace;
  flex-shrink: 0;
}

.sp-version-bar-track {
  flex: 1;
  height: 6px;
  background: var(--border-secondary);
  border-radius: 999px;
  overflow: hidden;
}

.sp-version-bar-fill {
  height: 100%;
  background: var(--accent-info);
  border-radius: 999px;
  transition: width 0.4s ease;
}

.sp-version-bar-count {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  width: 20px;
  text-align: right;
  flex-shrink: 0;
}
</style>
