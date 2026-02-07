import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

export const useAlertTemplatesStore = defineStore('alertTemplates', () => {
  const api = useApi()
  const notify = useNotification()

  const templates = ref([])
  const loading = ref(false)
  const meta = ref({
    categories: [],
    channels: [],
    placeholders: {},
  })
  const lastFilters = ref({})

  const templateCount = computed(() => templates.value.length)

  const loadTemplates = async (filters = {}) => {
    loading.value = true
    lastFilters.value = { ...filters }

    try {
      const params = new URLSearchParams()
      if (filters.category) params.append('category', filters.category)
      if (filters.channel) params.append('channel', filters.channel)
      if (filters.is_active !== undefined) params.append('is_active', filters.is_active)

      const query = params.toString()
      const url = `/setup_app/api/alert-templates/${query ? `?${query}` : ''}`

      const res = await api.get(url)
      if (res && (res.success || Array.isArray(res.templates))) {
        templates.value = res.templates || []
        if (res.meta) {
          meta.value = {
            categories: res.meta.categories || [],
            channels: res.meta.channels || [],
            placeholders: res.meta.placeholders || {},
          }
        }
      } else {
        templates.value = []
        notify.error('Modelos de Aviso', res?.message || 'Falha ao carregar modelos.')
      }
    } catch (error) {
      console.error('[AlertTemplatesStore] Error loading templates:', error)
      notify.error('Modelos de Aviso', error.message || 'Erro ao carregar modelos de aviso.')
    } finally {
      loading.value = false
    }
  }

  const saveTemplate = async (templateData) => {
    const payload = { ...templateData }

    try {
      loading.value = true
      let res
      if (payload.id) {
        res = await api.patch(`/setup_app/api/alert-templates/${payload.id}/`, payload)
      } else {
        res = await api.post('/setup_app/api/alert-templates/', payload)
      }

      if (res?.success) {
        notify.success('Modelos de Aviso', res.message || 'Modelo salvo com sucesso.')
        await loadTemplates(lastFilters.value)
        return res.template
      }

      notify.error('Modelos de Aviso', res?.message || 'Falha ao salvar modelo.')
      return null
    } catch (error) {
      console.error('[AlertTemplatesStore] Error saving template:', error)
      notify.error('Modelos de Aviso', error.message || 'Erro ao salvar modelo de aviso.')
      return null
    } finally {
      loading.value = false
    }
  }

  const deleteTemplate = async (templateId) => {
    if (!templateId) return false

    try {
      loading.value = true
      const res = await api.delete(`/setup_app/api/alert-templates/${templateId}/`)
      if (res?.success) {
        notify.success('Modelos de Aviso', res.message || 'Modelo removido.')
        await loadTemplates(lastFilters.value)
        return true
      }
      notify.error('Modelos de Aviso', res?.message || 'Não foi possível remover o modelo.')
      return false
    } catch (error) {
      console.error('[AlertTemplatesStore] Error deleting template:', error)
      notify.error('Modelos de Aviso', error.message || 'Erro ao remover modelo de aviso.')
      return false
    } finally {
      loading.value = false
    }
  }

  const toggleActive = async (templateId, isActive) => {
    try {
      const template = templates.value.find(t => t.id === templateId)
      if (!template) {
        notify.error('Modelos de Aviso', 'Modelo não encontrado.')
        return false
      }
      const res = await api.patch(`/setup_app/api/alert-templates/${templateId}/`, {
        is_active: isActive,
      })
      if (res?.success) {
        notify.success('Modelos de Aviso', res.message || 'Modelo atualizado.')
        await loadTemplates(lastFilters.value)
        return true
      }
      notify.error('Modelos de Aviso', res?.message || 'Falha ao atualizar modelo.')
      return false
    } catch (error) {
      console.error('[AlertTemplatesStore] Error toggling template:', error)
      notify.error('Modelos de Aviso', error.message || 'Erro ao atualizar modelo de aviso.')
      return false
    }
  }

  const getPlaceholdersByCategory = (category) => {
    const catalog = meta.value.placeholders || {}
    return catalog[category] || []
  }

  return {
    templates,
    loading,
    meta,
    templateCount,
    loadTemplates,
    saveTemplate,
    deleteTemplate,
    toggleActive,
    getPlaceholdersByCategory,
  }
})
