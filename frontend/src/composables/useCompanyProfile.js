/**
 * Composable para gerenciamento do perfil da empresa
 * API: GET /setup_app/api/company-profile/
 *      POST /setup_app/api/company-profile/update/
 */

import { ref } from 'vue'
import { useApi } from '@/composables/useApi'
import { useNotification } from '@/composables/useNotification'

export function useCompanyProfile() {
  const api = useApi()
  const notify = useNotification()

  const loading = ref(false)
  const saving = ref(false)

  const profile = ref({
    company_legal_name: '',
    company_trade_name: '',
    company_doc: '',
    company_owner_name: '',
    company_owner_doc: '',
    company_owner_birth: '',
    company_state_reg: '',
    company_city_reg: '',
    company_fistel: '',
    company_created_date: '',
    company_active: true,
    company_reports_active: true,
    address_zip: '',
    address_street: '',
    address_number: '',
    address_district: '',
    address_city: '',
    address_state: '',
    address_country: 'Brasil',
    address_extra: '',
    address_reference: '',
    assets_logo_url: null,
    assets_cert_password: '',
  })

  const logoFile = ref(null)
  const logoPreview = ref(null)
  const certFile = ref(null)

  const loadProfile = async () => {
    try {
      loading.value = true
      const res = await api.get('/setup_app/api/company-profile/')
      if (res?.data?.profile) {
        Object.assign(profile.value, res.data.profile)
        logoPreview.value = res.data.profile.assets_logo_url || null
      }
    } catch {
      notify.error('Erro ao carregar perfil da empresa')
    } finally {
      loading.value = false
    }
  }

  const saveProfile = async () => {
    try {
      saving.value = true
      const formData = new FormData()

      const fields = [
        'company_legal_name', 'company_trade_name', 'company_doc',
        'company_owner_name', 'company_owner_doc', 'company_owner_birth',
        'company_state_reg', 'company_city_reg', 'company_fistel',
        'company_created_date', 'company_active', 'company_reports_active',
        'address_zip', 'address_street', 'address_number', 'address_district',
        'address_city', 'address_state', 'address_country', 'address_extra',
        'address_reference', 'assets_cert_password',
      ]
      fields.forEach(f => formData.append(f, profile.value[f] ?? ''))

      if (logoFile.value) {
        formData.append('assets_logo', logoFile.value)
      }
      if (certFile.value) {
        formData.append('assets_cert_file', certFile.value)
      }

      const res = await api.post('/setup_app/api/company-profile/update/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      if (res?.data?.success) {
        notify.success('Perfil da empresa salvo com sucesso')
        if (res.data.profile?.assets_logo_url) {
          logoPreview.value = res.data.profile.assets_logo_url
        }
        logoFile.value = null
        certFile.value = null
        return true
      }
    } catch {
      notify.error('Erro ao salvar perfil da empresa')
    } finally {
      saving.value = false
    }
    return false
  }

  const onLogoChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    logoFile.value = file
    logoPreview.value = URL.createObjectURL(file)
  }

  const removeLogo = () => {
    logoFile.value = null
    logoPreview.value = null
  }

  const onCertChange = (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    certFile.value = file
  }

  const removeCert = () => {
    certFile.value = null
    profile.value.assets_cert_password = ''
  }

  return {
    loading,
    saving,
    profile,
    logoPreview,
    certFile,
    loadProfile,
    saveProfile,
    onLogoChange,
    removeLogo,
    onCertChange,
    removeCert,
  }
}
