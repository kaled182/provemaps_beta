<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 p-6 transition-colors duration-300">
    <div class="mb-6">
      <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 class="text-2xl font-bold tracking-tight">Configurações do Sistema</h1>
          <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Gerencie monitoramento, mapas, dados e variáveis de ambiente.</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button @click="exportConfig" class="btn-secondary">Export</button>
          <label class="btn-secondary cursor-pointer">
            <input type="file" class="hidden" @change="handleImportConfig" accept=".json">
            Importar Config
          </label>
          <button @click="openHistory" class="btn-secondary">History</button>
          <span class="inline-flex items-center rounded-full bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200 px-3 py-1 text-xs font-semibold">Configurado</span>
        </div>
      </div>
    </div>

    <div class="border-b border-gray-200 dark:border-gray-700 mb-6 overflow-x-auto">
      <nav class="-mb-px flex space-x-8 min-w-max" aria-label="Tabs">
        <button
          v-for="item in navItems"
          :key="item.id"
          @click="activeTab = item.id"
          class="group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-colors whitespace-nowrap"
          :class="activeTab === item.id
            ? 'border-primary-500 text-primary-600 dark:text-primary-400'
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'"
        >
          <component
            :is="item.icon"
            class="mr-2 h-5 w-5"
            :class="activeTab === item.id ? 'text-primary-500 dark:text-primary-400' : 'text-gray-400 group-hover:text-gray-500'"
          />
          {{ item.label }}
        </button>
      </nav>
    </div>

    <div class="animate-fade-in">
      <div v-if="activeTab === 'general'" class="space-y-6">
        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 max-w-4xl">
          <h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Resumo Operacional</h3>
          <div class="grid gap-4 md:grid-cols-2">
            <div class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Zabbix</p>
              <p class="mt-2 text-sm font-medium text-gray-900 dark:text-white break-all">{{ configForm.ZABBIX_API_URL || 'Não configurado' }}</p>
            </div>
            <div class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Banco</p>
              <p class="mt-2 text-sm font-medium text-gray-900 dark:text-white">{{ configForm.DB_HOST || 'Não configurado' }}:{{ configForm.DB_PORT || '--' }}</p>
            </div>
            <div class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Mapa</p>
              <p class="mt-2 text-sm font-medium text-gray-900 dark:text-white">{{ configForm.MAP_PROVIDER || 'google' }}</p>
            </div>
            <div class="p-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/40">
              <p class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide">Backups</p>
              <p class="mt-2 text-sm font-medium text-gray-900 dark:text-white">Retenção {{ backupSettings.retention_days || '0' }} dias / {{ backupSettings.retention_count || '0' }} arquivos</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'monitoring'" class="space-y-6">
        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 class="text-lg font-semibold">Configuração Zabbix (Padrão)</h2>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Credenciais principais usadas pelos serviços internos.</p>
            </div>
            <button @click="testZabbix" class="btn-secondary text-xs">Testar conexão</button>
          </div>

          <div class="mt-6 grid gap-4 md:grid-cols-2">
            <div class="md:col-span-2">
              <label class="label-custom">Zabbix API URL</label>
              <input v-model="configForm.ZABBIX_API_URL" type="url" class="app-input input-custom" placeholder="http://zabbix.exemplo.com/api_jsonrpc.php">
            </div>
            <div>
              <label class="label-custom">Usuário</label>
              <input v-model="configForm.ZABBIX_API_USER" type="text" class="app-input input-custom">
            </div>
            <div>
              <label class="label-custom">Senha</label>
              <input v-model="configForm.ZABBIX_API_PASSWORD" type="password" class="app-input input-custom">
            </div>
            <div class="md:col-span-2">
              <label class="label-custom">Token API (opcional)</label>
              <input v-model="configForm.ZABBIX_API_KEY" type="password" class="app-input input-custom">
              <p class="input-helper">Se informado, substitui o login/senha.</p>
            </div>
          </div>

          <div class="mt-6 flex justify-end">
            <button @click="saveConfiguration" class="btn-primary">Salvar Monitoramento</button>
          </div>
        </div>

        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 class="text-lg font-bold">Servidores Integrados</h2>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Cadastre múltiplos servidores (SNMP, Zabbix, Prometheus, etc).</p>
          </div>
          <button @click="openServerModal()" class="btn-primary flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" /></svg>
            Adicionar Servidor
          </button>
        </div>

        <div class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <div v-for="server in servers" :key="server.id" class="bg-white dark:bg-gray-800 p-5 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 relative group hover:shadow-md transition-shadow">
            <div class="flex justify-between items-start mb-4">
              <div class="flex items-center gap-3">
                <div class="p-2 rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400 font-bold text-xs uppercase border border-indigo-100 dark:border-indigo-800">
                  {{ server.server_type }}
                </div>
              </div>
              <span class="flex h-3 w-3 relative">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" v-if="server.is_active"></span>
                <span class="relative inline-flex rounded-full h-3 w-3" :class="server.is_active ? 'bg-green-500' : 'bg-gray-300'"></span>
              </span>
            </div>

            <h3 class="font-bold text-gray-900 dark:text-white truncate">{{ server.name }}</h3>
            <p class="text-xs text-gray-500 truncate mt-1 font-mono bg-gray-50 dark:bg-gray-900/50 p-1 rounded">{{ server.url }}</p>

            <div class="mt-5 flex justify-end gap-3 border-t border-gray-100 dark:border-gray-700 pt-3">
              <button @click="openServerModal(server)" class="text-xs font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition-colors">Editar</button>
              <button @click="deleteServer(server.id)" class="text-xs font-medium text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300 transition-colors">Remover</button>
            </div>
          </div>

          <div v-if="servers.length === 0" class="col-span-full text-center py-12 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl bg-gray-50/50 dark:bg-gray-800/30">
            <p class="text-gray-500 dark:text-gray-400">Nenhum servidor de monitoramento configurado.</p>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'maps'" class="space-y-6">
        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 max-w-3xl">
          <h2 class="text-lg font-semibold mb-6">Configuração de Mapas</h2>

          <div class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="label-custom">Provedor de Mapa</label>
                <select v-model="configForm.MAP_PROVIDER" class="app-input input-custom">
                  <option value="google">Google Maps Platform</option>
                  <option value="mapbox">Mapbox GL</option>
                  <option value="osm">OpenStreetMap (Leaflet)</option>
                </select>
                <p class="input-helper">Escolha o serviço base para renderização.</p>
              </div>
            </div>

            <div v-if="configForm.MAP_PROVIDER === 'google'" class="animate-fade-in">
              <label class="label-custom">Google Maps API Key</label>
              <input v-model="configForm.GOOGLE_MAPS_API_KEY" type="password" class="app-input input-custom" placeholder="Cole sua chave API aqui...">
              <div class="input-helper flex items-center gap-1">
                <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                APIs necessárias: Maps JavaScript API, Places API, Geocoding API.
              </div>
            </div>

            <div v-if="configForm.MAP_PROVIDER === 'mapbox'" class="animate-fade-in">
              <label class="label-custom">Mapbox Access Token</label>
              <input v-model="configForm.MAPBOX_TOKEN" type="password" class="app-input input-custom" placeholder="pk.eyJ...">
            </div>
          </div>

          <div class="mt-8 flex justify-end">
            <button @click="saveConfiguration" class="btn-primary">Salvar Mapas</button>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'system'" class="space-y-6">
        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 class="text-lg font-semibold mb-4">Django / Core</h3>
          <div class="grid gap-4 md:grid-cols-2">
            <div class="md:col-span-2">
              <label class="label-custom">SECRET_KEY</label>
              <input v-model="configForm.SECRET_KEY" type="text" class="app-input input-custom font-mono">
            </div>
            <div class="md:col-span-2">
              <label class="label-custom">ALLOWED_HOSTS</label>
              <input v-model="configForm.ALLOWED_HOSTS" type="text" class="app-input input-custom" placeholder="localhost,127.0.0.1">
            </div>
            <div class="flex items-center gap-3">
              <input id="debug-toggle" v-model="configForm.DEBUG" type="checkbox" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded">
              <label for="debug-toggle" class="text-sm font-medium">DEBUG</label>
            </div>
            <div class="flex items-center gap-3">
              <input id="diag-toggle" v-model="configForm.ENABLE_DIAGNOSTIC_ENDPOINTS" type="checkbox" class="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded">
              <label for="diag-toggle" class="text-sm font-medium">ENABLE_DIAGNOSTIC_ENDPOINTS</label>
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 class="text-lg font-semibold">Banco de Dados</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">PostgreSQL / PostGIS</p>
            </div>
            <button @click="testDatabase" class="btn-secondary text-xs">Testar conexão</button>
          </div>
          <div class="mt-6 grid gap-4 md:grid-cols-2">
            <div>
              <label class="label-custom">DB_HOST</label>
              <input v-model="configForm.DB_HOST" type="text" class="app-input input-custom">
            </div>
            <div>
              <label class="label-custom">DB_PORT</label>
              <input v-model="configForm.DB_PORT" type="text" class="app-input input-custom">
            </div>
            <div>
              <label class="label-custom">DB_NAME</label>
              <input v-model="configForm.DB_NAME" type="text" class="app-input input-custom">
            </div>
            <div>
              <label class="label-custom">DB_USER</label>
              <input v-model="configForm.DB_USER" type="text" class="app-input input-custom">
            </div>
            <div class="md:col-span-2">
              <label class="label-custom">DB_PASSWORD</label>
              <input v-model="configForm.DB_PASSWORD" type="password" class="app-input input-custom">
            </div>
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 class="text-lg font-semibold">Redis</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Cache e filas</p>
            </div>
            <button @click="testRedis" class="btn-secondary text-xs">Testar conexão</button>
          </div>
          <div class="mt-6">
            <label class="label-custom">REDIS_URL</label>
            <input v-model="configForm.REDIS_URL" type="text" class="app-input input-custom" placeholder="redis://redis:6379/0">
          </div>
        </div>

        <div class="bg-white dark:bg-gray-800 p-6 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700">
          <label class="label-custom">SERVICE_RESTART_COMMANDS</label>
          <textarea v-model="configForm.SERVICE_RESTART_COMMANDS" class="app-input input-custom font-mono h-24"></textarea>
          <p class="input-helper">Comandos executados após salvar configuração.</p>
        </div>

        <div class="flex justify-end">
          <button @click="saveConfiguration" class="btn-primary">Salvar Sistema</button>
        </div>

        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 flex-1 flex flex-col overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 class="font-bold text-gray-800 dark:text-white">Editor de Ambiente (.env)</h3>
              <p class="text-xs text-yellow-600 dark:text-yellow-400 mt-0.5">⚠ Alterações aqui exigem reinício do container.</p>
            </div>
            <button @click="saveEnv" class="btn-primary text-xs py-1.5">Salvar Arquivo</button>
          </div>
          <div class="flex-1 relative bg-[#1e1e1e] min-h-[320px]">
            <textarea
              v-model="envContent"
              class="absolute inset-0 w-full h-full p-4 bg-transparent text-gray-200 font-mono text-sm resize-none focus:outline-none leading-relaxed"
              spellcheck="false"
            ></textarea>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'backups'" class="space-y-6">
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-6">
          <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
            <div>
              <h2 class="text-lg font-bold text-gray-900 dark:text-white">Snapshots do Banco de Dados</h2>
              <p class="text-sm text-gray-500 dark:text-gray-400">Gerencie backups manuais e automáticos do PostGIS.</p>
            </div>

            <div class="flex flex-wrap gap-3 w-full md:w-auto">
              <button
                @click="createBackup"
                :disabled="backupLoading"
                class="btn-primary flex-1 md:flex-none justify-center whitespace-nowrap"
              >
                <svg v-if="backupLoading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                {{ backupLoading ? 'Gerando...' : 'Criar Novo Backup' }}
              </button>

              <label class="btn-secondary flex-1 md:flex-none justify-center whitespace-nowrap cursor-pointer">
                <input type="file" class="hidden" @change="handleUploadBackup" accept=".dump,.sql,.json">
                <span>Upload Externo</span>
              </label>
            </div>
          </div>

          <div class="grid gap-4 md:grid-cols-2 mb-6">
            <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <label class="label-custom">Retenção (dias)</label>
              <input v-model="backupSettings.retention_days" type="number" class="app-input input-custom">
            </div>
            <div class="rounded-lg border border-gray-200 dark:border-gray-700 p-4">
              <label class="label-custom">Retenção (quantidade)</label>
              <input v-model="backupSettings.retention_count" type="number" class="app-input input-custom">
            </div>
            <div class="md:col-span-2 flex justify-end">
              <button @click="saveBackupSettings" class="btn-secondary">Salvar retenção</button>
            </div>
          </div>

          <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
            <table class="w-full text-sm text-left">
              <thead class="bg-gray-50 dark:bg-gray-700/50 text-gray-500 uppercase text-xs">
                <tr>
                  <th class="px-6 py-4 font-semibold">Arquivo</th>
                  <th class="px-6 py-4 font-semibold">Data Criação</th>
                  <th class="px-6 py-4 font-semibold">Tipo</th>
                  <th class="px-6 py-4 font-semibold">Tamanho</th>
                  <th class="px-6 py-4 font-semibold text-right">Ações</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-800">
                <tr v-for="file in backups" :key="file.name" class="hover:bg-gray-50 dark:hover:bg-gray-700/30 transition-colors">
                  <td class="px-6 py-4 font-mono text-gray-700 dark:text-gray-300 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd" /></svg>
                    {{ file.name }}
                  </td>
                  <td class="px-6 py-4 text-gray-500 dark:text-gray-400">{{ formatDate(file.created_at) }}</td>
                  <td class="px-6 py-4 text-gray-500 dark:text-gray-400">{{ file.type || '-' }}</td>
                  <td class="px-6 py-4 text-gray-500 dark:text-gray-400">{{ formatSize(file.size) }}</td>
                  <td class="px-6 py-4 text-right space-x-3">
                    <button @click="restoreBackup(file)" class="text-sm font-medium text-orange-600 hover:text-orange-800 dark:hover:text-orange-400 transition-colors">Restaurar</button>
                    <span class="text-gray-300 dark:text-gray-600">|</span>
                    <button @click="deleteBackup(file)" class="text-sm font-medium text-red-600 hover:text-red-800 dark:hover:text-red-400 transition-colors">Excluir</button>
                    <span class="text-gray-300 dark:text-gray-600">|</span>
                    <a :href="`/setup_app/api/backups/download/${file.name}/`" target="_blank" class="text-sm font-medium text-blue-600 hover:text-blue-800 dark:hover:text-blue-400 transition-colors">Baixar</a>
                  </td>
                </tr>
                <tr v-if="backups.length === 0">
                  <td colspan="5" class="px-6 py-8 text-center text-gray-400">Nenhum backup encontrado.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showServerModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="showServerModal = false"></div>
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-md border border-gray-200 dark:border-gray-700 overflow-hidden relative z-10 transform transition-all">
        <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
          <h3 class="text-lg font-bold">{{ editingServer ? 'Editar Servidor' : 'Novo Servidor' }}</h3>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="label-custom">Nome Identificador</label>
            <input v-model="serverForm.name" type="text" class="app-input input-custom" placeholder="Ex: Zabbix Core">
          </div>
          <div>
            <label class="label-custom">Tipo de Serviço</label>
            <select v-model="serverForm.server_type" class="app-input input-custom">
              <option value="zabbix">Zabbix</option>
              <option value="snmp">SNMP</option>
              <option value="prometheus">Prometheus</option>
              <option value="librenms">LibreNMS</option>
            </select>
          </div>
          <div>
            <label class="label-custom">URL de Acesso</label>
            <input v-model="serverForm.url" type="url" class="app-input input-custom" placeholder="http://192.168.1.100/zabbix">
          </div>
          <div>
            <label class="label-custom">Token de Autenticação / API Key</label>
            <input v-model="serverForm.auth_token" type="password" class="app-input input-custom">
          </div>
          <div>
            <label class="label-custom">Configuração Extra (JSON)</label>
            <textarea v-model="serverForm.extra_config_text" class="app-input input-custom font-mono h-24"></textarea>
          </div>
          <div class="pt-2">
            <label class="flex items-center space-x-2 cursor-pointer">
              <input v-model="serverForm.is_active" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4">
              <span class="text-sm font-medium text-gray-700 dark:text-gray-300">Servidor Ativo</span>
            </label>
          </div>
        </div>
        <div class="bg-gray-50 dark:bg-gray-700/30 px-6 py-4 flex justify-end gap-3">
          <button @click="showServerModal = false" class="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">Cancelar</button>
          <button @click="saveServer" class="btn-primary">Salvar Dados</button>
        </div>
      </div>
    </div>

    <div v-if="showHistory" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="closeHistory"></div>
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-3xl border border-gray-200 dark:border-gray-700 overflow-hidden relative z-10">
        <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 flex items-center justify-between">
          <h3 class="text-lg font-bold">Histórico de Alterações</h3>
          <button @click="closeHistory" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">✕</button>
        </div>
        <div class="p-6 max-h-[60vh] overflow-y-auto">
          <div v-if="auditEntries.length === 0" class="text-sm text-gray-500">Nenhum histórico encontrado.</div>
          <div v-else class="space-y-4">
            <div v-for="entry in auditEntries" :key="entry.id" class="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <div class="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                <span class="font-semibold text-gray-700 dark:text-gray-200">{{ entry.section }}</span>
                <span>{{ entry.action }}</span>
                <span>{{ formatDate(entry.timestamp) }}</span>
                <span>por {{ entry.user }}</span>
              </div>
              <p v-if="entry.new_value" class="mt-2 text-sm text-gray-600 dark:text-gray-300">{{ entry.new_value }}</p>
              <p v-if="entry.error_message" class="mt-2 text-sm text-red-500">{{ entry.error_message }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useToast } from 'vue-toastification';
import { useApi } from '@/composables/useApi';

const Icons = {
  Cog: { template: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>' },
  Server: { template: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" /></svg>' },
  Map: { template: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" /></svg>' },
  Terminal: { template: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>' },
  Database: { template: '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" /></svg>' },
};

const toast = useToast();
const api = useApi();
const activeTab = ref('general');
const showHistory = ref(false);
const auditEntries = ref([]);

const navItems = [
  { id: 'general', label: 'Geral & Operação', icon: Icons.Cog },
  { id: 'monitoring', label: 'Monitoramento', icon: Icons.Server },
  { id: 'maps', label: 'Mapas & API', icon: Icons.Map },
  { id: 'system', label: 'Sistema & Env', icon: Icons.Terminal },
  { id: 'backups', label: 'Dados & Backup', icon: Icons.Database },
];

const configForm = ref({
  SECRET_KEY: '',
  DEBUG: false,
  ZABBIX_API_URL: '',
  ZABBIX_API_USER: '',
  ZABBIX_API_PASSWORD: '',
  ZABBIX_API_KEY: '',
  GOOGLE_MAPS_API_KEY: '',
  MAP_PROVIDER: 'google',
  MAPBOX_TOKEN: '',
  ALLOWED_HOSTS: '',
  ENABLE_DIAGNOSTIC_ENDPOINTS: false,
  DB_HOST: '',
  DB_PORT: '',
  DB_NAME: '',
  DB_USER: '',
  DB_PASSWORD: '',
  REDIS_URL: '',
  SERVICE_RESTART_COMMANDS: '',
});

const servers = ref([]);
const showServerModal = ref(false);
const editingServer = ref(null);
const serverForm = ref({
  name: '',
  server_type: 'zabbix',
  url: '',
  auth_token: '',
  is_active: true,
  extra_config_text: '{}',
});

const envContent = ref('');

const backups = ref([]);
const backupLoading = ref(false);
const backupSettings = ref({
  retention_days: '',
  retention_count: '',
});

const fetchConfiguration = async () => {
  try {
    const res = await api.get('/setup_app/api/config/');
    if (res.success && res.configuration) {
      configForm.value = { ...configForm.value, ...res.configuration };
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao carregar configurações.');
  }
};

const saveConfiguration = async () => {
  try {
    await api.post('/setup_app/api/config/update/', configForm.value);
    toast.success('Configurações salvas!');
    fetchConfiguration();
  } catch (e) {
    toast.error(e.message || 'Erro ao salvar configurações.');
  }
};

const testZabbix = async () => {
  try {
    const payload = {
      zabbix_api_url: configForm.value.ZABBIX_API_URL,
      zabbix_api_user: configForm.value.ZABBIX_API_USER,
      zabbix_api_password: configForm.value.ZABBIX_API_PASSWORD,
      zabbix_api_key: configForm.value.ZABBIX_API_KEY,
      auth_type: configForm.value.ZABBIX_API_KEY ? 'token' : 'login',
    };
    const res = await api.post('/setup_app/api/test-zabbix/', payload);
    if (res.success) {
      toast.success(res.message || 'Conexão OK');
    } else {
      toast.error(res.message || 'Falha ao testar');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao testar Zabbix.');
  }
};

const testDatabase = async () => {
  try {
    const payload = {
      db_host: configForm.value.DB_HOST,
      db_port: configForm.value.DB_PORT,
      db_name: configForm.value.DB_NAME,
      db_user: configForm.value.DB_USER,
      db_password: configForm.value.DB_PASSWORD,
    };
    const res = await api.post('/setup_app/api/test-database/', payload);
    if (res.success) {
      toast.success(res.message || 'Banco OK');
    } else {
      toast.error(res.message || 'Falha ao testar');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao testar banco.');
  }
};

const testRedis = async () => {
  try {
    const payload = { redis_url: configForm.value.REDIS_URL };
    const res = await api.post('/setup_app/api/test-redis/', payload);
    if (res.success) {
      toast.success(res.message || 'Redis OK');
    } else {
      toast.error(res.message || 'Falha ao testar');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao testar Redis.');
  }
};

const fetchServers = async () => {
  try {
    const res = await api.get('/setup_app/api/monitoring-servers/');
    servers.value = res.servers || [];
  } catch (e) {
    toast.error(e.message || 'Erro ao carregar servidores.');
  }
};

const openServerModal = (server = null) => {
  if (server) {
    editingServer.value = server;
    serverForm.value = {
      name: server.name || '',
      server_type: server.server_type || 'zabbix',
      url: server.url || '',
      auth_token: '',
      is_active: !!server.is_active,
      extra_config_text: JSON.stringify(server.extra_config || {}, null, 2),
    };
  } else {
    editingServer.value = null;
    serverForm.value = {
      name: '',
      server_type: 'zabbix',
      url: '',
      auth_token: '',
      is_active: true,
      extra_config_text: '{}',
    };
  }
  showServerModal.value = true;
};

const saveServer = async () => {
  let extraConfig = {};
  try {
    extraConfig = serverForm.value.extra_config_text
      ? JSON.parse(serverForm.value.extra_config_text)
      : {};
  } catch (e) {
    toast.error('JSON inválido em Configuração Extra.');
    return;
  }

  const payload = {
    name: serverForm.value.name,
    server_type: serverForm.value.server_type,
    url: serverForm.value.url,
    auth_token: serverForm.value.auth_token,
    is_active: serverForm.value.is_active,
    extra_config: extraConfig,
  };

  try {
    if (editingServer.value) {
      await api.patch(`/setup_app/api/monitoring-servers/${editingServer.value.id}/`, payload);
      toast.success('Servidor atualizado!');
    } else {
      await api.post('/setup_app/api/monitoring-servers/', payload);
      toast.success('Servidor adicionado!');
    }
    showServerModal.value = false;
    fetchServers();
  } catch (e) {
    toast.error(e.message || 'Erro ao salvar servidor.');
  }
};

const deleteServer = async (id) => {
  if (!confirm('Remover este servidor?')) return;
  try {
    await api.delete(`/setup_app/api/monitoring-servers/${id}/`);
    fetchServers();
  } catch (e) {
    toast.error(e.message || 'Erro ao remover servidor.');
  }
};

const fetchEnv = async () => {
  try {
    const res = await api.get('/setup_app/api/env/');
    if (res.success) {
      envContent.value = res.content || '';
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao carregar .env.');
  }
};

const saveEnv = async () => {
  try {
    await api.post('/setup_app/api/env/update/', { content: envContent.value });
    toast.success('Arquivo .env atualizado!');
  } catch (e) {
    toast.error(e.message || 'Erro ao salvar .env.');
  }
};

const fetchBackups = async () => {
  try {
    const res = await api.get('/setup_app/api/backups/');
    backups.value = res.backups || [];
    backupSettings.value = res.settings || backupSettings.value;
  } catch (e) {
    toast.error(e.message || 'Erro ao listar backups.');
  }
};

const createBackup = async () => {
  backupLoading.value = true;
  try {
    const res = await api.post('/setup_app/api/backups/', {});
    if (res.success) {
      toast.success(res.message || 'Backup iniciado!');
      setTimeout(fetchBackups, 2000);
    } else {
      toast.error(res.message || 'Erro ao criar backup');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao criar backup');
  } finally {
    backupLoading.value = false;
  }
};

const restoreBackup = async (file) => {
  if (!confirm(`ATENÇÃO: Restaurar o backup ${file.name} substituirá todos os dados atuais. Continuar?`)) {
    return;
  }
  try {
    const res = await api.post('/setup_app/api/backups/restore/', { filename: file.name });
    if (res.success) {
      toast.success(res.message || 'Restauração iniciada.');
    } else {
      toast.error(res.message || 'Erro ao restaurar.');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao restaurar.');
  }
};

const deleteBackup = async (file) => {
  if (!confirm(`Excluir permanentemente ${file.name}?`)) return;
  try {
    const res = await api.post('/setup_app/api/backups/delete/', { filename: file.name });
    if (res.success) {
      toast.success(res.message || 'Backup removido.');
      fetchBackups();
    } else {
      toast.error(res.message || 'Erro ao excluir.');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao excluir.');
  }
};

const saveBackupSettings = async () => {
  try {
    const res = await api.post('/setup_app/api/backups/settings/', {
      retention_days: backupSettings.value.retention_days,
      retention_count: backupSettings.value.retention_count,
    });
    if (res.success) {
      toast.success(res.message || 'Retenção atualizada.');
      backupSettings.value = res.settings || backupSettings.value;
      fetchBackups();
    } else {
      toast.error(res.message || 'Erro ao salvar retenção.');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao salvar retenção.');
  }
};

const handleUploadBackup = async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await api.postFormData('/setup_app/api/backups/', formData);
    if (res.success) {
      toast.success(res.message || 'Upload concluído!');
      fetchBackups();
    } else {
      toast.error(res.message || 'Erro no upload.');
    }
  } catch (e) {
    toast.error(e.message || 'Erro no upload.');
  } finally {
    event.target.value = '';
  }
};

const exportConfig = () => {
  window.location.href = '/setup_app/api/export/';
};

const handleImportConfig = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('config_file', file);
  try {
    const res = await api.postFormData('/setup_app/api/import/', formData);
    if (res.success) {
      toast.success(res.message || 'Configuração importada!');
      fetchConfiguration();
    } else {
      toast.error(res.message || 'Erro ao importar.');
    }
  } catch (e) {
    toast.error(e.message || 'Erro ao importar.');
  } finally {
    event.target.value = '';
  }
};

const openHistory = async () => {
  try {
    const res = await api.get('/setup_app/api/audit-history/?limit=100');
    auditEntries.value = res.audits || [];
    showHistory.value = true;
  } catch (e) {
    toast.error(e.message || 'Erro ao carregar histórico.');
  }
};

const closeHistory = () => {
  showHistory.value = false;
};

const formatSize = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (isoString) => {
  if (!isoString) return '-';
  return new Date(isoString).toLocaleString('pt-BR');
};

onMounted(() => {
  fetchConfiguration();
  fetchServers();
  fetchEnv();
  fetchBackups();
});
</script>

<style scoped>
/* --- INPUTS & LABELS --- */
.label-custom {
  @apply text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider ml-1;
  display: block;
  margin-bottom: 0.5rem;
}

.input-custom {
  @apply w-full p-2.5 transition-all duration-200 ease-in-out;
  display: block;
}

.input-custom:focus {
  @apply outline-none;
}

select.input-custom {
  @apply pr-10 appearance-none;
}

.input-helper {
  @apply text-xs text-gray-500 dark:text-gray-400;
  margin-top: 0.5rem;
}

/* --- BOTÕES --- */
.btn-primary {
  @apply inline-flex items-center justify-center px-4 py-2.5
  bg-primary-600 hover:bg-primary-700 text-white
  rounded-lg text-sm font-medium transition-all duration-200
  shadow-sm hover:shadow-md focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500
  disabled:opacity-60 disabled:cursor-not-allowed;
}

.btn-secondary {
  @apply inline-flex items-center justify-center px-4 py-2.5
  bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600
  hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200
  rounded-lg text-sm font-medium transition-all duration-200
  shadow-sm hover:shadow focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500;
}

/* --- ANIMAÇÕES --- */
.animate-fade-in {
  animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* --- SCROLLBARS PERSONALIZADAS --- */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  @apply bg-gray-300 dark:bg-gray-600 rounded-full border-[2px] border-transparent bg-clip-content;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-400 dark:bg-gray-500;
}

textarea.font-mono {
  font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
  line-height: 1.6;
}

table {
  @apply w-full border-collapse;
}
</style>
