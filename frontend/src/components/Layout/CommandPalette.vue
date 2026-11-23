<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[2000] flex items-start justify-center bg-neutral-950/50 px-4 pt-[12vh]"
      data-testid="command-palette"
      @mousedown.self="close"
    >
      <div
        class="w-full max-w-xl overflow-hidden rounded-lg border border-neutral-200 bg-surface shadow-2xl"
        role="dialog"
        aria-modal="true"
        aria-label="Busca rápida"
      >
        <div class="flex items-center gap-2 border-b border-neutral-200 px-3">
          <PhMagnifyingGlass :size="18" class="shrink-0 text-neutral-500" />
          <input
            ref="inputEl"
            v-model="query"
            type="text"
            class="h-11 w-full bg-transparent text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none"
            placeholder="Buscar site, cabo, dispositivo ou página…"
            aria-label="Termo de busca"
            data-testid="command-palette-input"
            @keydown.down.prevent="move(1)"
            @keydown.up.prevent="move(-1)"
            @keydown.enter.prevent="choose(flat[activeIdx])"
            @keydown.esc.prevent="close"
          />
          <kbd class="hidden rounded border border-neutral-200 px-1.5 py-0.5 font-mono text-[10px] text-neutral-500 sm:inline">Esc</kbd>
        </div>

        <div class="max-h-[60vh] overflow-y-auto py-1">
          <p v-if="!query.trim()" class="px-4 py-6 text-center text-xs text-neutral-500">
            Digite pelo menos 2 caracteres. ↑ ↓ para navegar, Enter para abrir.
          </p>

          <template v-else>
            <section v-for="group in groups" :key="group.label">
              <h3 class="px-4 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-wider text-neutral-500">
                {{ group.label }}
              </h3>
              <button
                v-for="item in group.items"
                :key="item.key"
                type="button"
                class="flex w-full items-center gap-3 px-4 py-2 text-left text-sm"
                :class="[
                  item.idx === activeIdx ? 'bg-primary-500/10 text-neutral-900' : 'text-neutral-700',
                  item.disabled ? 'cursor-not-allowed opacity-50' : 'hover:bg-neutral-100',
                ]"
                :disabled="item.disabled"
                :data-testid="`command-item-${item.key}`"
                @mouseenter="activeIdx = item.idx"
                @click="choose(item)"
              >
                <component :is="item.icon" :size="16" class="shrink-0 text-neutral-500" />
                <span class="min-w-0 flex-1 truncate">{{ item.label }}</span>
                <span class="max-w-[45%] truncate text-xs text-neutral-500">{{ item.hint }}</span>
              </button>
            </section>

            <p v-if="loading" class="px-4 py-3 text-xs text-neutral-500">Buscando no inventário…</p>
            <p v-else-if="error" class="px-4 py-3 text-xs text-danger">
              Erro ao consultar o inventário: {{ error }}
            </p>
            <p
              v-else-if="!flat.length && query.trim().length >= 2"
              class="px-4 py-6 text-center text-xs text-neutral-500"
            >
              Nada encontrado para «{{ query.trim() }}».
            </p>
          </template>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * Paleta de comandos (Ctrl K / ⌘K) — EV-0044.
 * Páginas vêm de `NAV_SECTIONS`; sites, cabos e dispositivos de
 * `GET /api/v1/inventory/search/`. Um resultado com coordenadas abre o
 * Projeto de rede centrado nele (`?foco=<tipo>&id=&lat=&lng=`).
 */
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import {
  PhMagnifyingGlass,
  PhMapPin,
  PhLineSegments,
  PhCpu,
} from '@phosphor-icons/vue';
import { useApi } from '@/composables/useApi';
import { searchPages } from '@/composables/useNavSections';
import { buildFocusLocation } from '@/utils/mapFocus';

const MIN_QUERY = 2;
const DEBOUNCE_MS = 250;

const TYPE_META = {
  site: { group: 'Sites', icon: PhMapPin },
  cable: { group: 'Cabos', icon: PhLineSegments },
  device: { group: 'Dispositivos', icon: PhCpu },
};

const open = defineModel('open', { type: Boolean, default: false });

const router = useRouter();
const api = useApi();

const query = ref('');
const results = ref([]);
const loading = ref(false);
const error = ref('');
const activeIdx = ref(0);
const inputEl = ref(null);

let debounceTimer = null;
let requestSeq = 0;

const groups = computed(() => {
  const out = [];
  let idx = 0;
  const pages = searchPages(query.value).map((p) => ({
    key: `page-${p.path}`,
    kind: 'page',
    label: p.label,
    hint: p.section,
    icon: p.icon,
    path: p.path,
    external: Boolean(p.external),
    idx: idx++,
  }));
  if (pages.length) out.push({ label: 'Páginas', items: pages });

  for (const type of ['site', 'cable', 'device']) {
    const items = results.value
      .filter((r) => r.type === type)
      .map((r) => {
        const hasCoords = r.lat != null && r.lng != null;
        return {
          key: `${type}-${r.id}`,
          kind: 'inventory',
          raw: r,
          label: r.name,
          hint: hasCoords ? r.subtitle || '' : 'sem coordenadas',
          icon: TYPE_META[type].icon,
          disabled: !hasCoords,
          idx: idx++,
        };
      });
    if (items.length) out.push({ label: TYPE_META[type].group, items });
  }
  return out;
});

const flat = computed(() => groups.value.flatMap((g) => g.items));

function move(dir) {
  const total = flat.value.length;
  if (!total) return;
  let next = activeIdx.value;
  for (let i = 0; i < total; i += 1) {
    next = (next + dir + total) % total;
    if (!flat.value[next].disabled) break;
  }
  activeIdx.value = next;
}

async function runSearch(term) {
  const seq = ++requestSeq;
  loading.value = true;
  error.value = '';
  try {
    const data = await api.get('/api/v1/inventory/search/', { q: term });
    if (seq !== requestSeq) return;
    results.value = Array.isArray(data?.results) ? data.results : [];
  } catch (e) {
    if (seq !== requestSeq) return;
    results.value = [];
    error.value = e?.message || 'erro desconhecido';
  } finally {
    if (seq === requestSeq) loading.value = false;
  }
}

watch(query, (value) => {
  clearTimeout(debounceTimer);
  activeIdx.value = 0;
  const term = value.trim();
  if (term.length < MIN_QUERY) {
    requestSeq += 1; // descarta respostas em voo
    results.value = [];
    loading.value = false;
    error.value = '';
    return;
  }
  debounceTimer = setTimeout(() => runSearch(term), DEBOUNCE_MS);
});

function close() {
  open.value = false;
}

function choose(item) {
  if (!item || item.disabled) return;
  if (item.kind === 'page') {
    if (item.external) {
      window.location.assign(item.path);
    } else {
      router.push(item.path);
    }
  } else {
    const location = buildFocusLocation(item.raw);
    if (!location) return;
    router.push(location);
  }
  close();
}

watch(open, async (isOpen) => {
  if (isOpen) {
    query.value = '';
    results.value = [];
    error.value = '';
    activeIdx.value = 0;
    await nextTick();
    inputEl.value?.focus();
  } else {
    clearTimeout(debounceTimer);
    requestSeq += 1;
  }
});

function onGlobalKeydown(event) {
  if ((event.ctrlKey || event.metaKey) && (event.key === 'k' || event.key === 'K')) {
    event.preventDefault();
    open.value = !open.value;
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKeydown));
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onGlobalKeydown);
  clearTimeout(debounceTimer);
});
</script>
