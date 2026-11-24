<template>
  <section class="rounded-lg border border-neutral-200 bg-surface" :data-testid="`gpon-chassis-${olt.device_id}`">
    <header class="flex items-center gap-3 flex-wrap px-3 py-2 border-b border-neutral-200 text-sm">
      <PhHardDrives :size="16" class="text-neutral-500" />
      <span class="font-semibold">{{ olt.name }}</span>
      <span class="text-xs text-neutral-500">{{ vendorModel }}</span>
      <span class="num text-xs text-neutral-600">{{ olt.ip || '—' }}</span>
      <span v-if="olt.status === 'offline'" class="flag flag-danger">offline</span>
      <span v-else-if="olt.status === 'unknown'" class="flag">estado desconhecido</span>
      <span v-if="olt.collection_ok === false" class="flag flag-warning" data-testid="gpon-chassis-nodata">coleta sem dados</span>
      <span class="ml-auto flex items-center gap-3 text-xs text-neutral-600 num">
        <span title="CPU"><PhCpu :size="13" class="inline -mt-0.5" /> {{ formatPercent(olt.cpu_pct) }}</span>
        <span title="Temperatura"><PhThermometer :size="13" class="inline -mt-0.5" /> {{ isNum(olt.temperature_c) ? `${formatNumber(olt.temperature_c, 0)} °C` : '—' }}</span>
        <span title="ONUs online / total">{{ formatInt(olt.onus_online) }}/{{ formatInt(olt.onus_total) }} ONUs</span>
      </span>
    </header>

    <div class="split p-3">
      <div ref="wrap" class="stage" @mouseleave="tip = null">
        <ChassisZteC300
          v-if="layout === 'zte_c300' || layout === 'zte_modular'"
          :chassis="chassis"
          :pons="pons"
          :visible-pon-ids="visiblePonIds"
          :selected-port="portId"
          :selected-slot="slotNum"
          @toggle-pon="(id) => $emit('toggle-pon', olt.device_id, id)"
          @toggle-slot="(n) => $emit('toggle-slot', olt.device_id, n)"
          @hover="onHover"
        />
        <ChassisRack1u
          v-else
          :chassis="chassis"
          :pons="pons"
          :olt="olt"
          :visible-pon-ids="visiblePonIds"
          :selected-port="portId"
          @toggle-pon="(id) => $emit('toggle-pon', olt.device_id, id)"
          @hover="onHover"
        />
        <div
          v-if="tip"
          class="tip num"
          :class="{ 'tip-below': tip.below }"
          :style="{ left: `${tip.left}px`, top: `${tip.top}px` }"
          role="tooltip"
          data-testid="chassis-tooltip"
        >
          {{ tip.text }}
        </div>
      </div>

      <PonInspector
        :port-id="inspectPortId"
        :pon="selectedPonObj"
        :preview="isPreview"
        :ports-count="pons.length"
        @clear="$emit('clear-selection')"
        :port-status="selectedPortStatus"
        :card="selectedCard"
        :card-pons="selectedCardPons"
        :thresholds="thresholds"
      />
    </div>
  </section>
</template>

<script setup>
/**
 * Uma OLT na vista do chassi (EV-0101): cabeçalho como o OltCard + painel frontal (70 %)
 * e inspetor (340 px a partir de 1280 px), empilhados em ecrã estreito. O chassi usa TODAS as PONs da OLT
 * (`pons`) para os LEDs; as que a pílula esconde ficam esbatidas, não apagadas.
 */
import { computed, ref } from 'vue'
import { PhCpu, PhHardDrives, PhThermometer } from '@phosphor-icons/vue'
import ChassisZteC300 from './ChassisZteC300.vue'
import ChassisRack1u from './ChassisRack1u.vue'
import PonInspector from './PonInspector.vue'
import { indexPons, mostCriticalPon, slotPons } from './chassisLed'
import { formatInt, formatNumber, formatPercent } from '@/utils/ptBrFormat'

const props = defineProps({
  /** OLT como vem de visibleOlts (pons já filtradas pela pílula). */
  olt: { type: Object, required: true },
  /** Todas as PONs da OLT (sem filtro), para os LEDs e o inspetor. */
  pons: { type: Array, default: () => [] },
  /** true quando há pílula ativa (as PONs fora dela ficam esbatidas). */
  filtered: { type: Boolean, default: false },
  selectedPon: { type: String, default: null },
  selectedSlot: { type: String, default: null },
  thresholds: { type: Object, default: null },
})
defineEmits(['toggle-pon', 'toggle-slot', 'clear-selection'])

const isNum = (v) => v !== null && v !== undefined && Number.isFinite(Number(v))

const vendorModel = computed(() =>
  [props.olt.vendor ? props.olt.vendor.toUpperCase() : null, props.olt.model, props.olt.technology?.toUpperCase()]
    .filter(Boolean)
    .join(' · '),
)

/** Sem `chassis` no payload (versão antiga): 1U com as PONs conhecidas em estado desconhecido. */
const chassis = computed(
  () =>
    props.olt.chassis || {
      layout: 'rack_1u',
      slots: [],
      ports: props.pons.map((p, i) => ({ port_id: String(p.pon_id), port: i + 1, status: 'unknown' })),
    },
)
const layout = computed(() => chassis.value.layout)
const visiblePonIds = computed(() => (props.filtered ? (props.olt.pons || []).map((p) => String(p.pon_id)) : null))

const ownPrefix = computed(() => `${props.olt.device_id}:`)
const ownPart = (key) => (key !== null && key.startsWith(ownPrefix.value) ? key.slice(ownPrefix.value.length) : null)
const portId = computed(() => ownPart(props.selectedPon))
const slotNum = computed(() => {
  const s = ownPart(props.selectedSlot)
  return s === null ? null : Number(s)
})

const ponIdx = computed(() => indexPons(props.pons))
// EV-0106: sem porta nem placa selecionadas nesta OLT, o inspetor mostra já a PON mais crítica
// («pré-visualização» — não filtra a tabela; clicar na porta é que seleciona).
const previewPortId = computed(() => (portId.value === null && slotNum.value === null ? mostCriticalPon(props.pons) : null))
const isPreview = computed(() => previewPortId.value !== null)
const inspectPortId = computed(() => portId.value ?? previewPortId.value)
const selectedPonObj = computed(() => (inspectPortId.value === null ? null : ponIdx.value.get(inspectPortId.value) || null))
const allPorts = computed(() => [
  ...(chassis.value.ports || []),
  ...(chassis.value.slots || []).flatMap((s) => s.ports || []),
])
const selectedPortStatus = computed(
  () => allPorts.value.find((p) => String(p.port_id) === inspectPortId.value)?.status || null,
)
const selectedCard = computed(
  () => (slotNum.value === null ? null : (chassis.value.slots || []).find((s) => Number(s.slot) === slotNum.value) || null),
)
const selectedCardPons = computed(() => (selectedCard.value ? slotPons(selectedCard.value.slot, ponIdx.value) : []))

// Tooltip HTML junto da porta: posição pela caixa do elemento em relação ao palco.
const wrap = ref(null)
const tip = ref(null)
function onHover(payload) {
  if (!payload || !wrap.value) {
    tip.value = null
    return
  }
  const r = payload.el.getBoundingClientRect()
  const w = wrap.value.getBoundingClientRect()
  const below = r.top - w.top < 36
  tip.value = {
    text: payload.text,
    // o texto está centrado na porta; não deixa sair pelas bordas do palco
    left: Math.min(Math.max(r.left - w.left + r.width / 2, 130), Math.max(w.width - 130, 130)),
    top: below ? r.bottom - w.top : r.top - w.top,
    below,
  }
}
</script>

<style scoped>
.num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
}
/* EV-0102: chassi elástico + inspetor fixo de 300 px a partir de xl (1280 px); abaixo empilha.
   O 7fr/3fr cortava o 1U à direita: o SVG tem largura mínima e o 3fr roubava-a. */
.split {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}
@media (min-width: 1280px) {
  .split {
    grid-template-columns: minmax(0, 1fr) 340px;
  }
}
.stage {
  position: relative;
  min-width: 0;
}
.tip {
  position: absolute;
  z-index: 5;
  transform: translate(-50%, calc(-100% - 6px));
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 11.5px;
  white-space: nowrap;
  pointer-events: none;
  color: rgb(var(--n-50));
  background: rgb(var(--n-900));
  box-shadow: 0 4px 12px rgb(var(--n-950) / 0.25);
}
.tip-below {
  transform: translate(-50%, 6px);
}
.flag {
  padding: 0 6px;
  border-radius: 4px;
  font-size: 11px;
  color: rgb(var(--n-600));
  border: 1px solid rgb(var(--n-300));
}
.flag-danger {
  color: rgb(var(--danger));
  border-color: rgb(var(--danger) / 0.4);
}
.flag-warning {
  color: rgb(var(--warning));
  border-color: rgb(var(--warning) / 0.4);
}
</style>
