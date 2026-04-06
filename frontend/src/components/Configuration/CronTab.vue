<template>
  <div class="space-y-4">

    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-base font-semibold text-gray-900 dark:text-white">Tarefas Agendadas (Cron)</h3>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
          Gerencie jobs cron do servidor. Após salvar, clique em "Aplicar no Servidor" para gerar o arquivo crontab.
        </p>
      </div>
      <div class="flex gap-2">
        <button @click="applyToServer" :disabled="applying"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 disabled:opacity-50 transition-colors">
          <svg v-if="!applying" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
          </svg>
          <svg v-else class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          Aplicar no Servidor
        </button>
        <button @click="openCreate"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors">
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Nova Cron
        </button>
      </div>
    </div>

    <!-- Apply success banner -->
    <div v-if="applyResult" class="flex items-start gap-2 p-3 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-sm text-green-800 dark:text-green-300">
      <svg class="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
      </svg>
      <div>
        <p class="font-medium">{{ applyResult.message }}</p>
        <p class="text-xs mt-0.5 font-mono opacity-75">{{ applyResult.path }}</p>
        <p class="text-xs mt-1 opacity-75">No servidor: <code class="bg-green-100 dark:bg-green-900/40 px-1 rounded">crontab {{ applyResult.path }}</code></p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <svg class="animate-spin w-6 h-6 text-blue-500" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
      </svg>
    </div>

    <!-- Empty state -->
    <div v-else-if="jobs.length === 0" class="flex flex-col items-center justify-center py-12 text-center">
      <svg class="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
      </svg>
      <p class="text-sm text-gray-500 dark:text-gray-400">Nenhum cron job configurado</p>
      <button @click="openCreate" class="mt-3 text-xs text-blue-500 hover:text-blue-600">Criar o primeiro →</button>
    </div>

    <!-- Jobs list -->
    <div v-else class="space-y-2">
      <div
        v-for="job in jobs"
        :key="job.id"
        class="flex items-center gap-3 p-3 rounded-xl border transition-colors"
        :class="job.enabled
          ? 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700'
          : 'bg-gray-50 dark:bg-gray-800/50 border-gray-200 dark:border-gray-700 opacity-60'"
      >
        <!-- Toggle -->
        <button @click="toggleJob(job)" class="flex-shrink-0">
          <div class="relative w-9 h-5 rounded-full transition-colors"
            :class="job.enabled ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'">
            <div class="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
              :class="job.enabled ? 'left-4' : 'left-0.5'"></div>
          </div>
        </button>

        <!-- Info -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2">
            <span class="text-sm font-semibold text-gray-900 dark:text-white truncate">{{ job.name }}</span>
            <span class="flex-shrink-0 text-xs font-mono px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
              {{ job.schedule }}
            </span>
          </div>
          <p v-if="job.description" class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">{{ job.description }}</p>
          <p class="text-xs font-mono text-gray-400 dark:text-gray-500 truncate mt-0.5">{{ job.command }}</p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-1 flex-shrink-0">
          <button @click="openEdit(job)" title="Editar"
            class="p-1.5 rounded-lg text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
            </svg>
          </button>
          <button @click="confirmDelete(job)" title="Apagar"
            class="p-1.5 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

  </div>

  <!-- Modal Criar / Editar -->
  <Teleport to="body">
    <div v-if="showModal" class="fixed inset-0 z-[9999] overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="showModal = false"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg border border-gray-200 dark:border-gray-700">

          <div class="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 class="text-base font-semibold text-gray-900 dark:text-white">
              {{ editingJob ? 'Editar Cron Job' : 'Novo Cron Job' }}
            </h3>
            <button @click="showModal = false" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>

          <div class="p-5 space-y-4">
            <div>
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Nome *</label>
              <input v-model="form.name" type="text" placeholder="Ex: Limpeza Docker Semanal"
                class="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"/>
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Descrição</label>
              <input v-model="form.description" type="text" placeholder="Ex: Remove cache de build do Docker antigo"
                class="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"/>
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">
                Agendamento (Cron Expression) *
              </label>
              <input v-model="form.schedule" type="text" placeholder="0 3 * * 0"
                class="w-full px-3 py-2 text-sm font-mono rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"/>
              <div class="mt-1.5 flex flex-wrap gap-1.5">
                <button v-for="preset in presets" :key="preset.label"
                  @click="form.schedule = preset.value"
                  class="text-xs px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-blue-100 dark:hover:bg-blue-900/30 hover:text-blue-600 transition-colors">
                  {{ preset.label }}
                </button>
              </div>
              <p v-if="scheduleHuman" class="mt-1 text-xs text-blue-500 dark:text-blue-400">↳ {{ scheduleHuman }}</p>
            </div>

            <div>
              <label class="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase mb-1">Comando *</label>
              <textarea v-model="form.command" rows="2" placeholder="docker builder prune -f --filter 'until=168h'"
                class="w-full px-3 py-2 text-sm font-mono rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none resize-none"/>
            </div>

            <div class="flex items-center gap-2">
              <button @click="form.enabled = !form.enabled"
                class="relative w-9 h-5 rounded-full transition-colors flex-shrink-0"
                :class="form.enabled ? 'bg-blue-500' : 'bg-gray-300 dark:bg-gray-600'">
                <div class="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform"
                  :class="form.enabled ? 'left-4' : 'left-0.5'"></div>
              </button>
              <span class="text-sm text-gray-700 dark:text-gray-300">Ativo</span>
            </div>

            <p v-if="formError" class="text-xs text-red-500">{{ formError }}</p>
          </div>

          <div class="flex justify-end gap-2 px-5 py-4 border-t border-gray-200 dark:border-gray-700">
            <button @click="showModal = false"
              class="px-4 py-2 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
              Cancelar
            </button>
            <button @click="saveJob" :disabled="saving"
              class="px-4 py-2 text-sm font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white transition-colors">
              {{ saving ? 'Salvando...' : 'Salvar' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- Confirm delete -->
  <Teleport to="body">
    <div v-if="deleteTarget" class="fixed inset-0 z-[9999] overflow-y-auto">
      <div class="flex min-h-screen items-center justify-center p-4">
        <div class="fixed inset-0 bg-black/50" @click="deleteTarget = null"></div>
        <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-sm border border-gray-200 dark:border-gray-700 p-6">
          <div class="flex items-start gap-3 mb-4">
            <div class="w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
              <svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
              </svg>
            </div>
            <div>
              <h4 class="text-sm font-semibold text-gray-900 dark:text-white">Apagar Cron Job</h4>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Tem certeza que deseja apagar <strong>{{ deleteTarget.name }}</strong>? Esta ação não pode ser desfeita.</p>
            </div>
          </div>
          <div class="flex justify-end gap-2">
            <button @click="deleteTarget = null"
              class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700">
              Cancelar
            </button>
            <button @click="deleteJob"
              class="px-3 py-1.5 text-sm font-semibold rounded-lg bg-red-600 hover:bg-red-700 text-white">
              Apagar
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const jobs      = ref([])
const loading   = ref(false)
const applying  = ref(false)
const saving    = ref(false)
const showModal = ref(false)
const editingJob  = ref(null)
const deleteTarget = ref(null)
const applyResult  = ref(null)
const formError    = ref('')

const form = ref({ name: '', description: '', schedule: '', command: '', enabled: true })

const presets = [
  { label: 'A cada hora',    value: '0 * * * *'   },
  { label: 'Todo dia 3h',    value: '0 3 * * *'    },
  { label: 'Semanal Dom 3h', value: '0 3 * * 0'    },
  { label: 'Mensal 1º 3h',   value: '0 3 1 * *'    },
  { label: 'Seg-Sex 8h',     value: '0 8 * * 1-5'  },
]

const scheduleLabels = {
  '0 * * * *':   'Todo início de hora',
  '0 3 * * *':   'Todo dia às 03:00',
  '0 3 * * 0':   'Todo domingo às 03:00',
  '0 3 1 * *':   'Todo dia 1 do mês às 03:00',
  '0 8 * * 1-5': 'De segunda a sexta às 08:00',
}
const scheduleHuman = computed(() => scheduleLabels[form.value.schedule] || '')

async function fetchJobs() {
  loading.value = true
  try {
    const res = await fetch('/setup/api/cron/')
    const data = await res.json()
    jobs.value = data.jobs || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingJob.value = null
  form.value = { name: '', description: '', schedule: '', command: '', enabled: true }
  formError.value = ''
  showModal.value = true
}

function openEdit(job) {
  editingJob.value = job
  form.value = { name: job.name, description: job.description, schedule: job.schedule, command: job.command, enabled: job.enabled }
  formError.value = ''
  showModal.value = true
}

async function saveJob() {
  if (!form.value.name.trim() || !form.value.schedule.trim() || !form.value.command.trim()) {
    formError.value = 'Nome, agendamento e comando são obrigatórios.'
    return
  }
  saving.value = true
  formError.value = ''
  try {
    const url = editingJob.value ? `/setup/api/cron/${editingJob.value.id}/` : '/setup/api/cron/'
    const method = editingJob.value ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
      body: JSON.stringify(form.value),
    })
    if (!res.ok) throw new Error('Erro ao salvar')
    await fetchJobs()
    showModal.value = false
  } catch (e) {
    formError.value = e.message
  } finally {
    saving.value = false
  }
}

function confirmDelete(job) {
  deleteTarget.value = job
}

async function deleteJob() {
  if (!deleteTarget.value) return
  await fetch(`/setup/api/cron/${deleteTarget.value.id}/`, {
    method: 'DELETE',
    headers: { 'X-CSRFToken': getCsrf() },
  })
  deleteTarget.value = null
  await fetchJobs()
}

async function toggleJob(job) {
  await fetch(`/setup/api/cron/${job.id}/toggle/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': getCsrf() },
  })
  await fetchJobs()
}

async function applyToServer() {
  applying.value = true
  applyResult.value = null
  try {
    const res = await fetch('/setup/api/cron/apply/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrf() },
    })
    applyResult.value = await res.json()
    setTimeout(() => { applyResult.value = null }, 10000)
  } finally {
    applying.value = false
  }
}

function getCsrf() {
  return document.cookie.split(';').map(c => c.trim()).find(c => c.startsWith('csrftoken='))?.split('=')[1] || ''
}

onMounted(fetchJobs)
</script>
