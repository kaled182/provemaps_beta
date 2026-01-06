<template>
  <div class="min-h-screen app-page p-6">
    <div class="max-w-6xl mx-auto space-y-6">
      <header class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 class="text-2xl font-semibold app-text-primary">System Configuration</h1>
          <p class="text-sm app-text-tertiary mt-1">
            Manage environment variables and integration settings.
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <button
            v-if="activeTab === 'config'"
            type="button"
            class="px-3 py-2 rounded-md app-btn text-sm"
            @click="exportConfig"
          >
            Export
          </button>
          <button
            v-if="activeTab === 'config'"
            type="button"
            class="px-3 py-2 rounded-md app-btn text-sm"
            @click="triggerImport"
          >
            Importar Config
          </button>
          <button
            v-if="activeTab === 'config'"
            type="button"
            class="px-3 py-2 rounded-md app-btn text-sm"
            @click="openAuditHistory"
          >
            History
          </button>
          <span class="app-badge" :class="isConfigured ? 'app-badge-success' : 'app-badge-warning'">
            {{ isConfigured ? 'Configurado' : 'Incompleto' }}
          </span>
          <input ref="importInput" type="file" class="hidden" accept=".json,application/json" @change="handleImport" />
        </div>
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

      <form v-if="activeTab === 'config'" class="space-y-6 animate-fade-in" @submit.prevent>
        <div v-if="configLoading" class="app-surface rounded-lg p-6 app-text-tertiary">
          Carregando configuração...
        </div>

        <div v-else class="space-y-6">
          <section class="app-surface rounded-xl overflow-hidden">
            <div class="app-surface-muted px-6 py-4 border-b app-divider">
              <h2 class="text-lg font-semibold app-text-primary">Django Core Settings</h2>
              <p class="text-sm app-text-tertiary mt-1">Security and debug configuration</p>
            </div>
            <div class="px-6 py-5 space-y-5">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div class="space-y-2 md:col-span-2">
                  <label class="field-label" for="secret-key">SECRET_KEY <span class="text-red-500">*</span></label>
                  <input
                    id="secret-key"
                    v-model="config.SECRET_KEY"
                    type="text"
                    class="app-input field-input font-mono"
                    required
                  />
                  <p class="field-help">Restart the server after changing this value.</p>
                </div>

                <div class="space-y-2">
                  <label class="field-checkbox">
                    <input v-model="config.DEBUG" type="checkbox" class="field-checkbox-input" />
                    <span>DEBUG</span>
                  </label>
                  <p class="field-help">Disable in production to avoid leaking sensitive information.</p>
                </div>

                <div class="space-y-2 md:col-span-2">
                  <label class="field-label" for="allowed-hosts">ALLOWED_HOSTS</label>
                  <input
                    id="allowed-hosts"
                    v-model="config.ALLOWED_HOSTS"
                    type="text"
                    class="app-input field-input"
                    placeholder="localhost,127.0.0.1,example.com"
                  />
                  <p class="field-help">Comma separated. Example: localhost,127.0.0.1,example.com</p>
                </div>

                <div class="space-y-2">
                  <label class="field-checkbox">
                    <input v-model="config.ENABLE_DIAGNOSTIC_ENDPOINTS" type="checkbox" class="field-checkbox-input" />
                    <span>ENABLE_DIAGNOSTIC_ENDPOINTS</span>
                  </label>
                  <p class="field-help">Allow diagnostic endpoints (ping/telnet).</p>
                </div>
              </div>
            </div>
          </section>

          <section class="app-surface rounded-xl overflow-hidden">
            <div class="app-surface-muted px-6 py-4 border-b app-divider flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 class="text-lg font-semibold app-text-primary">Zabbix Integration</h2>
                <p class="text-sm app-text-tertiary mt-1">Monitoring server connection settings</p>
              </div>
              <button
                type="button"
                class="px-4 py-2 rounded-md app-btn-primary text-sm"
                :disabled="zabbixTest.loading"
                @click="testZabbix"
              >
                {{ zabbixTest.loading ? 'Testando...' : 'Test Connection' }}
              </button>
            </div>
            <div class="px-6 py-5 space-y-5">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div class="space-y-2 md:col-span-2">
                  <label class="field-label" for="zabbix-url">ZABBIX_API_URL <span class="text-red-500">*</span></label>
                  <input
                    id="zabbix-url"
                    v-model="config.ZABBIX_API_URL"
                    type="url"
                    class="app-input field-input"
                    placeholder="https://zabbix.example.com/api_jsonrpc.php"
                    required
                  />
                </div>

                <div class="space-y-2">
                  <label class="field-label" for="zabbix-user">ZABBIX_API_USER</label>
                  <input id="zabbix-user" v-model="config.ZABBIX_API_USER" type="text" class="app-input field-input" />
                </div>

                <div class="space-y-2">
                  <label class="field-label" for="zabbix-password">ZABBIX_API_PASSWORD</label>
                  <input
                    id="zabbix-password"
                    v-model="config.ZABBIX_API_PASSWORD"
                    type="password"
                    class="app-input field-input"
                  />
                </div>

                <div class="space-y-2 md:col-span-2">
                  <label class="field-label" for="zabbix-key">ZABBIX_API_KEY</label>
                  <input
                    id="zabbix-key"
                    v-model="config.ZABBIX_API_KEY"
                    type="text"
                    class="app-input field-input"
                  />
                  <p class="field-help">Use when authenticating via API token.</p>
                </div>
              </div>

              <div v-if="zabbixTest.message" class="test-result" :class="testResultClass(zabbixTest)">
                {{ zabbixTest.message }}
              </div>
            </div>
          </section>

          <section class="app-surface rounded-xl overflow-hidden">
            <div class="app-surface-muted px-6 py-4 border-b app-divider">
              <h2 class="text-lg font-semibold app-text-primary">External Services</h2>
              <p class="text-sm app-text-tertiary mt-1">Third-party integrations and APIs</p>
            </div>
            <div class="px-6 py-5">
              <div class="space-y-2">
                <label class="field-label" for="maps-key">GOOGLE_MAPS_API_KEY</label>
                <input
                  id="maps-key"
                  v-model="config.GOOGLE_MAPS_API_KEY"
                  type="text"
                  class="app-input field-input font-mono"
                />
              </div>
            </div>
          </section>

          <section class="app-surface rounded-xl overflow-hidden">
            <div class="app-surface-muted px-6 py-4 border-b app-divider flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <h2 class="text-lg font-semibold app-text-primary">Database Configuration</h2>
                <p class="text-sm app-text-tertiary mt-1">PostgreSQL connection settings</p>
              </div>
              <button
                type="button"
                class="px-4 py-2 rounded-md app-btn-success text-sm"
                :disabled="databaseTest.loading"
                @click="testDatabase"
              >
                {{ databaseTest.loading ? 'Testando...' : 'Test Connection' }}
              </button>
            </div>
            <div class="px-6 py-5 space-y-5">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div class="space-y-2">
                  <label class="field-label" for="db-host">DB_HOST <span class="text-red-500">*</span></label>
                  <input id="db-host" v-model="config.DB_HOST" type="text" class="app-input field-input" required />
                </div>

                <div class="space-y-2">
                  <label class="field-label" for="db-port">DB_PORT <span class="text-red-500">*</span></label>
                  <input id="db-port" v-model="config.DB_PORT" type="text" class="app-input field-input" required />
                </div>

                <div class="space-y-2">
                  <label class="field-label" for="db-name">DB_NAME <span class="text-red-500">*</span></label>
                  <input id="db-name" v-model="config.DB_NAME" type="text" class="app-input field-input" required />
                </div>

                <div class="space-y-2">
                  <label class="field-label" for="db-user">DB_USER <span class="text-red-500">*</span></label>
                  <input id="db-user" v-model="config.DB_USER" type="text" class="app-input field-input" required />
                </div>

                <div class="space-y-2 md:col-span-2">
                  <label class="field-label" for="db-password">DB_PASSWORD</label>
                  <input
                    id="db-password"
                    v-model="config.DB_PASSWORD"
                    type="password"
                    class="app-input field-input"
                  />
                </div>
              </div>

              <div v-if="databaseTest.message" class="test-result" :class="testResultClass(databaseTest)">
                {{ databaseTest.message }}
              </div>
            </div>
          </section>

          <section class="app-surface rounded-xl overflow-hidden">
            <div class="app-surface-muted px-6 py-4 border-b app-divider">
              <h2 class="text-lg font-semibold app-text-primary">Redis & Caching</h2>
              <p class="text-sm app-text-tertiary mt-1">Cache and Celery broker configuration</p>
            </div>
            <div class="px-6 py-5">
              <div class="space-y-2">
                <label class="field-label" for="redis-url">REDIS_URL</label>
                <input
                  id="redis-url"
                  v-model="config.REDIS_URL"
                  type="text"
                  class="app-input field-input font-mono"
                  placeholder="redis://redis:6379/1"
                />
                <p class="field-help">Example: redis://redis:6379/1</p>
              </div>
            </div>
          </section>

          <section class="app-surface rounded-xl overflow-hidden">
            <div class="app-surface-muted px-6 py-4 border-b app-divider">
              <h2 class="text-lg font-semibold app-text-primary">System Operations</h2>
              <p class="text-sm app-text-tertiary mt-1">Service management and restart commands</p>
            </div>
            <div class="px-6 py-5">
              <div class="space-y-2">
                <label class="field-label" for="restart-commands">SERVICE_RESTART_COMMANDS</label>
                <textarea
                  id="restart-commands"
                  v-model="config.SERVICE_RESTART_COMMANDS"
                  rows="3"
                  class="app-input field-input field-textarea font-mono"
                ></textarea>
                <p class="field-help">
                  Commands executed after saving credentials. Separate multiple commands with ';'. Example:
                  docker compose restart web; docker compose restart worker
                </p>
              </div>
            </div>
          </section>

          <div class="sticky bottom-0 app-surface rounded-xl">
            <div class="px-6 py-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div class="text-sm app-text-tertiary">
                Changes are encrypted and stored securely. No data is sent to external servers.
              </div>
              <div class="flex items-center gap-3">
                <button
                  type="button"
                  class="px-4 py-2 rounded-md app-btn"
                  @click="fetchConfig"
                  :disabled="configSaving"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  class="px-5 py-2 rounded-md app-btn-primary"
                  :disabled="configSaving"
                  @click="saveConfig"
                >
                  {{ configSaving ? 'Salvando...' : 'Save Configuration' }}
                </button>
              </div>
            </div>
          </div>

          <div v-if="config.SERVICE_RESTART_COMMANDS" class="app-surface rounded-lg p-4">
            <div class="flex items-start gap-3">
              <span class="app-badge app-badge-warning">Restart Required</span>
              <div class="space-y-2">
                <p class="text-sm app-text-secondary">
                  After saving changes, restart the services for the new configuration to take effect:
                </p>
                <code class="block app-surface-muted px-3 py-2 rounded text-xs font-mono app-text-primary">
                  {{ config.SERVICE_RESTART_COMMANDS }}
                </code>
              </div>
            </div>
          </div>

          <div class="app-surface rounded-lg p-4">
            <div class="flex items-start gap-3">
              <span class="app-badge app-badge-info">Help</span>
              <div class="space-y-2 text-sm app-text-secondary">
                <p>All sensitive data (passwords, API keys) is encrypted using Fernet encryption.</p>
                <p>Use either Zabbix API User/Password or API Key (not both).</p>
                <p>Database settings must match your PostgreSQL instance.</p>
                <p>Redis URL is optional but recommended for production.</p>
              </div>
            </div>
          </div>
        </div>
      </form>

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
              class="mt-4 w-full py-2 rounded-md app-btn-primary flex items-center justify-center gap-2"
              :disabled="backupCreating || backupUploading"
              @click="createBackup"
            >
              <span v-if="backupCreating" class="app-spinner h-4 w-4"></span>
              <span>{{ backupCreating ? 'Gerando...' : 'Iniciar Backup Agora' }}</span>
            </button>
          </div>

          <div class="app-surface rounded-lg p-6 flex flex-col">
            <h3 class="text-lg font-semibold app-text-primary">Upload externo</h3>
            <p class="text-sm app-text-tertiary mt-2">Envie um arquivo .dump ou .sql de outro servidor.</p>
            <div class="mt-4">
              <input
                ref="backupFileInput"
                type="file"
                class="hidden"
                accept=".dump,.sql"
                @change="handleBackupUpload"
              />
              <button
                type="button"
                class="w-full py-2 rounded-md app-btn flex items-center justify-center gap-2"
                @click="selectBackupFile"
              >
                <span v-if="backupUploading" class="app-spinner h-4 w-4"></span>
                <span>{{ backupUploading ? 'Enviando...' : 'Selecionar arquivo' }}</span>
              </button>
              <p v-if="backupUploading" class="text-xs app-text-tertiary mt-2">Upload em andamento...</p>
            </div>
          </div>

          <div class="app-surface rounded-lg p-6 flex flex-col">
            <h3 class="text-lg font-semibold app-text-primary">Retenção automática</h3>
            <p class="text-sm app-text-tertiary mt-2">Defina quantos backups manter no servidor.</p>
            <div class="grid grid-cols-1 gap-4 mt-4">
              <div>
                <label class="field-label" for="retention-days">Dias máximos</label>
                <input
                  id="retention-days"
                  v-model="retentionDays"
                  type="number"
                  min="0"
                  class="app-input field-input"
                />
              </div>
              <div>
                <label class="field-label" for="retention-count">Quantidade máxima</label>
                <input
                  id="retention-count"
                  v-model="retentionCount"
                  type="number"
                  min="0"
                  class="app-input field-input"
                />
              </div>
              <button
                type="button"
                class="w-full py-2 rounded-md app-btn-success"
                :disabled="retentionSaving"
                @click="saveRetentionSettings"
              >
                {{ retentionSaving ? 'Salvando...' : 'Salvar Retenção' }}
              </button>
            </div>
          </div>
        </div>

        <div class="app-surface rounded-lg p-6">
          <h3 class="text-lg font-semibold app-text-primary">Resumo</h3>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
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
            <div class="app-surface-muted rounded-md p-4">
              <p class="text-sm app-text-tertiary">Retenção</p>
              <p class="text-base font-semibold app-text-primary mt-1">
                {{ retentionSummary }}
              </p>
            </div>
          </div>
        </div>

        <div class="app-surface rounded-lg overflow-hidden">
          <div class="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b app-divider">
            <div>
              <h3 class="font-semibold app-text-primary">Histórico de Arquivos</h3>
              <p class="text-xs app-text-tertiary">Total: {{ backups.length }} arquivo(s)</p>
            </div>
            <button type="button" class="text-sm app-text-secondary" @click="fetchBackups">
              Atualizar Lista
            </button>
          </div>

          <div v-if="backupLoading" class="p-6 text-sm app-text-tertiary">Carregando backups...</div>

          <table v-else class="min-w-full divide-y app-divide">
            <thead class="app-surface-muted">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Arquivo</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Tipo</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Data</th>
                <th class="px-6 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Tamanho</th>
                <th class="px-6 py-3 text-right text-xs font-medium app-text-tertiary uppercase">Ações</th>
              </tr>
            </thead>
            <tbody class="divide-y app-divide">
              <tr v-for="file in backups" :key="file.name" class="app-row">
                <td class="px-6 py-4 text-sm font-medium app-text-primary">{{ file.name }}</td>
                <td class="px-6 py-4 text-sm">
                  <span class="app-chip">{{ formatBackupType(file.type) }}</span>
                </td>
                <td class="px-6 py-4 text-sm app-text-tertiary">{{ formatDate(file.created_at) }}</td>
                <td class="px-6 py-4 text-sm app-text-tertiary">{{ formatSize(file.size) }}</td>
                <td class="px-6 py-4 text-right text-sm space-x-2">
                  <a
                    class="app-btn px-3 py-1 rounded"
                    :href="backupDownloadUrl(file.name)"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Baixar
                  </a>
                  <button
                    v-if="canRestore(file)"
                    type="button"
                    class="app-btn-warning px-3 py-1 rounded"
                    :disabled="backupCreating || backupUploading"
                    @click="restoreBackup(file)"
                  >
                    Restaurar
                  </button>
                  <button
                    v-else-if="canApplyConfig(file)"
                    type="button"
                    class="app-btn-primary px-3 py-1 rounded"
                    :disabled="configImporting"
                    @click="applyConfigBackup(file)"
                  >
                    {{ configImporting ? 'Aplicando...' : 'Aplicar Config' }}
                  </button>
                  <button
                    type="button"
                    class="app-btn-danger px-3 py-1 rounded"
                    :disabled="backupDeleting.has(file.name)"
                    @click="deleteBackup(file)"
                  >
                    {{ backupDeleting.has(file.name) ? 'Removendo...' : 'Excluir' }}
                  </button>
                </td>
              </tr>
              <tr v-if="backups.length === 0">
                <td colspan="5" class="px-6 py-10 text-center text-sm app-text-tertiary">
                  Nenhum backup encontrado.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-if="auditOpen" class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div class="app-surface rounded-xl max-w-6xl w-full max-h-[90vh] overflow-hidden">
        <div class="flex items-center justify-between border-b app-divider px-6 py-4 app-surface-muted">
          <h2 class="text-xl font-semibold app-text-primary">Configuration Change History</h2>
          <button type="button" class="app-text-tertiary" @click="auditOpen = false">✕</button>
        </div>
        <div class="overflow-y-auto max-h-[calc(90vh-120px)] p-6">
          <table class="min-w-full divide-y app-divide">
            <thead class="app-surface-muted">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Timestamp</th>
                <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase">User</th>
                <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Action</th>
                <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Section</th>
                <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Field</th>
                <th class="px-4 py-3 text-left text-xs font-medium app-text-tertiary uppercase">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y app-divide">
              <tr v-if="auditLoading">
                <td colspan="6" class="px-4 py-6 text-center text-sm app-text-tertiary">Carregando...</td>
              </tr>
              <tr v-else-if="audits.length === 0">
                <td colspan="6" class="px-4 py-6 text-center text-sm app-text-tertiary">Sem registros.</td>
              </tr>
              <tr v-for="entry in audits" :key="entry.id" class="app-row">
                <td class="px-4 py-3 text-sm app-text-secondary">{{ formatDate(entry.timestamp) }}</td>
                <td class="px-4 py-3 text-sm app-text-secondary">{{ entry.user }}</td>
                <td class="px-4 py-3 text-sm app-text-secondary">{{ entry.action }}</td>
                <td class="px-4 py-3 text-sm app-text-secondary">{{ entry.section }}</td>
                <td class="px-4 py-3 text-sm app-text-secondary">{{ entry.field_name || '-' }}</td>
                <td class="px-4 py-3 text-sm">
                  <span class="app-badge" :class="entry.success ? 'app-badge-success' : 'app-badge-danger'">
                    {{ entry.success ? 'Ok' : 'Erro' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useApi } from '@/composables/useApi';
import { useNotification } from '@/composables/useNotification';

const api = useApi();
const { success, error: notifyError, info } = useNotification();

const tabs = [
  { id: 'config', name: 'Configuração' },
  { id: 'backups', name: 'Backups' },
];

const activeTab = ref('config');

const config = reactive({
  SECRET_KEY: '',
  DEBUG: false,
  ALLOWED_HOSTS: '',
  ENABLE_DIAGNOSTIC_ENDPOINTS: false,
  ZABBIX_API_URL: '',
  ZABBIX_API_USER: '',
  ZABBIX_API_PASSWORD: '',
  ZABBIX_API_KEY: '',
  GOOGLE_MAPS_API_KEY: '',
  DB_HOST: '',
  DB_PORT: '',
  DB_NAME: '',
  DB_USER: '',
  DB_PASSWORD: '',
  REDIS_URL: '',
  SERVICE_RESTART_COMMANDS: '',
});

const configLoading = ref(false);
const configSaving = ref(false);

const zabbixTest = reactive({
  loading: false,
  success: false,
  message: '',
});

const databaseTest = reactive({
  loading: false,
  success: false,
  message: '',
});

const audits = ref([]);
const auditOpen = ref(false);
const auditLoading = ref(false);

const backups = ref([]);
const backupLoading = ref(false);
const backupCreating = ref(false);
const backupUploading = ref(false);
const backupDeleting = ref(new Set());
const retentionDays = ref('');
const retentionCount = ref('');
const retentionSaving = ref(false);
const backupFileInput = ref(null);
const configImporting = ref(false);

const importInput = ref(null);

const lastBackupLabel = computed(() => {
  if (!backups.value.length) return 'Nenhum';
  return formatDate(backups.value[0].created_at);
});

const retentionSummary = computed(() => {
  const days = retentionDays.value ? `${retentionDays.value} dias` : 'n/a';
  const count = retentionCount.value ? `${retentionCount.value} arquivos` : 'n/a';
  if (retentionDays.value && retentionCount.value) {
    return `${days} ou ${count}`;
  }
  if (retentionDays.value) {
    return days;
  }
  if (retentionCount.value) {
    return count;
  }
  return 'Sem política';
});

const isConfigured = computed(() => {
  return Boolean(
    config.SECRET_KEY &&
      config.ZABBIX_API_URL &&
      config.DB_HOST &&
      config.DB_PORT &&
      config.DB_NAME &&
      config.DB_USER
  );
});

const testResultClass = (result) => {
  if (!result.message) return '';
  return result.success ? 'test-success' : 'test-error';
};

const fetchConfig = async () => {
  configLoading.value = true;
  try {
    const data = await api.get('/setup_app/api/config/');
    if (data.configuration) {
      Object.entries(data.configuration).forEach(([key, value]) => {
        if (key in config) {
          config[key] = value;
        }
      });
    }
  } catch (err) {
    notifyError('Falha ao carregar configuração', err.message || String(err));
  } finally {
    configLoading.value = false;
  }
};

const saveConfig = async () => {
  configSaving.value = true;
  try {
    const payload = { ...config };
    const data = await api.post('/setup_app/api/config/update/', payload);
    success('Configuração salva', data.message || 'Alterações registradas.');
  } catch (err) {
    notifyError('Falha ao salvar configuração', err.message || String(err));
  } finally {
    configSaving.value = false;
  }
};

const testZabbix = async () => {
  zabbixTest.loading = true;
  zabbixTest.message = '';
  try {
    const authType = config.ZABBIX_API_KEY ? 'token' : 'login';
    const data = await api.post('/setup_app/api/test-zabbix/', {
      zabbix_api_url: config.ZABBIX_API_URL,
      auth_type: authType,
      zabbix_api_user: config.ZABBIX_API_USER,
      zabbix_api_password: config.ZABBIX_API_PASSWORD,
      zabbix_api_key: config.ZABBIX_API_KEY,
    });
    zabbixTest.success = Boolean(data.success);
    zabbixTest.message = data.message || 'Conexão testada.';
  } catch (err) {
    zabbixTest.success = false;
    zabbixTest.message = err.message || 'Falha ao testar Zabbix.';
  } finally {
    zabbixTest.loading = false;
  }
};

const testDatabase = async () => {
  databaseTest.loading = true;
  databaseTest.message = '';
  try {
    const data = await api.post('/setup_app/api/test-database/', {
      db_host: config.DB_HOST,
      db_port: config.DB_PORT,
      db_name: config.DB_NAME,
      db_user: config.DB_USER,
      db_password: config.DB_PASSWORD,
    });
    databaseTest.success = Boolean(data.success);
    databaseTest.message = data.message || 'Conexão testada.';
  } catch (err) {
    databaseTest.success = false;
    databaseTest.message = err.message || 'Falha ao testar banco.';
  } finally {
    databaseTest.loading = false;
  }
};

const exportConfig = async () => {
  try {
    const response = await fetch('/setup_app/api/export/', {
      method: 'GET',
      credentials: 'same-origin',
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `mapsprove_config_${new Date().toISOString().split('T')[0]}.json`;
    anchor.click();
    window.URL.revokeObjectURL(url);
    success('Configuração exportada', 'Arquivo baixado com sucesso.');
  } catch (err) {
    notifyError('Falha ao exportar', err.message || String(err));
  }
};

const triggerImport = () => {
  importInput.value?.click();
};

const handleImport = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('config_file', file);

  try {
    const data = await api.postFormData('/setup_app/api/import/', formData);
    success('Importação concluída', data.message || 'Configuração importada.');
    await fetchConfig();
  } catch (err) {
    notifyError('Falha ao importar', err.message || String(err));
  } finally {
    event.target.value = '';
  }
};

const openAuditHistory = async () => {
  auditOpen.value = true;
  await fetchAuditHistory();
};

const fetchAuditHistory = async () => {
  auditLoading.value = true;
  try {
    const data = await api.get('/setup_app/api/audit-history/?limit=50');
    audits.value = data.audits || [];
  } catch (err) {
    notifyError('Falha ao carregar histórico', err.message || String(err));
  } finally {
    auditLoading.value = false;
  }
};

const fetchBackups = async () => {
  backupLoading.value = true;
  try {
    const data = await api.get('/setup_app/api/backups/');
    backups.value = data.backups || [];
    if (data.settings) {
      retentionDays.value = data.settings.retention_days || '';
      retentionCount.value = data.settings.retention_count || '';
    }
  } catch (err) {
    notifyError('Falha ao listar backups', err.message || String(err));
  } finally {
    backupLoading.value = false;
  }
};

const createBackup = async () => {
  backupCreating.value = true;
  try {
    const data = await api.post('/setup_app/api/backups/', {});
    info('Backup iniciado', data.message || 'Processo de backup iniciado.');
    await fetchBackups();
  } catch (err) {
    notifyError('Falha ao criar backup', err.message || String(err));
  } finally {
    backupCreating.value = false;
  }
};

const selectBackupFile = () => {
  backupFileInput.value?.click();
};

const handleBackupUpload = async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;

  if (!file.name.toLowerCase().endsWith('.dump') && !file.name.toLowerCase().endsWith('.sql')) {
    notifyError('Formato inválido', 'Envie apenas arquivos .dump ou .sql');
    event.target.value = '';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  backupUploading.value = true;
  try {
    const data = await api.postFormData('/setup_app/api/backups/', formData);
    success('Backup enviado', data.message || 'Upload concluído.');
    await fetchBackups();
  } catch (err) {
    notifyError('Falha no upload', err.message || String(err));
  } finally {
    backupUploading.value = false;
    event.target.value = '';
  }
};

const saveRetentionSettings = async () => {
  retentionSaving.value = true;
  try {
    const payload = {
      retention_days: retentionDays.value,
      retention_count: retentionCount.value,
    };
    const data = await api.post('/setup_app/api/backups/settings/', payload);
    success('Retenção atualizada', data.message || 'Configuração salva.');
    await fetchBackups();
  } catch (err) {
    notifyError('Falha ao salvar retenção', err.message || String(err));
  } finally {
    retentionSaving.value = false;
  }
};

const restoreBackup = async (file) => {
  const code = window.prompt(
    `PERIGO: Isso irá restaurar o backup ${file.name}.\nDigite \"CONFIRMAR\" para continuar.`
  );
  if (code !== 'CONFIRMAR') {
    info('Restauração cancelada', 'Nenhuma alteração foi aplicada.');
    return;
  }

  try {
    const data = await api.post('/setup_app/api/backups/restore/', { filename: file.name });
    info('Restauração iniciada', data.message || 'Processo iniciado.');
  } catch (err) {
    notifyError('Falha ao restaurar backup', err.message || String(err));
  }
};

const deleteBackup = async (file) => {
  const confirmed = window.confirm(`Excluir permanentemente ${file.name}?`);
  if (!confirmed) return;

  backupDeleting.value = new Set([...backupDeleting.value, file.name]);
  try {
    const data = await api.post('/setup_app/api/backups/delete/', { filename: file.name });
    success('Backup removido', data.message || 'Arquivo excluído.');
    await fetchBackups();
  } catch (err) {
    notifyError('Falha ao excluir backup', err.message || String(err));
  } finally {
    const updated = new Set(backupDeleting.value);
    updated.delete(file.name);
    backupDeleting.value = updated;
  }
};

const backupDownloadUrl = (filename) => {
  return `/setup_app/api/backups/download/${encodeURIComponent(filename)}/`;
};

const formatBackupType = (type) => {
  const normalized = (type || '').toLowerCase();
  if (normalized === 'auto') return 'Automático';
  if (normalized === 'manual') return 'Manual';
  if (normalized === 'upload') return 'Upload';
  if (normalized === 'config') return 'Config';
  return 'Outro';
};

const canRestore = (file) => {
  const name = (file?.name || '').toLowerCase();
  return name.endsWith('.dump') || name.endsWith('.sql');
};

const canApplyConfig = (file) => {
  const name = (file?.name || '').toLowerCase();
  return name.endsWith('.config.json');
};

const applyConfigBackup = async (file) => {
  const code = window.prompt(
    `Isso irá aplicar a configuração salva em ${file.name}.\nDigite \"CONFIRMAR\" para continuar.`
  );
  if (code !== 'CONFIRMAR') {
    info('Importação cancelada', 'Nenhuma alteração foi aplicada.');
    return;
  }

  configImporting.value = true;
  try {
    const response = await fetch(backupDownloadUrl(file.name), { credentials: 'same-origin' });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const payload = await response.json();
    if (payload.env_file) {
      await api.post('/setup_app/api/env/import/', { env_file: payload.env_file });
      success('Configuração aplicada', 'Arquivo .env restaurado.');
    } else if (payload.configuration) {
      await api.post('/setup_app/api/config/update/', payload.configuration);
      success('Configuração aplicada', 'Configuração do sistema atualizada.');
    } else {
      notifyError('Arquivo inválido', 'Nenhuma configuração encontrada no backup.');
    }
  } catch (err) {
    notifyError('Falha ao aplicar config', err.message || String(err));
  } finally {
    configImporting.value = false;
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
  fetchConfig();
  fetchBackups();
});
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.field-help {
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

.field-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
}

.field-textarea {
  min-height: 96px;
}

.field-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.field-checkbox-input {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-info);
}

.test-result {
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  border: 1px solid transparent;
}

.test-success {
  background: var(--status-online-light);
  color: var(--status-online);
  border-color: var(--status-online);
}

.test-error {
  background: var(--status-offline-light);
  color: var(--status-offline);
  border-color: var(--status-offline);
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
