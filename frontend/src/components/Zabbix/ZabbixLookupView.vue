<template>
  <div class="flex h-full flex-col overflow-hidden">
    <div class="space-y-6 overflow-auto px-4 py-6 sm:px-6 lg:px-8">
      <section class="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-slate-700 text-white shadow-xl ring-1 ring-slate-800/50">
        <div class="absolute inset-0 opacity-40 bg-[radial-gradient(circle_at_20%_20%,#22c55e_0,transparent_25%),radial-gradient(circle_at_80%_0%,#38bdf8_0,transparent_30%)]"></div>
        <div class="relative flex flex-col gap-4 px-6 py-6 sm:px-8 sm:py-8 lg:flex-row lg:items-center lg:justify-between">
          <div class="space-y-2">
            <p class="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-emerald-200 ring-1 ring-white/20">
              Zabbix Lookup · Inventory bridge
            </p>
            <div>
              <h1 class="text-3xl font-semibold leading-tight">Lookup Zabbix</h1>
              <p class="mt-2 text-sm text-slate-100/80">
                Busque hosts no Zabbix, importe para o inventário e revise interfaces e níveis ópticos.
              </p>
            </div>
            <div class="flex flex-wrap gap-2 text-xs text-slate-100/70">
              <span class="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/15">Host groups &amp; filtros</span>
              <span class="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/15">Inventory sync</span>
              <span class="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/15">Ping/Telnet</span>
            </div>
          </div>
          <RouterLink
            to="/monitoring/monitoring-all"
            class="inline-flex items-center gap-2 rounded-xl bg-white/10 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/10 ring-1 ring-white/15 transition hover:bg-white/15"
          >
            Dashboard
          </RouterLink>
        </div>
      </section>

      <div class="grid gap-6 xl:grid-cols-[1.1fr,1fr]">
        <section class="rounded-2xl border border-slate-200/70 bg-white/90 shadow-xl shadow-slate-900/5 backdrop-blur">
          <header class="flex items-start justify-between gap-4 border-b border-slate-200/70 px-6 py-5">
            <div>
              <h2 class="text-lg font-semibold text-slate-900">Buscar hosts</h2>
              <p class="mt-1 text-sm text-slate-500">Filtre por nome, IP ou grupos para localizar dispositivos rapidamente.</p>
            </div>
            <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
              {{ hosts.length ? `${hosts.length} resultados` : 'Aguardando' }}
            </span>
          </header>
          <div class="space-y-4 px-6 py-5">
            <div class="grid gap-3 md:grid-cols-[1.5fr,1fr]">
              <input
                v-model="searchTerm"
                class="rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-inner shadow-slate-900/5 focus:border-emerald-500 focus:outline-none focus:ring focus:ring-emerald-500/20"
                placeholder="Exemplo: core, 192.168."
                @keyup.enter="searchHosts"
              />
          <select
            v-model="selectedGroup"
            class="rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-inner shadow-slate-900/5 focus:border-emerald-500 focus:outline-none focus:ring focus:ring-emerald-500/20 text-slate-900 bg-white"
            :disabled="groupLoading"
          >
            <option value="">Selecione um grupo</option>
            <option v-for="g in hostGroups" :key="g.value" :value="g.value">
              {{ g.label }}
            </option>
          </select>
          <p v-if="groupError" class="text-xs text-red-600">{{ groupError }}</p>
        </div>
            <div class="flex items-center justify-between gap-3">
              <div class="flex items-center gap-2">
                <button
                  class="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-700 focus:outline-none focus:ring focus:ring-emerald-500/40 disabled:cursor-not-allowed disabled:bg-emerald-300"
                  :disabled="hostsLoading"
                  @click="searchHosts"
                >
                  {{ hostsLoading ? 'Buscando...' : 'Buscar' }}
                </button>
              </div>
              <span class="text-xs text-slate-500">Use termo ou grupo para iniciar a busca.</span>
            </div>
            <div class="space-y-3">
              <div
                v-if="hostsLoading"
                class="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
              >
                Buscando hosts...
              </div>
              <div
                v-else-if="hostsError"
                class="rounded-lg border border-dashed border-red-200 bg-red-50 px-4 py-6 text-center text-sm text-red-600"
              >
                {{ hostsError }}
              </div>
              <div
                v-else-if="!hosts.length"
                class="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
              >
                Digite um termo ou selecione um grupo e clique em Buscar.
              </div>
              <div v-else class="space-y-3">
                <div
                  v-for="host in hosts"
                  :key="host.hostid || host.name"
                  class="flex items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm"
                >
                  <div>
                    <p class="font-medium text-slate-900">{{ host.name }}</p>
                    <p class="text-xs text-slate-500">hostid: {{ host.hostid || '-' }}</p>
                    <p class="text-xs text-slate-500">
                      IP: {{ host.ip || host.primary_ip || '-' }} • Status:
                      <StatusBadge :availability="host.availability" inline />
                    </p>
                  </div>
                  <button
                    type="button"
                    class="inline-flex items-center justify-center rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
                    :disabled="!host.hostid"
                    @click="selectHost(host)"
                  >
                    Selecionar
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="rounded-2xl border border-slate-200/70 bg-white/90 shadow-xl shadow-slate-900/5 backdrop-blur">
          <header class="flex items-start justify-between gap-4 border-b border-slate-200/70 px-6 py-5">
            <div>
              <h2 class="text-lg font-semibold text-slate-900">Host selecionado</h2>
              <p class="mt-1 text-sm text-slate-500">Revise dados, importe para o inventário e veja interfaces disponíveis.</p>
            </div>
            <span class="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">Zabbix → Inventory</span>
          </header>
          <div class="space-y-6 px-6 py-5">
            <div
              class="rounded-lg border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
              v-if="!selectedHost"
            >
              Nenhum host selecionado.
            </div>
            <div v-else class="rounded-lg border border-slate-200 bg-emerald-50/40 px-4 py-3">
              <div class="flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-emerald-900">{{ selectedHost.name }}</p>
                  <p class="text-xs text-emerald-700">hostid: {{ selectedHost.hostid }}</p>
                  <p v-if="selectedHost.ip" class="text-xs text-emerald-700">IP: {{ selectedHost.ip }}</p>
                </div>
                <StatusBadge :availability="selectedHost.availability" />
              </div>
            </div>

            <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <button
                id="btnAddDevice"
                class="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300 focus:outline-none focus:ring focus:ring-emerald-500/40"
                :disabled="!selectedHost || addLoading"
                @click="addToInventory"
              >
                {{ addLoading ? 'Adicionando...' : '+ Adicionar ao inventário' }}
              </button>
              <span class="text-sm text-slate-500">{{ addResult }}</span>
            </div>

            <div class="space-y-4">
              <div>
                <div class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_0_3px_rgba(16,185,129,0.2)]"></span>
                  <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-700">Interfaces</h3>
                </div>
                <div class="mt-3 space-y-3">
                  <div
                    v-if="ifaceLoading"
                    class="rounded-md border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-center text-sm text-slate-500"
                  >
                    Carregando interfaces...
                  </div>
                  <div
                    v-else-if="!interfaces.length"
                    class="rounded-md border border-dashed border-slate-200 bg-slate-50 px-4 py-4 text-center text-sm text-slate-500"
                  >
                    Selecione um host para listar interfaces.
                  </div>
                  <div v-else class="space-y-3">
                    <div
                      v-for="iface in interfaces"
                      :key="iface.interfaceid"
                      class="rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm"
                    >
                      <p class="text-sm font-medium text-slate-900">ifaceid: {{ iface.interfaceid }}</p>
                      <p class="text-xs text-slate-500">
                        <span v-if="iface.ip">IP: {{ iface.ip }}</span>
                        <span v-if="iface.dns"> · DNS: {{ iface.dns }}</span>
                        <span v-if="iface.port"> · Porta: {{ iface.port }}</span>
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <div class="flex items-center gap-2">
                  <span class="h-2 w-2 rounded-full bg-sky-400 shadow-[0_0_0_3px_rgba(56,189,248,0.2)]"></span>
                  <h3 class="text-xs font-semibold uppercase tracking-wide text-slate-700">Portas do dispositivo</h3>
                </div>
                <div class="mt-3 space-y-3">
                  <div
                    v-if="portsLoading"
                    class="rounded-md border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
                  >
                    Carregando portas...
                  </div>
                  <div
                    v-else-if="!ports.length"
                    class="rounded-md border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-center text-sm text-slate-500"
                  >
                    Adicione o dispositivo ao inventário para listar portas.
                  </div>
                  <div v-else class="space-y-3">
                    <div
                      v-for="port in ports"
                      :key="port.id"
                      class="flex items-start justify-between gap-4 rounded-lg border border-slate-200 bg-white px-4 py-4 shadow-sm"
                    >
                      <div class="space-y-2">
                        <div>
                          <p class="text-sm font-semibold text-slate-900">{{ port.name }}</p>
                          <p class="text-xs text-slate-500">Port #{{ port.id }}</p>
                        </div>
                        <p class="text-xs text-slate-500">
                          Cable: {{ port.cable_name || '-' }} <span class="text-slate-400">({{ port.cable_id || '-' }})</span>
                        </p>
                        <p class="text-xs text-slate-500">
                          Optical: RX={{ fmtDbm(port.optical?.rx_dbm) }} | TX={{ fmtDbm(port.optical?.tx_dbm) }}
                        </p>
                      </div>
                      <div class="flex flex-col gap-2">
                        <button
                          class="inline-flex items-center justify-center rounded-md border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                          @click="refreshOptical(port.id)"
                        >
                          Optical
                        </button>
                        <button
                          class="inline-flex items-center justify-center rounded-md border border-slate-200 bg-white px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-100"
                          @click="viewTraffic(port.id)"
                        >
                          Traffic
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <section class="rounded-2xl border border-slate-200/70 bg-white/90 shadow-xl shadow-slate-900/5 backdrop-blur">
        <header class="border-b border-slate-200/70 px-6 py-5">
          <h2 class="text-lg font-semibold text-slate-900">Testes rápidos</h2>
          <p class="mt-1 text-sm text-slate-500">Execute ping, telnet ou ambos no host selecionado para validar conectividade.</p>
        </header>
        <div class="space-y-4 px-6 py-5">
          <div class="grid gap-3 md:grid-cols-[1.5fr,1fr]">
            <input
              v-model="testHost"
              class="rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-inner shadow-slate-900/5 focus:border-emerald-500 focus:outline-none focus:ring focus:ring-emerald-500/20"
              placeholder="Hostname ou IP"
            />
            <input
              v-model="testPort"
              class="rounded-lg border border-slate-300 px-3 py-2 text-sm shadow-inner shadow-slate-900/5 focus:border-emerald-500 focus:outline-none focus:ring focus:ring-emerald-500/20"
              placeholder="Porta (ex.: 22)"
            />
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              class="inline-flex items-center justify-center rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition hover:bg-slate-900 focus:outline-none focus:ring focus:ring-slate-700/40"
              @click="runPing"
            >
              Ping
            </button>
            <button
              class="inline-flex items-center justify-center rounded-lg bg-slate-800 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition hover:bg-slate-900 focus:outline-none focus:ring focus:ring-slate-700/40"
              @click="runTelnet"
            >
              Telnet
            </button>
            <button
              class="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-700 focus:outline-none focus:ring focus:ring-emerald-500/40"
              @click="runPingTelnet"
            >
              Ping + Telnet
            </button>
          </div>
          <pre class="max-h-64 overflow-auto rounded-lg bg-slate-900 px-4 py-3 text-sm text-cyan-200 shadow-inner">{{ testOutput }}</pre>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { defineComponent, computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';

const ZABBIX_LOOKUP_API = '/api/v1/inventory/zabbix';
const INVENTORY_API = '/api/v1/inventory';

const searchTerm = ref('');
const selectedGroup = ref('');
const groupError = ref('');
const hostGroups = ref([]);
const groupLoading = ref(false);

const hosts = ref([]);
const hostsLoading = ref(false);
const hostsError = ref('');

const selectedHost = ref(null);
const interfaces = ref([]);
const ifaceLoading = ref(false);

const ports = ref([]);
const portsLoading = ref(false);

const addLoading = ref(false);
const addResult = ref('');

const testHost = ref('');
const testPort = ref('');
const testOutput = ref('Output will appear here...');

const getCsrfToken = () => {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
};

const fmtDbm = (value) => {
  if (value === null || value === undefined) return '-';
  const num = Number(value);
  return Number.isFinite(num) ? `${num.toFixed(1)} dBm` : String(value);
};

const normalizeHost = (raw = {}) => ({
  hostid: raw.hostid || raw.host_id || null,
  name: raw.name || raw.host || raw.slug || 'Host',
  ip: raw.ip || raw.address || raw.primary_interface?.ip || '',
  status: raw.status ?? null,
  availability: raw.availability || raw.available || { value: raw.available ?? null },
});

const fetchJSON = async (url, options = {}) => {
  const resp = await fetch(url, { credentials: 'same-origin', ...options });
  let data = null;
  try {
    data = await resp.json();
  } catch (err) {
    data = null;
  }
  if (!resp.ok) {
    const baseMessage =
      (data && (data.error || data.message || data.detail)) || resp.statusText || 'Request failed';
    const error = new Error(baseMessage);
    error.payload = data;
    throw error;
  }
  return data;
};

const loadGroups = async () => {
  groupLoading.value = true;
  groupError.value = '';
  try {
    const payload = await fetchJSON(`${ZABBIX_LOOKUP_API}/lookup/host-groups/?exclude_empty=1`);
    const groups = payload?.data || [];
    hostGroups.value = groups
      .map((g) => {
        const id = g?.groupid || g?.group_id;
        if (!id) return null;
        const hostCount = Number(g?.host_count ?? g?.hosts ?? 0) || 0;
        const suffix = hostCount ? ` (${hostCount})` : '';
        return {
          value: id,
          label: `${g?.name || `Grupo ${id}`}${suffix}`,
        };
      })
      .filter(Boolean);
  } catch (err) {
    hostGroups.value = [];
    groupError.value = err?.message || 'Erro ao carregar grupos do Zabbix.';
    console.error('[ZabbixLookup] loadGroups failed', err);
  } finally {
    groupLoading.value = false;
  }
};

const searchHosts = async () => {
  hostsError.value = '';
  const q = searchTerm.value.trim();
  const group = selectedGroup.value.trim();
  if (!q && !group) {
    hostsError.value = 'Informe um termo ou grupo para buscar.';
    hosts.value = [];
    return;
  }
  hostsLoading.value = true;
  try {
    const params = new URLSearchParams();
    if (q) params.set('q', q);
    if (group) params.set('groupids', group);
    const data = await fetchJSON(`${ZABBIX_LOOKUP_API}/lookup/hosts/?${params.toString()}`);
    hosts.value = (data.data || []).map(normalizeHost);
  } catch (err) {
    hostsError.value = err.message || 'Erro ao buscar hosts.';
    hosts.value = [];
    console.error('[ZabbixLookup] searchHosts failed', err);
  } finally {
    hostsLoading.value = false;
  }
};

const refreshAvailability = async (hostid) => {
  if (!hostid) return;
  try {
    const payload = await fetchJSON(`${ZABBIX_LOOKUP_API}/lookup/hosts/${encodeURIComponent(hostid)}/status/`);
    const availability = payload?.data?.availability;
    const ip = payload?.data?.primary_interface?.ip;
    if (selectedHost.value && String(selectedHost.value.hostid) === String(hostid)) {
      selectedHost.value = {
        ...selectedHost.value,
        availability: availability || selectedHost.value.availability,
        ip: ip || selectedHost.value.ip,
      };
    }
  } catch (err) {
    addResult.value = `Availability lookup failed: ${err.message}`;
  }
};

const loadInterfaces = async (hostid) => {
  ifaceLoading.value = true;
  interfaces.value = [];
  try {
    const data = await fetchJSON(
      `${ZABBIX_LOOKUP_API}/lookup/hosts/${encodeURIComponent(hostid)}/interfaces/?only_main=true`,
    );
    interfaces.value = data.data || [];
  } catch (err) {
    addResult.value = `Erro ao carregar interfaces: ${err.message}`;
  } finally {
    ifaceLoading.value = false;
  }
};

const selectHost = async (host) => {
  if (!host?.hostid) {
    selectedHost.value = null;
    interfaces.value = [];
    ports.value = [];
    return;
  }
  selectedHost.value = { ...host };
  testHost.value = host.ip || testHost.value;
  addResult.value = '';
  await refreshAvailability(host.hostid);
  await loadInterfaces(host.hostid);
  ports.value = [];
};

const loadPorts = async (deviceId, deviceName) => {
  portsLoading.value = true;
  ports.value = [];
  try {
    const data = await fetchJSON(`${INVENTORY_API}/devices/${deviceId}/ports/optical/`);
    ports.value = data.ports || [];
    ports.value.forEach((p) => {
      if (!p.optical || (p.optical.rx_dbm == null && p.optical.tx_dbm == null)) {
        refreshOptical(p.id);
      }
    });
  } catch (err) {
    addResult.value = `Erro ao carregar portas: ${err.message}`;
  } finally {
    portsLoading.value = false;
  }
};

const addToInventory = async () => {
  if (!selectedHost.value?.hostid) return;
  addLoading.value = true;
  addResult.value = 'Adicionando...';
  try {
    const resp = await fetchJSON(`${INVENTORY_API}/devices/add-from-zabbix/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ hostid: selectedHost.value.hostid }),
    });
    const { device } = resp;
    const createdMessage = resp.created ? 'criado' : 'existente';
    addResult.value = `Device ${createdMessage}: ${device.name} (id=${device.id}). Ports detectadas: ${resp.total_ports_detected}.`;
    await loadPorts(device.id, device.name);
  } catch (err) {
    addResult.value = `Erro: ${err.message}`;
  } finally {
    addLoading.value = false;
  }
};

const refreshOptical = async (portId) => {
  try {
    const data = await fetchJSON(`${INVENTORY_API}/ports/${portId}/optical/`);
    ports.value = ports.value.map((p) =>
      p.id === portId ? { ...p, optical: data?.optical ?? p.optical } : p,
    );
  } catch (err) {
    addResult.value = `Optical error (${err.message})`;
  }
};

const viewTraffic = async (portId) => {
  try {
    const data = await fetchJSON(`${INVENTORY_API}/ports/${portId}/traffic/?period=24h`);
    const lastIn = data.in?.history?.at?.(-1)?.value ?? '-';
    const lastOut = data.out?.history?.at?.(-1)?.value ?? '-';
    alert(`Port #${portId}\nIN (latest): ${lastIn} ${data.in?.unit || ''}\nOUT (latest): ${lastOut} ${data.out?.unit || ''}`);
  } catch (err) {
    alert(`Erro ao obter tráfego: ${err.message}`);
  }
};

const runTest = async (url) => {
  try {
    const result = await fetchJSON(url);
    testOutput.value = JSON.stringify(result, null, 2);
  } catch (err) {
    testOutput.value = `Error: ${err.message}`;
  }
};

const runPing = () => {
  const ip = testHost.value.trim();
  if (!ip) return;
  runTest(`${INVENTORY_API}/diagnostics/ping/?ip=${encodeURIComponent(ip)}&count=1`);
};

const runTelnet = () => {
  const ip = testHost.value.trim();
  const port = testPort.value.trim() || '23';
  if (!ip) return;
  runTest(`${INVENTORY_API}/diagnostics/telnet/?ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`);
};

const runPingTelnet = () => {
  const ip = testHost.value.trim();
  const port = testPort.value.trim() || '23';
  if (!ip) return;
  runTest(`${INVENTORY_API}/diagnostics/ping-telnet/?ip=${encodeURIComponent(ip)}&port=${encodeURIComponent(port)}`);
};

onMounted(() => {
  loadGroups();
});

watch(selectedGroup, (val) => {
  if (val) {
    searchHosts();
  }
});

const StatusBadge = defineComponent({
  name: 'StatusBadge',
  props: {
    availability: {
      type: Object,
      default: () => ({}),
    },
    inline: {
      type: Boolean,
      default: false,
    },
  },
  setup(props) {
    const value = computed(() => {
      const v = props.availability?.value;
      if (v === undefined || v === null || v === '') return null;
      return String(v);
    });
    const label = computed(() => {
      if (value.value === '1') return 'Online';
      if (value.value === '2') return 'Offline';
      return props.availability?.label || 'Unknown';
    });
    const classes = computed(() => {
      if (value.value === '1') return 'border-green-200 bg-green-100 text-green-700';
      if (value.value === '2') return 'border-red-200 bg-red-100 text-red-700';
      return 'border-slate-200 bg-slate-100 text-slate-600';
    });
    return {
      label,
      classes,
    };
  },
  template: `
    <span :class="['inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium border', classes, inline ? 'align-middle' : '']">
      <span class="text-base leading-none">●</span>
      {{ inline ? label : 'DEVICE - ' + label }}
    </span>
  `,
});
</script>
