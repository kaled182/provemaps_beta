<template>
  <div class="h-full flex flex-col bg-canvas text-neutral-900">
    <header class="flex-none px-4 md:px-6 py-2 border-b border-neutral-200 bg-surface flex items-center gap-3 flex-wrap">
      <h1 class="text-base font-semibold mr-2">Topologia</h1>
      <span class="flex items-center gap-3 text-xs text-neutral-600" aria-label="Legenda">
        <span v-for="(label, key) in LEGEND" :key="key" class="flex items-center gap-1">
          <span class="legend-line" :class="`stroke-${key}`"></span>{{ label }}
        </span>
      </span>
      <span v-if="topo" class="ml-auto text-xs text-neutral-500 font-mono tabular-nums" data-testid="topology-counts">
        {{ topo.nodes.length }} POPs · {{ topo.edges.length }} enlaces
      </span>
      <button type="button" class="px-2 py-1.5 rounded-md text-neutral-600 hover:bg-neutral-100" :class="{ 'ml-auto': !topo }" title="Atualizar" :disabled="loading" @click="load">
        <i class="fas fa-rotate" :class="{ 'animate-spin': loading }"></i>
      </button>
    </header>

    <main class="flex-1 min-h-0 overflow-auto px-4 md:px-6 py-3 grid gap-3 lg:grid-cols-[1fr_340px]">
      <p v-if="error" class="lg:col-span-2 px-3 py-2 rounded-md border border-danger/40 bg-danger/10 text-sm text-danger" role="alert">
        Erro ao carregar a topologia: {{ error }}
      </p>

      <section class="rounded-lg border border-neutral-200 bg-surface min-h-[360px] relative">
        <p v-if="loading && !topo" class="p-4 text-sm text-neutral-500">Carregando topologia…</p>
        <p v-else-if="topo && !topo.nodes.length" class="p-4 text-sm text-neutral-500">Nenhum enlace entre POPs com coordenadas.</p>
        <svg
          v-else-if="topo"
          :viewBox="`0 0 ${W} ${H}`"
          class="w-full h-full"
          role="img"
          aria-label="Topologia esquemática dos POPs e enlaces"
          data-testid="topology-svg"
        >
          <g>
            <path
              v-for="p in paths"
              :key="p.edge.id"
              :d="p.d"
              fill="none"
              class="edge"
              :class="[`stroke-${p.edge.health}`, { 'edge-active': selected?.id === p.edge.id }]"
              :data-testid="`edge-${p.edge.id}`"
              tabindex="0"
              @mouseenter="selected = p.edge"
              @focus="selected = p.edge"
              @click="selected = p.edge"
            >
              <title>{{ p.edge.name }}</title>
            </path>
          </g>
          <g>
            <g v-for="n in placedNodes" :key="n.id" :transform="`translate(${n.x} ${n.y})`" :data-testid="`node-${n.id}`">
              <circle r="7" class="node" />
              <text y="-12" text-anchor="middle" class="node-label">{{ shortName(n.name) }}</text>
            </g>
          </g>
        </svg>
      </section>

      <aside class="flex flex-col gap-3 min-w-0">
        <div class="rounded-lg border border-neutral-200 bg-surface p-3" data-testid="topology-detail">
          <template v-if="selected">
            <h2 class="text-sm font-semibold">{{ selected.name }}</h2>
            <dl class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
              <dt class="text-neutral-500">Estado</dt><dd>{{ LEGEND[selected.health] || selected.health }}</dd>
              <dt class="text-neutral-500">Trecho</dt><dd>{{ nodeName(selected.source) }} ↔ {{ nodeName(selected.target) }}</dd>
              <dt class="text-neutral-500">Extensão</dt><dd class="num">{{ selected.length_km !== null ? `${selected.length_km.toFixed(2)} km` : '—' }}</dd>
              <dt class="text-neutral-500">Capacidade</dt><dd>{{ capacityLabel(selected) }}</dd>
            </dl>
          </template>
          <p v-else class="text-sm text-neutral-500">Passe o rato ou clique num enlace para ver o detalhe.</p>
        </div>

        <div v-if="topo && topo.strands_registered === 0" class="rounded-lg border border-neutral-200 bg-surface p-3 text-xs text-neutral-600" data-testid="topology-no-strands">
          Nenhuma fibra cadastrada: a ocupação por trecho fica «sem dados» até as fibras dos cabos serem registadas no inventário.
        </div>

        <div v-if="topo?.unplaced.length" class="rounded-lg border border-warning/40 bg-surface p-3" data-testid="topology-unplaced">
          <h2 class="text-xs font-semibold uppercase tracking-wide text-warning">Fora do desenho · {{ topo.unplaced.length }}</h2>
          <ul class="mt-2 flex flex-col gap-1 text-sm">
            <li v-for="u in topo.unplaced" :key="u.id">
              <span class="font-medium">{{ u.name }}</span>
              <span class="text-neutral-500"> — {{ u.reason }}</span>
            </li>
          </ul>
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
/**
 * Topologia (EV-0060, ADR 0009): POPs projetados pelas coordenadas, enlaces
 * coloridos pelo estado óptico; capacidade só com fibras cadastradas.
 */
import { computed, onMounted, ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { capacityLabel, edgePaths, projectNodes } from '@/utils/topologyLayout'

const W = 1000
const H = 640
const LEGEND = { healthy: 'Saudável', attention: 'Atenção', critical: 'Crítico', unknown: 'Sem leitura' }

const api = useApi()
const topo = ref(null)
const loading = ref(false)
const error = ref('')
const selected = ref(null)

const positions = computed(() => projectNodes(topo.value?.nodes || [], { width: W, height: H }))
const placedNodes = computed(() =>
  (topo.value?.nodes || []).filter((n) => positions.value.has(n.id)).map((n) => ({ ...n, ...positions.value.get(n.id) })),
)
const paths = computed(() => edgePaths(topo.value?.edges || [], positions.value))

const nodeName = (id) => topo.value?.nodes.find((n) => n.id === id)?.name || '—'
const shortName = (name) => String(name || '').replace(/^SITE\s*-\s*/i, '').trim()

async function load() {
  loading.value = true
  error.value = ''
  try {
    topo.value = await api.get('/api/v1/fiber-cables/topology/')
  } catch (e) {
    error.value = e?.message || 'erro desconhecido'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.edge {
  stroke-width: 3;
  stroke-linecap: round;
  cursor: pointer;
  outline: none;
}
.edge:hover,
.edge:focus,
.edge-active {
  stroke-width: 6;
}
.stroke-healthy { stroke: rgb(var(--success)); }
.stroke-attention { stroke: rgb(var(--warning)); }
.stroke-critical { stroke: rgb(var(--danger)); }
.stroke-unknown { stroke: rgb(var(--n-400)); stroke-dasharray: 6 5; }
.node {
  fill: rgb(var(--surface));
  stroke: rgb(var(--n-700));
  stroke-width: 2;
}
.node-label {
  font-size: 12px;
  font-weight: 600;
  fill: rgb(var(--n-800));
  paint-order: stroke;
  stroke: rgb(var(--surface));
  stroke-width: 3px;
}
.legend-line {
  display: inline-block;
  width: 18px;
  height: 0;
  border-top: 3px solid rgb(var(--n-400));
}
.legend-line.stroke-healthy { border-top-color: rgb(var(--success)); }
.legend-line.stroke-attention { border-top-color: rgb(var(--warning)); }
.legend-line.stroke-critical { border-top-color: rgb(var(--danger)); }
.legend-line.stroke-unknown { border-top-style: dashed; }
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
</style>
