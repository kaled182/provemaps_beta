<template>
  <div class="min-h-screen app-page p-6">
    <div class="max-w-5xl mx-auto space-y-6">
      <header>
        <h1 class="text-2xl font-semibold app-text-primary">Meu Perfil</h1>
        <p class="text-sm app-text-tertiary mt-1">
          Gerencie seu avatar, contato e preferencias de notificacao.
        </p>
      </header>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div class="app-surface rounded-lg p-6 flex flex-col items-center text-center">
          <div class="relative group">
            <div class="w-28 h-28 rounded-full overflow-hidden app-surface-muted flex items-center justify-center">
              <img
                v-if="avatarSrc"
                :src="avatarSrc"
                class="w-full h-full object-cover"
                alt="Avatar"
              />
              <span v-else class="text-3xl font-semibold app-text-tertiary">
                {{ getInitials(profile.first_name || profile.username) }}
              </span>
            </div>
            <label class="absolute inset-0 rounded-full bg-black/50 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity">
              Alterar foto
              <input type="file" class="hidden" accept="image/*" @change="handleFileUpload" />
            </label>
          </div>
          <h2 class="mt-4 text-lg font-semibold app-text-primary">
            {{ profile.first_name }} {{ profile.last_name }}
          </h2>
          <p class="text-sm app-text-tertiary">@{{ profile.username }}</p>
          <div class="mt-2 app-badge app-badge-muted">
            {{ profile.profile.department || 'Sem departamento' }}
          </div>
        </div>

        <div class="lg:col-span-2 app-surface rounded-lg overflow-hidden">
          <div class="flex border-b app-divider">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              class="flex-1 py-3 text-sm font-medium"
              :class="activeTab === tab.id ? 'app-text-primary border-b-2 border-sky-400' : 'app-text-tertiary'"
              @click="activeTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="p-6 space-y-4">
            <div v-if="activeTab === 'personal'" class="space-y-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label class="field-label">Nome</label>
                  <input v-model="form.first_name" type="text" class="app-input w-full" />
                </div>
                <div>
                  <label class="field-label">Sobrenome</label>
                  <input v-model="form.last_name" type="text" class="app-input w-full" />
                </div>
              </div>
              <div>
                <label class="field-label">Email</label>
                <input v-model="form.email" type="email" class="app-input w-full" disabled />
              </div>
              <div>
                <label class="field-label">Celular / WhatsApp</label>
                <input v-model="form.profile.phone_number" type="text" class="app-input w-full" />
              </div>
            </div>

            <div v-if="activeTab === 'notifications'" class="space-y-4">
              <div class="app-surface-muted rounded-lg p-4 space-y-3">
                <label class="field-label">Telegram Chat ID</label>
                <input v-model="form.profile.telegram_chat_id" type="text" class="app-input w-full" />
              </div>
              <div class="app-surface-muted rounded-lg p-4 space-y-3">
                <div class="flex items-center justify-between">
                  <span class="text-sm app-text-secondary">Receber via Email</span>
                  <input v-model="form.profile.notify_via_email" type="checkbox" class="field-checkbox-input" />
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm app-text-secondary">Receber via WhatsApp</span>
                  <input v-model="form.profile.notify_via_whatsapp" type="checkbox" class="field-checkbox-input" />
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm app-text-secondary">Receber via Telegram</span>
                  <input v-model="form.profile.notify_via_telegram" type="checkbox" class="field-checkbox-input" />
                </div>
              </div>
              <div class="app-surface-muted rounded-lg p-4 space-y-3">
                <div class="flex items-center justify-between">
                  <span class="text-sm app-text-secondary">Alertas Criticos</span>
                  <input v-model="form.profile.receive_critical_alerts" type="checkbox" class="field-checkbox-input" />
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-sm app-text-secondary">Alertas de Aviso</span>
                  <input v-model="form.profile.receive_warning_alerts" type="checkbox" class="field-checkbox-input" />
                </div>
              </div>
            </div>

            <div v-if="activeTab === 'security'" class="space-y-4">
              <div class="app-surface-muted rounded-lg p-4">
                <p class="text-sm app-text-tertiary">
                  Para alterar sua senha, utilize o fluxo de redefinicao via email.
                </p>
                <div class="flex flex-wrap gap-3 mt-3">
                  <a href="/accounts/password_change/" class="app-btn-primary inline-flex px-4 py-2 rounded">
                    Alterar senha
                  </a>
                  <a href="/accounts/password_reset/" class="app-btn inline-flex px-4 py-2 rounded">
                    Solicitar redefinicao
                  </a>
                </div>
              </div>
              <div class="app-surface-muted rounded-lg p-4">
                <div class="flex flex-wrap items-start justify-between gap-4">
                  <div class="space-y-2">
                    <div class="text-sm font-semibold app-text-primary">Autenticador (TOTP)</div>
                    <p class="text-xs app-text-tertiary">
                      Use apps como Google Authenticator ou Authy (RFC 6238).
                    </p>
                    <span class="app-badge" :class="totpStatusClass">
                      {{ totpStatusLabel }}
                    </span>
                  </div>
                  <button
                    type="button"
                    class="app-btn-primary px-4 py-2 rounded"
                    @click="openTotpModal"
                  >
                    Configurar TOTP
                  </button>
                </div>
              </div>
            </div>

            <div class="flex justify-end gap-3 pt-2">
              <button
                type="button"
                class="app-btn px-4 py-2 rounded"
                @click="resetChanges"
              >
                Descartar
              </button>
              <button
                type="button"
                class="app-btn-primary px-4 py-2 rounded"
                :disabled="isSaving"
                @click="saveProfile"
              >
                {{ isSaving ? 'Salvando...' : 'Salvar alteracoes' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div v-if="showTotpModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
    <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeTotpModal"></div>
    <div class="relative w-full max-w-xl app-surface rounded-lg shadow-2xl border border-white/10">
      <div class="px-6 py-4 border-b app-divider flex items-center justify-between">
        <div>
          <h3 class="text-base font-semibold app-text-primary">Configurar TOTP</h3>
          <p class="text-xs app-text-tertiary">Ative autenticacao em duas etapas com app.</p>
        </div>
        <button class="text-sm app-text-tertiary hover:text-white" @click="closeTotpModal">✕</button>
      </div>
      <div class="p-6 space-y-4">
        <div class="flex items-center gap-2">
          <span class="app-badge" :class="totpStatusClass">{{ totpStatusLabel }}</span>
          <span v-if="totpSetup.configured" class="text-xs app-text-tertiary">Segredo configurado.</span>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-[180px_1fr] gap-4 items-start">
          <div class="app-surface-muted rounded-lg p-3 flex items-center justify-center">
            <img
              v-if="totpQrDataUrl"
              :src="totpQrDataUrl"
              alt="QR Code TOTP"
              class="w-40 h-40"
            />
            <div v-else class="text-xs app-text-tertiary text-center">
              Gere o QR para configurar.
            </div>
          </div>
          <div class="space-y-2 text-xs app-text-tertiary">
            <p>Abra o app autenticador e escaneie o QR ao lado.</p>
            <p>Se preferir, use a chave secreta manualmente.</p>
          </div>
        </div>
        <div class="space-y-2">
          <label class="field-label">Chave secreta</label>
          <div class="flex flex-wrap gap-2">
            <input
              :value="totpSetup.secret || 'Gerar para configurar'"
              type="text"
              class="app-input w-full font-mono text-xs"
              readonly
            />
            <button
              type="button"
              class="app-btn px-3 py-2 rounded text-xs"
              @click="copyTotpValue(totpSetup.secret)"
            >
              Copiar chave
            </button>
            <button
              type="button"
              class="app-btn px-3 py-2 rounded text-xs"
              :disabled="totpLoading"
              @click="regenerateTotp"
            >
              Gerar novo
            </button>
          </div>
        </div>
        <div class="space-y-2">
          <label class="field-label">URL de configuracao</label>
          <div class="flex flex-wrap gap-2">
            <input
              :value="totpSetup.otpauth_url || 'Gerar para configurar'"
              type="text"
              class="app-input w-full font-mono text-xs"
              readonly
            />
            <button
              type="button"
              class="app-btn px-3 py-2 rounded text-xs"
              @click="copyTotpValue(totpSetup.otpauth_url)"
            >
              Copiar URL
            </button>
          </div>
          <p class="text-xs app-text-tertiary">
            Caso o app nao leia QR, cole a chave secreta manualmente.
          </p>
        </div>
        <div class="space-y-2">
          <label class="field-label">Codigo do app</label>
          <input v-model="totpCode" type="text" class="app-input w-full" placeholder="000000" autocomplete="one-time-code" />
        </div>
      </div>
      <div class="px-6 py-4 border-t app-divider flex flex-wrap items-center justify-between gap-3">
        <button type="button" class="app-btn px-4 py-2 rounded" @click="closeTotpModal">
          Cancelar
        </button>
        <div class="flex flex-wrap gap-2">
          <button
            v-if="totpSetup.enabled"
            type="button"
            class="app-btn px-4 py-2 rounded"
            :disabled="totpLoading"
            @click="disableTotp"
          >
            Desativar
          </button>
          <button
            v-if="!totpSetup.enabled"
            type="button"
            class="app-btn-primary px-4 py-2 rounded"
            :disabled="totpLoading"
            @click="verifyTotp"
          >
            Ativar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';
import QRCode from 'qrcode';

const api = useApi();
const { success, error: notifyError } = useNotification();

const tabs = [
  { id: 'personal', label: 'Dados pessoais' },
  { id: 'notifications', label: 'Notificacoes' },
  { id: 'security', label: 'Seguranca' },
];

const activeTab = ref('personal');
const isSaving = ref(false);
const previewImage = ref(null);
const avatarFile = ref(null);

const defaultProfile = {
  phone_number: '',
  telegram_chat_id: '',
  notify_via_email: true,
  notify_via_whatsapp: false,
  notify_via_telegram: false,
  receive_critical_alerts: true,
  receive_warning_alerts: false,
  department: '',
  avatar_url: null,
  totp_enabled: false,
  totp_configured: false,
};

const profile = ref({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  profile: { ...defaultProfile },
});

const form = ref({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  profile: { ...defaultProfile },
});

const avatarSrc = computed(() => (
  previewImage.value || profile.value.profile.avatar_url || ''
));

const totpStatusLabel = computed(() => {
  if (profile.value.profile.totp_enabled) return 'Ativo';
  if (profile.value.profile.totp_configured) return 'Configurado';
  return 'Nao configurado';
});

const totpStatusClass = computed(() => {
  if (profile.value.profile.totp_enabled) return 'app-badge-success';
  if (profile.value.profile.totp_configured) return 'app-badge-warning';
  return 'app-badge-muted';
});

const showTotpModal = ref(false);
const totpSetup = ref({
  enabled: false,
  configured: false,
  secret: '',
  otpauth_url: '',
});
const totpCode = ref('');
const totpLoading = ref(false);
const totpQrDataUrl = ref('');

const getInitials = (name) => {
  if (!name) return 'ME';
  return name.slice(0, 2).toUpperCase();
};

const fetchProfile = async () => {
  try {
    const data = await api.get('/api/users/me/');
    const userData = data.user || data;
    profile.value = {
      ...userData,
      profile: { ...defaultProfile, ...(userData.profile || {}) },
    };
    form.value = JSON.parse(JSON.stringify(profile.value));
  } catch (err) {
    notifyError('Erro ao carregar perfil', err.message || String(err));
  }
};

const handleFileUpload = (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  avatarFile.value = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImage.value = e.target.result;
  };
  reader.readAsDataURL(file);
};

const openTotpModal = async () => {
  showTotpModal.value = true;
  await loadTotpSetup(false);
};

const closeTotpModal = () => {
  showTotpModal.value = false;
  totpCode.value = '';
};

const loadTotpSetup = async (reset) => {
  totpLoading.value = true;
  try {
    const params = new URLSearchParams({ setup: '1' });
    if (reset) {
      params.set('reset', '1');
    }
    const data = await api.get(`/api/users/me/totp/?${params.toString()}`);
    totpSetup.value = {
      enabled: Boolean(data.enabled),
      configured: Boolean(data.configured),
      secret: data.secret || '',
      otpauth_url: data.otpauth_url || '',
    };
    await refreshTotpQr();
    await fetchProfile();
  } catch (err) {
    notifyError('Erro ao carregar TOTP', err.message || String(err));
  } finally {
    totpLoading.value = false;
  }
};

const regenerateTotp = async () => {
  await loadTotpSetup(true);
};

const verifyTotp = async () => {
  if (!totpCode.value.trim()) {
    notifyError('Codigo obrigatorio', 'Informe o codigo do app autenticador.');
    return;
  }
  totpLoading.value = true;
  try {
    await api.post('/api/users/me/totp/verify/', { code: totpCode.value.trim() });
    totpCode.value = '';
    await fetchProfile();
    success('TOTP ativado', 'Autenticacao em duas etapas ativada.');
  } catch (err) {
    notifyError('Falha ao ativar', err.message || String(err));
  } finally {
    totpLoading.value = false;
  }
};

const disableTotp = async () => {
  totpLoading.value = true;
  try {
    await api.post('/api/users/me/totp/disable/', { reset: false });
    await fetchProfile();
    success('TOTP desativado', 'Autenticacao em duas etapas desativada.');
  } catch (err) {
    notifyError('Falha ao desativar', err.message || String(err));
  } finally {
    totpLoading.value = false;
  }
};

const copyTotpValue = async (value) => {
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    success('Copiado', 'Valor copiado para a area de transferencia.');
  } catch (err) {
    notifyError('Erro ao copiar', err.message || String(err));
  }
};

const refreshTotpQr = async () => {
  if (!totpSetup.value.otpauth_url) {
    totpQrDataUrl.value = '';
    return;
  }
  try {
    totpQrDataUrl.value = await QRCode.toDataURL(totpSetup.value.otpauth_url, {
      margin: 1,
      width: 180,
      errorCorrectionLevel: 'M',
    });
  } catch (err) {
    totpQrDataUrl.value = '';
  }
};

watch(
  () => totpSetup.value.otpauth_url,
  () => {
    refreshTotpQr();
  }
);


const saveProfile = async () => {
  isSaving.value = true;
  try {
    const payload = {
      first_name: form.value.first_name || '',
      last_name: form.value.last_name || '',
      profile: {
        phone_number: form.value.profile.phone_number || '',
        department: form.value.profile.department || '',
        telegram_chat_id: form.value.profile.telegram_chat_id || '',
        notify_via_email: form.value.profile.notify_via_email,
        notify_via_whatsapp: form.value.profile.notify_via_whatsapp,
        notify_via_telegram: form.value.profile.notify_via_telegram,
        receive_critical_alerts: form.value.profile.receive_critical_alerts,
        receive_warning_alerts: form.value.profile.receive_warning_alerts,
      },
    };

    const data = await api.patch('/api/users/me/', payload);
    const userData = data.user || data;

    if (avatarFile.value) {
      const avatarData = new FormData();
      avatarData.append('avatar', avatarFile.value);
      const avatarResponse = await api.postFormData('/api/users/me/avatar/', avatarData);
      if (avatarResponse?.avatar_url) {
        userData.profile = userData.profile || {};
        userData.profile.avatar_url = avatarResponse.avatar_url;
      }
    }
    profile.value = {
      ...userData,
      profile: { ...defaultProfile, ...(userData.profile || {}) },
    };
    form.value = JSON.parse(JSON.stringify(profile.value));
    previewImage.value = null;
    avatarFile.value = null;
    success('Perfil atualizado', 'Suas informacoes foram salvas.');
  } catch (err) {
    notifyError('Erro ao salvar perfil', err.message || String(err));
  } finally {
    isSaving.value = false;
  }
};

const resetChanges = () => {
  form.value = JSON.parse(JSON.stringify(profile.value));
  previewImage.value = null;
  avatarFile.value = null;
};

onMounted(() => {
  fetchProfile();
});
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-tertiary);
  margin-bottom: 0.35rem;
}

.field-checkbox-input {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-info);
}
</style>
