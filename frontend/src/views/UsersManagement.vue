<template>
  <div class="min-h-screen app-page p-6">
    <div class="max-w-6xl mx-auto space-y-6">
      <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 class="text-2xl font-semibold app-text-primary">Gestao de Usuarios</h1>
          <p class="text-sm app-text-tertiary mt-1">
            Administre acessos, contatos e politicas de notificacao do sistema.
          </p>
        </div>
        <button type="button" class="app-btn-primary px-4 py-2 rounded-md" @click="openModal()">
          Novo Usuario
        </button>
      </header>

      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="app-surface rounded-lg p-4 flex items-center justify-between">
          <div>
            <p class="text-xs app-text-tertiary uppercase">Total</p>
            <p class="text-2xl font-semibold app-text-primary">{{ totalUsers }}</p>
          </div>
          <span class="text-xs app-text-tertiary">Usuarios</span>
        </div>
        <div class="app-surface rounded-lg p-4 flex items-center justify-between">
          <div>
            <p class="text-xs app-text-tertiary uppercase">Ativos</p>
            <p class="text-2xl font-semibold text-emerald-400">{{ activeUsers }}</p>
          </div>
          <span class="text-xs app-text-tertiary">Status</span>
        </div>
        <div class="app-surface rounded-lg p-4 flex items-center justify-between">
          <div>
            <p class="text-xs app-text-tertiary uppercase">Admins</p>
            <p class="text-2xl font-semibold text-sky-400">{{ adminUsers }}</p>
          </div>
          <span class="text-xs app-text-tertiary">Permissoes</span>
        </div>
        <div class="app-surface rounded-lg p-4 flex items-center justify-between">
          <div>
            <p class="text-xs app-text-tertiary uppercase">Inativos</p>
            <p class="text-2xl font-semibold text-rose-400">{{ inactiveUsers }}</p>
          </div>
          <span class="text-xs app-text-tertiary">Status</span>
        </div>
      </section>

      <div class="app-surface rounded-lg p-4 flex flex-col gap-4 md:flex-row md:items-center">
        <div class="relative flex-1">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-sm app-text-tertiary">🔍</span>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Buscar por nome, usuario ou email"
            class="app-input w-full pl-10 pr-3 py-2"
          />
        </div>
        <div class="flex items-center gap-3">
          <label class="text-sm app-text-tertiary">Status</label>
          <select v-model="statusFilter" class="app-input px-3 py-2">
            <option value="all">Todos</option>
            <option value="active">Ativos</option>
            <option value="inactive">Inativos</option>
          </select>
        </div>
      </div>

      <div class="app-surface rounded-lg overflow-hidden">
        <div class="flex items-center justify-between px-6 py-4 border-b app-divider">
          <h2 class="font-semibold app-text-primary">Usuarios</h2>
          <span class="text-xs app-text-tertiary">{{ filteredUsers.length }} usuarios</span>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y app-divide">
            <thead class="app-surface-muted">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Usuario</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Contato</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Notificacoes</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Permissoes</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Status</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Atividade</th>
                <th class="px-6 py-3 text-right text-xs font-medium app-text-tertiary uppercase">Acoes</th>
              </tr>
            </thead>
            <tbody class="divide-y app-divide">
              <tr v-for="user in filteredUsers" :key="user.id" class="app-row">
                <td class="px-6 py-4">
                  <div class="flex items-center gap-3">
                    <div class="h-10 w-10 rounded-full app-surface-muted flex items-center justify-center font-semibold app-text-primary overflow-hidden">
                      <img
                        v-if="user.profile.avatar_url"
                        :src="user.profile.avatar_url"
                        class="w-full h-full object-cover"
                        alt="Avatar"
                      />
                      <span v-else>
                        {{ getInitials(user.full_name || user.username) }}
                      </span>
                    </div>
                    <div>
                      <div class="text-sm font-medium app-text-primary">{{ user.full_name || user.username }}</div>
                      <div class="text-xs app-text-tertiary">@{{ user.username }}</div>
                      <div class="text-xs app-text-tertiary">
                        {{ user.profile.department || 'Sem departamento' }}
                      </div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="text-sm app-text-secondary">{{ user.email || '-' }}</div>
                  <div class="text-xs app-text-tertiary">
                    {{ user.profile.phone_number || 'Sem celular' }}
                  </div>
                  <div v-if="user.profile.telegram_chat_id" class="text-xs app-text-tertiary">
                    TG: {{ user.profile.telegram_chat_id }}
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex flex-wrap gap-2">
                    <span v-if="user.profile.notify_via_email" class="app-badge app-badge-muted">Email</span>
                    <span v-if="user.profile.notify_via_whatsapp" class="app-badge app-badge-success">Whats</span>
                    <span v-if="user.profile.notify_via_telegram" class="app-badge app-badge-info">Tele</span>
                    <span v-if="user.profile.receive_critical_alerts" class="app-badge app-badge-danger">Critico</span>
                    <span v-if="user.profile.receive_warning_alerts" class="app-badge app-badge-warning">Aviso</span>
                    <span v-if="!hasNotificationPrefs(user.profile)" class="text-xs app-text-tertiary">-</span>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex flex-wrap gap-2">
                    <span v-if="user.is_superuser" class="app-badge app-badge-info">Superuser</span>
                    <span v-if="user.is_staff" class="app-badge app-badge-muted">Staff</span>
                    <span v-for="group in user.groups" :key="group.id" class="app-badge">
                      {{ group.name }}
                    </span>
                    <span v-if="!user.is_staff && !user.is_superuser && user.groups.length === 0" class="text-xs app-text-tertiary">
                      Padrao
                    </span>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class="app-badge" :class="user.is_active ? 'app-badge-success' : 'app-badge-danger'">
                    {{ user.is_active ? 'Ativo' : 'Inativo' }}
                  </span>
                </td>
                <td class="px-6 py-4 text-sm app-text-tertiary">
                  {{ user.last_login ? timeAgo(user.last_login) : 'Nunca' }}
                </td>
                <td class="px-6 py-4 text-right text-sm">
                  <button class="app-btn px-3 py-1 rounded mr-2" @click="openModal(user)">Editar</button>
                  <button class="app-btn-warning px-3 py-1 rounded mr-2" @click="toggleActive(user)">
                    {{ user.is_active ? 'Desativar' : 'Ativar' }}
                  </button>
                  <button
                    class="app-btn-danger px-3 py-1 rounded"
                    :class="user.is_superuser ? 'opacity-50 cursor-not-allowed' : ''"
                    :disabled="user.is_superuser"
                    @click="confirmDelete(user)"
                  >
                    Excluir
                  </button>
                </td>
              </tr>
              <tr v-if="filteredUsers.length === 0">
                <td colspan="7" class="px-6 py-10 text-center text-sm app-text-tertiary">
                  Nenhum usuario encontrado.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div class="app-surface rounded-lg w-full max-w-2xl">
        <div class="px-6 py-4 border-b app-divider app-surface-muted flex items-center justify-between">
          <h3 class="text-lg font-semibold app-text-primary">
            {{ isEditing ? 'Editar usuario' : 'Novo usuario' }}
          </h3>
          <button class="app-btn px-2 py-1 rounded" @click="closeModal">Fechar</button>
        </div>

        <div class="flex border-b app-divider">
          <button
            class="flex-1 py-2 text-sm font-medium"
            :class="activeTab === 'profile' ? 'app-text-primary border-b-2 border-sky-400' : 'app-text-tertiary'"
            @click="activeTab = 'profile'"
          >
            Perfil
          </button>
          <button
            class="flex-1 py-2 text-sm font-medium"
            :class="activeTab === 'notifications' ? 'app-text-primary border-b-2 border-sky-400' : 'app-text-tertiary'"
            @click="activeTab = 'notifications'"
          >
            Notificacoes
          </button>
          <button
            class="flex-1 py-2 text-sm font-medium"
            :class="activeTab === 'permissions' ? 'app-text-primary border-b-2 border-sky-400' : 'app-text-tertiary'"
            @click="activeTab = 'permissions'"
          >
            Permissoes
          </button>
          <button
            class="flex-1 py-2 text-sm font-medium"
            :class="activeTab === 'security' ? 'app-text-primary border-b-2 border-sky-400' : 'app-text-tertiary'"
            @click="activeTab = 'security'"
          >
            Seguranca
          </button>
        </div>

        <form class="p-6 space-y-4" @submit.prevent="saveUser">
          <div v-if="activeTab === 'profile'" class="space-y-4">
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
              <label class="field-label">Usuario</label>
              <input v-model="form.username" type="text" class="app-input w-full" :disabled="isEditing" />
            </div>
            <div>
              <label class="field-label">Email</label>
              <input v-model="form.email" type="email" class="app-input w-full" />
            </div>
            <div>
              <label class="field-label">Departamento</label>
              <input v-model="form.profile.department" type="text" class="app-input w-full" />
            </div>
          </div>

          <div v-if="activeTab === 'notifications'" class="space-y-4">
            <div class="app-surface-muted rounded-lg p-4 space-y-3">
              <label class="field-label">Celular / WhatsApp</label>
              <input v-model="form.profile.phone_number" type="text" class="app-input w-full" />
              <label class="field-label">Telegram Chat ID</label>
              <input v-model="form.profile.telegram_chat_id" type="text" class="app-input w-full" />
            </div>
            <div class="app-surface-muted rounded-lg p-4 space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm app-text-secondary">Receber via Email</span>
                <input type="checkbox" v-model="form.profile.notify_via_email" class="field-checkbox-input" />
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm app-text-secondary">Receber via WhatsApp</span>
                <input type="checkbox" v-model="form.profile.notify_via_whatsapp" class="field-checkbox-input" />
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm app-text-secondary">Receber via Telegram</span>
                <input type="checkbox" v-model="form.profile.notify_via_telegram" class="field-checkbox-input" />
              </div>
            </div>
            <div class="app-surface-muted rounded-lg p-4 space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm app-text-secondary">Alertas Criticos</span>
                <input type="checkbox" v-model="form.profile.receive_critical_alerts" class="field-checkbox-input" />
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm app-text-secondary">Alertas de Aviso</span>
                <input type="checkbox" v-model="form.profile.receive_warning_alerts" class="field-checkbox-input" />
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'permissions'" class="space-y-4">
            <div class="app-surface-muted rounded-lg p-4 space-y-3">
              <div class="flex items-center justify-between">
                <span class="text-sm app-text-secondary">Staff</span>
                <input type="checkbox" v-model="form.is_staff" class="field-checkbox-input" />
              </div>
              <div class="flex items-center justify-between">
                <span class="text-sm app-text-secondary">Superuser</span>
                <input type="checkbox" v-model="form.is_superuser" class="field-checkbox-input" />
              </div>
            </div>
            <div>
              <label class="field-label">Grupos</label>
              <div class="app-surface-muted rounded-lg p-3 max-h-40 overflow-y-auto space-y-2">
                <div v-if="availableGroups.length === 0" class="text-xs app-text-tertiary">
                  Nenhum grupo disponivel.
                </div>
                <label
                  v-for="group in availableGroups"
                  :key="group.id"
                  class="flex items-center gap-2 text-sm app-text-secondary"
                >
                  <input
                    type="checkbox"
                    :value="group.id"
                    v-model="form.groups"
                    class="field-checkbox-input"
                  />
                  {{ group.name }}
                </label>
              </div>
            </div>
          </div>

          <div v-if="activeTab === 'security'" class="space-y-4">
            <div class="app-surface-muted rounded-lg p-4">
              <label class="field-label">Senha</label>
              <input
                v-model="form.password"
                type="password"
                class="app-input w-full"
                :placeholder="isEditing ? 'Nova senha (opcional)' : 'Obrigatorio'"
              />
            </div>
            <div class="app-surface-muted rounded-lg p-4 flex items-center justify-between">
              <span class="text-sm app-text-secondary">Conta ativa</span>
              <input type="checkbox" v-model="form.is_active" class="field-checkbox-input" />
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="app-btn px-4 py-2 rounded" @click="closeModal">Cancelar</button>
            <button type="submit" class="app-btn-primary px-4 py-2 rounded">
              {{ isEditing ? 'Salvar' : 'Criar' }}
            </button>
          </div>
        </form>
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

const defaultProfile = {
  phone_number: '',
  telegram_chat_id: '',
  notify_via_email: true,
  notify_via_whatsapp: false,
  notify_via_telegram: false,
  receive_critical_alerts: true,
  receive_warning_alerts: false,
  department: '',
};

const users = ref([]);
const availableGroups = ref([]);
const searchQuery = ref('');
const statusFilter = ref('all');
const showModal = ref(false);
const isEditing = ref(false);
const activeTab = ref('profile');

const form = ref({
  username: '',
  email: '',
  first_name: '',
  last_name: '',
  password: '',
  is_active: true,
  is_staff: false,
  is_superuser: false,
  groups: [],
  profile: { ...defaultProfile },
});

const totalUsers = computed(() => users.value.length);
const activeUsers = computed(() => users.value.filter(user => user.is_active).length);
const adminUsers = computed(() => users.value.filter(user => user.is_staff || user.is_superuser).length);
const inactiveUsers = computed(() => users.value.filter(user => !user.is_active).length);

const filteredUsers = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  let result = users.value;

  if (statusFilter.value !== 'all') {
    const isActive = statusFilter.value === 'active';
    result = result.filter(user => user.is_active === isActive);
  }

  if (!query) return result;

  return result.filter(user => {
    const fullName = (user.full_name || '').toLowerCase();
    const username = (user.username || '').toLowerCase();
    const email = (user.email || '').toLowerCase();
    return fullName.includes(query) || username.includes(query) || email.includes(query);
  });
});

const hasNotificationPrefs = (profile) => {
  return (
    profile.notify_via_email ||
    profile.notify_via_whatsapp ||
    profile.notify_via_telegram ||
    profile.receive_critical_alerts ||
    profile.receive_warning_alerts
  );
};

const fetchUsers = async () => {
  const data = await api.get('/api/users/');
  users.value = (data.users || []).map(user => ({
    ...user,
    groups: user.groups || [],
    profile: { ...defaultProfile, ...(user.profile || {}) },
  }));
};

const fetchGroups = async () => {
  const data = await api.get('/api/groups/');
  availableGroups.value = data.groups || [];
};

const loadData = async () => {
  try {
    await Promise.all([fetchUsers(), fetchGroups()]);
  } catch (err) {
    notifyError('Erro ao carregar dados', err.message || String(err));
  }
};

const openModal = (user = null) => {
  activeTab.value = 'profile';
  if (user) {
    isEditing.value = true;
    form.value = {
      id: user.id,
      username: user.username,
      email: user.email,
      first_name: user.first_name || '',
      last_name: user.last_name || '',
      password: '',
      is_active: user.is_active,
      is_staff: user.is_staff,
      is_superuser: user.is_superuser,
      groups: (user.groups || []).map(group => group.id),
      profile: { ...defaultProfile, ...(user.profile || {}) },
    };
  } else {
    isEditing.value = false;
    form.value = {
      username: '',
      email: '',
      first_name: '',
      last_name: '',
      password: '',
      is_active: true,
      is_staff: false,
      is_superuser: false,
      groups: [],
      profile: { ...defaultProfile },
    };
  }
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const saveUser = async () => {
  try {
    if (!form.value.username) {
      notifyError('Usuario obrigatorio', 'Informe o nome de usuario.');
      activeTab.value = 'profile';
      return;
    }
    if (!form.value.email) {
      notifyError('Email obrigatorio', 'Informe o email.');
      activeTab.value = 'profile';
      return;
    }

    if (isEditing.value) {
      const payload = { ...form.value };
      delete payload.id;
      if (!payload.password) {
        delete payload.password;
      }
      const data = await api.patch(`/api/users/${form.value.id}/update/`, payload);
      success('Usuario atualizado', data.message || 'Alteracoes salvas.');
    } else {
      if (!form.value.password) {
        notifyError('Senha obrigatoria', 'Informe a senha na aba Seguranca.');
        activeTab.value = 'security';
        return;
      }
      const payload = { ...form.value };
      const data = await api.post('/api/users/create/', payload);
      success('Usuario criado', data.message || 'Usuario criado.');
    }

    showModal.value = false;
    await fetchUsers();
  } catch (err) {
    notifyError('Falha ao salvar usuario', err.message || String(err));
  }
};

const toggleActive = async (user) => {
  try {
    const payload = { is_active: !user.is_active };
    const data = await api.patch(`/api/users/${user.id}/update/`, payload);
    success('Status atualizado', data.message || 'Usuario atualizado.');
    await fetchUsers();
  } catch (err) {
    notifyError('Falha ao atualizar status', err.message || String(err));
  }
};

const confirmDelete = async (user) => {
  if (user.is_superuser) {
    notifyError('Nao e possivel excluir', 'Remova a permissao de superuser antes de excluir.');
    return;
  }
  if (!window.confirm(`Excluir ${user.username}?`)) return;
  try {
    const data = await api.delete(`/api/users/${user.id}/delete/`);
    success('Usuario removido', data?.message || 'Usuario removido.');
    await fetchUsers();
  } catch (err) {
    notifyError('Falha ao excluir usuario', err.message || String(err));
  }
};

const getInitials = (name) => {
  if (!name) return 'UU';
  return name.slice(0, 2).toUpperCase();
};

const timeAgo = (value) => {
  const date = new Date(value);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 0) return `Ha ${days} dia${days > 1 ? 's' : ''}`;
  if (hours > 0) return `Ha ${hours} hora${hours > 1 ? 's' : ''}`;
  if (minutes > 0) return `Ha ${minutes} min`;
  return 'Agora';
};

onMounted(() => {
  loadData();
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
