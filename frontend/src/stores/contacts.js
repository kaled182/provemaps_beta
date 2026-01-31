import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

export const useContactsStore = defineStore('contacts', () => {
  const api = useApi()
  const notify = useNotification()
  
  // State
  const contacts = ref([])
  const groups = ref([])
  const importHistory = ref([])
  const loading = ref(false)
  const selectedContacts = ref([])
  
  // Computed
  const activeContacts = computed(() => 
    contacts.value.filter(c => c.is_active)
  )
  
  const contactsByGroup = computed(() => (groupId) => {
    if (!groupId) return contacts.value
    return contacts.value.filter(c => 
      c.groups?.some(g => g === groupId)
    )
  })
  
  const totalActiveContacts = computed(() => 
    contacts.value.filter(c => c.is_active).length
  )
  
  // Actions
  
  /**
   * Carrega todos os contatos
   * @param {Object} filters - Filtros opcionais (is_active, group_id, search)
   */
  const loadContacts = async (filters = {}) => {
    loading.value = true
    try {
      const params = new URLSearchParams()
      if (filters.is_active !== undefined) {
        params.append('is_active', filters.is_active)
      }
      if (filters.group_id) {
        params.append('group_id', filters.group_id)
      }
      if (filters.search) {
        params.append('search', filters.search)
      }
      
      const queryString = params.toString()
      const url = `/setup_app/api/contacts/${queryString ? '?' + queryString : ''}`
      
      const res = await api.get(url)
      
      // API retorna { success: true, contacts: [...] } ou apenas os dados diretamente
      if (res && (res.success === true || Array.isArray(res.contacts) || Array.isArray(res))) {
        contacts.value = res.contacts || res || []
        console.log('[ContactsStore] Loaded contacts:', contacts.value.length)
      } else {
        contacts.value = []
        notify.error('Contatos', res?.message || 'Falha ao carregar contatos')
      }
    } catch (error) {
      console.error('[ContactsStore] Error loading contacts:', error)
      notify.error('Contatos', error.message || 'Erro ao carregar contatos')
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Carrega todos os grupos
   */
  const loadGroups = async () => {
    try {
      const res = await api.get('/setup_app/api/contact-groups/')
      
      if (res && (res.success === true || Array.isArray(res.groups) || Array.isArray(res))) {
        groups.value = res.groups || res || []
        console.log('[ContactsStore] Loaded groups:', groups.value.length)
      } else {
        groups.value = []
        notify.error('Grupos', res?.message || 'Falha ao carregar grupos')
      }
    } catch (error) {
      console.error('[ContactsStore] Error loading groups:', error)
      notify.error('Grupos', error.message || 'Erro ao carregar grupos')
    }
  }
  
  /**
   * Carrega histórico de importações
   */
  const loadImportHistory = async () => {
    try {
      const res = await api.get('/setup_app/api/contact-imports/')
      
      if (res.success) {
        importHistory.value = res.imports || []
        console.log('[ContactsStore] Loaded import history:', importHistory.value.length)
      }
    } catch (error) {
      console.error('[ContactsStore] Error loading import history:', error)
    }
  }
  
  /**
   * Salva contato (criar ou atualizar)
   * @param {Object} contactData - Dados do contato
   * @returns {Boolean} true se sucesso
   */
  const saveContact = async (contactData) => {
    try {
      loading.value = true
      
      const url = contactData.id 
        ? `/setup_app/api/contacts/${contactData.id}/`
        : '/setup_app/api/contacts/'
      
      const res = contactData.id
        ? await api.patch(url, contactData)
        : await api.post(url, contactData)
      
      if (res.success) {
        notify.success('Contato', res.message || 'Contato salvo com sucesso')
        await loadContacts()
        return true
      } else {
        notify.error('Contato', res.message || 'Falha ao salvar contato')
        return false
      }
    } catch (error) {
      console.error('[ContactsStore] Error saving contact:', error)
      notify.error('Contato', error.message || 'Erro ao salvar contato')
      return false
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Deleta contato
   * @param {Number} contactId - ID do contato
   * @returns {Boolean} true se sucesso
   */
  const deleteContact = async (contactId) => {
    try {
      const res = await api.delete(`/setup_app/api/contacts/${contactId}/`)
      
      if (res.success) {
        notify.success('Contato', res.message || 'Contato excluído com sucesso')
        await loadContacts()
        return true
      } else {
        notify.error('Contato', res.message || 'Falha ao excluir contato')
        return false
      }
    } catch (error) {
      console.error('[ContactsStore] Error deleting contact:', error)
      notify.error('Contato', error.message || 'Erro ao excluir contato')
      return false
    }
  }
  
  /**
   * Importa contatos de arquivo CSV/Excel
   * @param {File} file - Arquivo para upload
   * @param {Number} groupId - ID do grupo (opcional)
   * @param {Boolean} updateExisting - Atualizar existentes
   * @returns {Object} Resultado da importação
   */
  const importContacts = async (file, groupId = null, updateExisting = false) => {
    try {
      loading.value = true
      
      const formData = new FormData()
      formData.append('file', file)
      if (groupId) formData.append('group_id', groupId)
      formData.append('update_existing', updateExisting)
      
      const res = await api.post('/setup_app/api/contacts/import_file/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      
      if (res.success) {
        notify.success('Importação', res.message || 'Importação concluída')
        await loadContacts()
        await loadImportHistory()
        return res.import_history
      } else {
        notify.error('Importação', res.message || 'Falha na importação')
        return null
      }
    } catch (error) {
      console.error('[ContactsStore] Error importing contacts:', error)
      notify.error('Importação', error.message || 'Erro ao importar contatos')
      return null
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Sincroniza contatos a partir dos usuários do sistema
   * @returns {Boolean} true se sucesso
   */
  const syncFromUsers = async () => {
    try {
      loading.value = true
      
      const res = await api.post('/setup_app/api/contacts/sync_from_users/')
      
      if (res.success) {
        notify.success('Sincronização', res.message || 'Usuários sincronizados')
        await loadContacts()
        return true
      } else {
        notify.error('Sincronização', res.message || 'Falha ao sincronizar')
        return false
      }
    } catch (error) {
      console.error('[ContactsStore] Error syncing users:', error)
      notify.error('Sincronização', error.message || 'Erro ao sincronizar')
      return false
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Envia mensagem para um contato
   * @param {Number} contactId - ID do contato
   * @param {String} message - Mensagem
   * @param {Number} gatewayId - ID do gateway WhatsApp
   * @returns {Boolean} true se sucesso
   */
  const sendMessage = async (contactId, message, gatewayId, channel = 'whatsapp') => {
    const channelLabels = {
      sms: 'SMS',
      whatsapp: 'WhatsApp',
      smtp: 'E-mail',
      email: 'E-mail',
      telegram: 'Telegram',
    }
    const channelLabel = channelLabels[channel] || 'Canal'
    try {
      const res = await api.post(`/setup_app/api/contacts/${contactId}/send_message/`, {
        message,
        gateway_id: gatewayId,
        channel
      })
      
      if (res.success) {
        notify.success(channelLabel, res.message || 'Mensagem enviada')
        await loadContacts() // Atualiza contador de mensagens
        return true
      } else {
        notify.error(channelLabel, res.message || 'Falha ao enviar mensagem')
        return false
      }
    } catch (error) {
      console.error('[ContactsStore] Error sending message:', error)
      notify.error(channelLabel, error.message || 'Erro ao enviar mensagem')
      return false
    }
  }
  
  /**
   * Envia mensagens em massa
   * @param {Array} contactIds - IDs dos contatos
   * @param {Array} groupIds - IDs dos grupos
   * @param {String} message - Mensagem
   * @param {Number} gatewayId - ID do gateway WhatsApp
   * @param {String} scheduleAt - Data/hora agendamento (opcional)
   * @returns {Boolean} true se sucesso
   */
  const sendBulkMessage = async (contactIds, groupIds, message, gatewayId, scheduleAt = null) => {
    try {
      loading.value = true
      
      const res = await api.post('/setup_app/api/contacts/bulk_message/', {
        contact_ids: contactIds,
        group_ids: groupIds || [],
        message,
        gateway_id: gatewayId,
        schedule_at: scheduleAt
      })
      
      if (res.success) {
        notify.success('WhatsApp', res.message || 'Mensagens agendadas')
        return true
      } else {
        notify.error('WhatsApp', res.message || 'Falha ao enviar mensagens')
        return false
      }
    } catch (error) {
      console.error('[ContactsStore] Error sending bulk messages:', error)
      notify.error('WhatsApp', error.message || 'Erro ao enviar mensagens')
      return false
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Salva grupo (criar ou atualizar)
   * @param {Object} groupData - Dados do grupo
   * @returns {Boolean} true se sucesso
   */
  const saveGroup = async (groupData) => {
    try {
      const url = groupData.id 
        ? `/setup_app/api/contact-groups/${groupData.id}/`
        : '/setup_app/api/contact-groups/'
      
      const res = groupData.id
        ? await api.patch(url, groupData)
        : await api.post(url, groupData)
      
      if (res.success) {
        notify.success('Grupo', res.message || 'Grupo salvo com sucesso')
        await loadGroups()
        return true
      } else {
        notify.error('Grupo', res.message || 'Falha ao salvar grupo')
        return false
      }
    } catch (error) {
      console.error('[ContactsStore] Error saving group:', error)
      notify.error('Grupo', error.message || 'Erro ao salvar grupo')
      return false
    }
  }
  
  /**
   * Deleta grupo
   * @param {Number} groupId - ID do grupo
   * @returns {Boolean} true se sucesso
   */
  const deleteGroup = async (groupId) => {
    try {
      const res = await api.delete(`/setup_app/api/contact-groups/${groupId}/`)
      
      if (res.success) {
        notify.success('Grupo', res.message || 'Grupo excluído com sucesso')
        await loadGroups()
        return true
      } else {
        notify.error('Grupo', res.message || 'Falha ao excluir grupo')
        return false
      }
    } catch (error) {
      console.error('[ContactsStore] Error deleting group:', error)
      notify.error('Grupo', error.message || 'Erro ao excluir grupo')
      return false
    }
  }
  
  /**
   * Limpa seleção de contatos
   */
  const clearSelection = () => {
    selectedContacts.value = []
  }
  
  /**
   * Seleciona/deseleciona contato
   * @param {Number} contactId - ID do contato
   */
  const toggleContactSelection = (contactId) => {
    const index = selectedContacts.value.indexOf(contactId)
    if (index > -1) {
      selectedContacts.value.splice(index, 1)
    } else {
      selectedContacts.value.push(contactId)
    }
  }
  
  /**
   * Seleciona todos os contatos
   * @param {Array} contactIds - IDs dos contatos
   */
  const selectAll = (contactIds) => {
    selectedContacts.value = [...contactIds]
  }
  
  return {
    // State
    contacts,
    groups,
    importHistory,
    loading,
    selectedContacts,
    
    // Computed
    activeContacts,
    contactsByGroup,
    totalActiveContacts,
    
    // Actions
    loadContacts,
    loadGroups,
    loadImportHistory,
    saveContact,
    deleteContact,
    importContacts,
    syncFromUsers,
    sendMessage,
    sendBulkMessage,
    saveGroup,
    deleteGroup,
    clearSelection,
    toggleContactSelection,
    selectAll,
  }
})
