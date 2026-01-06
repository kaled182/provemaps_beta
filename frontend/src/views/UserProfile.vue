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
                <a href="/accounts/password_reset/" class="app-btn-primary inline-flex mt-3 px-4 py-2 rounded">
                  Solicitar redefinicao
                </a>
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
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';

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
