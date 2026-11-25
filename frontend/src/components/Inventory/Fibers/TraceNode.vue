<template>
  <div class="tn" :class="{ 'tn-dim': !node.focus }">
    <ol class="ft-steps">
      <li v-for="(s, i) in node.steps" :key="i" class="ft-step" :class="`ft-${s.type}`" :data-testid="`trace-step-${s.type}`">
        <template v-if="s.type === 'port'">
          <b>{{ s.device_name }}</b> → <span class="num">{{ s.port_name }}</span>
          <span v-if="s.site_name" class="ft-sub"> · {{ s.site_name }}</span>
        </template>
        <template v-else-if="s.type === 'cable'">
          <span class="core" :style="{ background: s.color_hex }" aria-hidden="true" />
          {{ s.cable_name }} · F{{ s.absolute_number }} ({{ s.color }})
          <span class="ft-sub">rumo a {{ s.toward }} · <span class="num">{{ fmtKm(s.km) }}</span></span>
          <span v-if="s.passes?.length" class="ft-sub"> · passa direto: {{ s.passes.join(', ') }}</span>
          <span v-if="s.broken" class="text-danger"> · rompido</span>
          <span class="ft-sub num"> · −{{ db(s.loss_db) }}</span>
          <span class="ft-acc num">{{ fmtKm(s.acc_km) }}<template v-if="s.dbm != null"> · <b>{{ fmtDbm(s.dbm) }}</b></template></span>
        </template>
        <template v-else-if="s.type === 'fusion'">
          Fusão na <b>{{ s.ceo_name }}</b>
          <span v-if="s.tray" class="ft-sub num"> · bandeja {{ s.tray }}{{ s.slot ? `, posição ${s.slot}` : '' }}</span>
          <span class="ft-sub num"> · −{{ db(s.loss_db) }}</span>
          <span v-if="s.dbm != null" class="ft-acc num"><b>{{ fmtDbm(s.dbm) }}</b></span>
        </template>
        <template v-else-if="s.type === 'splitter'">
          Splitter {{ s.ratio }} na <b>{{ s.ceo_name }}</b> (porta {{ s.port }})
          <span class="ft-sub num"> · −{{ db(s.loss_db) }}</span>
          <span v-if="s.dbm != null" class="ft-acc num"><b>{{ fmtDbm(s.dbm) }}</b></span>
        </template>
      </li>
      <li v-if="node.splitter" class="ft-step ft-splitter" data-testid="trace-splitter">
        <b>{{ node.splitter.name }}</b> ({{ node.splitter.ratio }}) na <b>{{ node.splitter.ceo_name }}</b>
        <span class="ft-sub num"> · −{{ db(node.splitter.loss_db) }}</span>
        <span v-if="node.splitter.dbm_out != null" class="ft-acc num">saída <b>{{ fmtDbm(node.splitter.dbm_out) }}</b></span>
      </li>
    </ol>
    <p v-if="!node.splitter && !node.focus" class="ft-sub tn-end" data-testid="trace-node-end">Fim: {{ node.end.label }}</p>

    <ul v-if="node.splitter" class="tn-branches">
      <li v-for="b in node.branches" :key="b.number" class="tn-branch" :data-testid="`trace-branch-${b.number}`">
        <button
          v-if="b.node"
          type="button"
          class="tn-toggle"
          :aria-expanded="isOpen(b)"
          :class="{ 'tn-focus': b.node.focus }"
          @click="toggle(b)"
        >
          {{ isOpen(b) ? '▾' : '▸' }} Porta {{ b.number }}
          <span class="tn-st" :class="`st-${b.status}`">{{ STATUS[b.status] || b.status }}</span>
          <span v-if="b.customer" class="ft-sub"> · {{ b.customer }}</span>
          <span class="ft-acc num">{{ fmtKm(b.node.km) }}<template v-if="b.node.dbm != null"> · {{ fmtDbm(b.node.dbm) }}</template></span>
        </button>
        <span v-else class="tn-leaf">
          Porta {{ b.number }}
          <span class="tn-st" :class="`st-${b.status}`">{{ STATUS[b.status] || b.status }}</span>
          <span v-if="b.customer" class="ft-sub"> · {{ b.customer }}</span>
          <span v-if="b.dbm != null" class="ft-acc num ft-sub">{{ fmtDbm(b.dbm) }}</span>
        </span>
        <TraceNode v-if="b.node && isOpen(b)" :node="b.node" class="tn-child" />
      </li>
    </ul>
  </div>
</template>

<script setup>
/** Um nó do rastreamento em árvore (EV-0143): passos até ao fim ou ao splitter, e os ramos. */
import { reactive } from 'vue'
import { fmtDbm, fmtKm } from '@/utils/traceTree'

defineProps({ node: { type: Object, required: true } })
const STATUS = { livre: 'livre', reservada: 'reservada', ocupada: 'ocupada', bloqueada: 'bloqueada' }
const fmtDec = (v) => Number(v ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const db = (v) => `${fmtDec(v)} dB`

// o ramo em foco abre sozinho; os outros ficam fechados até ao clique
const open = reactive({})
const isOpen = (b) => open[b.number] ?? !!b.node?.focus
const toggle = (b) => {
  open[b.number] = !isOpen(b)
}
</script>

<style scoped>
.num {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.ft-steps {
  margin: 0;
  padding: 0;
  list-style: none;
  border-left: 2px solid rgb(var(--primary-500));
}
.tn-dim > .ft-steps {
  border-left-color: rgb(var(--n-200));
}
.ft-step {
  position: relative;
  margin: 0 0 6px;
  padding-left: 12px;
  color: rgb(var(--n-900));
}
.ft-step::before {
  content: '';
  position: absolute;
  left: -5px;
  top: 5px;
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgb(var(--n-400));
}
.ft-port::before {
  background: rgb(var(--success));
}
.ft-fusion::before {
  background: rgb(var(--info));
  border-radius: 2px;
  transform: rotate(45deg);
}
.ft-splitter::before {
  background: rgb(var(--warning));
  border-radius: 2px;
}
.ft-sub {
  color: rgb(var(--n-500));
}
.ft-acc {
  float: right;
  margin-left: 8px;
  color: rgb(var(--n-700));
}
.tn-end {
  margin: 0 0 4px 12px;
}
.tn-branches {
  margin: 0 0 6px 12px;
  padding: 0;
  list-style: none;
}
.tn-branch {
  margin: 2px 0;
}
.tn-toggle {
  width: 100%;
  text-align: left;
  border: 0;
  background: none;
  padding: 2px 4px;
  border-radius: 6px;
  color: rgb(var(--n-900));
  font: inherit;
  cursor: pointer;
}
.tn-toggle:hover {
  background: rgb(var(--n-100));
}
.tn-toggle.tn-focus {
  font-weight: 600;
  background: rgb(var(--primary-500) / 0.1);
}
.tn-leaf {
  display: block;
  padding: 2px 4px 2px 18px;
  color: rgb(var(--n-600));
}
.tn-child {
  margin: 4px 0 4px 10px;
}
.tn-st {
  display: inline-block;
  margin-left: 4px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
  background: rgb(var(--n-100));
  color: rgb(var(--n-700));
}
.st-livre {
  background: rgb(var(--success) / 0.15);
  color: rgb(var(--success));
}
.st-reservada {
  background: rgb(var(--warning) / 0.15);
  color: rgb(var(--warning));
}
.st-ocupada {
  background: rgb(var(--info) / 0.15);
  color: rgb(var(--info));
}
.st-bloqueada {
  background: rgb(var(--danger) / 0.15);
  color: rgb(var(--danger));
}
.core {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 999px;
  border: 1px solid rgb(var(--n-400));
  vertical-align: -1px;
}
</style>
