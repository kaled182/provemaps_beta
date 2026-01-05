<template>
  <div class="min-h-screen app-page p-6">
    <div class="max-w-6xl mx-auto space-y-6">
      <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 class="text-2xl font-semibold app-text-primary">Configurações do Sistema</h1>
          <p class="text-sm app-text-tertiary mt-1">
            Gerencie variáveis de ambiente e backups do banco de dados.
          </p>
        </div>
        <button
          v-if="activeTab === 'env'"
          type="button"
          class="px-4 py-2 rounded-md app-btn-primary inline-flex items-center gap-2"
          :disabled="envSaving"
          @click="saveEnv"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
          <span>{{ envSaving ? 'Salvando...' : 'Salvar Alterações' }}</span>
        </button>
      </header>

      <div class="border-b app-divider">
        <nav class="flex gap-6 -mb-px">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            class="py-3 px-1 text-sm font-medium app-tab-underline"
            :class="{ 'is-active': activeTab === tab.id }"
            @click="activeTab = tab.id"
          >
            {{ tab.name }}
          </button>
        </nav>
      </div>

      <section v-if="activeTab === 'env'" class="space-y-4 animate-fade-in">
        <div class="app-surface rounded-lg overflow-hidden">
          <div class="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b app-divider app-surface-muted">
            <div>
              <h2 class="text-lg font-semibold app-text-primary">Editor de .env</h2>
              <p class="text-sm app-text-tertiary">Alterações exigem reinício do serviço web.</p>
            </div>
            <span class="app-badge app-badge-warning">Atenção</span>
          </div>
          <div class="p-0">
            <textarea
              v-model="envContent"
              class="env-editor"
              spellcheck="false"
              :disabled="envLoading"
            ></textarea>
          </div>
        </div>
      </section>

      <section v-if="activeTab === 'backups'" class="space-y-6 animate-fade-in">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div class="app-surface rounded-lg p-6 flex flex-col items-center text-center">
            <div class="backup-icon">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2a1 1 0 011 1v10.586l3.293-3.293a1 1 0 111.414 1.414l-5 5a1 1 0 01-1.414 0l-5-5a1 1 0 111.414-1.414L11 13.586V3a1 1 0 011-1z" />
                <path d="M4 14a2 2 0 012-2h4a1 1 0 110 2H6v5h12v-5h-4a1 1 0 110-2h4a2 2 0 012 2v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5z" />
              </svg>
            </div>
            <h3 class="text-lg font-semibold app-text-primary mt-3">Criar Backup</h3>
            <p class="text-sm app-text-tertiary mt-2">Gera um snapshot completo do banco PostGIS.</p>
            <button
              type="button"
              class="mt-4 w-full py-2 rounded-md app-btn-primary"
              :disabled="backupCreating"
              @click="createBackup"
            >
              {{ backupCreating ? 'Gerando...' : 'Iniciar Backup Agora' }}
            </button>
          </div>

          <div class="app-surface rounded-lg p-6 lg:col-span-2">
            <h3 class="text-lg font-semibold app-text-primary">Resumo</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
              <div class="app-surface-muted rounded-md p-4">
                <p class="text-sm app-text-tertiary">Total de Backups</p>
                <p class="text-2xl font-semibold app-text-primary mt-1">{{ backups.length }}</p>
              </div>
              <div class="app-surface-muted rounded-md p-4">
                <p class="text-sm app-text-tertiary">Último Backup</p>
                <p class="text-base font-semibold app-text-primary mt-1 truncate">
                  {{ lastBackupLabel }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div class="app-surface rounded-lg overflow-hidden">
          <div class="flex items-center justify-between px-6 py-4 border-b app-divider">
            <h3 class="font-semibold app-text-primary">Histórico de Arquivos</h3>
            <button type="button" class="text-sm app-text-secondary" @click="fetchBackups">
              Atualizar Lista
            </button>
          </div>

          <div v-if="backupLoading" class="p-6 text-sm app-text-tertiary">Carregando backups...</div>

          <table v-else class="min-w-full divide-y app-divide">
            <thead class="app-surface-muted">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Arquivo</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Data</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Tamanho</th>
                <th class="px-6 py-3 text-right text-xs font-medium app-text-tertiary uppercase">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y app-divide">
              <tr v-for="file in backups" :key="file.name" class="app-row">
                <td class="px-6 py-4 text-sm font-medium app-text-primary">{{ file.name }}</td>
                <td class="px-6 py-4 text-sm app-text-tertiary">{{ formatDate(file.created_at) }}</td>
                <td class="px-6 py-4 text-sm app-text-tertiary">{{ formatSize(file.size) }}</td>
                <td class="px-6 py-4 text-right text-sm">
                  <button
                    type="button"
                    class="app-btn-warning px-3 py-1 rounded"
                    @click="restoreBackup(file)"
                  >
                    Restaurar
                  </button>
                </td>
              </tr>
              <tr v-if="backups.length === 0">
                <td colspan="4" class="px-6 py-10 text-center text-sm app-text-tertiary">
                  Nenhum backup encontrado.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';

const api = useApi();
const { success, error: notifyError, info } = useNotification();

const tabs = [
  { id: 'env', name: 'Variáveis de Ambiente' },
  { id: 'backups', name: 'Backups' },
];

const activeTab = ref('env');
const envContent = ref('');
const envLoading = ref(false);
const envSaving = ref(false);

const backups = ref([]);
const backupLoading = ref(false);
const backupCreating = ref(false);

const lastBackupLabel = computed(() => {
  if (!backups.value.length) return 'Nenhum';
  return formatDate(backups.value[0].created_at);
});

const fetchEnv = async () => {
  envLoading.value = true;
  try {
    const data = await api.get('/setup/api/env/');
    envContent.value = data.content || '';
  } catch (err) {
    notifyError('Falha ao carregar .env', err.message || String(err));
  } finally {
    envLoading.value = false;
  }
};

const saveEnv = async () => {
  envSaving.value = true;
  try {
    const data = await api.post('/setup/api/env/update/', { content: envContent.value });
    success('Arquivo .env salvo', data.message || 'Alterações registradas.');
  } catch (err) {
    notifyError('Falha ao salvar .env', err.message || String(err));
  } finally {
    envSaving.value = false;
  }
};

const fetchBackups = async () => {
  backupLoading.value = true;
  try {
    const data = await api.get('/setup/api/backups/');
    backups.value = data.backups || [];
  } catch (err) {
    notifyError('Falha ao listar backups', err.message || String(err));
  } finally {
    backupLoading.value = false;
  }
};

const createBackup = async () => {
  backupCreating.value = true;
  try {
    const data = await api.post('/setup/api/backups/', {});
    info('Backup iniciado', data.message || 'Processo de backup iniciado.');
    await fetchBackups();
  } catch (err) {
    notifyError('Falha ao criar backup', err.message || String(err));
  } finally {
    backupCreating.value = false;
  }
};

const restoreBackup = async (file) => {
  const confirmed = window.confirm(
    `ATENÇÃO: Isso irá restaurar o backup ${file.name}. Deseja continuar?`
  );
  if (!confirmed) return;

  try {
    const data = await api.post('/setup/api/backups/restore/', { filename: file.name });
    info('Restauração iniciada', data.message || 'Processo iniciado.');
  } catch (err) {
    notifyError('Falha ao restaurar backup', err.message || String(err));
  }
};

const formatSize = (bytes = 0) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
};

const formatDate = (isoString) => {
  if (!isoString) return '';
  return new Date(isoString).toLocaleString('pt-BR');
};

onMounted(() => {
  fetchEnv();
  fetchBackups();
});
</script>

<style scoped>
.env-editor {
  width: 100%;
  min-height: 600px;
  padding: 16px;
  background: #0b1220;
  color: #e2e8f0;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  border: none;
  resize: none;
}

:root[data-theme="light"] .env-editor {
  background: #f8fafc;
  color: #0f172a;
}

.backup-icon {
  width: 64px;
  height: 64px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: var(--accent-info-light);
  color: var(--accent-info);
}

.animate-fade-in {
  animation: fadeIn 0.2s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
