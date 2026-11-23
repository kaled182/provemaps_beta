/**
 * Níveis ópticos de todos os cabos (EV-0057 / EV-0049):
 * `GET /api/v1/fiber-cables/optical-summary/` — lido do banco, sem Zabbix.
 * A resposta mais recente ganha; erro fica em `error` (a UI diz «erro», não «sem dados»).
 * @module useOpticalSummary
 */
import { ref, shallowRef } from 'vue'
import { useApi } from '@/composables/useApi'

export const OPTICAL_SUMMARY_URL = '/api/v1/fiber-cables/optical-summary/'

export function useOpticalSummary() {
  const api = useApi()
  const data = shallowRef(null)
  const loading = ref(false)
  const error = ref('')
  let seq = 0

  async function load() {
    const mine = ++seq
    loading.value = true
    error.value = ''
    try {
      const body = await api.get(OPTICAL_SUMMARY_URL)
      if (mine !== seq) return
      data.value = body
    } catch (e) {
      if (mine !== seq) return
      error.value = e?.message || 'erro desconhecido'
    } finally {
      if (mine === seq) loading.value = false
    }
  }

  return { data, loading, error, load }
}
