<template>
  <div class="contacts-tab">
    <div class="contacts-toolbar">
      <div class="toolbar-left">
        <button type="button" class="btn btn-primary" @click="openCreateModal">
          <i class="fas fa-plus"></i>
          Novo Contato
        </button>

        <button type="button" class="btn btn-secondary" @click="showImportModal = true">
          <i class="fas fa-file-import"></i>
          Importar CSV/Excel
        </button>

        <button type="button" class="btn btn-secondary" :disabled="loading" @click="handleSyncUsers">
          <i class="fas fa-sync"></i>
          Sincronizar Usuários
        </button>

        <button
          v-if="selectedContacts.length > 0"
          type="button"
          class="btn btn-success"
          @click="showBulkMessageModal = true"
        >
          <i class="fas fa-paper-plane"></i>
          Enviar Mensagem ({{ selectedContacts.length }})
        </button>
      </div>

      <div class="toolbar-right">
        <input
          v-model="searchQuery"
          class="search-input"
          type="text"
          placeholder="Buscar contatos..."
          @input="handleSearch"
        />

        <select v-model="filterGroup" class="filter-select" @change="applyFilters">
          <option value="">Todos os grupos</option>
          <option v-for="group in groups" :key="group.id" :value="group.id">
            {{ group.name }}
          </option>
        </select>

        <select v-model="filterActive" class="filter-select" @change="applyFilters">
          <option value="">Todos</option>
          <option value="true">Ativos</option>
          <option value="false">Inativos</option>
        </select>

        <button type="button" class="btn btn-icon" title="Gerenciar Grupos" @click="showGroupManager = true">
          <i class="fas fa-layer-group"></i>
        </button>
      </div>
    </div>

    <div class="contacts-stats">
      <div class="stat-card">
        <div class="stat-value">{{ totalActiveContacts }}</div>
        <div class="stat-label">Contatos Ativos</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ groups.length }}</div>
        <div class="stat-label">Grupos</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ selectedContacts.length }}</div>
        <div class="stat-label">Selecionados</div>
      </div>
    </div>

    <ContactList
      :contacts="contacts"
      :loading="loading"
      :selected-contacts="selectedContacts"
      @edit="handleEdit"
      @delete="handleDelete"
      @send-message="handleSendMessage"
      @toggle-selection="toggleContactSelection"
      @select-all="handleSelectAll"
    />

    <ContactEditModal
      v-if="showEditModal"
      :contact="editingContact"
      :groups="groups"
      @close="closeEditModal"
      @save="handleSave"
    />

    <ContactImportModal
      v-if="showImportModal"
      :groups="groups"
      @close="showImportModal = false"
      @import="handleImport"
    />

    <BulkMessageModal
      v-if="showBulkMessageModal"
      :selected-contact-ids="selectedContacts"
      :groups="groups"
      @close="showBulkMessageModal = false"
      @send="handleBulkSend"
    />

    <ContactGroupManager
      v-if="showGroupManager"
      :groups="groups"
      @close="showGroupManager = false"
      @refresh="loadGroups"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { storeToRefs } from 'pinia'
import { useContactsStore } from '@/stores/contacts'
import ContactList from './ContactList.vue'
import ContactEditModal from './ContactEditModal.vue'
import ContactImportModal from './ContactImportModal.vue'
import BulkMessageModal from './BulkMessageModal.vue'
import ContactGroupManager from './ContactGroupManager.vue'

const contactsStore = useContactsStore()

const {
  contacts,
  groups,
  loading,
  selectedContacts,
  totalActiveContacts,
} = storeToRefs(contactsStore)

const {
  loadContacts,
  loadGroups,
  saveContact,
  deleteContact,
  importContacts,
  syncFromUsers,
  sendMessage,
  sendBulkMessage,
  toggleContactSelection,
  selectAll,
  clearSelection,
} = contactsStore

const showEditModal = ref(false)
const showImportModal = ref(false)
const showBulkMessageModal = ref(false)
const showGroupManager = ref(false)
const editingContact = ref(null)
const searchQuery = ref('')
const filterGroup = ref('')
const filterActive = ref('')

let searchDebounceId = null

const openCreateModal = () => {
  editingContact.value = null
  showEditModal.value = true
}

const handleSearch = () => {
  if (searchDebounceId) {
    clearTimeout(searchDebounceId)
  }
  searchDebounceId = setTimeout(() => {
    applyFilters()
  }, 300)
}

const applyFilters = () => {
  const filters = {}
  if (searchQuery.value.trim()) {
    filters.search = searchQuery.value.trim()
  }
  if (filterGroup.value) {
    filters.group_id = filterGroup.value
  }
  if (filterActive.value) {
    filters.is_active = filterActive.value === 'true'
  }
  loadContacts(filters)
}

const handleEdit = (contact) => {
  editingContact.value = { ...contact }
  showEditModal.value = true
}

const handleDelete = async (contactId) => {
  if (confirm('Deseja realmente excluir este contato?')) {
    await deleteContact(contactId)
  }
}

const handleSave = async (contactData) => {
  const success = await saveContact(contactData)
  if (success) {
    closeEditModal()
  }
}

const closeEditModal = () => {
  showEditModal.value = false
  editingContact.value = null
}

const handleImport = async (file, groupId, updateExisting) => {
  const result = await importContacts(file, groupId, updateExisting)
  if (result) {
    showImportModal.value = false
  }
}

const handleSyncUsers = async () => {
  if (confirm('Sincronizar contatos a partir dos usuários do sistema?')) {
    await syncFromUsers()
  }
}

const handleSendMessage = async (contactId, message, gatewayId, channel) => {
  await sendMessage(contactId, message, gatewayId, channel)
}

const handleBulkSend = async (contactIds, groupIds, message, gatewayId, scheduleAt) => {
  const success = await sendBulkMessage(contactIds, groupIds, message, gatewayId, scheduleAt)
  if (success) {
    showBulkMessageModal.value = false
    clearSelection()
  }
}

const handleSelectAll = () => {
  const allIds = contacts.value.map((contact) => contact.id)
  selectAll(allIds)
}

onMounted(async () => {
  await Promise.all([loadContacts(), loadGroups()])
})

onBeforeUnmount(() => {
  if (searchDebounceId) {
    clearTimeout(searchDebounceId)
  }
})
</script>

<style scoped>
.contacts-tab {
  padding: 20px;
}

.contacts-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}

.toolbar-left,
.toolbar-right {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--accent-primary, #2563eb);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--accent-primary-dark, #1e40af);
}

.btn-secondary {
  background: var(--bg-secondary, #f1f5f9);
  color: var(--text-primary, #0f172a);
  border: 1px solid var(--border-secondary, #cbd5e1);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--surface-highlight, #e2e8f0);
}

.btn-success {
  background: var(--status-online, #16a34a);
  color: #fff;
}

.btn-success:hover:not(:disabled) {
  background: var(--status-online-dark, #15803d);
}

.btn-icon {
  padding: 8px 10px;
  border-radius: 6px;
  background: transparent;
  color: var(--text-secondary, #475569);
  border: 1px solid var(--border-secondary, #cbd5e1);
}

.btn-icon:hover {
  background: var(--surface-highlight, #e2e8f0);
  color: var(--text-primary, #0f172a);
}

.search-input,
.filter-select {
  padding: 8px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  font-size: 14px;
}

.search-input::placeholder {
  color: var(--text-tertiary, #94a3b8);
}

.contacts-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--surface-card, #ffffff);
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: var(--shadow-sm, 0 8px 24px rgba(15, 23, 42, 0.06));
  text-align: center;
}

.stat-value {
  font-size: 30px;
  font-weight: 600;
  color: var(--accent-info, #38bdf8);
  margin-bottom: 4px;
}

.stat-label {
  font-size: 13px;
  color: var(--text-tertiary, #94a3b8);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

@media (max-width: 768px) {
  .contacts-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-right {
    width: 100%;
    justify-content: flex-start;
  }

  .search-input {
    flex: 1;
    min-width: 180px;
  }
}
</style>