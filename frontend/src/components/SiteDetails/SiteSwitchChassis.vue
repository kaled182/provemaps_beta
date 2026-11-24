<template>
  <div data-testid="site-switch-chassis">
    <p v-if="loading && !data" class="py-6 text-center text-sm text-neutral-500">A carregar o chassi do switch…</p>
    <template v-else-if="data">
      <p v-if="!data.zabbix_ok" class="mb-2 text-xs text-warning" role="alert" data-testid="site-switch-zabbix">
        Zabbix indisponível — o estado das portas pode não estar atualizado.
      </p>
      <!-- chassi + inspetor em cima, portas logo por baixo, como na OLT; quem rola é só o modal (EV-0125) -->
      <div class="ssc-top">
        <SwitchChassisBlock
          :sw="data.switch"
          :ports="data.ports"
          :selected="selected"
          :thresholds="data.thresholds"
          @select="select"
        />
      </div>
      <section class="ssc-ports">
        <SwitchPortTable
          :ports="tablePorts"
          :thresholds="data.thresholds"
          :selected-key="selected ? `${selected.device_id}:${selected.name}` : null"
          :free-hidden="freeCount"
          :show-history="false"
          @select="select"
        />
      </section>
    </template>
  </div>
</template>

<script setup>
/**
 * Switch no modal de Site (EV-0124), igual à OLT (EV-0113/0121): o chassi 1U e o inspetor da
 * porta da tela de Switches (EV-0116) e a tabela das portas por baixo, com
 * `GET /api/v1/monitoring/switches/<id>/`. Clicar numa porta (no chassi ou na tabela) muda o
 * inspetor — que já tem os 24 h de tráfego e RX, por isso a tabela não abre outro modal.
 * 404 (switch sem coleta, ex. Ubiquiti) → `unavailable`: o modal mostra a grelha simples.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useApi } from '@/composables/useApi'
import SwitchChassisBlock from '@/components/Switches/SwitchChassisBlock.vue'
import SwitchPortTable from '@/components/Switches/SwitchPortTable.vue'
import { REFRESH_MS } from '@/composables/useSwitchesOverview'

const props = defineProps({
  deviceId: { type: Number, required: true },
})
const emit = defineEmits(['loaded', 'unavailable'])

const api = useApi()
const data = ref(null)
const loading = ref(false)
const selected = ref(null)
let seq = 0
let timer = null

async function load() {
  const mine = ++seq
  loading.value = true
  try {
    const body = await api.get(`/api/v1/monitoring/switches/${encodeURIComponent(props.deviceId)}/`)
    if (mine !== seq) return
    if (!body?.switch) {
      if (!data.value) emit('unavailable')
      return
    }
    data.value = body
    emit('loaded', body.switch)
  } catch {
    if (mine === seq && !data.value) emit('unavailable')
  } finally {
    if (mine === seq) loading.value = false
  }
}

watch(
  () => props.deviceId,
  () => {
    data.value = null
    selected.value = null
    load()
    clearInterval(timer)
    timer = setInterval(load, REFRESH_MS)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearInterval(timer))

/** a porta escolhida segue as atualizações (o objeto muda a cada carga) */
function select(port) {
  selected.value = port ? { device_id: port.device_id, name: port.name } : null
}

const dataPorts = computed(() => (data.value?.ports || []).filter((p) => p.kind !== 'mgmt'))
/** em uso primeiro, pior primeiro; as livres ficam de fora (como no filtro «Todas» da tela) */
const tablePorts = computed(() =>
  dataPorts.value
    .filter((p) => p.state !== 'free')
    .slice()
    .sort((a, b) => a.severity_rank - b.severity_rank || a.name.localeCompare(b.name, 'pt-BR', { numeric: true })),
)
const freeCount = computed(() => dataPorts.value.filter((p) => p.state === 'free').length)
</script>

<style scoped>
.ssc-ports {
  margin-top: 10px;
}
</style>
