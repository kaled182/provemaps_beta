<template>
  <section class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-2" aria-label="Resumo dos switches">
    <div class="kpi" data-testid="sw-kpi-switches">
      <span class="kpi-label"><PhHardDrives :size="13" />Switches ativos</span>
      <span class="kpi-value">{{ n(k.online) }}<span class="kpi-of">/ {{ n(k.switches) }}</span></span>
      <span class="kpi-sub">
        <span :class="k.offline ? 'text-danger' : ''">{{ n(k.offline) }} offline</span>
        <template v-if="k.unknown"> · {{ n(k.unknown) }} sem dados</template>
        · {{ n(k.portsMonitored) }} portas
      </span>
    </div>

    <div class="kpi" data-testid="sw-kpi-ports">
      <span class="kpi-label"><PhPlugsConnected :size="13" />Portas em uso</span>
      <span class="kpi-value text-success">{{ n(k.portsUp) }}<span class="kpi-of">UP / {{ n(k.portsInUse) }} em uso</span></span>
      <span class="kpi-sub">{{ n(k.portsFree) }} livres</span>
      <span class="bar" aria-hidden="true"><span class="bar-fill bg-success" :style="{ width: `${usePct}%` }"></span></span>
    </div>

    <div class="kpi" data-testid="sw-kpi-signal">
      <span class="kpi-label"><PhWarning :size="13" />Sinal crítico / atenção</span>
      <span class="kpi-value" :class="k.signalCritical ? 'text-danger' : 'text-warning'">{{ n(k.signalCritical) }}<span class="kpi-of">+ {{ n(k.signalWarning) }}</span></span>
      <span class="kpi-sub">RX das portas ópticas{{ k.highUtilization ? ` · ${n(k.highUtilization)} com banda > 80%` : '' }}</span>
    </div>

    <div class="kpi" :class="{ 'kpi-alert': k.down > 0 }" data-testid="sw-kpi-down">
      <span class="kpi-label"><PhLinkBreak :size="13" />Portas down / LOS</span>
      <span class="kpi-value text-danger">{{ n(k.down) }}</span>
      <span class="kpi-sub">{{ k.down ? `${n(k.los)} sem luz (LOS) · ${n(k.down - k.los)} sem link` : 'nenhuma porta em uso caída' }}</span>
    </div>

    <div class="kpi" data-testid="sw-kpi-hardware">
      <span class="kpi-label"><PhThermometer :size="13" />Saúde de hardware</span>
      <span class="kpi-value">{{ k.hottest ? `${fmt(k.hottest.temperature_c)} °C` : '—' }}</span>
      <span class="kpi-sub" :title="k.hottest?.name || ''">
        {{ k.hottest ? `mais quente: ${short(k.hottest.name)}` : 'sem leitura de temperatura' }}
        <template v-if="k.busiestCpu"> · CPU máx. {{ fmt(k.busiestCpu.cpu_pct) }}%</template>
      </span>
    </div>
  </section>
</template>

<script setup>
/** 5 KPIs da tela de Switches (EV-0115), do recorte atual. Sem leitura → «—», nunca 0. */
import { computed } from 'vue'
import { PhHardDrives, PhLinkBreak, PhPlugsConnected, PhThermometer, PhWarning } from '@phosphor-icons/vue'
import { formatInt, formatNumber } from '@/utils/ptBrFormat'

const props = defineProps({
  kpis: { type: Object, required: true },
})
const k = computed(() => props.kpis)
const n = formatInt
const fmt = (v) => formatNumber(v, 0)
const short = (name) => String(name || '').replace(/^huawei\s*-\s*switch\s*/i, '')
const usePct = computed(() => (k.value.portsMonitored ? (k.value.portsInUse / k.value.portsMonitored) * 100 : 0))
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
