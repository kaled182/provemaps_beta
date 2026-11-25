<template>
  <div class="cmm" data-testid="custom-maps">
    <!-- Cabeçalho em linha, como as outras telas de Monitoramento -->
    <header class="cmm-head">
      <div class="min-w-0">
        <h1 class="cmm-title">Mapas · {{ categoryLabel }}</h1>
        <p class="cmm-sub">O mapa completo mostra toda a rede; os personalizados guardam um recorte de equipamentos e cabos.</p>
      </div>
      <button type="button" class="cmm-btn cmm-btn-primary" data-testid="custom-maps-create" @click="openCreate">
        <PhPlus :size="14" weight="bold" /> Novo mapa
      </button>
    </header>

    <p v-if="loadError" class="cmm-alert" role="alert" data-testid="custom-maps-error">
      Erro ao carregar os mapas personalizados: {{ loadError }}
    </p>

    <div class="cmm-grid" data-testid="custom-maps-grid">
      <!-- Mapa completo (sempre existe) -->
      <article
        class="cmm-card"
        role="button"
        tabindex="0"
        data-testid="custom-maps-default"
        @click="openDefaultMap"
        @keydown.enter.prevent="openDefaultMap"
      >
        <header class="cmm-card-head">
          <span class="cmm-card-icon cmm-card-icon-primary" aria-hidden="true"><PhGlobeHemisphereWest :size="18" /></span>
          <div class="min-w-0 flex-1">
            <h3 class="cmm-card-name">Mapa completo</h3>
            <p class="cmm-card-desc">Todos os sites, equipamentos e cabos da rede</p>
          </div>
          <span class="cmm-tag">Padrão</span>
        </header>
        <footer class="cmm-card-foot">
          <span class="cmm-go">Abrir mapa →</span>
        </footer>
      </article>

      <article
        v-for="map in customMaps"
        :key="map.id"
        class="cmm-card"
        role="button"
        tabindex="0"
        data-testid="custom-maps-card"
        @click="openMap(map)"
        @keydown.enter.prevent="openMap(map)"
      >
        <header class="cmm-card-head">
          <span class="cmm-card-icon" aria-hidden="true"><PhMapTrifold :size="18" /></span>
          <div class="min-w-0 flex-1">
            <h3 class="cmm-card-name" :title="map.name">{{ map.name }}</h3>
            <p class="cmm-card-desc">{{ map.description || 'Sem descrição' }}</p>
          </div>
          <span v-if="!map.is_public" class="cmm-tag" title="Só visível para quem o criou">Privado</span>
          <button type="button" class="cmm-icon-btn" title="Editar mapa" @click.stop="openEdit(map)">
            <PhPencilSimple :size="14" />
          </button>
          <button type="button" class="cmm-icon-btn cmm-icon-danger" title="Excluir mapa" data-testid="custom-maps-delete" @click.stop="askDelete(map)">
            <PhTrash :size="14" />
          </button>
        </header>
        <footer class="cmm-card-foot">
          <span class="cmm-stat" title="Equipamentos"><PhHardDrives :size="12" /> {{ map.devices_count ?? 0 }}</span>
          <span class="cmm-stat" title="Cabos"><PhLineSegments :size="12" /> {{ map.cables_count ?? 0 }}</span>
          <span class="cmm-stat" title="Câmeras"><PhVideoCamera :size="12" /> {{ map.cameras_count ?? 0 }}</span>
          <span class="cmm-go">Abrir mapa →</span>
        </footer>
      </article>
    </div>

    <!-- Criar / editar -->
    <BaseModal
      :show="showForm"
      :title="editingMap ? 'Editar mapa' : 'Novo mapa'"
      :subtitle="editingMap ? editingMap.name : 'Mapa personalizado'"
      :icon="PhMapTrifold"
      :dirty="formDirty"
      size="md"
      @close="closeForm"
    >
      <form class="space-y-3" @submit.prevent="saveMap">
        <label class="cmm-field">
          <span>Nome do mapa</span>
          <input v-model.trim="form.name" type="text" required placeholder="Ex.: Backbone Brasília" data-testid="custom-maps-name" />
        </label>
        <label class="cmm-field">
          <span>Descrição</span>
          <textarea v-model="form.description" rows="3" placeholder="Para que serve este mapa" />
        </label>
        <label class="cmm-field">
          <span>Categoria</span>
          <select v-model="form.category">
            <option value="backbone">Backbone</option>
            <option value="gpon">GPON</option>
            <option value="dwdm">DWDM</option>
            <option value="custom">Personalizado</option>
          </select>
        </label>
        <label class="flex items-center gap-2 text-sm text-neutral-700">
          <input v-model="form.is_public" type="checkbox" />
          Público (visível para todos os utilizadores)
        </label>
        <p v-if="formError" class="text-sm text-danger" role="alert">{{ formError }}</p>
      </form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button type="button" class="cmm-btn" @click="closeForm">Cancelar</button>
          <button
            type="button"
            class="cmm-btn cmm-btn-primary"
            :disabled="saving || !form.name"
            data-testid="custom-maps-save"
            @click="saveMap"
          >
            {{ saving ? 'A guardar…' : editingMap ? 'Guardar alterações' : 'Criar mapa' }}
          </button>
        </div>
      </template>
    </BaseModal>

    <!-- Confirmar exclusão -->
    <BaseModal
      :show="deleting !== null"
      title="Excluir mapa"
      :subtitle="deleting?.name || ''"
      :icon="PhTrash"
      status="critical"
      size="sm"
      @close="deleting = null"
    >
      <p class="text-sm text-neutral-700">
        O mapa «{{ deleting?.name }}» deixa de existir. Os equipamentos e cabos não são apagados.
      </p>
      <p v-if="deleteError" class="mt-2 text-sm text-danger" role="alert">{{ deleteError }}</p>
      <template #footer>
        <div class="flex justify-end gap-2">
          <button type="button" class="cmm-btn" @click="deleting = null">Cancelar</button>
          <button type="button" class="cmm-btn cmm-btn-danger" :disabled="removing" data-testid="custom-maps-confirm-delete" @click="confirmDelete">
            {{ removing ? 'A excluir…' : 'Excluir' }}
          </button>
        </div>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
/**
 * Mapas do Monitoramento (/monitoring/backbone): mapa completo + mapas personalizados.
 * EV-0114: cartões do design system (sem o banner lilás), modais em BaseModal e
 * mutações pelo `useApi` — o `fetch` cru lia o CSRF de um `csrfmiddlewaretoken` que a SPA
 * não tem, e o DRF recusava criar/editar/excluir com 403.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  PhGlobeHemisphereWest,
  PhHardDrives,
  PhLineSegments,
  PhMapTrifold,
  PhPencilSimple,
  PhPlus,
  PhTrash,
  PhVideoCamera,
} from '@phosphor-icons/vue'
import { useApi } from '@/composables/useApi'
import BaseModal from '@/components/Common/BaseModal.vue'

const MAPS_URL = '/api/v1/maps/custom/'
const CATEGORY_LABELS = { backbone: 'Backbone', gpon: 'GPON', dwdm: 'DWDM', custom: 'Personalizados' }

const router = useRouter()
const route = useRoute()
const api = useApi()

/** A rota /monitoring/backbone não tem `:category` — é a do backbone. */
const category = computed(() => route.params.category || 'backbone')
const categoryLabel = computed(() => CATEGORY_LABELS[category.value] || 'Backbone')

const customMaps = ref([])
const loadError = ref('')

const emptyForm = () => ({ name: '', description: '', category: category.value, is_public: true })
const showForm = ref(false)
const editingMap = ref(null)
const form = ref(emptyForm())
const formSnapshot = ref('')
const formError = ref('')
const saving = ref(false)
const formDirty = computed(() => showForm.value && JSON.stringify(form.value) !== formSnapshot.value)

const deleting = ref(null)
const deleteError = ref('')
const removing = ref(false)

async function loadMaps() {
  loadError.value = ''
  try {
    const data = await api.get(MAPS_URL)
    customMaps.value = data?.maps || []
  } catch (e) {
    customMaps.value = []
    loadError.value = e?.message || 'erro desconhecido'
  }
}

const openMap = (map) => router.push(`/monitoring/${map.category}/map/${map.id}`)
const openDefaultMap = () => router.push(`/monitoring/${category.value}/map/default`)

function openForm(map) {
  editingMap.value = map
  form.value = map
    ? { name: map.name, description: map.description || '', category: map.category, is_public: map.is_public }
    : emptyForm()
  formSnapshot.value = JSON.stringify(form.value)
  formError.value = ''
  showForm.value = true
}
const openCreate = () => openForm(null)
const openEdit = (map) => openForm(map)
function closeForm() {
  showForm.value = false
  editingMap.value = null
}

async function saveMap() {
  if (!form.value.name || saving.value) return
  saving.value = true
  formError.value = ''
  try {
    if (editingMap.value) await api.put(`${MAPS_URL}${editingMap.value.id}/`, form.value)
    else await api.post(MAPS_URL, form.value)
    formSnapshot.value = JSON.stringify(form.value)
    closeForm()
    await loadMaps()
  } catch (e) {
    formError.value = `Não foi possível guardar: ${e?.message || 'erro desconhecido'}`
  } finally {
    saving.value = false
  }
}

function askDelete(map) {
  deleteError.value = ''
  deleting.value = map
}
async function confirmDelete() {
  if (!deleting.value || removing.value) return
  removing.value = true
  deleteError.value = ''
  try {
    await api.delete(`${MAPS_URL}${deleting.value.id}/`)
    deleting.value = null
    await loadMaps()
  } catch (e) {
    deleteError.value = `Não foi possível excluir: ${e?.message || 'erro desconhecido'}`
  } finally {
    removing.value = false
  }
}

onMounted(loadMaps)
</script>

<style scoped>
.cmm {
  padding: 16px 20px;
  min-height: 100%;
  background: rgb(var(--canvas));
}
.cmm-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.cmm-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: rgb(var(--n-900));
}
.cmm-sub {
  margin: 2px 0 0;
  font-size: 12px;
  color: rgb(var(--n-500));
}
.cmm-alert {
  margin-bottom: 12px;
  padding: 8px 12px;
  border: 1px solid rgb(var(--danger) / 0.4);
  border-radius: 8px;
  background: rgb(var(--danger) / 0.08);
  color: rgb(var(--danger));
  font-size: 13px;
}
.cmm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
}
.cmm-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  background: rgb(var(--surface));
  cursor: pointer;
  transition: border-color 0.15s ease;
}
.cmm-card:hover,
.cmm-card:focus-visible {
  border-color: rgb(var(--primary-500));
  outline: none;
}
.cmm-card-head {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}
.cmm-card-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 8px;
  background: rgb(var(--n-100));
  color: rgb(var(--n-600));
}
.cmm-card-icon-primary {
  background: rgb(var(--primary-500) / 0.12);
  color: rgb(var(--primary-600));
}
.cmm-card-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: rgb(var(--n-900));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cmm-card-desc {
  margin: 2px 0 0;
  font-size: 12px;
  color: rgb(var(--n-500));
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.cmm-tag {
  flex-shrink: 0;
  font-size: 10px;
  line-height: 16px;
  padding: 0 6px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 4px;
  color: rgb(var(--n-600));
}
.cmm-icon-btn {
  display: inline-flex;
  padding: 4px;
  border-radius: 6px;
  color: rgb(var(--n-500));
}
.cmm-icon-btn:hover {
  background: rgb(var(--n-100));
  color: rgb(var(--n-900));
}
.cmm-icon-danger:hover {
  background: rgb(var(--danger) / 0.1);
  color: rgb(var(--danger));
}
.cmm-card-foot {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 11px;
  color: rgb(var(--n-600));
}
.cmm-stat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
}
.cmm-go {
  margin-left: auto;
  color: rgb(var(--n-500));
}
.cmm-card:hover .cmm-go {
  color: rgb(var(--primary-600));
}
.cmm-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 13px;
  font-weight: 500;
  color: rgb(var(--n-700));
}
.cmm-btn:hover {
  background: rgb(var(--n-100));
}
.cmm-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.cmm-btn-primary {
  border-color: rgb(var(--primary-600));
  background: rgb(var(--primary-600));
  @apply text-white;
}
.cmm-btn-primary:hover {
  background: rgb(var(--primary-700));
}
.cmm-btn-danger {
  border-color: rgb(var(--danger));
  background: rgb(var(--danger));
  @apply text-white;
}
.cmm-btn-danger:hover {
  background: rgb(var(--danger) / 0.88);
}
.cmm-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  font-weight: 500;
  color: rgb(var(--n-700));
}
.cmm-field input,
.cmm-field textarea,
.cmm-field select {
  padding: 6px 10px;
  border: 1px solid rgb(var(--n-200));
  border-radius: 6px;
  background: rgb(var(--surface));
  font-size: 13px;
  font-weight: 400;
  color: rgb(var(--n-900));
}
.cmm-field input:focus,
.cmm-field textarea:focus,
.cmm-field select:focus {
  border-color: rgb(var(--primary-500));
  outline: none;
}
</style>
