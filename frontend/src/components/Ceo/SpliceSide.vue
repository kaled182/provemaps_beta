<template>
  <section class="ss" :data-testid="`splice-side-${side}`">
    <h4 class="ss-title">{{ title }}</h4>
    <p v-if="!groups.length" class="ss-empty">Nenhum cabo deste lado.</p>
    <div v-for="g in groups" :key="g.key" class="ss-cable">
      <p class="ss-cable-name">{{ g.cableName }} <span class="ss-toward">→ {{ g.toward }}</span></p>
      <div v-for="t in g.tubes" :key="t.number" class="ss-tube" :data-testid="`tube-${g.cableId}-${side}-${t.number}`">
        <header class="ss-tube-head">
          <button type="button" class="ss-tube-toggle" :aria-expanded="isOpen(g, t)" @click="toggle(g, t)">
            <span class="ss-caret" :class="{ open: isOpen(g, t) }" aria-hidden="true">›</span>
            <span class="ss-swatch" :style="{ background: t.colorHex }" aria-hidden="true" />
            Tubo {{ t.number }} · {{ t.color }}
          </button>
          <span class="ss-badge" :class="{ full: t.fused === t.ends.length }" :data-testid="`tube-badge-${g.cableId}-${side}-${t.number}`">
            {{ t.fused }}/{{ t.ends.length }}
          </span>
          <template v-if="!readonly">
            <button
              v-if="tubePick && !isTubePick(g, t)"
              type="button"
              class="ss-act ss-act-on"
              :data-testid="`tube-target-${g.cableId}-${side}-${t.number}`"
              @click="$emit('tube-target', { cable_id: g.cableId, tube_number: t.number, side })"
            >
              Fundir aqui
            </button>
            <button
              v-else
              type="button"
              class="ss-act"
              :class="{ 'ss-act-on': isTubePick(g, t) }"
              :title="isTubePick(g, t) ? 'Cancelar' : 'Fusionar este tubo cor com cor com um tubo do outro lado'"
              :data-testid="`tube-11-${g.cableId}-${side}-${t.number}`"
              @click="$emit('tube-pick', isTubePick(g, t) ? null : { cable_id: g.cableId, tube_number: t.number, side, label: `${g.cableName} T${t.number}` })"
            >
              {{ isTubePick(g, t) ? 'Cancelar' : '1:1' }}
            </button>
          </template>
        </header>
        <div v-if="isOpen(g, t)" class="ss-fibers">
          <button
            v-for="e in t.ends"
            :key="e.key"
            type="button"
            class="ss-fiber"
            :class="{ used: e.fusion_id || e.splitter_use, picked: picked === e.key }"
            :disabled="readonly || !!e.fusion_id || !!e.splitter_use"
            :title="partnerOf(e) ? `Fusionada com ${partnerOf(e)}` : e.splitter_use ? `Ligada a ${e.splitter_use}` : `Fibra ${e.absolute_number} · ${e.color}`"
            :data-testid="`fiber-${e.key}`"
            @click="$emit('pick', e)"
          >
            <span class="ss-core" :style="{ background: e.color_hex }" aria-hidden="true" />
            <span class="num">{{ e.number }}</span>
            <span v-if="partnerOf(e)" class="ss-partner">↔ {{ partnerOf(e) }}</span>
            <span v-else-if="e.splitter_use" class="ss-partner">⑂ {{ e.splitter_use }}</span>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
/** Uma coluna do editor da caixa (EV-0141): cabos → tubos em acordeão → fibras. */
import { reactive } from 'vue'

const props = defineProps({
  side: { type: String, required: true },
  title: { type: String, required: true },
  /** [{key, cableId, cableName, toward, tubes: [{number, color, colorHex, fused, ends: []}]}] */
  groups: { type: Array, required: true },
  /** fusion_id → texto curto da outra ponta */
  partners: { type: Object, default: () => ({}) },
  picked: { type: String, default: null },
  tubePick: { type: Object, default: null },
  readonly: { type: Boolean, default: false },
})
defineEmits(['pick', 'tube-pick', 'tube-target'])

// o 1.º tubo de cada cabo abre aberto; os outros abrem com um clique
const open = reactive({})
const k = (g, t) => `${g.key}:${t.number}`
const isOpen = (g, t) => (k(g, t) in open ? open[k(g, t)] : t.number === g.tubes[0]?.number)
const toggle = (g, t) => (open[k(g, t)] = !isOpen(g, t))
const isTubePick = (g, t) =>
  !!props.tubePick && props.tubePick.cable_id === g.cableId && props.tubePick.tube_number === t.number && props.tubePick.side === props.side
const partnerOf = (e) => (e.fusion_id ? props.partners[`${e.fusion_id}:${e.key}`] : '')
</script>

<style scoped>
.ss {
  min-width: 0;
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.ss-title {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.ss-empty {
  font-size: 12px;
  color: rgb(var(--n-500));
}
.ss-cable {
  margin-bottom: 10px;
}
.ss-cable-name {
  margin: 0 0 4px;
  font-size: 13px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.ss-toward {
  font-weight: 400;
  font-size: 11px;
  color: rgb(var(--n-500));
}
.ss-tube {
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  margin-bottom: 6px;
  background: rgb(var(--surface));
}
.ss-tube-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
}
.ss-tube-toggle {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 12px;
  font-weight: 600;
  color: rgb(var(--n-800));
  text-align: left;
}
.ss-caret {
  display: inline-block;
  transition: transform 0.12s;
  color: rgb(var(--n-500));
}
.ss-caret.open {
  transform: rotate(90deg);
}
.ss-swatch {
  width: 18px;
  height: 8px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
  flex: none;
}
.ss-badge {
  font-size: 11px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgb(var(--n-100));
  color: rgb(var(--n-700));
  font-family: 'JetBrains Mono', ui-monospace, monospace;
}
.ss-badge.full {
  background: rgb(var(--info) / 0.15);
  color: rgb(var(--info));
}
.ss-act {
  height: 22px;
  padding: 0 8px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 11px;
  color: rgb(var(--n-700));
}
.ss-act-on {
  border-color: rgb(var(--primary-600));
  color: rgb(var(--primary-700));
  background: rgb(var(--primary-500) / 0.12);
}
.ss-fibers {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 2px 8px 8px;
}
.ss-fiber {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 11px;
  color: rgb(var(--n-800));
  background: rgb(var(--surface));
}
.ss-fiber:hover:not(:disabled) {
  border-color: rgb(var(--primary-500));
}
.ss-fiber.used {
  border-color: rgb(var(--info) / 0.5);
  background: rgb(var(--info) / 0.07);
  cursor: default;
}
.ss-fiber.picked {
  border-color: rgb(var(--primary-600));
  box-shadow: 0 0 0 2px rgb(var(--primary-500) / 0.35);
}
.ss-core {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
}
.ss-partner {
  color: rgb(var(--info));
}
</style>
