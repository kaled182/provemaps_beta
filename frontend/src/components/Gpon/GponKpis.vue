<template>
  <section class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-2" aria-label="Resumo GPON">
    <!-- EV-0120: com uma OLT em foco (OLT, placa ou PON), o 1.º cartão é o estado dela -->
    <div v-if="olt" class="kpi" :class="{ 'kpi-alert': olt.status === 'offline' }" data-testid="gpon-kpi-olts">
      <span class="kpi-label"><PhHardDrives :size="13" />Status da OLT</span>
      <span class="kpi-value" :class="OLT_STATUS[olt.status]?.cls" data-testid="gpon-kpi-olt-status">{{ OLT_STATUS[olt.status]?.label || 'Sem dados' }}</span>
      <span class="kpi-sub truncate" :title="olt.name">{{ olt.name }} · {{ n(t.pons) }} {{ t.pons === 1 ? 'PON' : 'PONs' }}</span>
    </div>
    <div v-else class="kpi" data-testid="gpon-kpi-olts">
      <span class="kpi-label"><PhHardDrives :size="13" />OLTs ativas</span>
      <span class="kpi-value">{{ n(t.olts_online) }}<span class="kpi-of">/ {{ n(t.olts) }}</span></span>
      <span class="kpi-sub">
        <span :class="t.olts_offline ? 'text-danger' : ''">{{ n(t.olts_offline) }} offline</span> · {{ n(t.pons) }} PONs
      </span>
    </div>

    <div class="kpi" data-testid="gpon-kpi-onus">
      <span class="kpi-label"><PhWifiHigh :size="13" />ONUs online</span>
      <span class="kpi-value text-success">{{ n(t.onus_online) }}<span class="kpi-of">/ {{ n(t.onus_provisioned) }}</span></span>
      <span class="kpi-sub" data-testid="gpon-kpi-onus-pct">{{ onlinePct === null ? '—' : formatPercent(onlinePct, 1) }}</span>
      <span class="bar" aria-hidden="true"><span class="bar-fill bg-success" :style="{ width: `${onlinePct ?? 0}%` }"></span></span>
    </div>

    <div class="kpi" data-testid="gpon-kpi-signal">
      <span class="kpi-label"><PhWarning :size="13" />Sinal crítico / atenção</span>
      <span class="kpi-value text-warning">{{ n(t.signal_critical) }}<span class="kpi-of">+ {{ n(t.signal_warning) }}</span></span>
      <span class="kpi-sub">crítico + atenção</span>
    </div>

    <div class="kpi" :class="{ 'kpi-alert': collective > 0 }" data-testid="gpon-kpi-los">
      <span class="kpi-label"><PhLinkBreak :size="13" />Quedas por sinal (LOS)</span>
      <span class="kpi-value text-danger">{{ n(t.los) }}</span>
      <span class="kpi-sub" :class="{ 'text-danger font-semibold': collective > 0 }" data-testid="gpon-kpi-collective">
        {{ collective === null ? '—' : collective > 0 ? `${n(collective)} PON em queda em massa` : 'sem queda em massa' }}
      </span>
    </div>

    <div class="kpi" data-testid="gpon-kpi-dying">
      <span class="kpi-label"><PhLightningSlash :size="13" />Quedas por energia</span>
      <span class="kpi-value text-info">{{ n(t.dying_gasp) }}</span>
      <span class="kpi-sub">Dying Gasp</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { PhHardDrives, PhLightningSlash, PhLinkBreak, PhWarning, PhWifiHigh } from '@phosphor-icons/vue'
import { formatInt, formatPercent } from '@/utils/ptBrFormat'

const props = defineProps({
  totals: { type: Object, default: () => ({}) },
  /** EV-0120: OLT em foco no funil (null = rede/recorte) */
  olt: { type: Object, default: null },
})

const OLT_STATUS = {
  online: { label: 'Online', cls: 'text-success' },
  offline: { label: 'Offline', cls: 'text-danger' },
  unknown: { label: 'Sem dados', cls: 'text-neutral-500' },
}

const t = computed(() => props.totals || {})
const n = formatInt
const isNum = (v) => typeof v === 'number' && Number.isFinite(v)

const onlinePct = computed(() => {
  const { onus_online: on, onus_provisioned: prov } = t.value
  return isNum(on) && isNum(prov) && prov > 0 ? (on / prov) * 100 : null
})
const collective = computed(() => (isNum(t.value.pons_collective_drop) ? t.value.pons_collective_drop : null))
</script>

<style scoped>
.kpi {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-height: 88px;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
}
.kpi-alert {
  border-color: rgb(var(--danger) / 0.5);
  background: rgb(var(--danger) / 0.06);
}
.kpi-label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: rgb(var(--n-500));
}
.kpi-value {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: 20px;
  font-weight: 600;
}
.kpi-of {
  margin-left: 4px;
  font-size: 13px;
  font-weight: 500;
  color: rgb(var(--n-500));
}
.kpi-sub {
  font-size: 12px;
  color: rgb(var(--n-500));
  font-variant-numeric: tabular-nums;
}
.bar {
  margin-top: auto;
  height: 3px;
  border-radius: 2px;
  background: rgb(var(--n-200));
  overflow: hidden;
}
.bar-fill {
  display: block;
  height: 100%;
}
</style>
