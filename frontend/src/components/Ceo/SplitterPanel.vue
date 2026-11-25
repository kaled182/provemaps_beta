<template>
  <section class="spp" data-testid="splitter-panel">
    <h4 class="spp-title">Splitters · {{ splitters.length }}</h4>
    <div v-if="!readonly" class="spp-add">
      <select v-model="ratio" class="spp-select" aria-label="Razão do splitter" data-testid="splitter-ratio">
        <option v-for="r in RATIOS" :key="r" :value="r">{{ r }}</option>
      </select>
      <button type="button" class="spp-btn" :disabled="busy" data-testid="splitter-add" @click="$emit('add', ratio)">Adicionar splitter</button>
    </div>
    <p v-if="!splitters.length" class="spp-empty">Sem splitters nesta caixa.</p>

    <article v-for="sp in splitters" :key="sp.id" class="spp-card" :data-testid="`splitter-${sp.id}`">
      <header class="spp-head">
        <b>{{ sp.name }}</b>
        <span class="spp-ratio num">{{ sp.ratio }} · −{{ fmt(sp.loss_db) }} dB</span>
        <span class="spp-counts">
          <span v-for="(n, st) in sp.counts" :key="st" v-show="n" class="spp-count" :class="`st-${st}`">{{ n }} {{ STATUS[st] }}</span>
        </span>
        <button v-if="!readonly" type="button" class="spp-del" :disabled="busy" :data-testid="`splitter-del-${sp.id}`" @click="$emit('remove', sp)">Remover</button>
      </header>

      <p class="spp-input" :data-testid="`splitter-input-${sp.id}`">
        Entrada:
        <template v-if="sp.input">
          <span class="spp-core" :style="{ background: sp.input.color_hex }" />
          {{ sp.input.cable_name }} · F{{ sp.input.absolute_number }} ({{ sp.input.color }})
          <button v-if="!readonly" type="button" class="spp-link" :disabled="busy" :data-testid="`splitter-unlink-${sp.id}`" @click="$emit('unlink-input', sp)">desligar</button>
        </template>
        <template v-else>
          <span class="text-neutral-500">sem fibra</span>
          <button
            v-if="!readonly"
            type="button"
            class="spp-link"
            :class="{ on: isPicking('input', sp.id) }"
            :data-testid="`splitter-pick-input-${sp.id}`"
            @click="$emit('pick-target', isPicking('input', sp.id) ? null : { type: 'input', splitterId: sp.id, label: `entrada do ${sp.name}` })"
          >
            {{ isPicking('input', sp.id) ? 'cancelar' : 'ligar entrada' }}
          </button>
        </template>
      </p>
      <p class="spp-power" :data-testid="`splitter-power-${sp.id}`">
        <template v-if="sp.power.dbm !== null && sp.power.dbm !== undefined">
          Chega <b class="num">{{ dbm(sp.power.dbm) }}</b>
          <span class="text-neutral-500"> · {{ sp.power.source === 'zabbix' ? 'TX do Zabbix' : 'TX padrão' }} em {{ sp.power.from }}, {{ fmt(sp.power.km) }} km, −{{ fmt(sp.power.loss_db) }} dB</span>
        </template>
        <span v-else class="text-neutral-500">Sem potência estimada: {{ sp.power.reason }}</span>
      </p>

      <div class="spp-ports">
        <button
          v-for="p in sp.ports"
          :key="p.number"
          type="button"
          class="spp-port"
          :class="[`st-${p.status}`, { sel: editing?.sp === sp.id && editing?.number === p.number }]"
          :title="`Porta ${p.number} · ${STATUS[p.status]}${p.customer ? ` · ${p.customer}` : ''}${p.output ? ` → ${p.output.cable_name} F${p.output.absolute_number}` : ''}`"
          :data-testid="`port-${sp.id}-${p.number}`"
          @click="openPort(sp, p)"
        >
          <span class="num spp-port-n">{{ p.number }}</span>
          <span class="num spp-port-dbm">{{ p.dbm === null || p.dbm === undefined ? '—' : fmt(p.dbm) }}</span>
        </button>
      </div>

      <!-- editor da porta escolhida -->
      <div v-if="editing && editing.sp === sp.id" class="spp-edit" :data-testid="`port-editor-${sp.id}`">
        <p class="spp-edit-title">Porta {{ editing.number }}<span v-if="currentPort(sp)?.dbm != null" class="num"> · ≈ {{ dbm(currentPort(sp).dbm) }}</span></p>
        <template v-if="!readonly">
          <div class="spp-row">
            <select v-model="form.status" class="spp-select" data-testid="port-status">
              <option v-for="(label, st) in STATUS" :key="st" :value="st">{{ label }}</option>
            </select>
            <input v-model.trim="form.customer" class="spp-in" :placeholder="form.status === 'reservada' ? 'Reservada para… (obrigatório)' : 'Cliente / ONU'" data-testid="port-customer" />
          </div>
          <input v-model.trim="form.note" class="spp-in spp-wide" placeholder="Nota (ex.: conector danificado)" data-testid="port-note" />
          <p class="spp-out">
            Saída:
            <template v-if="currentPort(sp)?.output">
              {{ currentPort(sp).output.cable_name }} · F{{ currentPort(sp).output.absolute_number }}
              <button type="button" class="spp-link" :disabled="busy" data-testid="port-unlink-output" @click="$emit('save-port', sp, editing.number, { output: null })">desligar</button>
            </template>
            <template v-else>
              <span class="text-neutral-500">direto ao cliente (sem fibra)</span>
              <button
                type="button"
                class="spp-link"
                :class="{ on: isPicking('output', sp.id, editing.number) }"
                data-testid="port-pick-output"
                @click="$emit('pick-target', isPicking('output', sp.id, editing.number) ? null : { type: 'output', splitterId: sp.id, number: editing.number, label: `saída da porta ${editing.number}` })"
              >
                {{ isPicking('output', sp.id, editing.number) ? 'cancelar' : 'ligar a uma fibra' }}
              </button>
            </template>
          </p>
          <div class="spp-row spp-end">
            <button type="button" class="spp-btn" @click="editing = null">Fechar</button>
            <button type="button" class="spp-btn spp-primary" :disabled="busy" data-testid="port-save" @click="save(sp)">Guardar</button>
          </div>
        </template>
        <template v-else>
          <p class="spp-ro">{{ STATUS[currentPort(sp)?.status] }}{{ currentPort(sp)?.customer ? ` · ${currentPort(sp).customer}` : '' }}{{ currentPort(sp)?.note ? ` · ${currentPort(sp).note}` : '' }}</p>
        </template>
      </div>
    </article>
  </section>
</template>

<script setup>
/**
 * Splitters na bandeja da CEO/CTO (EV-0142): entrada, portas com o estado de atendimento
 * (Livre/Reservada/Ocupada/Bloqueada), cliente, nota, fibra de saída e o dBm estimado por porta
 * (TX da fonte a montante − perdas − perda do splitter, calculado no servidor).
 */
import { reactive, ref } from 'vue'

const props = defineProps({
  splitters: { type: Array, required: true },
  readonly: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  /** {type: 'input'|'output', splitterId, number?} — escolher a fibra nas colunas */
  pickTarget: { type: Object, default: null },
})
const emit = defineEmits(['add', 'remove', 'unlink-input', 'pick-target', 'save-port'])

const RATIOS = ['1x2', '1x4', '1x8', '1x16', '1x32']
const STATUS = { livre: 'Livre', reservada: 'Reservada', ocupada: 'Ocupada', bloqueada: 'Bloqueada' }
const ratio = ref('1x8')
const editing = ref(null) // {sp, number}
const form = reactive({ status: 'livre', customer: '', note: '' })

const fmt = (v) => Number(v ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const dbm = (v) => `${v > 0 ? '+' : ''}${fmt(v)} dBm`
const isPicking = (type, sid, number) =>
  !!props.pickTarget && props.pickTarget.type === type && props.pickTarget.splitterId === sid && (number === undefined || props.pickTarget.number === number)
const currentPort = (sp) => sp.ports.find((p) => p.number === editing.value?.number)

function openPort(sp, p) {
  editing.value = { sp: sp.id, number: p.number }
  Object.assign(form, { status: p.status, customer: p.customer || '', note: p.note || '' })
}
function save(sp) {
  emit('save-port', sp, editing.value.number, { status: form.status, customer: form.customer, note: form.note })
}
</script>

<style scoped>
.spp {
  margin-top: 14px;
  padding-top: 10px;
  border-top: 1px solid rgb(var(--n-200));
}
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.spp-title {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.spp-add,
.spp-row {
  display: flex;
  gap: 6px;
  margin-bottom: 8px;
}
.spp-end {
  justify-content: flex-end;
}
.spp-empty,
.spp-ro {
  font-size: 12px;
  color: rgb(var(--n-500));
}
.spp-card {
  margin-bottom: 10px;
  padding: 8px 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  font-size: 12px;
  color: rgb(var(--n-900));
}
.spp-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}
.spp-ratio {
  color: rgb(var(--n-500));
}
.spp-counts {
  display: inline-flex;
  gap: 4px;
  flex-wrap: wrap;
}
.spp-count {
  padding: 0 6px;
  border-radius: 999px;
  font-size: 10px;
  border: 1px solid currentColor;
}
.spp-del {
  margin-left: auto;
  font-size: 11px;
  color: rgb(var(--danger));
}
.spp-input,
.spp-power,
.spp-out {
  margin: 6px 0 0;
}
.spp-core {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
  vertical-align: -1px;
}
.spp-link {
  margin-left: 6px;
  font-size: 11px;
  color: rgb(var(--primary-600));
  text-decoration: underline;
}
.spp-link.on {
  font-weight: 700;
}
.spp-ports {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(46px, 1fr));
  gap: 4px;
  margin-top: 8px;
}
.spp-port {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3px 0;
  border-radius: 6px;
  border: 1px solid currentColor;
  background: rgb(var(--surface));
}
.spp-port.sel {
  box-shadow: 0 0 0 2px rgb(var(--primary-500) / 0.45);
}
.spp-port-n {
  font-size: 11px;
  font-weight: 700;
}
.spp-port-dbm {
  font-size: 10px;
  color: rgb(var(--n-600));
}
/* estado da porta: livre verde, reservada âmbar, ocupada azul/info, bloqueada vermelho */
.st-livre {
  color: rgb(var(--success));
}
.st-reservada {
  color: rgb(var(--warning));
}
.st-ocupada {
  color: rgb(var(--info));
}
.st-bloqueada {
  color: rgb(var(--danger));
}
.spp-edit {
  margin-top: 8px;
  padding: 8px;
  border-radius: 8px;
  background: rgb(var(--canvas));
}
.spp-edit-title {
  margin: 0 0 6px;
  font-weight: 600;
}
.spp-select,
.spp-in {
  min-width: 0;
  padding: 4px 8px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 12px;
  color: rgb(var(--n-900));
}
.spp-in {
  flex: 1;
}
.spp-wide {
  width: 100%;
  margin-bottom: 4px;
}
.spp-btn {
  height: 28px;
  padding: 0 10px;
  border: 1px solid rgb(var(--n-300));
  border-radius: 6px;
  font-size: 12px;
  color: rgb(var(--n-700));
  background: rgb(var(--surface));
}
.spp-primary {
  border-color: rgb(var(--primary-600));
  background: rgb(var(--primary-600));
  @apply text-white;
}
.spp-btn:disabled {
  opacity: 0.5;
}
</style>
