<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col h-[calc(100vh-64px)] overflow-hidden transition-colors duration-300">
    <div class="flex-none px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-10 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
          <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-slate-500/10 text-slate-400">
            <i class="fas fa-id-card"></i>
          </span>
          Meu Cadastro
        </h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Informações da empresa e dados administrativos.</p>
      </div>
      <div class="flex items-center gap-2">
        <button class="btn-white text-xs" type="button">
          <svg class="w-4 h-4 mr-1.5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
          Novo Registro
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-6 bg-gray-50 dark:bg-gray-900">
      <div class="max-w-5xl mx-auto space-y-6 animate-fade-in">
        <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
          <div class="px-6 py-5 border-b border-gray-100 dark:border-gray-700">
            <h3 class="text-base font-bold text-gray-900 dark:text-white">Cadastros</h3>
            <p class="text-xs text-gray-500">Seções colapsáveis no padrão de Gateway.</p>
          </div>

          <div class="divide-y divide-gray-100 dark:divide-gray-700">
            <div>
              <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleSection('company')">
                <div class="flex items-center gap-3">
                  <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
                    <i class="fas fa-building"></i>
                  </span>
                  <div class="text-left">
                    <p class="text-sm font-semibold text-gray-900 dark:text-white">Empresa</p>
                    <p class="text-xs text-gray-500">Dados fiscais e responsáveis.</p>
                  </div>
                </div>
                <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expanded.company ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
              </button>
              <div v-show="expanded.company" class="px-6 pb-6">
                <form class="space-y-6" autocomplete="off" @submit.prevent>
                  <div class="grid gap-4 md:grid-cols-2">
                    <div>
                      <label class="label-custom">Razao Social</label>
                      <input v-model="form.companyLegalName" type="text" class="input-custom" placeholder="P A THOMAZ MARCELINO E CIA LTDA EPP" autocomplete="organization">
                    </div>
                    <div>
                      <label class="label-custom">Nome Fantasia</label>
                      <input v-model="form.companyTradeName" type="text" class="input-custom" placeholder="SIMPLES INTERNET" autocomplete="organization">
                    </div>
                    <div>
                      <label class="label-custom">CPF/CNPJ</label>
                      <input v-model="form.companyDoc" type="text" class="input-custom font-mono" placeholder="00.000.000/0000-00" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Responsavel</label>
                      <input v-model="form.companyOwner" type="text" class="input-custom" placeholder="PAULO ADRIANO THOMAZ MARCELINO" autocomplete="name">
                    </div>
                    <div>
                      <label class="label-custom">Responsavel CPF</label>
                      <input v-model="form.companyOwnerDoc" type="text" class="input-custom font-mono" placeholder="000.000.000-00" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Responsavel Data Nascimento</label>
                      <input v-model="form.companyOwnerBirth" type="text" class="input-custom" placeholder="dd/mm/aaaa" autocomplete="bday">
                    </div>
                    <div>
                      <label class="label-custom">Inscricao Estadual</label>
                      <input v-model="form.companyStateReg" type="text" class="input-custom font-mono" placeholder="00.000.000-0" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Inscricao Municipal</label>
                      <input v-model="form.companyCityReg" type="text" class="input-custom font-mono" placeholder="0000000" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Anatel FISTEL</label>
                      <input v-model="form.companyFistel" type="text" class="input-custom font-mono" placeholder="00000000000" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Data de Cadastro</label>
                      <input v-model="form.companyCreatedAt" type="text" class="input-custom" placeholder="dd/mm/aaaa" autocomplete="off">
                    </div>
                  </div>
                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="checkbox-card">
                      <input v-model="form.companyActive" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
                      <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Ativa</span>
                    </label>
                    <label class="checkbox-card">
                      <input v-model="form.companyReportsActive" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
                      <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Ativa para Relatorios</span>
                    </label>
                  </div>
                  <div class="flex justify-end">
                    <button class="btn-primary" type="button" @click="saveProfile">Salvar</button>
                  </div>
                </form>
              </div>
            </div>

            <div>
              <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleSection('address')">
                <div class="flex items-center gap-3">
                  <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
                    <i class="fas fa-map-marker-alt"></i>
                  </span>
                  <div class="text-left">
                    <p class="text-sm font-semibold text-gray-900 dark:text-white">Endereco</p>
                    <p class="text-xs text-gray-500">Localizacao e coordenadas.</p>
                  </div>
                </div>
                <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expanded.address ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
              </button>
              <div v-show="expanded.address" class="px-6 pb-6">
                <form class="space-y-6" autocomplete="off" @submit.prevent>
                  <div class="grid gap-4 md:grid-cols-2">
                    <div>
                      <label class="label-custom">CEP</label>
                      <input v-model="form.addressZip" type="text" class="input-custom font-mono" placeholder="00000-000" autocomplete="postal-code">
                    </div>
                    <div>
                      <label class="label-custom">Endereco</label>
                      <input v-model="form.addressStreet" type="text" class="input-custom" autocomplete="address-line1">
                    </div>
                    <div>
                      <label class="label-custom">Numero</label>
                      <input v-model="form.addressNumber" type="text" class="input-custom" placeholder="13" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Bairro</label>
                      <input v-model="form.addressDistrict" type="text" class="input-custom" placeholder="CENTRO" autocomplete="address-level3">
                    </div>
                    <div>
                      <label class="label-custom">Cidade</label>
                      <input v-model="form.addressCity" type="text" class="input-custom" placeholder="SANTANA DO ARAGUAIA" autocomplete="address-level2">
                    </div>
                    <div>
                      <label class="label-custom">UF</label>
                      <select v-model="form.addressState" class="input-custom">
                        <option v-for="state in states" :key="state" :value="state">{{ state }}</option>
                      </select>
                    </div>
                    <div>
                      <label class="label-custom">Pais</label>
                      <select v-model="form.addressCountry" class="input-custom">
                        <option value="Brasil">Brasil</option>
                        <option value="Outro">Outro</option>
                      </select>
                    </div>
                    <div>
                      <label class="label-custom">Complemento</label>
                      <input v-model="form.addressExtra" type="text" class="input-custom" placeholder="Sala, bloco, apto" autocomplete="address-line2">
                    </div>
                    <div>
                      <label class="label-custom">Ponto de Referencia</label>
                      <input v-model="form.addressReference" type="text" class="input-custom" placeholder="Proximo a..." autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Latitude, Longitude</label>
                      <input v-model="form.addressCoords" type="text" class="input-custom font-mono" placeholder="-9.338936, -50.340506" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Condominio</label>
                      <input v-model="form.addressComplex" type="text" class="input-custom" placeholder="Condominio" autocomplete="off">
                    </div>
                    <div>
                      <label class="label-custom">Codigo Mun. (IBGE)</label>
                      <input v-model="form.addressIbge" type="text" class="input-custom font-mono" placeholder="0000000" autocomplete="off">
                    </div>
                  </div>
                  <div class="flex justify-end">
                    <button class="btn-primary" type="button" @click="saveProfile">Salvar</button>
                  </div>
                </form>
              </div>
            </div>

            <div>
              <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleSection('assets')">
                <div class="flex items-center gap-3">
                  <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400">
                    <i class="fas fa-folder"></i>
                  </span>
                  <div class="text-left">
                    <p class="text-sm font-semibold text-gray-900 dark:text-white">Outros</p>
                    <p class="text-xs text-gray-500">Arquivos e certificados.</p>
                  </div>
                </div>
                <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expanded.assets ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
              </button>
              <div v-show="expanded.assets" class="px-6 pb-6">
                <form class="space-y-6" autocomplete="off" @submit.prevent>
                  <input class="hidden" type="text" autocomplete="username" aria-hidden="true">
                  <div class="grid gap-4 md:grid-cols-2">
                    <div>
                      <label class="label-custom">Logo Arquivo</label>
                      <div v-if="logoPreviewUrl" class="mb-3 flex items-center gap-3 rounded-lg border border-white/10 bg-white/5 p-3">
                        <img :src="logoPreviewUrl" alt="Logo atual" class="h-10 w-auto rounded bg-white/10">
                        <div class="text-xs text-gray-300">
                          <div class="font-semibold text-gray-100">Logo atual</div>
                          <div class="text-gray-400">{{ logoPreviewName }}</div>
                        </div>
                      </div>
                      <input type="file" class="input-custom" autocomplete="off" @change="onFileChange('assets_logo', $event)" accept="image/*">
                    </div>
                    <div>
                      <label class="label-custom">Certificado A1</label>
                      <input type="file" class="input-custom" autocomplete="off" @change="onFileChange('assets_cert_file', $event)">
                    </div>
                    <div>
                      <label class="label-custom">Certificado A1 Senha</label>
                      <input v-model="form.assetsCertPassword" type="password" class="input-custom" autocomplete="new-password">
                    </div>
                  </div>
                  <div class="flex justify-end">
                    <button class="btn-primary" type="button" @click="saveProfile">Salvar</button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';

const expanded = ref({
  company: true,
  address: false,
  assets: false,
});

const api = useApi();
const notify = useNotification();
const lastLoaded = ref(null);
const logoPreviewUrl = ref('');
const logoPreviewName = ref('');
const logoPreviewObjectUrl = ref('');

const form = ref({
  companyLegalName: '',
  companyTradeName: '',
  companyDoc: '',
  companyOwner: '',
  companyOwnerDoc: '',
  companyOwnerBirth: '',
  companyStateReg: '',
  companyCityReg: '',
  companyFistel: '',
  companyCreatedAt: '',
  companyActive: true,
  companyReportsActive: true,
  addressZip: '',
  addressStreet: '',
  addressNumber: '',
  addressDistrict: '',
  addressCity: '',
  addressState: 'PA',
  addressCountry: 'Brasil',
  addressExtra: '',
  addressReference: '',
  addressCoords: '',
  addressComplex: '',
  addressIbge: '',
  assetsCertPassword: '',
});

const files = ref({
  assets_logo: null,
  assets_cert_file: null,
});

const states = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
  'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
  'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

const toggleSection = (section) => {
  expanded.value[section] = !expanded.value[section];
};

const onFileChange = (key, event) => {
  const file = event?.target?.files?.[0] || null;
  files.value[key] = file;
  if (key === 'assets_logo') {
    if (logoPreviewObjectUrl.value) {
      URL.revokeObjectURL(logoPreviewObjectUrl.value);
      logoPreviewObjectUrl.value = '';
    }
    if (file) {
      const objectUrl = URL.createObjectURL(file);
      logoPreviewObjectUrl.value = objectUrl;
      logoPreviewUrl.value = objectUrl;
      logoPreviewName.value = file.name;
    } else if (lastLoaded.value?.assets_logo) {
      logoPreviewUrl.value = lastLoaded.value.assets_logo.url || '';
      logoPreviewName.value = lastLoaded.value.assets_logo.name || '';
    } else {
      logoPreviewUrl.value = '';
      logoPreviewName.value = '';
    }
  }
};

const applyProfile = (profile) => {
  logoPreviewUrl.value = profile?.assets_logo?.url || '';
  logoPreviewName.value = profile?.assets_logo?.name || '';
  form.value = {
    companyLegalName: profile.company_legal_name || '',
    companyTradeName: profile.company_trade_name || '',
    companyDoc: profile.company_doc || '',
    companyOwner: profile.company_owner_name || '',
    companyOwnerDoc: profile.company_owner_doc || '',
    companyOwnerBirth: profile.company_owner_birth || '',
    companyStateReg: profile.company_state_reg || '',
    companyCityReg: profile.company_city_reg || '',
    companyFistel: profile.company_fistel || '',
    companyCreatedAt: profile.company_created_date || '',
    companyActive: !!profile.company_active,
    companyReportsActive: !!profile.company_reports_active,
    addressZip: profile.address_zip || '',
    addressStreet: profile.address_street || '',
    addressNumber: profile.address_number || '',
    addressDistrict: profile.address_district || '',
    addressCity: profile.address_city || '',
    addressState: profile.address_state || 'PA',
    addressCountry: profile.address_country || 'Brasil',
    addressExtra: profile.address_extra || '',
    addressReference: profile.address_reference || '',
    addressCoords: profile.address_coords || '',
    addressComplex: profile.address_complex || '',
    addressIbge: profile.address_ibge || '',
    assetsCertPassword: '',
  };
};

const fetchProfile = async () => {
  try {
    const res = await api.get('/setup_app/api/company-profile/');
    if (res?.success) {
      lastLoaded.value = res.profile || {};
      applyProfile(res.profile || {});
    } else {
      notify.error('Cadastro', res?.message || 'Erro ao carregar cadastro.');
    }
  } catch (err) {
    notify.error('Cadastro', err?.message || 'Erro ao carregar cadastro.');
  }
};

const resetForm = () => {
  if (lastLoaded.value) {
    applyProfile(lastLoaded.value);
  }
  files.value = {
    assets_logo: null,
    assets_cert_file: null,
  };
};

onBeforeUnmount(() => {
  if (logoPreviewObjectUrl.value) {
    URL.revokeObjectURL(logoPreviewObjectUrl.value);
  }
});

const saveProfile = async () => {
  try {
    const payload = new FormData();
    const data = {
      company_legal_name: form.value.companyLegalName,
      company_trade_name: form.value.companyTradeName,
      company_doc: form.value.companyDoc,
      company_owner_name: form.value.companyOwner,
      company_owner_doc: form.value.companyOwnerDoc,
      company_owner_birth: form.value.companyOwnerBirth,
      company_state_reg: form.value.companyStateReg,
      company_city_reg: form.value.companyCityReg,
      company_fistel: form.value.companyFistel,
      company_created_date: form.value.companyCreatedAt,
      company_active: form.value.companyActive,
      company_reports_active: form.value.companyReportsActive,
      address_zip: form.value.addressZip,
      address_street: form.value.addressStreet,
      address_number: form.value.addressNumber,
      address_district: form.value.addressDistrict,
      address_city: form.value.addressCity,
      address_state: form.value.addressState,
      address_country: form.value.addressCountry,
      address_extra: form.value.addressExtra,
      address_reference: form.value.addressReference,
      address_coords: form.value.addressCoords,
      address_complex: form.value.addressComplex,
      address_ibge: form.value.addressIbge,
      assets_cert_password: form.value.assetsCertPassword,
    };

    Object.entries(data).forEach(([key, value]) => {
      if (typeof value === 'boolean') {
        payload.append(key, value ? 'true' : 'false');
      } else {
        payload.append(key, value ?? '');
      }
    });

    Object.entries(files.value).forEach(([key, file]) => {
      if (file) {
        payload.append(key, file);
      }
    });

    const res = await api.postFormData('/setup_app/api/company-profile/update/', payload);
    if (res?.success) {
      notify.success('Cadastro', res?.message || 'Cadastro atualizado.');
      lastLoaded.value = res.profile || {};
      applyProfile(res.profile || {});
      files.value = {
        assets_logo: null,
        assets_cert_file: null,
      };
    } else {
      notify.error('Cadastro', res?.message || 'Erro ao salvar cadastro.');
    }
  } catch (err) {
    notify.error('Cadastro', err?.message || 'Erro ao salvar cadastro.');
  }
};

onMounted(() => {
  fetchProfile();
});
</script>

<style scoped>
/* Clean form styles (match System/Gateway). */
.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

.input-custom {
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  background-color: #ffffff;
  color: #111827;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  transition: box-shadow 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
}

.input-custom::placeholder {
  color: #9ca3af;
}

.input-custom:focus {
  outline: none;
  border-color: #6366f1;
  box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.35);
}

.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-gray-700 transition-all duration-200;
}

.btn-white {
  @apply inline-flex items-center rounded-md bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-gray-700 transition-all;
}

.checkbox-card {
  @apply flex items-center gap-2 cursor-pointer w-full p-3 border border-gray-200 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors;
  min-height: 48px;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}

textarea.font-mono {
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}
</style>

<style>
html.dark .input-custom,
html[data-theme="dark"] .input-custom {
  background-color: #374151 !important;
  border-color: #4b5563 !important;
  color: #ffffff !important;
}

html.dark .input-custom::placeholder,
html[data-theme="dark"] .input-custom::placeholder {
  color: #9ca3af !important;
}

html.dark .input-custom:focus,
html[data-theme="dark"] .input-custom:focus {
  border-color: #818cf8 !important;
  box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.45) !important;
}

html.dark .input-custom:-webkit-autofill,
html[data-theme="dark"] .input-custom:-webkit-autofill {
  -webkit-box-shadow: 0 0 0 1000px #374151 inset !important;
  -webkit-text-fill-color: #ffffff !important;
}

html[data-theme="light"] .input-custom,
html:not(.dark)[data-theme="light"] .input-custom {
  background-color: #ffffff !important;
  border-color: #d1d5db !important;
  color: #111827 !important;
}
</style>
