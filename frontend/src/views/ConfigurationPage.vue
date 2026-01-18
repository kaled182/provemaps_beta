<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100 flex flex-col h-[calc(100vh-64px)] overflow-hidden transition-colors duration-300">
    
    <div class="flex-none px-6 py-5 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
          <svg class="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>
          Configurações
        </h1>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Gestão centralizada de serviços e dados.</p>
      </div>
      
      <div class="flex items-center gap-2">
        <button @click="exportConfig" class="btn-white text-xs">
          <svg class="w-4 h-4 mr-1.5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
          Exportar JSON
        </button>
        <label class="btn-white text-xs cursor-pointer">
          <input type="file" class="hidden" @change="handleImportConfig" accept=".json" autocomplete="off">
          <svg class="w-4 h-4 mr-1.5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
          Importar
        </label>
        <button @click="openHistory" class="btn-white text-xs" title="Histórico de Auditoria">
          <svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
        </button>
      </div>
    </div>

    <div class="flex-none border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 px-6">
      <nav class="-mb-px flex space-x-6 overflow-x-auto custom-scrollbar" aria-label="Tabs">
        <button 
          v-for="item in navItems" 
          :key="item.id"
          @click="activeTab = item.id"
          class="group inline-flex items-center py-4 px-1 border-b-2 font-medium text-sm transition-all whitespace-nowrap"
          :class="activeTab === item.id 
            ? 'border-primary-500 text-primary-600 dark:text-primary-400' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'"
        >
          <component 
            :is="item.icon" 
            class="mr-2 h-5 w-5 transition-colors"
            :class="activeTab === item.id ? 'text-primary-500 dark:text-primary-400' : 'text-gray-400 group-hover:text-gray-500'"
          />
          {{ item.label }}
        </button>
      </nav>
    </div>

    <div class="flex-1 overflow-y-auto custom-scrollbar p-6 bg-gray-50 dark:bg-gray-900">
      <div class="max-w-6xl mx-auto space-y-6 animate-fade-in">

        <div v-if="activeTab === 'system'" class="space-y-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div class="px-6 py-5 border-b border-gray-100 dark:border-gray-700">
              <h3 class="text-base font-bold text-gray-900 dark:text-white">Serviços do Sistema</h3>
              <p class="text-xs text-gray-500">Monitoramento, mapas e backups no mesmo painel.</p>
            </div>

            <div class="divide-y divide-gray-100 dark:divide-gray-700">
              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleSystemSection('systemParams')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-slate-500/10 text-slate-300">
                      <i class="fas fa-sliders-h"></i>
                    </span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">Parâmetros do Sistema</p>
                      <p class="text-xs text-gray-500">Redis, banco de dados e debug</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">1</span>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedSystemSections.systemParams ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedSystemSections.systemParams" class="px-6 pb-6">
                  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 max-w-5xl">
                    <h3 class="text-base font-bold mb-4 text-gray-900 dark:text-white">Parâmetros do Sistema</h3>
                    <form class="space-y-6" autocomplete="off" @submit.prevent>
                      <div class="grid gap-4 md:grid-cols-2">
                        <div>
                          <label class="label-custom">Allowed Hosts</label>
                          <input v-model="configForm.ALLOWED_HOSTS" type="text" class="input-custom font-mono" placeholder="localhost, 127.0.0.1" autocomplete="off">
                        </div>
                        <div>
                          <div class="flex items-center justify-between">
                            <label class="label-custom mb-0">Redis Connection URL</label>
                            <button type="button" @click="testRedis" class="btn-white text-xs h-8">
                              <svg class="w-3.5 h-3.5 mr-1.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                              Testar Conexão
                            </button>
                          </div>
                          <input v-model="configForm.REDIS_URL" type="text" class="input-custom font-mono" autocomplete="off">
                        </div>
                      </div>

                      <div class="pt-2">
                        <label class="flex items-center gap-2 cursor-pointer p-3 border border-gray-200 dark:border-gray-700 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors">
                          <input v-model="configForm.DEBUG" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
                          <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Modo Debug (Verbose Logs)</span>
                        </label>
                      </div>

                      <div class="pt-2 border-t border-gray-100 dark:border-gray-700">
                        <div class="flex items-center justify-between mt-4">
                          <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">Banco de Dados</h4>
                          <button type="button" @click="testDatabase" class="btn-white text-xs h-8">
                            <svg class="w-3.5 h-3.5 mr-1.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            Testar Conexão
                          </button>
                        </div>
                        <div class="grid gap-4 md:grid-cols-2 mt-3">
                          <div>
                            <label class="label-custom">Host</label>
                          <input v-model="configForm.DB_HOST" type="text" class="input-custom font-mono" autocomplete="off">
                          </div>
                          <div>
                            <label class="label-custom">Porta</label>
                            <input v-model="configForm.DB_PORT" type="text" class="input-custom font-mono" autocomplete="off">
                          </div>
                          <div>
                            <label class="label-custom">Nome do Banco</label>
                            <input v-model="configForm.DB_NAME" type="text" class="input-custom font-mono" autocomplete="off">
                          </div>
                          <div>
                            <label class="label-custom">Usuário</label>
                            <input v-model="configForm.DB_USER" type="text" class="input-custom font-mono" autocomplete="username">
                          </div>
                          <div class="md:col-span-2">
                            <label class="label-custom">Senha</label>
                            <input v-model="configForm.DB_PASSWORD" type="password" class="input-custom font-mono" autocomplete="current-password">
                          </div>
                        </div>
                      </div>

                    </form>
                    <div class="mt-6 flex justify-end">
                      <button @click="saveConfiguration" class="btn-primary">
                        <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                        Atualizar
                      </button>
                    </div>
                  </div>
                </div>
              </div>
              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleSystemSection('monitoring')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">
                      <i class="fas fa-server"></i>
                    </span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">Monitoramento</p>
                      <p class="text-xs text-gray-500">Integração e servidores adicionais</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">{{ monitoringServerCount }}</span>
                    <button
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md shadow-sm text-xs app-btn-primary"
                      @click.stop="openServerModal()"
                      aria-label="Adicionar servidor"
                    >
                      <i class="fas fa-plus"></i>
                    </button>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedSystemSections.monitoring ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedSystemSections.monitoring" class="px-6 pb-6">
                  <div class="space-y-6">
                    <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
                      <div class="px-6 py-5 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
                        <div>
                          <h3 class="text-base font-bold text-gray-900 dark:text-white">Integração Zabbix Principal</h3>
                          <p class="text-xs text-gray-500">Conexão padrão para coleta de status da rede.</p>
                        </div>
                        <button @click="testZabbix" class="btn-white text-xs h-8">
                          <svg class="w-3.5 h-3.5 mr-1.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                          Testar Conexão
                        </button>
                      </div>
                      
                      <form class="p-6 grid gap-6 md:grid-cols-2" autocomplete="off" @submit.prevent>
                        <div class="md:col-span-2">
                          <label class="label-custom" for="zabbix-url">URL da API</label>
                          <div class="relative">
                            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                              <span class="text-gray-400 sm:text-sm">https://</span>
                            </div>
                            <input id="zabbix-url" v-model="configForm.ZABBIX_API_URL" type="url" class="input-custom input-custom--prefixed" placeholder="zabbix.seu-dominio.com/api_jsonrpc.php" autocomplete="url">
                          </div>
                        </div>
                        <div>
                          <label class="label-custom" for="zabbix-user">Usuário</label>
                          <input id="zabbix-user" v-model="configForm.ZABBIX_API_USER" type="text" class="input-custom" autocomplete="username">
                        </div>
                        <div>
                          <label class="label-custom" for="zabbix-password">Senha</label>
                          <input id="zabbix-password" v-model="configForm.ZABBIX_API_PASSWORD" type="password" class="input-custom" autocomplete="current-password">
                        </div>
                        <div class="md:col-span-2 pt-2">
                          <div class="flex items-center justify-between">
                            <label class="label-custom mb-0" for="zabbix-token">API Token (Opcional)</label>
                            <span class="text-xs text-gray-400">Substitui login/senha se preenchido</span>
                          </div>
                          <input id="zabbix-token" v-model="configForm.ZABBIX_API_KEY" type="password" class="input-custom mt-1" placeholder="Token de Autenticação" autocomplete="off">
                        </div>
                      </form>

                      <div class="px-6 py-4 bg-gray-50 dark:bg-gray-800/50 border-t border-gray-100 dark:border-gray-700 flex justify-end">
                        <button @click="saveConfiguration" class="btn-primary">
                          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/></svg>
                          Salvar Alterações
                        </button>
                      </div>
                    </div>

                    <div>
                      <div class="flex justify-between items-end mb-4">
                        <div>
                          <h3 class="text-lg font-bold text-gray-900 dark:text-white">Servidores Adicionais</h3>
                          <p class="text-sm text-gray-500">Collectors para outras regiões ou tecnologias.</p>
                        </div>
                        <button @click="openServerModal()" class="btn-primary py-2 text-xs">
                          <svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                          Novo Servidor
                        </button>
                      </div>

                      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                        <div v-for="server in servers" :key="server.id" class="group bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 hover:shadow-md transition-all">
                          <div class="flex justify-between items-start mb-3">
                            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wide bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300">
                              {{ server.server_type }}
                            </span>
                            <div class="flex items-center gap-2">
                              <span class="flex h-2.5 w-2.5 relative">
                                <span v-if="server.is_active" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                                <span class="relative inline-flex rounded-full h-2.5 w-2.5" :class="server.is_active ? 'bg-green-500' : 'bg-red-500'"></span>
                              </span>
                            </div>
                          </div>
                          <h4 class="font-bold text-gray-900 dark:text-white truncate">{{ server.name }}</h4>
                          <p class="text-xs text-gray-500 font-mono mt-1 truncate bg-gray-50 dark:bg-gray-900/50 p-1 rounded">{{ server.url }}</p>
                          
                          <div class="mt-4 pt-3 border-t border-gray-100 dark:border-gray-700 flex justify-end gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                            <button @click="openServerModal(server)" class="p-1 text-gray-400 hover:text-blue-600 rounded transition-colors" title="Editar">
                              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
                            </button>
                            <button @click="deleteServer(server.id)" class="p-1 text-gray-400 hover:text-red-600 rounded transition-colors" title="Excluir">
                              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                            </button>
                          </div>
                        </div>
                        
                        <div v-if="servers.length === 0" class="col-span-full py-8 border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-lg flex flex-col items-center justify-center text-gray-400">
                          <svg class="w-8 h-8 mb-2 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 00-2-2m-2-4h.01M17 16h.01"/></svg>
                          <span class="text-sm">Nenhum servidor configurado</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleSystemSection('maps')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">
                      <i class="fas fa-map"></i>
                    </span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">Mapas</p>
                      <p class="text-xs text-gray-500">Provedor e chave de API</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">1</span>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedSystemSections.maps ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedSystemSections.maps" class="px-6 pb-6">
                  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 max-w-4xl">
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-6">Provedor de Mapas</h3>
                    
                    <form class="space-y-6" autocomplete="off" @submit.prevent>
                      <div class="grid gap-6 md:grid-cols-2">
                        <div>
                          <label class="label-custom" for="map-provider">Serviço Ativo</label>
                          <div class="relative">
                            <select id="map-provider" v-model="configForm.MAP_PROVIDER" class="input-custom appearance-none">
                              <option value="google">Google Maps Platform</option>
                              <option value="mapbox">Mapbox GL</option>
                              <option value="osm">OpenStreetMap</option>
                            </select>
                            <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
                              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                            </div>
                          </div>
                          <p class="text-xs text-gray-500 mt-2">O provedor define a base visual e as ferramentas de geocodificação.</p>
                        </div>
                      </div>

                      <div class="pt-6 border-t border-gray-100 dark:border-gray-700">
                        <div v-if="configForm.MAP_PROVIDER === 'google'" class="animate-fade-in space-y-4">
                          <div>
                            <label class="label-custom" for="google-maps-key">Google Maps API Key</label>
                            <input id="google-maps-key" v-model="configForm.GOOGLE_MAPS_API_KEY" type="password" class="input-custom font-mono" placeholder="AIzaSy..." autocomplete="off">
                          </div>
                          <div class="flex items-start gap-2 text-xs text-gray-500 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-md border border-blue-100 dark:border-blue-800">
                            <svg class="w-4 h-4 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                            <span>Certifique-se de ativar: <strong>Maps JavaScript API</strong>, <strong>Places API</strong> e <strong>Geocoding API</strong> no console do Google Cloud.</span>
                          </div>
                        </div>

                        <div v-if="configForm.MAP_PROVIDER === 'mapbox'" class="animate-fade-in space-y-4">
                          <div>
                            <label class="label-custom" for="mapbox-token">Mapbox Access Token</label>
                            <input id="mapbox-token" v-model="configForm.MAPBOX_TOKEN" type="password" class="input-custom font-mono" placeholder="pk.eyJ..." autocomplete="off">
                          </div>
                        </div>
                      </div>

                      <div class="pt-2 flex justify-end">
                        <button @click="saveConfiguration" class="btn-primary">
                          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                          Salvar Configuração
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              </div>

              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleSystemSection('backups')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-purple-500/10 text-purple-400">
                      <i class="fas fa-database"></i>
                    </span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">Backups</p>
                      <p class="text-xs text-gray-500">Snapshots e envio para nuvem</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">{{ backups.length }}</span>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedSystemSections.backups ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedSystemSections.backups" class="px-6 pb-6">
                  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div class="p-6 border-b border-gray-200 dark:border-gray-700 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                      <div>
                        <h2 class="text-lg font-bold text-gray-900 dark:text-white">Snapshots do Banco</h2>
                        <p class="text-sm text-gray-500 dark:text-gray-400">Backups de segurança do PostGIS (Geoespacial).</p>
                      </div>
                      
                      <div class="flex flex-wrap gap-3">
                        <label class="btn-white cursor-pointer">
                          <input type="file" class="hidden" @change="handleUploadBackup" accept=".zip" autocomplete="off">
                          <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                          Upload Externo
                        </label>
                        <button @click="showBackupConfig = true" class="btn-white">
                          <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.983 5.25a2.25 2.25 0 013.182 0l3.585 3.585a2.25 2.25 0 010 3.182l-6.592 6.592a2.25 2.25 0 01-1.591.659H7.5A2.25 2.25 0 015.25 17.5v-2.067c0-.597.237-1.17.659-1.592l6.592-6.591z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7l8 8"/></svg>
                          Configurar Backup
                        </button>
                        <button @click="showCloudConfig = true" class="btn-white">
                          <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 15a4 4 0 004 4h9a4 4 0 000-8h-.5a5.5 5.5 0 10-10.9 1.5A4.5 4.5 0 003 15z"/></svg>
                          Configurar Nuvem
                        </button>
                        <button @click="createBackup" :disabled="backupLoading" class="btn-primary">
                          <svg v-if="backupLoading" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                          <svg v-else class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>
                          Novo Backup
                        </button>
                      </div>
                    </div>

                    <div class="bg-gray-50 dark:bg-gray-800/50 p-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row items-end gap-4">
                      <div class="w-full sm:w-32">
                        <label class="label-custom">Retenção (Dias)</label>
                        <input v-model="backupSettings.retention_days" type="number" class="input-custom mt-1" autocomplete="off">
                      </div>
                      <div class="w-full sm:w-32">
                        <label class="label-custom">Max Arquivos</label>
                        <input v-model="backupSettings.retention_count" type="number" class="input-custom mt-1" autocomplete="off">
                      </div>
                      <div>
                        <button @click="saveBackupSettings" class="btn-white h-[38px]">
                          <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
                          Salvar Regra
                        </button>
                      </div>
                    </div>

                    <div class="overflow-x-auto">
                      <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                        <thead class="bg-gray-50 dark:bg-gray-800">
                          <tr>
                            <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Arquivo</th>
                            <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Data</th>
                            <th scope="col" class="px-6 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Tamanho</th>
                            <th scope="col" class="px-6 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Ações</th>
                          </tr>
                        </thead>
                        <tbody class="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                          <tr v-for="file in backups" :key="file.name" class="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors group">
                            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white font-mono flex items-center gap-2">
                              <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/></svg>
                              {{ file.name }}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatDate(file.created_at) }}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatSize(file.size) }}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <div class="flex justify-end gap-3 opacity-60 group-hover:opacity-100 transition-opacity">
                                <button @click="uploadBackupToCloud(file)" class="text-emerald-500 hover:text-emerald-700 flex items-center gap-1" title="Enviar para nuvem">
                                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01.88-7.903A5 5 0 1115.9 6h.1a4 4 0 010 8H7z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 12v6m0 0l-3-3m3 3l3-3"/></svg>
                                </button>
                                <button @click="restoreBackup(file)" class="text-orange-600 hover:text-orange-800 flex items-center gap-1" title="Restaurar">
                                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                                </button>
                                <a :href="`/setup_app/api/backups/download/${file.name}/`" target="_blank" class="text-blue-600 hover:text-blue-800 flex items-center gap-1" title="Download">
                                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/></svg>
                                </a>
                                <button @click="deleteBackup(file)" class="text-red-600 hover:text-red-800 flex items-center gap-1" title="Excluir">
                                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                                </button>
                              </div>
                            </td>
                          </tr>
                          <tr v-if="backups.length === 0">
                            <td colspan="4" class="px-6 py-10 text-center text-sm text-gray-500 border-dashed">
                              Nenhum backup encontrado.
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'smtp'" class="space-y-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
            <div class="px-6 py-5 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
              <div>
                <h3 class="text-base font-bold text-gray-900 dark:text-white">Serviço de E-mail (SMTP)</h3>
                <p class="text-xs text-gray-500">Configuração de envio e validação do serviço.</p>
              </div>
              <button @click="testSmtp" class="btn-white text-xs h-8">
                <svg class="w-3.5 h-3.5 mr-1.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                Testar Envio
              </button>
            </div>

            <form class="p-6 grid gap-6 md:grid-cols-2" autocomplete="off" @submit.prevent>
              <div class="md:col-span-2 flex items-center justify-between">
                <label class="label-custom">Ativar SMTP</label>
                <input v-model="configForm.SMTP_ENABLED" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
              </div>
              <div>
                <label class="label-custom">Provedor</label>
                <select v-model="smtpProvider" class="input-custom" @change="applySmtpPreset">
                  <option value="gmail">Gmail</option>
                  <option value="custom">Servidor próprio</option>
                </select>
              </div>
              <div>
                <label class="label-custom">Autenticação</label>
                <select v-model="configForm.SMTP_AUTH_MODE" class="input-custom">
                  <option value="password">Senha</option>
                  <option value="oauth">OAuth (Google)</option>
                </select>
              </div>
              <div>
                <label class="label-custom">Segurança</label>
                <select v-model="configForm.SMTP_SECURITY" class="input-custom">
                  <option value="tls">TLS (587)</option>
                  <option value="ssl">SSL (465)</option>
                  <option value="none">Sem criptografia</option>
                </select>
              </div>
              <div>
                <label class="label-custom">Host</label>
                <input v-model="configForm.SMTP_HOST" type="text" class="input-custom font-mono" placeholder="smtp.gmail.com" autocomplete="url">
              </div>
              <div>
                <label class="label-custom">Porta</label>
                <input v-model="configForm.SMTP_PORT" type="text" class="input-custom font-mono" placeholder="587" autocomplete="off">
              </div>
              <div>
                <label class="label-custom">Usuário</label>
                <input v-model="configForm.SMTP_USER" type="text" class="input-custom font-mono" placeholder="usuario@dominio.com" autocomplete="username">
              </div>
              <div v-if="configForm.SMTP_AUTH_MODE === 'password'">
                <label class="label-custom">Senha</label>
                <input v-model="configForm.SMTP_PASSWORD" type="password" class="input-custom font-mono" autocomplete="current-password">
              </div>
              <div>
                <label class="label-custom">Remetente (Nome)</label>
                <input v-model="configForm.SMTP_FROM_NAME" type="text" class="input-custom" placeholder="ProveMaps" autocomplete="name">
              </div>
              <div>
                <label class="label-custom">Remetente (Email)</label>
                <input v-model="configForm.SMTP_FROM_EMAIL" type="email" class="input-custom font-mono" placeholder="noreply@dominio.com" autocomplete="email">
              </div>
              <div class="md:col-span-2">
                <label class="label-custom">Email de Teste</label>
                <input v-model="configForm.SMTP_TEST_RECIPIENT" type="email" class="input-custom font-mono" placeholder="paulo@simplesinternet.net.br" autocomplete="email">
                <p class="text-xs text-gray-400 mt-2">O botão “Testar Envio” enviará um email para este endereço.</p>
              </div>
              <div v-if="configForm.SMTP_AUTH_MODE === 'oauth'" class="md:col-span-2 space-y-4 border-t border-gray-700/40 pt-4">
                <div class="flex items-center justify-between">
                  <label class="label-custom">OAuth JSON (Google)</label>
                  <div class="flex items-center gap-2">
                    <input ref="smtpOauthFileInput" type="file" accept=".json" class="hidden" @change="handleSmtpOauthFileUpload" autocomplete="off">
                    <button @click="openSmtpOauthFilePicker" class="btn-white text-xs h-7">Importar JSON</button>
                    <button @click="applySmtpOauthJson" class="btn-white text-xs h-7">Aplicar JSON</button>
                  </div>
                </div>
                <textarea v-model="smtpOauthJson" class="input-custom font-mono h-28" placeholder="Cole aqui o JSON do OAuth (client_id / client_secret)."></textarea>
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Client ID</label>
                    <input v-model="configForm.SMTP_OAUTH_CLIENT_ID" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Client Secret</label>
                    <input v-model="configForm.SMTP_OAUTH_CLIENT_SECRET" type="password" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div class="md:col-span-2">
                    <label class="label-custom">Refresh Token</label>
                    <input v-model="configForm.SMTP_OAUTH_REFRESH_TOKEN" type="password" class="input-custom font-mono" autocomplete="off" placeholder="Informe o refresh_token do OAuth">
                    <p class="text-xs text-gray-400 mt-2">O JSON não traz o refresh_token; ele é gerado no fluxo OAuth.</p>
                  </div>
                </div>
              </div>
            </form>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-4 flex justify-end gap-3 border-t border-gray-100 dark:border-gray-700">
              <button @click="saveConfiguration" class="btn-primary">Salvar</button>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'gateways'" class="space-y-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div class="px-6 py-5 border-b border-gray-100 dark:border-gray-700">
              <h3 class="text-base font-bold text-gray-900 dark:text-white">Gateways de Mensageria</h3>
              <p class="text-xs text-gray-500">Organize por grupo e configure por gateway.</p>
            </div>

            <div class="divide-y divide-gray-100 dark:divide-gray-700">
              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleGatewayGroup('sms')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-400">SMS</span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">SMS</p>
                      <p class="text-xs text-gray-500">Gateways SMS configurados</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">{{ smsGatewayCount }}</span>
                    <button
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md shadow-sm text-xs app-btn-primary"
                      @click.stop="openGatewayModal('sms', true)"
                      aria-label="Adicionar gateway SMS"
                    >
                      <i class="fas fa-plus"></i>
                    </button>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedGateways.sms ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedGateways.sms" class="px-6 pb-4">
                  <div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div class="grid grid-cols-6 bg-gray-50 dark:bg-gray-800/60 text-xs text-gray-500 px-4 py-2">
                      <span>Status</span>
                      <span class="col-span-2">Gateway</span>
                      <span class="col-span-2">Configuração</span>
                      <span class="text-right">Ações</span>
                    </div>
                    <div v-if="smsGatewaysSorted.length === 0" class="px-4 py-6 text-sm text-gray-500">
                      Nenhum gateway configurado.
                    </div>
                    <div
                      v-for="gateway in smsGatewaysSorted"
                      :key="gateway.id"
                      class="grid grid-cols-6 items-center px-4 py-3 text-sm text-gray-200"
                    >
                      <span>
                        <span class="inline-flex h-2 w-2 rounded-full" :class="gateway.enabled ? 'bg-emerald-400' : 'bg-gray-500'"></span>
                      </span>
                      <div class="col-span-2">
                        <p class="font-semibold text-gray-100">{{ gateway.name }}</p>
                        <span class="inline-flex items-center mt-1 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300">
                          Prioridade {{ gateway.priority || 1 }}
                        </span>
                      </div>
                      <div class="col-span-2 text-xs text-gray-500">
                        <p>Provedor: {{ (gateway.provider || 'smsnet').toUpperCase() }}</p>
                        <p>Remetente: {{ gateway.config?.sender_id || '—' }}</p>
                      </div>
                      <div class="flex justify-end gap-2">
                        <button @click="openGatewayModal('sms', false, gateway)" class="btn-white text-xs h-8">Configurar</button>
                        <button @click="deleteGatewayRow(gateway)" class="inline-flex h-8 w-8 items-center justify-center rounded-md app-btn-danger text-xs" aria-label="Remover gateway SMS" title="Remover gateway">
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleGatewayGroup('whatsapp')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400">WA</span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">WhatsApp (Meta)</p>
                      <p class="text-xs text-gray-500">API oficial Meta Cloud</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">{{ whatsappGatewayCount }}</span>
                    <button
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md shadow-sm text-xs btn-secondary"
                      @click.stop="refreshWhatsappGatewayStatuses"
                      aria-label="Atualizar status do WhatsApp"
                      title="Atualizar status"
                    >
                      <i class="fas fa-sync"></i>
                    </button>
                    <button
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md shadow-sm text-xs app-btn-primary"
                      @click.stop="openGatewayModal('whatsapp', true)"
                      aria-label="Adicionar gateway WhatsApp"
                    >
                      <i class="fas fa-plus"></i>
                    </button>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedGateways.whatsapp ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedGateways.whatsapp" class="px-6 pb-4">
                  <div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div class="grid grid-cols-6 bg-gray-50 dark:bg-gray-800/60 text-xs text-gray-500 px-4 py-2">
                      <span>Status</span>
                      <span class="col-span-2">Gateway</span>
                      <span class="col-span-2">Configuração</span>
                      <span class="text-right">Ações</span>
                    </div>
                    <div v-if="whatsappGatewaysSorted.length === 0" class="px-4 py-6 text-sm text-gray-500">
                      Nenhum gateway configurado.
                    </div>
                    <div
                      v-for="gateway in whatsappGatewaysSorted"
                      :key="gateway.id"
                      class="grid grid-cols-6 items-center px-4 py-3 text-sm text-gray-200"
                    >
                      <span>
                        <span class="inline-flex items-center gap-2 text-xs text-gray-400">
                          <span class="inline-flex h-2 w-2 rounded-full" :class="getWhatsappGatewayStatusColor(gateway)"></span>
                          <span>{{ getWhatsappGatewayStatusLabel(gateway) }}</span>
                        </span>
                      </span>
                      <div class="col-span-2">
                        <p class="font-semibold text-gray-100">{{ gateway.name }}</p>
                        <span class="inline-flex items-center mt-1 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300">
                          Prioridade {{ gateway.priority || 1 }}
                        </span>
                      </div>
                      <div class="col-span-2 text-xs text-gray-500">
                        <p>Phone ID: {{ gateway.config?.phone_number_id || '—' }}</p>
                        <p>Business ID: {{ gateway.config?.business_account_id || '—' }}</p>
                      </div>
                      <div class="flex justify-end gap-2">
                        <button @click="openGatewayModal('whatsapp', false, gateway)" class="btn-white text-xs h-8">Configurar</button>
                        <button @click="deleteGatewayRow(gateway)" class="inline-flex h-8 w-8 items-center justify-center rounded-md app-btn-danger text-xs" aria-label="Remover gateway WhatsApp" title="Remover gateway">
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleGatewayGroup('telegram')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-400">TG</span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">Telegram</p>
                      <p class="text-xs text-gray-500">Bot Token + Chat ID</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">{{ telegramGatewayCount }}</span>
                    <button
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md shadow-sm text-xs app-btn-primary"
                      @click.stop="openGatewayModal('telegram', true)"
                      aria-label="Adicionar gateway Telegram"
                    >
                      <i class="fas fa-plus"></i>
                    </button>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedGateways.telegram ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedGateways.telegram" class="px-6 pb-4">
                  <div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div class="grid grid-cols-6 bg-gray-50 dark:bg-gray-800/60 text-xs text-gray-500 px-4 py-2">
                      <span>Status</span>
                      <span class="col-span-2">Gateway</span>
                      <span class="col-span-2">Configuração</span>
                      <span class="text-right">Ações</span>
                    </div>
                    <div v-if="telegramGatewaysSorted.length === 0" class="px-4 py-6 text-sm text-gray-500">
                      Nenhum gateway configurado.
                    </div>
                    <div
                      v-for="gateway in telegramGatewaysSorted"
                      :key="gateway.id"
                      class="grid grid-cols-6 items-center px-4 py-3 text-sm text-gray-200"
                    >
                      <span>
                        <span class="inline-flex h-2 w-2 rounded-full" :class="gateway.enabled ? 'bg-emerald-400' : 'bg-gray-500'"></span>
                      </span>
                      <div class="col-span-2">
                        <p class="font-semibold text-gray-100">{{ gateway.name }}</p>
                        <span class="inline-flex items-center mt-1 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300">
                          Prioridade {{ gateway.priority || 1 }}
                        </span>
                      </div>
                      <div class="col-span-2 text-xs text-gray-500">
                        <p>Chat ID: {{ gateway.config?.chat_id || '—' }}</p>
                        <p>Bot: {{ gateway.config?.bot_name || '—' }}</p>
                      </div>
                      <div class="flex justify-end gap-2">
                        <button @click="openGatewayModal('telegram', false, gateway)" class="btn-white text-xs h-8">Configurar</button>
                        <button @click="deleteGatewayRow(gateway)" class="inline-flex h-8 w-8 items-center justify-center rounded-md app-btn-danger text-xs" aria-label="Remover gateway Telegram" title="Remover gateway">
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleGatewayGroup('video')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-rose-500/10 text-rose-400">VID</span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">Vídeo</p>
                      <p class="text-xs text-gray-500">Transcodificação e pré-visualização HLS</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">{{ videoGatewayCount }}</span>
                    <button
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md shadow-sm text-xs app-btn-primary"
                      @click.stop="openGatewayModal('video', true)"
                      aria-label="Adicionar gateway de vídeo"
                    >
                      <i class="fas fa-plus"></i>
                    </button>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedGateways.video ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedGateways.video" class="px-6 pb-4">
                  <div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div class="grid grid-cols-6 bg-gray-50 dark:bg-gray-800/60 text-xs text-gray-500 px-4 py-2">
                      <span>Status</span>
                      <span class="col-span-2">Gateway</span>
                      <span class="col-span-2">Stream</span>
                      <span class="text-right">Ações</span>
                    </div>
                    <div v-if="videoGatewaysSorted.length === 0" class="px-4 py-6 text-sm text-gray-500">
                      Nenhum gateway configurado.
                    </div>
                    <div
                      v-for="gateway in videoGatewaysSorted"
                      :key="gateway.id"
                      class="grid grid-cols-6 items-center px-4 py-3 text-sm text-gray-200"
                    >
                      <span>
                        <span class="inline-flex items-center gap-1 text-[11px] text-gray-300">
                          <span class="inline-flex h-2 w-2 rounded-full" :class="getVideoGatewayStatusColor(gateway)"></span>
                          <span>{{ getVideoGatewayStatusLabel(gateway) }}</span>
                        </span>
                      </span>
                      <div class="col-span-2">
                        <p class="font-semibold text-gray-100">{{ gateway.name }}</p>
                        <span class="inline-flex items-center mt-1 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300">
                          Prioridade {{ gateway.priority || 1 }}
                        </span>
                      </div>
                      <div class="col-span-2 text-xs text-gray-500">
                        <p>Protocolo: {{ (gateway.config?.stream_type || 'rtmp').toUpperCase() }}</p>
                        <p class="truncate" :title="gateway.config?.stream_url || '—'">Origem: {{ gateway.config?.stream_url || '—' }}</p>
                      </div>
                      <div class="flex justify-end gap-2">
                        <button @click="openGatewayModal('video', false, gateway)" class="btn-white text-xs h-8">Configurar</button>
                        <button @click="deleteGatewayRow(gateway)" class="inline-flex h-8 w-8 items-center justify-center rounded-md app-btn-danger text-xs" aria-label="Remover gateway de vídeo" title="Remover gateway">
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <button class="w-full px-6 py-4 flex items-center justify-between" @click="toggleGatewayGroup('smtp')">
                  <div class="flex items-center gap-3">
                    <span class="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10 text-amber-400">SMTP</span>
                    <div class="text-left">
                      <p class="text-sm font-semibold text-gray-900 dark:text-white">SMTP</p>
                      <p class="text-xs text-gray-500">Gateways de e-mail</p>
                    </div>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-xs px-2 py-1 rounded-full bg-gray-500/10 text-gray-400">{{ smtpGatewayCount }}</span>
                    <button
                      class="inline-flex h-7 w-7 items-center justify-center rounded-md shadow-sm text-xs app-btn-primary"
                      @click.stop="openGatewayModal('smtp', true)"
                      aria-label="Adicionar gateway SMTP"
                    >
                      <i class="fas fa-plus"></i>
                    </button>
                    <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedGateways.smtp ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </div>
                </button>
                <div v-show="expandedGateways.smtp" class="px-6 pb-4">
                  <div class="rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                    <div class="grid grid-cols-6 bg-gray-50 dark:bg-gray-800/60 text-xs text-gray-500 px-4 py-2">
                      <span>Status</span>
                      <span class="col-span-2">Gateway</span>
                      <span class="col-span-2">Configuração</span>
                      <span class="text-right">Ações</span>
                    </div>
                    <div v-if="smtpGatewaysSorted.length === 0" class="px-4 py-6 text-sm text-gray-500">
                      Nenhum gateway configurado.
                    </div>
                    <div
                      v-for="gateway in smtpGatewaysSorted"
                      :key="gateway.id"
                      class="grid grid-cols-6 items-center px-4 py-3 text-sm text-gray-200"
                    >
                      <span>
                        <span class="inline-flex h-2 w-2 rounded-full" :class="gateway.enabled ? 'bg-emerald-400' : 'bg-gray-500'"></span>
                      </span>
                      <div class="col-span-2">
                        <p class="font-semibold text-gray-100">{{ gateway.name }}</p>
                        <span class="inline-flex items-center mt-1 text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300">
                          Prioridade {{ gateway.priority || 1 }}
                        </span>
                      </div>
                      <div class="col-span-2 text-xs text-gray-500">
                        <p>Host: {{ gateway.config?.host || '—' }}</p>
                        <p>Remetente: {{ gateway.config?.from_email || '—' }}</p>
                      </div>
                      <div class="flex justify-end gap-2">
                        <button @click="openGatewayModal('smtp', false, gateway)" class="btn-white text-xs h-8">Configurar</button>
                        <button @click="deleteGatewayRow(gateway)" class="inline-flex h-8 w-8 items-center justify-center rounded-md app-btn-danger text-xs" aria-label="Remover gateway SMTP" title="Remover gateway">
                          <i class="fas fa-trash"></i>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <div v-if="showServerModal" class="relative z-50" aria-labelledby="modal-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="showServerModal = false"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-gray-200 dark:border-gray-700 animate-fade-in">
            <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
              <h3 class="text-base font-bold leading-6 text-gray-900 dark:text-white" id="modal-title">{{ editingServer ? 'Editar Servidor' : 'Adicionar Servidor' }}</h3>
              <button @click="showServerModal = false" class="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <div class="p-6 space-y-4">
              <div>
                <label class="label-custom">Nome</label>
                <input v-model="serverForm.name" type="text" class="input-custom mt-1" placeholder="Ex: Zabbix Core" autocomplete="off">
              </div>
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="label-custom">Tipo</label>
                  <select v-model="serverForm.server_type" class="input-custom mt-1 appearance-none">
                    <option value="zabbix">Zabbix</option>
                    <option value="snmp">SNMP</option>
                    <option value="prometheus">Prometheus</option>
                  </select>
                </div>
                <div>
                  <label class="label-custom">Status</label>
                  <select v-model="serverForm.is_active" class="input-custom mt-1 appearance-none">
                    <option :value="true">Ativo</option>
                    <option :value="false">Inativo</option>
                  </select>
                </div>
              </div>
              <div>
                <label class="label-custom">URL</label>
                <input v-model="serverForm.url" type="url" class="input-custom mt-1" placeholder="http://10.0.0.1/api" autocomplete="url">
              </div>
              <div>
                <label class="label-custom">Token / Chave</label>
                <input v-model="serverForm.auth_token" type="password" class="input-custom mt-1" autocomplete="off">
              </div>
              <div>
                <label class="label-custom">Config Extra (JSON)</label>
                <textarea v-model="serverForm.extra_config_text" class="input-custom mt-1 font-mono h-24 text-xs"></textarea>
              </div>
            </div>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-4 flex justify-end gap-3 border-t border-gray-100 dark:border-gray-700">
              <button @click="showServerModal = false" class="btn-secondary">Cancelar</button>
              <button @click="saveServer" class="btn-primary">Salvar</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showHistory" class="relative z-50">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="closeHistory"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:w-full sm:max-w-2xl border border-gray-200 dark:border-gray-700 flex flex-col max-h-[80vh]">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
              <h3 class="text-lg font-bold text-gray-900 dark:text-white">Histórico de Auditoria</h3>
              <button @click="closeHistory" class="text-gray-400 hover:text-gray-500">✕</button>
            </div>
            <div class="flex-1 overflow-y-auto p-0 custom-scrollbar">
              <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                  <tr v-for="entry in auditEntries" :key="entry.id" class="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td class="whitespace-nowrap py-4 pl-6 pr-3 text-sm font-medium text-gray-900 dark:text-white">{{ entry.action }}</td>
                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{{ formatDate(entry.timestamp) }}</td>
                    <td class="whitespace-nowrap px-3 py-4 text-sm text-gray-500">{{ entry.user }}</td>
                  </tr>
                  <tr v-if="auditEntries.length === 0">
                    <td colspan="3" class="px-6 py-10 text-center text-sm text-gray-500">Nenhum registro.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showBackupConfig" class="relative z-50" aria-labelledby="backup-config-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="showBackupConfig = false"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-lg border border-gray-200 dark:border-gray-700 animate-fade-in">
            <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
              <h3 class="text-base font-bold leading-6 text-gray-900 dark:text-white" id="backup-config-title">Configuração de Backup</h3>
              <button @click="showBackupConfig = false" class="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form class="p-6 space-y-4" autocomplete="off" @submit.prevent>
              <input type="text" class="sr-only" autocomplete="username" tabindex="-1" aria-hidden="true">
              <div>
                <label class="label-custom" for="backup-password">Senha do Backup</label>
                <input id="backup-password" v-model="configForm.BACKUP_ZIP_PASSWORD" type="password" class="input-custom font-mono" autocomplete="new-password" placeholder="Defina uma senha para o arquivo .zip">
                <p class="text-xs text-gray-400 mt-2">Ao alterar a senha, um novo backup será gerado automaticamente.</p>
              </div>
              <div class="pt-2 border-t border-gray-100 dark:border-gray-700">
                <p class="text-xs text-gray-500">Em breve: integração com Google Drive, FTP e outros destinos.</p>
              </div>
            </form>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-4 flex justify-end gap-3 border-t border-gray-100 dark:border-gray-700">
              <button @click="showBackupConfig = false" class="btn-secondary">Cancelar</button>
              <button @click="saveConfiguration" class="btn-primary">Salvar</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showCloudConfig" class="relative z-50" aria-labelledby="cloud-config-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="showCloudConfig = false"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-2xl border border-gray-200 dark:border-gray-700 animate-fade-in">
            <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
              <h3 class="text-base font-bold leading-6 text-gray-900 dark:text-white" id="cloud-config-title">Configuração de Nuvem</h3>
              <button @click="showCloudConfig = false" class="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form class="p-6 space-y-6" autocomplete="off" @submit.prevent>
              <div>
                <div class="flex items-center justify-between">
                  <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">Google Drive</h4>
                  <div class="flex items-center gap-3">
                    <button
                      type="button"
                      class="inline-flex items-center justify-center w-6 h-6 rounded-full border border-gray-600/40 text-xs text-gray-400 hover:text-gray-200"
                      @click="showGdriveHelp = !showGdriveHelp"
                      aria-label="Ajuda"
                    >
                      ?
                    </button>
                    <button type="button" @click="testGdrive" class="btn-white text-xs h-8">
                      <svg class="w-3.5 h-3.5 mr-1.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                      Testar
                    </button>
                    <label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                      <input v-model="configForm.GDRIVE_ENABLED" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
                      Habilitar
                    </label>
                  </div>
                </div>
                <div v-if="showGdriveHelp" class="mt-3 rounded-lg border border-gray-600/40 bg-gray-900/30 p-4 text-xs text-gray-200 space-y-3">
                  <div>
                    <p class="font-semibold text-gray-100">Service Account (padrão)</p>
                    <p class="text-gray-300">Use quando tiver Shared Drive (Workspace) ou quando a pasta do Drive aceitar uploads pela Service Account.</p>
                    <p class="text-gray-400">Campos: ID da Pasta (opcional) e JSON da Service Account.</p>
                  </div>
                  <div>
                    <p class="font-semibold text-gray-100">Conta pessoal (OAuth)</p>
                    <p class="text-gray-300">Use para Drive pessoal. Precisa de Client ID/Secret e login do usuário.</p>
                    <p class="text-gray-400">Redirect URI: <span class="font-mono">/setup_app/api/gdrive/oauth/callback/</span></p>
                  </div>
                  <div>
                    <p class="font-semibold text-gray-100">Shared Drive</p>
                    <p class="text-gray-300">Só existe em contas Workspace. Use o <span class="font-mono">driveId</span> da URL <span class="font-mono">/drives/&lt;DRIVE_ID&gt;</span>.</p>
                    <p class="text-gray-400">Se o link for <span class="font-mono">/drive/folders/&lt;ID&gt;</span>, é Meu Drive.</p>
                  </div>
                </div>
                <div class="grid gap-4 mt-3">
                  <div>
                    <label class="label-custom">Modo de autenticação</label>
                    <select v-model="configForm.GDRIVE_AUTH_MODE" class="input-custom">
                      <option value="service_account">Service Account</option>
                      <option value="oauth">Conta pessoal (OAuth)</option>
                    </select>
                  </div>
                  <div>
                    <label class="label-custom">ID da Pasta</label>
                    <input v-model="configForm.GDRIVE_FOLDER_ID" type="text" class="input-custom font-mono" placeholder="Ex: 1AbcDEFghiJKLmnOP" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">ID do Shared Drive (opcional)</label>
                    <input v-model="configForm.GDRIVE_SHARED_DRIVE_ID" type="text" class="input-custom font-mono" placeholder="Ex: 0AAbcDEFghiJKLmnOP" autocomplete="off">
                    <p class="text-xs text-gray-400 mt-2">Informe o ID do Shared Drive para usar a cota do drive compartilhado.</p>
                  </div>
                  <div v-if="configForm.GDRIVE_AUTH_MODE === 'service_account'">
                    <div class="flex items-center justify-between">
                      <label class="label-custom">Service Account JSON</label>
                      <div class="flex items-center gap-3">
                        <button type="button" class="text-xs text-primary-600 hover:text-primary-500" @click="openGdriveFilePicker">
                          Importar JSON
                        </button>
                        <button
                          v-if="gdriveJsonLocked"
                          type="button"
                          class="text-xs text-gray-500 hover:text-gray-400"
                          @click="gdriveJsonLocked = false"
                        >
                          Editar
                        </button>
                        <input ref="gdriveFileInput" type="file" accept=".json,application/json" class="hidden" @change="handleGdriveFileUpload" autocomplete="off">
                      </div>
                    </div>
                    <textarea
                      v-model="configForm.GDRIVE_CREDENTIALS_JSON"
                      class="input-custom font-mono text-xs h-36"
                      :readonly="gdriveJsonLocked"
                      :class="gdriveJsonLocked ? 'cursor-not-allowed opacity-80' : ''"
                      placeholder='{"type":"service_account","project_id":"..."}'
                    ></textarea>
                    <p class="text-xs text-gray-400 mt-2">Importe o JSON original para evitar caracteres inválidos.</p>
                  </div>
                  <div v-else class="rounded-lg border border-dashed border-gray-600/40 p-4">
                    <div class="flex items-center justify-between">
                      <p class="text-sm text-gray-300">Conta pessoal (OAuth)</p>
                      <button type="button" class="btn-white text-xs h-8" @click="startGdriveOAuth">
                        Conectar Google
                      </button>
                    </div>
                    <div class="grid gap-4 mt-4 md:grid-cols-2">
                      <div>
                        <label class="label-custom">Client ID</label>
                        <input v-model="configForm.GDRIVE_OAUTH_CLIENT_ID" type="text" class="input-custom font-mono" placeholder="Seu Client ID" autocomplete="off">
                      </div>
                      <div>
                        <label class="label-custom">Client Secret</label>
                        <input v-model="configForm.GDRIVE_OAUTH_CLIENT_SECRET" type="password" class="input-custom font-mono" autocomplete="off">
                      </div>
                    </div>
                    <p class="text-xs text-gray-400 mt-3">
                      Status: <span class="text-emerald-400" v-if="configForm.GDRIVE_OAUTH_CONNECTED">Conectado</span>
                      <span class="text-amber-300" v-else>Não conectado</span>
                      <span v-if="configForm.GDRIVE_OAUTH_USER_EMAIL" class="text-gray-400">({{ configForm.GDRIVE_OAUTH_USER_EMAIL }})</span>
                    </p>
                  </div>
                </div>
              </div>

              <div class="pt-4 border-t border-gray-100 dark:border-gray-700">
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-3">
                    <button type="button" @click="showFtpConfig = !showFtpConfig" class="text-xs text-primary-600 hover:text-primary-500">
                      {{ showFtpConfig ? 'Ocultar' : 'Exibir' }}
                    </button>
                    <h4 class="text-sm font-semibold text-gray-700 dark:text-gray-200">FTP</h4>
                  </div>
                  <div class="flex items-center gap-3">
                    <button type="button" @click="testFtp" class="btn-white text-xs h-8">
                      <svg class="w-3.5 h-3.5 mr-1.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                      Testar
                    </button>
                    <span v-if="ftpTestStatus" class="text-xs" :class="ftpTestStatus === 'ok' ? 'text-emerald-400' : 'text-rose-400'">
                      {{ ftpTestStatus === 'ok' ? 'Conexão OK' : 'Falha na conexão' }}
                    </span>
                    <label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                      <input v-model="configForm.FTP_ENABLED" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
                      Habilitar
                    </label>
                  </div>
                </div>
                <div v-show="showFtpConfig" class="grid gap-4 md:grid-cols-2 mt-3">
                  <div>
                    <label class="label-custom">Host</label>
                    <input v-model="configForm.FTP_HOST" type="text" class="input-custom font-mono" placeholder="ftp.seudominio.com" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Porta</label>
                    <input v-model="configForm.FTP_PORT" type="text" class="input-custom font-mono" placeholder="21" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Usuário</label>
                    <input v-model="configForm.FTP_USER" type="text" class="input-custom font-mono" autocomplete="username">
                  </div>
                  <div>
                    <label class="label-custom">Senha</label>
                    <input v-model="configForm.FTP_PASSWORD" type="password" class="input-custom font-mono" autocomplete="current-password">
                  </div>
                  <div class="md:col-span-2">
                    <label class="label-custom">Caminho Remoto</label>
                    <input v-model="configForm.FTP_PATH" type="text" class="input-custom font-mono" placeholder="/backups/" autocomplete="off">
                  </div>
                </div>
                <p v-if="!showFtpConfig" class="text-xs text-gray-500 mt-2">Clique em "Exibir" para configurar FTP.</p>
              </div>
            </form>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-4 flex justify-end gap-3 border-t border-gray-100 dark:border-gray-700">
              <button @click="showCloudConfig = false" class="btn-secondary">Cancelar</button>
              <button @click="saveConfiguration" class="btn-primary">Salvar</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showGatewayModal" class="relative z-50" aria-labelledby="gateway-config-title" role="dialog" aria-modal="true">
      <div class="fixed inset-0 bg-gray-900/60 backdrop-blur-sm transition-opacity" @click="closeGatewayModal"></div>
      <div class="fixed inset-0 z-10 overflow-y-auto">
        <div class="flex min-h-full items-center justify-center p-4 text-center">
          <div class="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-2xl transition-all sm:my-8 sm:w-full sm:max-w-2xl border border-gray-200 dark:border-gray-700 animate-fade-in">
            <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
              <div>
                <h3 class="text-base font-bold leading-6 text-gray-900 dark:text-white" id="gateway-config-title">{{ gatewayModalTitle }}</h3>
                <p class="text-xs text-gray-500">{{ gatewayModalSubtitle }}</p>
              </div>
              <div class="flex items-center gap-3">
                <button v-if="activeGateway === 'sms'" @click="testSms" class="btn-white text-xs h-8">
                  <svg class="w-3.5 h-3.5 mr-1.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  Testar
                </button>
                <button v-if="activeGateway === 'smtp'" @click="testSmtpGateway" class="btn-white text-xs h-8">
                  <svg class="w-3.5 h-3.5 mr-1.5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                  Testar
                </button>
                <button @click="closeGatewayModal" class="text-gray-400 hover:text-gray-600">✕</button>
              </div>
            </div>
            <form class="p-6 space-y-6" autocomplete="off" @submit.prevent>
              <div v-if="activeGateway === 'sms'" class="grid gap-6 md:grid-cols-2">
                <div class="md:col-span-2 grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Nome do Gateway</label>
                    <input v-model="smsGatewayForm.name" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Prioridade</label>
                    <input v-model.number="smsGatewayForm.priority" type="number" min="1" class="input-custom font-mono" autocomplete="off">
                    <p class="text-xs text-gray-400 mt-2">1 = maior prioridade.</p>
                  </div>
                </div>
                <div>
                  <label class="label-custom">Provedor</label>
                  <select v-model="smsGatewayForm.provider" class="input-custom" @change="applySmsPreset">
                    <option value="smsnet">SMSNET</option>
                    <option value="zenvia">Zenvia</option>
                    <option value="totalvoice">TotalVoice</option>
                    <option value="aws_sns">AWS SNS</option>
                    <option value="infobip">Infobip</option>
                  </select>
                </div>
                <div>
                  <label class="label-custom">Remetente (ID)</label>
                  <input v-model="smsGatewayForm.config.sender_id" type="text" class="input-custom font-mono" placeholder="PROVEMAPS" autocomplete="off">
                </div>
                <div v-if="smsGatewayForm.provider !== 'smsnet'" class="md:col-span-2">
                  <p class="text-xs text-gray-400">Integrações Zenvia/TotalVoice/AWS/Infobip ficam disponíveis para configuração agora. Envio será habilitado na próxima etapa.</p>
                </div>

                <div v-if="smsGatewayForm.provider === 'smsnet'">
                  <label class="label-custom">Usuário</label>
                  <input v-model="smsGatewayForm.config.username" type="text" class="input-custom font-mono" autocomplete="username">
                </div>
                <div v-if="smsGatewayForm.provider === 'smsnet'">
                  <label class="label-custom">Senha</label>
                  <input v-model="smsGatewayForm.config.password" type="password" class="input-custom font-mono" autocomplete="current-password" placeholder="••••••">
                </div>
                <div v-if="smsGatewayForm.provider === 'smsnet'">
                  <label class="label-custom">Endpoint API</label>
                  <input v-model="smsGatewayForm.config.api_url" type="text" class="input-custom font-mono" placeholder="https://sistema.smsnet.com.br/sms/global" autocomplete="url">
                </div>

                <div v-if="smsGatewayForm.provider === 'zenvia' || smsGatewayForm.provider === 'totalvoice'">
                  <label class="label-custom">Token API</label>
                  <input v-model="smsGatewayForm.config.api_token" type="password" class="input-custom font-mono" autocomplete="off">
                </div>

                <div v-if="smsGatewayForm.provider === 'infobip'">
                  <label class="label-custom">Base URL</label>
                  <input v-model="smsGatewayForm.config.infobip_base_url" type="text" class="input-custom font-mono" placeholder="https://{subdominio}.api.infobip.com" autocomplete="url">
                </div>
                <div v-if="smsGatewayForm.provider === 'infobip'">
                  <label class="label-custom">API Token</label>
                  <input v-model="smsGatewayForm.config.api_token" type="password" class="input-custom font-mono" autocomplete="off">
                </div>

                <div v-if="smsGatewayForm.provider === 'aws_sns'">
                  <label class="label-custom">Região AWS</label>
                  <input v-model="smsGatewayForm.config.aws_region" type="text" class="input-custom font-mono" placeholder="sa-east-1" autocomplete="off">
                </div>
                <div v-if="smsGatewayForm.provider === 'aws_sns'">
                  <label class="label-custom">Access Key</label>
                  <input v-model="smsGatewayForm.config.aws_access_key_id" type="text" class="input-custom font-mono" autocomplete="off">
                </div>
                <div v-if="smsGatewayForm.provider === 'aws_sns'">
                  <label class="label-custom">Secret Key</label>
                  <input v-model="smsGatewayForm.config.aws_secret_access_key" type="password" class="input-custom font-mono" autocomplete="off" placeholder="••••••">
                </div>

                <div class="md:col-span-2">
                  <label class="label-custom">Telefone de Teste</label>
                  <input v-model="smsGatewayForm.config.test_recipient" type="text" class="input-custom font-mono" placeholder="55DDDNUMERO" autocomplete="tel">
                  <p v-if="smsPhoneError" class="text-xs text-red-400 mt-2">{{ smsPhoneError }}</p>
                </div>
                <div class="md:col-span-2">
                  <label class="label-custom">Mensagem de Teste</label>
                  <input v-model="smsGatewayForm.config.test_message" type="text" class="input-custom font-mono" autocomplete="off">
                  <p class="text-xs text-gray-400 mt-2">Para SMSNET use formato 55DDDNUMERO no destinatário.</p>
                </div>
              </div>

              <div v-if="activeGateway === 'whatsapp'" class="space-y-4">
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Nome do Gateway</label>
                    <input v-model="whatsappGatewayForm.name" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Prioridade</label>
                    <input v-model.number="whatsappGatewayForm.priority" type="number" min="1" class="input-custom font-mono" autocomplete="off">
                  </div>
                </div>
                <div>
                  <label class="label-custom">Modo de Autenticação</label>
                  <select v-model="whatsappGatewayForm.config.auth_mode" class="input-custom">
                    <option value="meta">Meta Cloud API</option>
                    <option value="qr">WhatsApp Web (QR Code)</option>
                  </select>
                  <p class="text-xs text-gray-400 mt-2">QR Code é indicado para quem não usa a API oficial.</p>
                </div>

                <div v-if="whatsappGatewayForm.config.auth_mode === 'meta'" class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Phone Number ID</label>
                    <input v-model="whatsappGatewayForm.config.phone_number_id" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Business Account ID</label>
                    <input v-model="whatsappGatewayForm.config.business_account_id" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div class="md:col-span-2">
                    <label class="label-custom">Access Token</label>
                    <input v-model="whatsappGatewayForm.config.access_token" type="password" class="input-custom font-mono" autocomplete="off" placeholder="••••••">
                  </div>
                  <div>
                    <label class="label-custom">App ID (opcional)</label>
                    <input v-model="whatsappGatewayForm.config.app_id" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Verify Token</label>
                    <input v-model="whatsappGatewayForm.config.verify_token" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div class="md:col-span-2">
                    <label class="label-custom">Webhook URL</label>
                    <input v-model="whatsappGatewayForm.config.webhook_url" type="text" class="input-custom font-mono" placeholder="https://seu-dominio.com/webhook/whatsapp" autocomplete="url">
                  </div>
                </div>

                <div v-else class="space-y-4">
                  <div class="grid gap-4 md:grid-cols-2">
                    <div class="md:col-span-2">
                      <label class="label-custom">URL do serviço QR</label>
                      <input v-model="whatsappGatewayForm.config.qr_service_url" type="text" class="input-custom font-mono" placeholder="http://whatsapp-qr:3000" autocomplete="url">
                      <p class="text-xs text-gray-400 mt-2">Opcional. Se vazio, usa a URL padrão do backend.</p>
                    </div>
                  </div>
                  <div class="rounded-lg border border-gray-700/60 bg-gray-900/40 p-4">
                  <div class="flex items-start gap-4">
                    <div class="h-28 w-28 rounded-md border border-gray-700/60 overflow-hidden bg-gray-800/70 flex items-center justify-center text-xs text-gray-400">
                      <img
                        v-if="whatsappGatewayForm.config.qr_image_url"
                        :src="whatsappGatewayForm.config.qr_image_url"
                        alt="QR Code WhatsApp"
                        class="h-full w-full object-cover"
                      >
                      <span v-else>QR Code</span>
                    </div>
                    <div class="text-sm text-gray-300">
                      <div class="flex items-center gap-2">
                        <p class="font-semibold text-gray-100">Conectar via QR Code</p>
                        <span
                          class="text-[10px] px-2 py-0.5 rounded-full border"
                          :class="whatsappQrStatusClass"
                        >
                          {{ whatsappQrStatusLabel }}
                        </span>
                      </div>
                      <p class="text-xs text-gray-400 mt-1">Clique em "Gerar QR" para iniciar a conexão.</p>
                      <div class="flex flex-wrap items-center gap-2 mt-3">
                        <button class="btn-white text-xs h-8" type="button" @click="generateWhatsappQr">Gerar QR</button>
                        <button class="btn-white text-xs h-8" type="button" @click="refreshWhatsappQr">Atualizar status</button>
                        <button class="btn-white text-xs h-8" type="button" @click="generateWhatsappQr">Atualizar QR</button>
                        <button class="btn-danger-outline text-xs h-8" type="button" @click="disconnectWhatsappQr">Desconectar</button>
                        <button class="btn-secondary text-xs h-8" type="button" @click="requestWhatsappQrReset">Resetar sessão</button>
                        <button class="btn-primary text-xs h-8" type="button" @click="testWhatsappMessage">Testar envio</button>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Telefone de Teste</label>
                    <input v-model="whatsappGatewayForm.config.test_recipient" type="text" class="input-custom font-mono" placeholder="55DDDNUMERO" autocomplete="tel">
                  </div>
                  <div class="md:col-span-2">
                    <label class="label-custom">Mensagem de Teste</label>
                    <input v-model="whatsappGatewayForm.config.test_message" type="text" class="input-custom font-mono" autocomplete="off" placeholder="Teste WhatsApp ProveMaps.">
                  </div>
                  <div class="md:col-span-2 flex justify-end">
                    <button class="btn-primary h-9" type="button" @click="testWhatsappMessage">Enviar teste</button>
                  </div>
                </div>
              </div>
            </div>

              <div v-if="activeGateway === 'video'" class="space-y-5">
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Nome do Gateway</label>
                    <input v-model="videoGatewayForm.name" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Prioridade</label>
                    <input v-model.number="videoGatewayForm.priority" type="number" min="1" class="input-custom font-mono" autocomplete="off">
                  </div>
                </div>

                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Protocolo de Entrada</label>
                    <select v-model="videoGatewayForm.config.stream_type" class="input-custom">
                      <option value="rtmp">RTMP</option>
                      <option value="rtsp">RTSP</option>
                      <option value="hls">HLS</option>
                    </select>
                    <p class="text-xs text-gray-400 mt-2">Selecione o protocolo utilizado pela câmera ou encoder.</p>
                  </div>
                  <div>
                    <label class="label-custom">Chave de Restream (opcional)</label>
                    <input v-model="videoGatewayForm.config.restream_key" type="text" class="input-custom font-mono" placeholder="gateway_{{ videoGatewayForm.id || 'novo' }}" autocomplete="off">
                    <p class="text-xs text-gray-400 mt-2">Se vazio, a chave é gerada automaticamente.</p>
                  </div>
                </div>

                <div>
                  <label class="label-custom">URL do Stream</label>
                  <input v-model="videoGatewayForm.config.stream_url" type="text" class="input-custom font-mono" placeholder="rtsp://camera.local/stream" autocomplete="off">
                  <p class="text-xs text-gray-400 mt-2">Use RTSP, RTMP ou HLS conforme selecionado acima.</p>
                </div>

                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Token de Reprodução (opcional)</label>
                    <input v-model="videoGatewayForm.config.playback_token" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Base pública HLS (opcional)</label>
                    <input v-model="videoGatewayForm.config.hls_public_base_url" type="text" class="input-custom font-mono" placeholder="https://videos.seudominio.com/hls" autocomplete="off">
                    <p class="text-xs text-gray-400 mt-2">Sobrescreve a URL padrão exposta pelo Docker.</p>
                  </div>
                </div>

                <div class="rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-900/40 p-4 space-y-4">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-sm font-semibold text-gray-200">Pré-visualização</p>
                      <p class="text-xs text-gray-400">Gera uma saída HLS temporária para validar a entrada.</p>
                    </div>
                    <div class="flex items-center gap-3 text-xs text-gray-400">
                      <span class="flex items-center gap-2">
                        <span
                          v-if="isVideoPreviewLoading"
                          class="inline-flex h-3 w-3 border border-gray-300 border-t-transparent rounded-full animate-spin"
                        ></span>
                        A pré-visualização inicia automaticamente.
                      </span>
                      <button
                        class="btn-secondary text-xs h-8"
                        type="button"
                        @click="stopVideoPreview()"
                        :disabled="!isVideoPreviewActive && !videoPreview.url"
                      >
                        Encerrar
                      </button>
                    </div>
                  </div>
                  <div class="relative h-52 bg-black rounded-md overflow-hidden flex items-center justify-center">
                    <video ref="videoPreviewElement" class="w-full h-full object-cover" controls playsinline muted></video>
                    <div
                      v-if="isVideoPreviewLoading"
                      class="absolute inset-0 bg-gray-900/70 flex items-center justify-center text-sm text-gray-200"
                    >
                      Carregando prévia...
                    </div>
                    <div
                      v-else-if="videoPreview.error"
                      class="absolute inset-0 bg-gray-900/70 flex items-center justify-center text-sm text-red-300 text-center px-4"
                    >
                      {{ videoPreview.error }}
                    </div>
                    <div
                      v-else-if="videoPreview.status === 'retrying'"
                      class="absolute inset-0 bg-gray-900/60 flex items-center justify-center text-xs text-gray-200 text-center px-4"
                    >
                      Tentando reconectar à transmissão...
                    </div>
                    <div
                      v-else-if="!videoPreview.url && !isVideoPreviewActive"
                      class="absolute inset-0 flex items-center justify-center text-xs text-gray-500 text-center px-4"
                    >
                      Preparando prévia automática...
                    </div>
                  </div>
                  <div class="flex items-center justify-between gap-4 text-[11px] text-gray-400">
                    <span v-if="previewUrlDisplay" class="truncate" :title="previewUrlDisplay">URL: {{ previewUrlDisplay }}</span>
                    <span v-else class="text-gray-500">URL ainda não gerada.</span>
                    <span
                      v-if="videoGatewayForm.config.preview_url && !videoPreview.url"
                      class="text-gray-500"
                    >Prévia anterior disponível.</span>
                  </div>
                </div>
              </div>

              <div v-if="activeGateway === 'telegram'" class="space-y-4">
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Nome do Gateway</label>
                    <input v-model="telegramGatewayForm.name" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Prioridade</label>
                    <input v-model.number="telegramGatewayForm.priority" type="number" min="1" class="input-custom font-mono" autocomplete="off">
                  </div>
                </div>
                <div class="grid gap-4 md:grid-cols-2">
                  <div class="md:col-span-2">
                    <label class="label-custom">Bot Token</label>
                    <input v-model="telegramGatewayForm.config.bot_token" type="password" class="input-custom font-mono" autocomplete="off" placeholder="••••••">
                  </div>
                  <div>
                    <label class="label-custom">Chat ID</label>
                    <input v-model="telegramGatewayForm.config.chat_id" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Nome do Bot (opcional)</label>
                    <input v-model="telegramGatewayForm.config.bot_name" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                </div>
              </div>

              <div v-if="activeGateway === 'smtp'" class="space-y-4">
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Nome do Gateway</label>
                    <input v-model="smtpGatewayForm.name" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Prioridade</label>
                    <input v-model.number="smtpGatewayForm.priority" type="number" min="1" class="input-custom font-mono" autocomplete="off">
                  </div>
                </div>
                <div class="grid gap-4 md:grid-cols-2">
                  <div>
                    <label class="label-custom">Segurança</label>
                    <select v-model="smtpGatewayForm.config.security" class="input-custom">
                      <option value="tls">TLS (587)</option>
                      <option value="ssl">SSL (465)</option>
                    </select>
                  </div>
                  <div>
                    <label class="label-custom">Porta</label>
                    <input v-model="smtpGatewayForm.config.port" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div class="md:col-span-2">
                    <label class="label-custom">Host</label>
                    <input v-model="smtpGatewayForm.config.host" type="text" class="input-custom font-mono" autocomplete="off">
                  </div>
                  <div>
                    <label class="label-custom">Usuário</label>
                    <input v-model="smtpGatewayForm.config.user" type="text" class="input-custom font-mono" autocomplete="username">
                  </div>
                  <div>
                    <label class="label-custom">Senha</label>
                    <input v-model="smtpGatewayForm.config.password" type="password" class="input-custom font-mono" autocomplete="current-password" placeholder="••••••">
                  </div>
                  <div>
                    <label class="label-custom">Remetente (Nome)</label>
                    <input v-model="smtpGatewayForm.config.from_name" type="text" class="input-custom" autocomplete="name">
                  </div>
                  <div>
                    <label class="label-custom">Remetente (Email)</label>
                    <input v-model="smtpGatewayForm.config.from_email" type="email" class="input-custom font-mono" autocomplete="email">
                  </div>
                  <div class="md:col-span-2">
                    <label class="label-custom">Email de Teste</label>
                    <input v-model="smtpGatewayForm.config.test_recipient" type="email" class="input-custom font-mono" autocomplete="email">
                  </div>
                </div>
              </div>
            </form>
            <div class="bg-gray-50 dark:bg-gray-800/50 px-6 py-4 flex justify-between gap-3 border-t border-gray-100 dark:border-gray-700">
              <div class="flex items-center gap-4">
                <button
                  v-if="(activeGateway === 'sms' && smsGatewayForm.id) || (activeGateway === 'whatsapp' && whatsappGatewayForm.id) || (activeGateway === 'telegram' && telegramGatewayForm.id) || (activeGateway === 'smtp' && smtpGatewayForm.id) || (activeGateway === 'video' && videoGatewayForm.id)"
                  @click="deleteGateway"
                  class="btn-secondary text-red-500 border-red-500/40 hover:border-red-400 hover:text-red-400"
                >
                  Remover
                </button>
                <label class="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-300">
                  <input v-model="gatewayEnabled" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4" autocomplete="off">
                  {{ gatewayEnabledLabel }}
                </label>
              </div>
              <div class="flex justify-end gap-3 ml-auto">
                <button @click="closeGatewayModal" class="btn-secondary">Cancelar</button>
                <button @click="saveGateway" class="btn-primary">Salvar</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      v-model:show="showGatewayDeleteConfirm"
      title="Remover gateway"
      :message="gatewayDeleteMessage"
      type="danger"
      confirm-text="Remover"
      cancel-text="Cancelar"
      @confirm="confirmGatewayDelete"
      @cancel="gatewayToDelete = null"
    />
    <ConfirmDialog
      v-model:show="showWhatsappResetConfirm"
      title="Resetar sessão WhatsApp"
      message="Isso apaga a sessão atual e força um novo QR. Deseja continuar?"
      type="warning"
      confirm-text="Resetar"
      cancel-text="Cancelar"
      @confirm="confirmWhatsappQrReset"
    />

  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, onBeforeUnmount, nextTick } from 'vue';
import Hls from 'hls.js';
import { useNotification } from '@/composables/useNotification';
import { useApi } from '@/composables/useApi';
import ConfirmDialog from '@/components/Common/ConfirmDialog.vue';

const Icons = {
  Cog: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
  Server: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 00-2-2m-2-4h.01M17 16h.01"/></svg>' },
  Map: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>' },
  Terminal: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>' },
  Database: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/></svg>' },
  Mail: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 8l9 6 9-6M5 5h14a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2z"/></svg>' },
  Chat: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 10h8M8 14h5m7 2a2 2 0 01-2 2H7l-4 4V6a2 2 0 012-2h12a2 2 0 012 2z"/></svg>' },
};

const notify = useNotification();
const api = useApi();
const activeTab = ref('system');
const showHistory = ref(false);
const auditEntries = ref([]);
const smsPhoneError = ref('');
const gateways = ref([]);
const gatewayLoading = ref(false);
const showWhatsappResetConfirm = ref(false);

const navItems = [
  { id: 'system', label: 'Sistema', icon: Icons.Terminal },
  { id: 'gateways', label: 'Gateway', icon: Icons.Chat },
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
  BACKUP_ZIP_PASSWORD: '',
  REDIS_URL: '',
  SERVICE_RESTART_COMMANDS: '',
  FTP_ENABLED: false,
  FTP_HOST: '',
  FTP_PORT: '21',
  FTP_USER: '',
  FTP_PASSWORD: '',
  FTP_PATH: '/backups/',
  GDRIVE_ENABLED: false,
  GDRIVE_AUTH_MODE: 'service_account',
  GDRIVE_CREDENTIALS_JSON: '',
  GDRIVE_FOLDER_ID: '',
  GDRIVE_SHARED_DRIVE_ID: '',
  GDRIVE_OAUTH_CLIENT_ID: '',
  GDRIVE_OAUTH_CLIENT_SECRET: '',
  GDRIVE_OAUTH_CONNECTED: false,
  GDRIVE_OAUTH_USER_EMAIL: '',
  SMTP_ENABLED: false,
  SMTP_HOST: '',
  SMTP_PORT: '',
  SMTP_SECURITY: 'tls',
  SMTP_USER: '',
  SMTP_PASSWORD: '',
  SMTP_AUTH_MODE: 'password',
  SMTP_OAUTH_CLIENT_ID: '',
  SMTP_OAUTH_CLIENT_SECRET: '',
  SMTP_OAUTH_REFRESH_TOKEN: '',
  SMTP_FROM_NAME: '',
  SMTP_FROM_EMAIL: '',
  SMTP_TEST_RECIPIENT: 'paulo@simplesinternet.net.br',
  SMS_ENABLED: false,
  SMS_PROVIDER: 'smsnet',
  SMS_PROVIDER_RANK: '1',
  SMS_USERNAME: '',
  SMS_PASSWORD: '',
  SMS_API_TOKEN: '',
  SMS_API_URL: 'https://sistema.smsnet.com.br/sms/global',
  SMS_SENDER_ID: '',
  SMS_TEST_RECIPIENT: '',
  SMS_TEST_MESSAGE: 'Teste SMS ProveMaps.',
  SMS_PRIORITY: '',
  SMS_AWS_REGION: '',
  SMS_AWS_ACCESS_KEY_ID: '',
  SMS_AWS_SECRET_ACCESS_KEY: '',
  SMS_INFOBIP_BASE_URL: '',
});

const servers = ref([]);
const showServerModal = ref(false);
const editingServer = ref(null);
const serverForm = ref({ name: '', server_type: 'zabbix', url: '', auth_token: '', is_active: true, extra_config_text: '{}' });
const backups = ref([]);
const backupLoading = ref(false);
const backupSettings = ref({ retention_days: '', retention_count: '' });
const showBackupConfig = ref(false);
const showCloudConfig = ref(false);
const backupPasswordSnapshot = ref('');
const showFtpConfig = ref(false);
const gdriveJsonLocked = ref(false);
const gdriveFileInput = ref(null);
const showGdriveHelp = ref(false);
const ftpTestStatus = ref('');
const smtpProvider = ref('gmail');
const smtpOauthJson = ref('');
const smtpOauthFileInput = ref(null);
const showGatewayModal = ref(false);
const activeGateway = ref('sms');
const showGatewayDeleteConfirm = ref(false);
const gatewayToDelete = ref(null);
const expandedGateways = ref({
  sms: true,
  whatsapp: false,
  telegram: false,
  smtp: false,
  video: false,
});
const expandedSystemSections = ref({
  systemParams: true,
  monitoring: true,
  maps: false,
  backups: false,
});
const smsGatewayForm = ref({
  id: null,
  name: 'SMSNET',
  provider: 'smsnet',
  priority: 1,
  enabled: true,
  config: {
    username: '',
    password: '',
    api_token: '',
    api_url: 'https://sistema.smsnet.com.br/sms/global',
    sender_id: '',
    test_recipient: '',
    test_message: 'Teste SMS ProveMaps.',
    aws_region: '',
    aws_access_key_id: '',
    aws_secret_access_key: '',
    infobip_base_url: '',
  },
});
const whatsappGatewayForm = ref({
  id: null,
  name: 'Meta Cloud API',
  provider: 'meta',
  priority: 1,
  enabled: false,
  config: {
    phone_number_id: '',
    business_account_id: '',
    access_token: '',
    app_id: '',
    verify_token: '',
    webhook_url: '',
    auth_mode: 'meta',
    qr_status: 'pending',
    qr_image_url: '',
    qr_service_url: '',
    test_recipient: '',
    test_message: 'Teste WhatsApp ProveMaps.',
  },
});
const telegramGatewayForm = ref({
  id: null,
  name: 'Bot Telegram',
  provider: 'telegram',
  priority: 1,
  enabled: false,
  config: {
    bot_token: '',
    chat_id: '',
    bot_name: '',
  },
});
const smtpGatewayForm = ref({
  id: null,
  name: 'SMTP Principal',
  provider: 'smtp',
  priority: 1,
  enabled: false,
  config: {
    host: '',
    port: '',
    security: 'tls',
    user: '',
    password: '',
    auth_mode: 'password',
    from_name: '',
    from_email: '',
    test_recipient: '',
    oauth_client_id: '',
    oauth_client_secret: '',
    oauth_refresh_token: '',
  },
});

const videoGatewayForm = ref({
  id: null,
  name: 'Gateway de Vídeo',
  provider: 'restreamer',
  priority: 1,
  enabled: false,
  config: {
    stream_type: 'rtmp',
    stream_url: '',
    restream_key: '',
    preview_url: '',
    preview_active: false,
    playback_token: '',
    hls_public_base_url: '',
  },
});

const videoPreview = ref({
  status: 'idle',
  url: '',
  error: '',
  loading: false,
});
const videoPreviewElement = ref(null);
const hlsInstance = ref(null);
const videoElementListeners = ref([]);
const autoPreviewHandle = ref(null);
const previewReloadHandle = ref(null);
const previewLoadHandle = ref(null);
const previewRetryCount = ref(0);
const MAX_PREVIEW_RETRIES = 12;
const previewWatchdogHandle = ref(null);
const previewWatchdogState = { lastTime: 0, stagnantTicks: 0 };

const clearPreviewWatchdog = () => {
  if (previewWatchdogHandle.value) {
    clearInterval(previewWatchdogHandle.value);
    previewWatchdogHandle.value = null;
  }
  previewWatchdogState.lastTime = 0;
  previewWatchdogState.stagnantTicks = 0;
};

const startPreviewWatchdog = (reportStall) => {
  clearPreviewWatchdog();
  if (typeof reportStall !== 'function') {
    return;
  }
  previewWatchdogHandle.value = setInterval(() => {
    const element = videoPreviewElement.value;
    if (!element) {
      previewWatchdogState.lastTime = 0;
      previewWatchdogState.stagnantTicks = 0;
      return;
    }

    const status = videoPreview.value.status;
    if (status !== 'playing' || status === 'retrying' || status === 'loading') {
      previewWatchdogState.lastTime = Number.isFinite(element.currentTime) ? element.currentTime : 0;
      previewWatchdogState.stagnantTicks = 0;
      return;
    }

    if (element.paused || element.ended) {
      previewWatchdogState.lastTime = Number.isFinite(element.currentTime) ? element.currentTime : 0;
      previewWatchdogState.stagnantTicks = 0;
      return;
    }

    const currentTime = Number.isFinite(element.currentTime) ? element.currentTime : 0;
    const delta = currentTime - (previewWatchdogState.lastTime || 0);
    
    if (Math.abs(delta) < 0.15) {
      previewWatchdogState.stagnantTicks += 1;
      if (previewWatchdogState.stagnantTicks >= 20) {
        previewWatchdogState.stagnantTicks = 0;
        previewWatchdogState.lastTime = currentTime;
        reportStall();
        return;
      }
    } else {
      previewWatchdogState.stagnantTicks = 0;
    }

    previewWatchdogState.lastTime = currentTime;
  }, 1000);
};

const clearPreviewReloadHandle = () => {
  if (previewReloadHandle.value) {
    clearTimeout(previewReloadHandle.value);
    previewReloadHandle.value = null;
  }
};

const clearPreviewLoadHandle = () => {
  if (previewLoadHandle.value) {
    clearTimeout(previewLoadHandle.value);
    previewLoadHandle.value = null;
  }
};

const unbindVideoElementListeners = () => {
  const element = videoPreviewElement.value;
  if (!element || videoElementListeners.value.length === 0) return;
  for (const [event, handler] of videoElementListeners.value) {
    element.removeEventListener(event, handler);
  }
  videoElementListeners.value = [];
};

const destroyHlsInstance = () => {
  clearPreviewWatchdog();
  clearPreviewReloadHandle();
  clearPreviewLoadHandle();
  if (hlsInstance.value) {
    try {
      if (typeof hlsInstance.value.stopLoad === 'function') {
        hlsInstance.value.stopLoad();
      }
      if (typeof hlsInstance.value.detachMedia === 'function') {
        hlsInstance.value.detachMedia();
      }
      hlsInstance.value.destroy();
    } catch (error) {
      // ignora erros de limpeza para evitar travar o fluxo da UI
    }
    hlsInstance.value = null;
  }
  const element = videoPreviewElement.value;
  if (element) {
    unbindVideoElementListeners();
    try {
      element.pause();
      element.removeAttribute('src');
      element.load();
    } catch (error) {
      // ignora erros de limpeza para evitar travar o fluxo da UI
    }
  }
};

const clearAutoPreviewHandle = () => {
  if (autoPreviewHandle.value) {
    clearTimeout(autoPreviewHandle.value);
    autoPreviewHandle.value = null;
  }
};

const resetVideoPreviewState = ({ clearUrl = true } = {}) => {
  destroyHlsInstance();
  clearAutoPreviewHandle();
  videoPreview.value.loading = false;
  videoPreview.value.error = '';
  previewRetryCount.value = 0;
  if (clearUrl) {
    videoPreview.value.url = '';
  }
  videoPreview.value.status = 'idle';
};

const gatewayModalTitle = computed(() => {
  if (activeGateway.value === 'video') return 'Gateway de Vídeo';
  if (activeGateway.value === 'whatsapp') return 'Gateway WhatsApp (Meta)';
  if (activeGateway.value === 'telegram') return 'Gateway Telegram';
  if (activeGateway.value === 'smtp') return 'Gateway SMTP';
  const provider = (smsGatewayForm.value.provider || 'smsnet').toUpperCase();
  return `Gateway SMS - ${provider}`;
});

const gatewayModalSubtitle = computed(() => {
  if (activeGateway.value === 'video') return 'Transcodificação e streaming HLS com pré-visualização.';
  if (activeGateway.value === 'whatsapp') return 'Configuração da API oficial do WhatsApp.';
  if (activeGateway.value === 'telegram') return 'Configuração com Bot Token e Chat ID.';
  if (activeGateway.value === 'smtp') return 'Configuração de envio SMTP.';
  return 'Configuração do gateway SMS e teste de envio.';
});

const qrPollingHandle = ref(null);

const stopWhatsappQrPolling = () => {
  if (qrPollingHandle.value) {
    clearInterval(qrPollingHandle.value);
    qrPollingHandle.value = null;
  }
};

const gatewayEnabled = computed({
  get() {
    if (activeGateway.value === 'sms') return smsGatewayForm.value.enabled;
    if (activeGateway.value === 'whatsapp') return whatsappGatewayForm.value.enabled;
    if (activeGateway.value === 'telegram') return telegramGatewayForm.value.enabled;
    if (activeGateway.value === 'smtp') return smtpGatewayForm.value.enabled;
    if (activeGateway.value === 'video') return videoGatewayForm.value.enabled;
    return false;
  },
  set(value) {
    if (activeGateway.value === 'sms') smsGatewayForm.value.enabled = value;
    if (activeGateway.value === 'whatsapp') whatsappGatewayForm.value.enabled = value;
    if (activeGateway.value === 'telegram') telegramGatewayForm.value.enabled = value;
    if (activeGateway.value === 'smtp') smtpGatewayForm.value.enabled = value;
    if (activeGateway.value === 'video') videoGatewayForm.value.enabled = value;
  },
});

const gatewayEnabledLabel = computed(() => {
  if (activeGateway.value === 'video') return 'Ativar vídeo';
  if (activeGateway.value === 'sms') return 'Ativar SMS';
  if (activeGateway.value === 'whatsapp') return 'Ativar WhatsApp';
  if (activeGateway.value === 'telegram') return 'Ativar Telegram';
  if (activeGateway.value === 'smtp') return 'Ativar SMTP';
  return 'Ativar gateway';
});

const gatewayDeleteMessage = computed(() => {
  if (!gatewayToDelete.value) return 'Deseja remover este gateway?';
  return `Deseja remover o gateway "${gatewayToDelete.value.name}"? Esta ação não pode ser desfeita.`;
});

const openGatewayModal = (type, reset = false, gateway = null) => {
  activeGateway.value = type;
  whatsappQrAutoTriggered.value = false;
  if (type !== 'video') {
    resetVideoPreviewState();
  }
  if (type === 'sms') {
    if (gateway && !reset) {
      smsGatewayForm.value = {
        id: gateway.id,
        name: gateway.name,
        provider: gateway.provider || 'smsnet',
        priority: gateway.priority || 1,
        enabled: !!gateway.enabled,
        config: {
          username: gateway.config?.username || '',
          password: '',
          api_token: gateway.config?.api_token || '',
          api_url: gateway.config?.api_url || 'https://sistema.smsnet.com.br/sms/global',
          sender_id: gateway.config?.sender_id || '',
          test_recipient: gateway.config?.test_recipient || '',
          test_message: gateway.config?.test_message || 'Teste SMS ProveMaps.',
          aws_region: gateway.config?.aws_region || '',
          aws_access_key_id: gateway.config?.aws_access_key_id || '',
          aws_secret_access_key: '',
          infobip_base_url: gateway.config?.infobip_base_url || '',
        },
      };
    } else {
      smsGatewayForm.value = {
        id: null,
        name: 'SMSNET',
        provider: 'smsnet',
        priority: 1,
        enabled: true,
        config: {
          username: '',
          password: '',
          api_token: '',
          api_url: 'https://sistema.smsnet.com.br/sms/global',
          sender_id: '',
          test_recipient: '',
          test_message: 'Teste SMS ProveMaps.',
          aws_region: '',
          aws_access_key_id: '',
          aws_secret_access_key: '',
          infobip_base_url: '',
        },
      };
    }
    applySmsPreset();
  }
  if (type === 'whatsapp') {
    if (gateway && !reset) {
      whatsappGatewayForm.value = {
        id: gateway.id,
        name: gateway.name,
        provider: gateway.provider || 'meta',
        priority: gateway.priority || 1,
        enabled: !!gateway.enabled,
        config: {
          phone_number_id: gateway.config?.phone_number_id || '',
          business_account_id: gateway.config?.business_account_id || '',
          access_token: '',
          app_id: gateway.config?.app_id || '',
          verify_token: gateway.config?.verify_token || '',
          webhook_url: gateway.config?.webhook_url || '',
          auth_mode: gateway.config?.auth_mode || 'meta',
          qr_status: gateway.config?.qr_status || 'pending',
          qr_image_url: gateway.config?.qr_image_url || '',
          qr_service_url: gateway.config?.qr_service_url || '',
          test_recipient: gateway.config?.test_recipient || '',
          test_message: gateway.config?.test_message || 'Teste WhatsApp ProveMaps.',
        },
      };
    } else {
      whatsappGatewayForm.value = {
        id: null,
        name: 'Meta Cloud API',
        provider: 'meta',
        priority: 1,
        enabled: false,
        config: {
          phone_number_id: '',
          business_account_id: '',
          access_token: '',
          app_id: '',
          verify_token: '',
          webhook_url: '',
          auth_mode: 'meta',
          qr_status: 'pending',
          qr_image_url: '',
          qr_service_url: '',
          test_recipient: '',
          test_message: 'Teste WhatsApp ProveMaps.',
        },
      };
    }
  }
  if (type === 'telegram') {
    if (gateway && !reset) {
      telegramGatewayForm.value = {
        id: gateway.id,
        name: gateway.name,
        provider: gateway.provider || 'telegram',
        priority: gateway.priority || 1,
        enabled: !!gateway.enabled,
        config: {
          bot_token: '',
          chat_id: gateway.config?.chat_id || '',
          bot_name: gateway.config?.bot_name || '',
        },
      };
    } else {
      telegramGatewayForm.value = {
        id: null,
        name: 'Bot Telegram',
        provider: 'telegram',
        priority: 1,
        enabled: false,
        config: {
          bot_token: '',
          chat_id: '',
          bot_name: '',
        },
      };
    }
  }
  if (type === 'smtp') {
    if (gateway && !reset) {
      smtpGatewayForm.value = {
        id: gateway.id,
        name: gateway.name,
        provider: gateway.provider || 'smtp',
        priority: gateway.priority || 1,
        enabled: !!gateway.enabled,
        config: {
          host: gateway.config?.host || '',
          port: gateway.config?.port || '',
          security: gateway.config?.security || 'tls',
          user: gateway.config?.user || '',
          password: '',
          auth_mode: gateway.config?.auth_mode || 'password',
          from_name: gateway.config?.from_name || '',
          from_email: gateway.config?.from_email || '',
          test_recipient: gateway.config?.test_recipient || '',
          oauth_client_id: gateway.config?.oauth_client_id || '',
          oauth_client_secret: '',
          oauth_refresh_token: '',
        },
      };
    } else {
      smtpGatewayForm.value = {
        id: null,
        name: 'SMTP Principal',
        provider: 'smtp',
        priority: 1,
        enabled: false,
        config: {
          host: '',
          port: '',
          security: 'tls',
          user: '',
          password: '',
          auth_mode: 'password',
          from_name: '',
          from_email: '',
          test_recipient: '',
          oauth_client_id: '',
          oauth_client_secret: '',
          oauth_refresh_token: '',
        },
      };
    }
  }
  if (type === 'video') {
    resetVideoPreviewState();
    if (gateway && !reset) {
      videoGatewayForm.value = {
        id: gateway.id,
        name: gateway.name,
        provider: gateway.provider || 'restreamer',
        priority: gateway.priority || 1,
        enabled: !!gateway.enabled,
        config: {
          stream_type: gateway.config?.stream_type || 'rtmp',
          stream_url: gateway.config?.stream_url || '',
          restream_key: gateway.config?.restream_key || '',
          preview_url: gateway.config?.preview_url || '',
          preview_active: gateway.config?.preview_active === true,
          playback_token: gateway.config?.playback_token || '',
          hls_public_base_url: gateway.config?.hls_public_base_url || '',
        },
      };
    } else {
      videoGatewayForm.value = {
        id: null,
        name: 'Gateway de Vídeo',
        provider: 'restreamer',
        priority: 1,
        enabled: false,
        config: {
          stream_type: 'rtmp',
          stream_url: '',
          restream_key: '',
          preview_url: '',
          preview_active: false,
          playback_token: '',
          hls_public_base_url: '',
        },
      };
    }
  }
  showGatewayModal.value = true;
};

const closeGatewayModal = () => {
  stopWhatsappQrPolling();
  stopVideoPreview({ remote: true, silent: true });
  showGatewayModal.value = false;
};

const toggleGatewayGroup = (id) => {
  expandedGateways.value[id] = !expandedGateways.value[id];
};

const toggleSystemSection = (id) => {
  expandedSystemSections.value[id] = !expandedSystemSections.value[id];
};

const smsGateways = computed(() => gateways.value.filter((gw) => gw.gateway_type === 'sms'));
const whatsappGateways = computed(() => gateways.value.filter((gw) => gw.gateway_type === 'whatsapp'));
const telegramGateways = computed(() => gateways.value.filter((gw) => gw.gateway_type === 'telegram'));
const smtpGateways = computed(() => gateways.value.filter((gw) => gw.gateway_type === 'smtp'));
const videoGateways = computed(() => gateways.value.filter((gw) => gw.gateway_type === 'video'));
const smsGatewaysSorted = computed(() => [...smsGateways.value].sort((a, b) => a.priority - b.priority));
const whatsappGatewaysSorted = computed(() => [...whatsappGateways.value].sort((a, b) => a.priority - b.priority));
const telegramGatewaysSorted = computed(() => [...telegramGateways.value].sort((a, b) => a.priority - b.priority));
const smtpGatewaysSorted = computed(() => [...smtpGateways.value].sort((a, b) => a.priority - b.priority));
const videoGatewaysSorted = computed(() => [...videoGateways.value].sort((a, b) => a.priority - b.priority));
const smsGatewayCount = computed(() => smsGateways.value.length);
const whatsappGatewayCount = computed(() => whatsappGateways.value.length);
const telegramGatewayCount = computed(() => telegramGateways.value.length);
const smtpGatewayCount = computed(() => smtpGateways.value.length);
const videoGatewayCount = computed(() => videoGateways.value.length);
const monitoringServerCount = computed(() => (servers.value?.length || 0) + 1);

// API ACTIONS
const fetchConfiguration = async () => {
  try {
    const res = await api.get('/setup_app/api/config/');
    if (res.success && res.configuration) {
      configForm.value = { ...configForm.value, ...res.configuration };
      if (!configForm.value.SMTP_AUTH_MODE) {
        configForm.value.SMTP_AUTH_MODE = 'password';
      }
      backupPasswordSnapshot.value = configForm.value.BACKUP_ZIP_PASSWORD || '';
    }
  } catch (e) { console.error(e); }
};

const fetchGateways = async () => {
  try {
    gatewayLoading.value = true;
    const res = await api.get('/setup_app/api/gateways/');
    if (res.success) {
      gateways.value = res.gateways || [];
    }
  } catch (e) {
    notify.error('Gateways', e.message || 'Erro ao carregar gateways.');
  } finally {
    gatewayLoading.value = false;
  }
};

const getWhatsappGatewayStatusLabel = (gateway) => {
  if (!gateway) return '—';
  const authMode = gateway.config?.auth_mode;
  if (authMode === 'qr') {
    return getWhatsappQrStatusLabel(gateway.config?.qr_status);
  }
  return gateway.enabled ? 'Ativo' : 'Inativo';
};

const getWhatsappGatewayStatusColor = (gateway) => {
  if (!gateway) return 'bg-gray-500';
  const authMode = gateway.config?.auth_mode;
  if (authMode === 'qr') {
    const status = gateway.config?.qr_status;
    if (status === 'connected') return 'bg-emerald-400';
    if (status === 'disconnected') return 'bg-red-400';
    if (status === 'connecting') return 'bg-blue-400';
    return 'bg-amber-400';
  }
  return gateway.enabled ? 'bg-emerald-400' : 'bg-gray-500';
};

const refreshWhatsappGatewayStatuses = async () => {
  if (whatsappGatewaysSorted.value.length === 0) return;
  try {
    for (const gateway of whatsappGatewaysSorted.value) {
      if (gateway.config?.auth_mode !== 'qr') continue;
      const res = await api.get(
        `/setup_app/api/gateways/${gateway.id}/whatsapp/qr/status/`,
        { qr_service_url: gateway.config?.qr_service_url || '' }
      );
      if (!res.success) continue;
      const idx = gateways.value.findIndex((item) => item.id === gateway.id);
      if (idx === -1) continue;
      const updated = { ...gateways.value[idx] };
      updated.config = {
        ...updated.config,
        qr_status: res.qr_status || updated.config?.qr_status,
        qr_image_url:
          res.qr_image_url !== undefined ? res.qr_image_url : updated.config?.qr_image_url,
      };
      gateways.value.splice(idx, 1, updated);
    }
  } catch (e) {
    notify.error('WhatsApp', e.message || 'Erro ao atualizar status.');
  }
};

const getVideoGatewayStatusLabel = (gateway) => {
  if (!gateway) return '—';
  if (!gateway.enabled) return 'Inativo';
  if (gateway.config?.preview_url) return 'Prévia ativa';
  return 'Ativo';
};

const getVideoGatewayStatusColor = (gateway) => {
  if (!gateway || !gateway.enabled) return 'bg-gray-500';
  if (gateway.config?.preview_url) return 'bg-emerald-400';
  return 'bg-blue-400';
};

const saveConfiguration = async () => {
  try {
    const res = await api.post('/setup_app/api/config/update/', configForm.value);
    notify.success('Configurações', res.message || 'Configurações salvas!');
    if (res.backup_warning) {
      notify.warning('Backups', res.backup_message || 'Backup não gerado automaticamente.');
    }
    if (res.gdrive_upload && res.gdrive_upload.success) {
      notify.success('Google Drive', res.gdrive_upload.message || 'Backup enviado.');
    } else if (res.gdrive_upload && res.gdrive_upload.success === false && res.gdrive_upload.message && configForm.value.GDRIVE_ENABLED) {
      notify.warning('Google Drive', res.gdrive_upload.message);
    }
    if (res.ftp_upload && res.ftp_upload.success) {
      notify.success('FTP', res.ftp_upload.message || 'Backup enviado.');
    } else if (res.ftp_upload && res.ftp_upload.success === false && res.ftp_upload.message && configForm.value.FTP_ENABLED) {
      notify.warning('FTP', res.ftp_upload.message);
    }
    fetchConfiguration();
    const passwordChanged = backupPasswordSnapshot.value !== (configForm.value.BACKUP_ZIP_PASSWORD || '');
    if (res.backup_created || passwordChanged) {
      fetchBackups();
    }
    if (passwordChanged && !res.backup_created) {
      await createBackup();
    }
    backupPasswordSnapshot.value = configForm.value.BACKUP_ZIP_PASSWORD || '';
  } catch (e) { notify.error('Configurações', e.message || 'Erro ao salvar.'); }
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
    if (res.success) notify.success('Zabbix', res.message);
    else notify.error('Zabbix', res.message);
  } catch (e) { notify.error('Zabbix', e.message || 'Erro ao testar Zabbix.'); }
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
    if (res.success) notify.success('Banco de Dados', res.message);
    else notify.error('Banco de Dados', res.message);
  } catch (e) { notify.error('Banco de Dados', e.message || 'Erro ao testar banco.'); }
};

const testRedis = async () => {
  try {
    const payload = { redis_url: configForm.value.REDIS_URL };
    const res = await api.post('/setup_app/api/test-redis/', payload);
    if (res.success) notify.success('Redis', res.message);
    else notify.error('Redis', res.message);
  } catch (e) { notify.error('Redis', e.message || 'Erro ao testar Redis.'); }
};

const testGdrive = async () => {
  try {
    const payload = {
      gdrive_auth_mode: configForm.value.GDRIVE_AUTH_MODE,
      gdrive_credentials_json: configForm.value.GDRIVE_CREDENTIALS_JSON,
      gdrive_folder_id: configForm.value.GDRIVE_FOLDER_ID,
      gdrive_shared_drive_id: configForm.value.GDRIVE_SHARED_DRIVE_ID,
      gdrive_oauth_client_id: configForm.value.GDRIVE_OAUTH_CLIENT_ID,
      gdrive_oauth_client_secret: configForm.value.GDRIVE_OAUTH_CLIENT_SECRET,
    };
    const res = await api.post('/setup_app/api/test-gdrive/', payload);
    if (res.success) notify.success('Google Drive', res.message);
    else notify.error('Google Drive', res.message);
  } catch (e) { notify.error('Google Drive', e.message || 'Erro ao testar Drive.'); }
};

const testFtp = async () => {
  try {
    ftpTestStatus.value = '';
    const payload = {
      ftp_host: configForm.value.FTP_HOST,
      ftp_port: configForm.value.FTP_PORT,
      ftp_user: configForm.value.FTP_USER,
      ftp_password: configForm.value.FTP_PASSWORD,
      ftp_path: configForm.value.FTP_PATH,
    };
    const res = await api.post('/setup_app/api/test-ftp/', payload);
    if (res.success) {
      ftpTestStatus.value = 'ok';
      notify.success('FTP', res.message);
    } else {
      ftpTestStatus.value = 'fail';
      notify.error('FTP', res.message);
    }
  } catch (e) {
    ftpTestStatus.value = 'fail';
    notify.error('FTP', e.message || 'Erro ao testar FTP.');
  }
};

const applySmtpPreset = () => {
  if (smtpProvider.value === 'gmail') {
    configForm.value.SMTP_HOST = 'smtp.gmail.com';
    configForm.value.SMTP_PORT = '587';
    configForm.value.SMTP_SECURITY = 'tls';
  }
};

const applySmsPreset = () => {
  if (smsGatewayForm.value.provider === 'smsnet' && !smsGatewayForm.value.config.api_url) {
    smsGatewayForm.value.config.api_url = 'https://sistema.smsnet.com.br/sms/global';
  }
  if (smsGatewayForm.value.provider === 'infobip' && !smsGatewayForm.value.config.infobip_base_url) {
    smsGatewayForm.value.config.infobip_base_url = 'https://seu-subdominio.api.infobip.com';
  }
};

const syncVideoGatewayInList = (gatewayId, configUpdates = {}) => {
  if (!gatewayId) return;
  const index = gateways.value.findIndex((item) => item.id === gatewayId);
  if (index === -1) return;
  const current = gateways.value[index];
  gateways.value.splice(index, 1, {
    ...current,
    config: {
      ...(current.config || {}),
      ...configUpdates,
    },
  });
};

const isVideoPreviewActive = computed(() => videoPreview.value.status === 'playing');
const isVideoPreviewLoading = computed(() => videoPreview.value.loading);
const previewUrlDisplay = computed(() => videoPreview.value.url || videoGatewayForm.value.config.preview_url || '');

const loadVideoPreview = async (url, { force = false } = {}) => {
  if (!url) {
    videoPreview.value.status = 'idle';
    destroyHlsInstance();
    return;
  }
  await nextTick();
  const element = videoPreviewElement.value;
  if (!element) return;
  if (force) {
    destroyHlsInstance();
  }
  videoPreview.value.error = '';
  const snapPlayerToLive = () => {
    if (!element.seekable || element.seekable.length === 0) {
      return;
    }
    const liveEdge = element.seekable.end(element.seekable.length - 1);
    if (Number.isFinite(liveEdge)) {
      const target = liveEdge - 0.6;
      if (Math.abs(element.currentTime - target) > 1.5) {
        element.currentTime = target;
      }
    }
  };

  const ensurePlayback = () => {
    if (!element || !videoPreview.value.url) return;
    if (videoPreview.value.status === 'idle' || videoPreview.value.status === 'error') return;
    snapPlayerToLive();
    if (element.paused) {
      element.play().catch(() => {});
    }
  };

  const handlePlaybackStall = () => {
    if (!videoPreview.value.url) return;
    if (['retrying', 'loading', 'idle', 'error'].includes(videoPreview.value.status)) return;
    ensurePlayback();
    schedulePreviewReload(400);
  };

  const bindElementEvents = () => {
    unbindVideoElementListeners();
    const listeners = [
      ['ended', handlePlaybackStall],
      ['pause', ensurePlayback],
      ['stalled', handlePlaybackStall],
      ['waiting', ensurePlayback],
      ['error', handlePlaybackStall],
    ];
    for (const [event, handler] of listeners) {
      element.addEventListener(event, handler);
    }
    videoElementListeners.value = listeners;
  };

  try {
    element.muted = true;
    element.playsInline = true;
    element.controls = true;
    bindElementEvents();
    startPreviewWatchdog(handlePlaybackStall);
    if (Hls.isSupported()) {
      const instance = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        liveSyncDurationCount: 1,
        liveMaxLatencyDurationCount: 2,
        maxLiveSyncPlaybackRate: 1.4,
        backBufferLength: 0,
        startPosition: -1,
        maxBufferLength: 6,
        maxMaxBufferLength: 8,
        maxBufferSize: 6 * 1024 * 1024,
        fragLoadingRetryDelay: 500,
        manifestLoadingRetryDelay: 500,
        levelLoadingRetryDelay: 500,
        manifestLoadingMaxRetry: 6,
        fragLoadingMaxRetry: 4,
        levelLoadingMaxRetry: 4,
        nudgeOffset: 0.1,
      });
      instance.on(Hls.Events.ERROR, (_event, data) => {
        if (!data) return;
        if (data.details === Hls.ErrorDetails.BUFFER_STALLED_ERROR) {
          element.play().catch(() => {});
          snapPlayerToLive();
          return;
        }
        if (
          data.details === Hls.ErrorDetails.MANIFEST_LOAD_ERROR ||
          data.details === Hls.ErrorDetails.MANIFEST_LOAD_TIMEOUT ||
          data.details === Hls.ErrorDetails.FRAG_LOAD_ERROR ||
          data.details === Hls.ErrorDetails.FRAG_LOAD_TIMEOUT ||
          data.details === Hls.ErrorDetails.LEVEL_LOAD_ERROR
        ) {
          schedulePreviewReload();
          return;
        }
        if (data.type === Hls.ErrorTypes.MEDIA_ERROR && hlsInstance.value) {
          try {
            hlsInstance.value.recoverMediaError();
            return;
          } catch (recoverError) {
            console.warn('[VideoPreview] Falha ao recuperar media error', recoverError);
          }
        }
        if (data.fatal) {
          videoPreview.value.error = 'Stream indisponível ou formato inválido.';
          videoPreview.value.status = 'error';
          destroyHlsInstance();
        }
      });
      instance.on(Hls.Events.LEVEL_UPDATED, () => {
        snapPlayerToLive();
      });
      instance.on(Hls.Events.FRAG_BUFFERED, () => {
        element.play().catch(() => {});
      });
      instance.on(Hls.Events.MANIFEST_PARSED, () => {
        previewRetryCount.value = 0;
        videoPreview.value.status = 'playing';
        videoPreview.value.loading = false;
        videoPreview.value.error = '';
        snapPlayerToLive();
        element.play().catch(() => {});
      });
      instance.loadSource(url);
      instance.attachMedia(element);
      hlsInstance.value = instance;
      videoPreview.value.loading = true;
      videoPreview.value.status = 'loading';
    } else if (element.canPlayType('application/vnd.apple.mpegurl')) {
      element.src = url;
      videoPreview.value.loading = true;
      videoPreview.value.status = 'loading';
      element.onloadedmetadata = () => {
        previewRetryCount.value = 0;
        videoPreview.value.status = 'playing';
        videoPreview.value.loading = false;
        videoPreview.value.error = '';
        snapPlayerToLive();
        element.play().catch(() => {});
      };
    } else {
      throw new Error('O navegador não suporta reprodução HLS.');
    }
  } catch (error) {
    videoPreview.value.status = 'error';
    videoPreview.value.error = error?.message || 'Falha ao iniciar a pré-visualização.';
    destroyHlsInstance();
  }
};

const stopVideoPreview = async ({ remote = true, silent = false, gatewayId = null } = {}) => {
  clearAutoPreviewHandle();
  const targetId = gatewayId || videoGatewayForm.value.id;
  destroyHlsInstance();
  videoPreview.value.loading = false;
  videoPreview.value.status = 'idle';
  videoPreview.value.error = '';
  videoPreview.value.url = '';
  previewRetryCount.value = 0;
  if (targetId === videoGatewayForm.value.id) {
    videoGatewayForm.value.config.preview_active = false;
  }
  if (targetId) {
    syncVideoGatewayInList(targetId, { preview_active: false });
  }
  if (targetId && remote) {
    try {
      await api.post(`/setup_app/api/gateways/${targetId}/video/preview/stop/`);
    } catch (error) {
      const status = error?.response?.status || error?.status;
      if (!silent && status !== 404) {
        notify.warning('Vídeo', error?.message || 'Não foi possível encerrar a pré-visualização.');
      }
    }
  }
};

const startVideoPreview = async ({ silent = false } = {}) => {
  clearAutoPreviewHandle();
  if (!videoGatewayForm.value.id) {
    if (!silent) {
      notify.error('Vídeo', 'Salve o gateway antes de iniciar a pré-visualização.');
    }
    return;
  }
  const streamUrl = (videoGatewayForm.value.config.stream_url || '').trim();
  if (!streamUrl) {
    if (!silent) {
      notify.error('Vídeo', 'Informe a URL do stream para pré-visualizar.');
    }
    return;
  }
  try {
    videoPreview.value.loading = true;
    videoPreview.value.status = 'loading';
    videoPreview.value.error = '';
    previewRetryCount.value = 0;
    clearPreviewReloadHandle();
    const res = await api.post(
      `/setup_app/api/gateways/${videoGatewayForm.value.id}/video/preview/start/`
    );
    if (!res?.success) {
      videoPreview.value.status = 'error';
      videoPreview.value.error = res?.message || 'Não foi possível iniciar a pré-visualização.';
      return;
    }
    const previewUrl = res.preview_url || videoGatewayForm.value.config.preview_url || '';
    if (!previewUrl) {
      videoPreview.value.status = 'error';
      videoPreview.value.error = 'Backend não retornou a URL de pré-visualização.';
      return;
    }
    videoGatewayForm.value.config.preview_url = previewUrl;
    videoGatewayForm.value.config.preview_active = true;
    videoPreview.value.url = previewUrl;
    syncVideoGatewayInList(videoGatewayForm.value.id, { preview_url: previewUrl, preview_active: true });
    if (!silent) {
      notify.success('Vídeo', 'Pré-visualização iniciada.');
    }
  } catch (error) {
    videoPreview.value.status = 'error';
    videoPreview.value.error = error?.message || 'Erro ao iniciar a pré-visualização.';
  } finally {
    videoPreview.value.loading = false;
  }
};

const scheduleVideoPreviewStart = (delayMs = 600) => {
  clearAutoPreviewHandle();
  const hasGateway = Boolean(videoGatewayForm.value.id);
  const streamUrl = (videoGatewayForm.value.config.stream_url || '').trim();
  if (!showGatewayModal.value || activeGateway.value !== 'video' || !hasGateway || !streamUrl) {
    return;
  }
  autoPreviewHandle.value = setTimeout(() => {
    autoPreviewHandle.value = null;
    startVideoPreview({ silent: true });
  }, delayMs);
};

const queuePreviewLoad = (url, delayMs = 600, { force = false } = {}) => {
  if (!url) return;
  clearPreviewLoadHandle();
  previewLoadHandle.value = setTimeout(() => {
    previewLoadHandle.value = null;
    loadVideoPreview(url, { force });
  }, delayMs);
};

const schedulePreviewReload = (delayMs = 800) => {
  clearPreviewReloadHandle();
  if (!videoPreview.value.url) {
    return;
  }
  if (previewRetryCount.value >= MAX_PREVIEW_RETRIES) {
    videoPreview.value.status = 'error';
    videoPreview.value.loading = false;
    videoPreview.value.error = 'Stream indisponível após múltiplas tentativas.';
    return;
  }
  previewRetryCount.value += 1;
  videoPreview.value.loading = true;
  videoPreview.value.status = 'retrying';
  videoPreview.value.error = '';
  destroyHlsInstance();
  previewReloadHandle.value = setTimeout(() => {
    previewReloadHandle.value = null;
    queuePreviewLoad(videoPreview.value.url, 200, { force: true });
  }, delayMs);
};

watch(
  () => videoPreview.value.url,
  (url, previous) => {
    if (!showGatewayModal.value || activeGateway.value !== 'video') {
      return;
    }
    if (url && url !== previous) {
      previewRetryCount.value = 0;
      queuePreviewLoad(url, 600, { force: true });
    }
    if (!url) {
      destroyHlsInstance();
    }
  }
);

watch(showGatewayModal, (visible, previous) => {
  if (visible) {
    scheduleVideoPreviewStart(400);
  } else if (!visible && previous) {
    stopVideoPreview({ remote: true, silent: true });
  }
});

watch(activeGateway, (current, previous) => {
  if (current === 'video') {
    scheduleVideoPreviewStart(400);
  }
  if (previous === 'video' && current !== 'video') {
    stopVideoPreview({ remote: true, silent: true });
  }
});

watch(
  () => videoGatewayForm.value.config.stream_url,
  (current, previous) => {
    if (activeGateway.value !== 'video') return;
    if (current === previous) return;
    stopVideoPreview({ remote: false, silent: true });
    scheduleVideoPreviewStart(700);
  }
);

watch(
  () => videoGatewayForm.value.config.stream_type,
  (current, previous) => {
    if (activeGateway.value !== 'video') return;
    if (current === previous) return;
    stopVideoPreview({ remote: false, silent: true });
    scheduleVideoPreviewStart(700);
  }
);

const normalizeSmsPhone = (raw) => {
  const digits = String(raw || '').replace(/\D/g, '');
  if (!digits) {
    return { value: '', error: 'Informe um telefone.' };
  }
  if (digits.startsWith('55') && (digits.length === 12 || digits.length === 13)) {
    return { value: digits, error: '' };
  }
  if (digits.length === 10 || digits.length === 11) {
    return { value: `55${digits}`, error: '' };
  }
  return {
    value: digits,
    error: 'Telefone inválido. Use DDD + número (10 ou 11 dígitos), com ou sem 55.',
  };
};

const testSmtp = async () => {
  try {
    const payload = {
      smtp_host: configForm.value.SMTP_HOST,
      smtp_port: configForm.value.SMTP_PORT,
      smtp_security: configForm.value.SMTP_SECURITY,
      smtp_user: configForm.value.SMTP_USER,
      smtp_password: configForm.value.SMTP_PASSWORD,
      smtp_auth_mode: configForm.value.SMTP_AUTH_MODE,
      smtp_oauth_client_id: configForm.value.SMTP_OAUTH_CLIENT_ID,
      smtp_oauth_client_secret: configForm.value.SMTP_OAUTH_CLIENT_SECRET,
      smtp_oauth_refresh_token: configForm.value.SMTP_OAUTH_REFRESH_TOKEN,
      smtp_from_name: configForm.value.SMTP_FROM_NAME,
      smtp_from_email: configForm.value.SMTP_FROM_EMAIL,
      smtp_test_recipient: configForm.value.SMTP_TEST_RECIPIENT,
    };
    const res = await api.post('/setup_app/api/test-smtp/', payload);
    if (res.success) notify.success('SMTP', res.message);
    else notify.error('SMTP', res.message);
  } catch (e) { notify.error('SMTP', e.message || 'Erro ao testar SMTP.'); }
};

const testSms = async () => {
  try {
    const normalized = normalizeSmsPhone(smsGatewayForm.value.config.test_recipient);
    smsPhoneError.value = normalized.error;
    if (normalized.error) {
      notify.error('SMS', normalized.error);
      return;
    }
    smsGatewayForm.value.config.test_recipient = normalized.value;
    const payload = {
      sms_provider: smsGatewayForm.value.provider,
      sms_provider_rank: smsGatewayForm.value.priority,
      sms_test_recipient: smsGatewayForm.value.config.test_recipient,
      sms_test_message: smsGatewayForm.value.config.test_message,
    };
    const setIfFilled = (key, value) => {
      if (value !== undefined && value !== null && String(value).trim() !== '') {
        payload[key] = value;
      }
    };
    setIfFilled('sms_username', smsGatewayForm.value.config.username);
    setIfFilled('sms_password', smsGatewayForm.value.config.password);
    setIfFilled('sms_api_token', smsGatewayForm.value.config.api_token);
    setIfFilled('sms_api_url', smsGatewayForm.value.config.api_url);
    setIfFilled('sms_sender_id', smsGatewayForm.value.config.sender_id);
    setIfFilled('sms_aws_region', smsGatewayForm.value.config.aws_region);
    setIfFilled('sms_aws_access_key_id', smsGatewayForm.value.config.aws_access_key_id);
    setIfFilled('sms_aws_secret_access_key', smsGatewayForm.value.config.aws_secret_access_key);
    setIfFilled('sms_infobip_base_url', smsGatewayForm.value.config.infobip_base_url);
    const res = await api.post('/setup_app/api/test-sms/', payload);
    if (res.success) notify.success('SMS', res.message);
    else notify.error('SMS', res.message);
  } catch (e) { notify.error('SMS', e.message || 'Erro ao testar SMS.'); }
};

const testSmtpGateway = async () => {
  try {
    const payload = {
      smtp_host: smtpGatewayForm.value.config.host,
      smtp_port: smtpGatewayForm.value.config.port,
      smtp_security: smtpGatewayForm.value.config.security,
      smtp_user: smtpGatewayForm.value.config.user,
      smtp_password: smtpGatewayForm.value.config.password,
      smtp_auth_mode: smtpGatewayForm.value.config.auth_mode,
      smtp_oauth_client_id: smtpGatewayForm.value.config.oauth_client_id,
      smtp_oauth_client_secret: smtpGatewayForm.value.config.oauth_client_secret,
      smtp_oauth_refresh_token: smtpGatewayForm.value.config.oauth_refresh_token,
      smtp_from_name: smtpGatewayForm.value.config.from_name,
      smtp_from_email: smtpGatewayForm.value.config.from_email,
      smtp_test_recipient: smtpGatewayForm.value.config.test_recipient,
    };
    const res = await api.post('/setup_app/api/test-smtp/', payload);
    if (res.success) notify.success('SMTP', res.message);
    else notify.error('SMTP', res.message);
  } catch (e) { notify.error('SMTP', e.message || 'Erro ao testar SMTP.'); }
};

const saveGateway = async () => {
  try {
    let payload = null;
    if (activeGateway.value === 'sms') {
      payload = {
        id: smsGatewayForm.value.id,
        name: smsGatewayForm.value.name,
        gateway_type: 'sms',
        provider: smsGatewayForm.value.provider,
        priority: smsGatewayForm.value.priority,
        enabled: smsGatewayForm.value.enabled,
        config: smsGatewayForm.value.config,
      };
    }
    if (activeGateway.value === 'whatsapp') {
      payload = {
        id: whatsappGatewayForm.value.id,
        name: whatsappGatewayForm.value.name,
        gateway_type: 'whatsapp',
        provider: whatsappGatewayForm.value.provider,
        priority: whatsappGatewayForm.value.priority,
        enabled: whatsappGatewayForm.value.enabled,
        config: whatsappGatewayForm.value.config,
      };
    }
    if (activeGateway.value === 'telegram') {
      payload = {
        id: telegramGatewayForm.value.id,
        name: telegramGatewayForm.value.name,
        gateway_type: 'telegram',
        provider: telegramGatewayForm.value.provider,
        priority: telegramGatewayForm.value.priority,
        enabled: telegramGatewayForm.value.enabled,
        config: telegramGatewayForm.value.config,
      };
    }
    if (activeGateway.value === 'smtp') {
      payload = {
        id: smtpGatewayForm.value.id,
        name: smtpGatewayForm.value.name,
        gateway_type: 'smtp',
        provider: smtpGatewayForm.value.provider,
        priority: smtpGatewayForm.value.priority,
        enabled: smtpGatewayForm.value.enabled,
        config: smtpGatewayForm.value.config,
      };
    }
    if (activeGateway.value === 'video') {
      await stopVideoPreview({ remote: false, silent: true });
      payload = {
        id: videoGatewayForm.value.id,
        name: videoGatewayForm.value.name,
        gateway_type: 'video',
        provider: videoGatewayForm.value.provider,
        priority: videoGatewayForm.value.priority,
        enabled: videoGatewayForm.value.enabled,
        config: videoGatewayForm.value.config,
      };
    }

    if (!payload) {
      notify.error('Gateways', 'Gateway inválido.');
      return;
    }

    let res;
    if (payload.id) {
      res = await api.patch(`/setup_app/api/gateways/${payload.id}/`, payload);
    } else {
      res = await api.post('/setup_app/api/gateways/', payload);
    }

    if (res.success) {
      notify.success('Gateways', 'Gateway salvo.');
      await fetchGateways();
      closeGatewayModal();
    } else {
      notify.error('Gateways', res.message || 'Erro ao salvar gateway.');
    }
  } catch (e) {
    notify.error('Gateways', e.message || 'Erro ao salvar gateway.');
  }
};

const requestGatewayDelete = (gateway) => {
  if (!gateway || !gateway.id) {
    notify.error('Gateways', 'Gateway inválido.');
    return;
  }
  gatewayToDelete.value = gateway;
  showGatewayDeleteConfirm.value = true;
};

const deleteGateway = () => {
  let gateway = null;
  if (activeGateway.value === 'sms') gateway = smsGatewayForm.value;
  if (activeGateway.value === 'whatsapp') gateway = whatsappGatewayForm.value;
  if (activeGateway.value === 'telegram') gateway = telegramGatewayForm.value;
  if (activeGateway.value === 'smtp') gateway = smtpGatewayForm.value;
  if (activeGateway.value === 'video') gateway = videoGatewayForm.value;
  requestGatewayDelete(gateway);
};

const deleteGatewayRow = (gateway) => {
  requestGatewayDelete(gateway);
};

const confirmGatewayDelete = async () => {
  try {
    const gateway = gatewayToDelete.value;
    if (!gateway || !gateway.id) {
      notify.error('Gateways', 'Gateway inválido.');
      return;
    }
    const gatewayType = gateway.gateway_type || activeGateway.value;
    if (gatewayType === 'video') {
      await stopVideoPreview({ remote: true, silent: true, gatewayId: gateway.id });
    }
    const res = await api.delete(`/setup_app/api/gateways/${gateway.id}/`);
    if (res.success) {
      notify.success('Gateways', res.message || 'Gateway removido.');
      await fetchGateways();
      if (showGatewayModal.value) {
        closeGatewayModal();
      }
    } else {
      notify.error('Gateways', res.message || 'Erro ao remover gateway.');
    }
  } catch (e) {
    notify.error('Gateways', e.message || 'Erro ao remover gateway.');
  } finally {
    gatewayToDelete.value = null;
  }
};

const requestWhatsappQrReset = () => {
  if (!whatsappGatewayForm.value.id) {
    notify.error('WhatsApp', 'Salve o gateway antes de resetar a sessão.');
    return;
  }
  showWhatsappResetConfirm.value = true;
};

const testWhatsappMessage = async () => {
  try {
    if (!whatsappGatewayForm.value.id) {
      notify.error('WhatsApp', 'Salve o gateway antes de testar o envio.');
      return;
    }
    const recipient = (whatsappGatewayForm.value.config.test_recipient || '').trim();
    const message = (whatsappGatewayForm.value.config.test_message || '').trim();
    if (!recipient) {
      notify.error('WhatsApp', 'Informe o telefone de teste.');
      return;
    }
    if (!message) {
      notify.error('WhatsApp', 'Informe a mensagem de teste.');
      return;
    }
    const res = await api.post(
      `/setup_app/api/gateways/${whatsappGatewayForm.value.id}/whatsapp/qr/test-message/`,
      {
        recipient,
        message,
        qr_service_url: whatsappGatewayForm.value.config.qr_service_url,
      }
    );
    if (res.success) {
      notify.success('WhatsApp', res.message || 'Mensagem enviada.');
    } else {
      notify.error('WhatsApp', res.message || 'Falha ao enviar mensagem.');
    }
  } catch (e) {
    notify.error('WhatsApp', e.message || 'Falha ao enviar mensagem.');
  }
};

const confirmWhatsappQrReset = async () => {
  try {
    if (!whatsappGatewayForm.value.id) {
      notify.error('WhatsApp', 'Salve o gateway antes de resetar a sessão.');
      return;
    }
    stopWhatsappQrPolling();
    const res = await api.post(
      `/setup_app/api/gateways/${whatsappGatewayForm.value.id}/whatsapp/qr/reset/`,
      { qr_service_url: whatsappGatewayForm.value.config.qr_service_url }
    );
    if (res.success) {
      whatsappGatewayForm.value.config.qr_status = res.qr_status || 'pending';
      whatsappGatewayForm.value.config.qr_image_url = '';
      notify.success('WhatsApp', res.message || 'Sessão resetada.');
      await generateWhatsappQr();
    } else {
      notify.error('WhatsApp', res.message || 'Erro ao resetar sessão.');
    }
  } catch (e) {
    notify.error('WhatsApp', e.message || 'Erro ao resetar sessão.');
  } finally {
    showWhatsappResetConfirm.value = false;
  }
};

const getWhatsappQrStatusLabel = (status) => {
  if (status === 'connected') return 'Conectado';
  if (status === 'connecting') return 'Conectando';
  if (status === 'awaiting_qr') return 'Aguardando QR';
  if (status === 'disconnected') return 'Desconectado';
  if (status === 'reset') return 'Sessão resetada';
  return 'Aguardando QR';
};

const getWhatsappQrStatusClass = (status) => {
  if (status === 'connected') return 'border-emerald-500/40 text-emerald-300 bg-emerald-500/10';
  if (status === 'disconnected') return 'border-red-500/40 text-red-300 bg-red-500/10';
  if (status === 'connecting') return 'border-blue-500/40 text-blue-300 bg-blue-500/10';
  return 'border-amber-500/40 text-amber-300 bg-amber-500/10';
};

const whatsappQrStatusLabel = computed(() =>
  getWhatsappQrStatusLabel(whatsappGatewayForm.value.config.qr_status)
);

const whatsappQrStatusClass = computed(() =>
  getWhatsappQrStatusClass(whatsappGatewayForm.value.config.qr_status)
);

const updateWhatsappQrState = (payload) => {
  if (!payload) return;
  if (payload.qr_status) {
    whatsappGatewayForm.value.config.qr_status = payload.qr_status;
  }
  if (payload.qr_image_url) {
    whatsappGatewayForm.value.config.qr_image_url = payload.qr_image_url;
  } else if (payload.qr_image_url === '') {
    whatsappGatewayForm.value.config.qr_image_url = '';
  }
  if (
    payload.qr_status === 'disconnected' &&
    !whatsappGatewayForm.value.config.qr_image_url
  ) {
    whatsappQrAutoTriggered.value = false;
  }
};

const generateWhatsappQr = async () => {
  try {
    if (!whatsappGatewayForm.value.id) {
      notify.error('WhatsApp', 'Salve o gateway antes de gerar o QR.');
      return;
    }
    stopWhatsappQrPolling();
    const res = await api.post(
      `/setup_app/api/gateways/${whatsappGatewayForm.value.id}/whatsapp/qr/`,
      {
        qr_service_url: whatsappGatewayForm.value.config.qr_service_url,
      }
    );
    if (res.success) {
      updateWhatsappQrState(res);
      notify.success('WhatsApp', res.message || 'QR gerado.');
      startWhatsappQrPolling();
    } else {
      notify.error('WhatsApp', res.message || 'Erro ao gerar QR.');
    }
  } catch (e) {
    notify.error('WhatsApp', e.message || 'Erro ao gerar QR.');
  }
};

const refreshWhatsappQr = async () => {
  try {
    if (!whatsappGatewayForm.value.id) {
      notify.error('WhatsApp', 'Salve o gateway antes de consultar o status.');
      return;
    }
    const res = await api.get(
      `/setup_app/api/gateways/${whatsappGatewayForm.value.id}/whatsapp/qr/status/`,
      { qr_service_url: whatsappGatewayForm.value.config.qr_service_url }
    );
    if (res.success) {
      updateWhatsappQrState(res);
      const status = res.qr_status || whatsappGatewayForm.value.config.qr_status;
      const reason = res.last_disconnect_reason;
      if (status === 'connected') {
        notify.success('WhatsApp', res.message || 'Conectado.');
      } else if (status === 'awaiting_qr' || status === 'connecting') {
        notify.info('WhatsApp', res.message || 'Aguardando QR.');
      } else if (reason === 515 || reason === '515') {
        notify.info('WhatsApp', 'Reconectando, gerando novo QR.');
        if (!whatsappGatewayForm.value.config.qr_image_url) {
          maybeAutoStartWhatsappQr();
        }
      } else {
        const extra = res.last_disconnect_message ? ` ${res.last_disconnect_message}` : '';
        notify.warning('WhatsApp', `${res.message || 'Desconectado.'}${extra}`);
      }
    } else {
      notify.error('WhatsApp', res.message || 'Erro ao consultar status.');
    }
  } catch (e) {
    notify.error('WhatsApp', e.message || 'Erro ao consultar status.');
  }
};

const disconnectWhatsappQr = async () => {
  try {
    if (!whatsappGatewayForm.value.id) {
      notify.error('WhatsApp', 'Salve o gateway antes de desconectar.');
      return;
    }
    stopWhatsappQrPolling();
    const res = await api.post(
      `/setup_app/api/gateways/${whatsappGatewayForm.value.id}/whatsapp/qr/disconnect/`,
      { qr_service_url: whatsappGatewayForm.value.config.qr_service_url }
    );
    if (res.success) {
      whatsappGatewayForm.value.config.qr_status = res.qr_status || 'disconnected';
      whatsappGatewayForm.value.config.qr_image_url = '';
      notify.success('WhatsApp', res.message || 'Desconectado.');
    } else {
      notify.error('WhatsApp', res.message || 'Erro ao desconectar.');
    }
  } catch (e) {
    notify.error('WhatsApp', e.message || 'Erro ao desconectar.');
  }
};

const startWhatsappQrPolling = () => {
  if (
    !showGatewayModal.value ||
    activeGateway.value !== 'whatsapp' ||
    whatsappGatewayForm.value.config.auth_mode !== 'qr' ||
    !whatsappGatewayForm.value.id
  ) {
    stopWhatsappQrPolling();
    return;
  }
  if (qrPollingHandle.value) return;
  qrPollingHandle.value = setInterval(() => {
    refreshWhatsappQr();
  }, 15000);
};

const whatsappQrAutoTriggered = ref(false);

const maybeAutoStartWhatsappQr = async () => {
  if (whatsappQrAutoTriggered.value) return;
  if (
    !showGatewayModal.value ||
    activeGateway.value !== 'whatsapp' ||
    whatsappGatewayForm.value.config.auth_mode !== 'qr' ||
    !whatsappGatewayForm.value.id
  ) {
    return;
  }
  const status = whatsappGatewayForm.value.config.qr_status;
  const hasQr = !!whatsappGatewayForm.value.config.qr_image_url;
  if (status !== 'connected' && (!hasQr || status === 'disconnected')) {
    whatsappQrAutoTriggered.value = true;
    await generateWhatsappQr();
  }
};

watch(
  [
    showGatewayModal,
    activeGateway,
    () => whatsappGatewayForm.value.config.auth_mode,
    () => whatsappGatewayForm.value.id,
  ],
  () => {
    if (
      showGatewayModal.value &&
      activeGateway.value === 'whatsapp' &&
      whatsappGatewayForm.value.config.auth_mode === 'qr'
    ) {
      startWhatsappQrPolling();
      if (whatsappGatewayForm.value.id) {
        refreshWhatsappQr();
      }
      maybeAutoStartWhatsappQr();
    } else {
      stopWhatsappQrPolling();
      whatsappQrAutoTriggered.value = false;
    }
  }
);

onBeforeUnmount(() => {
  stopWhatsappQrPolling();
  stopVideoPreview({ remote: true, silent: true });
});

const openSmtpOauthFilePicker = () => {
  if (smtpOauthFileInput.value) {
    smtpOauthFileInput.value.value = '';
    smtpOauthFileInput.value.click();
  }
};

const applySmtpOauthJson = () => {
  if (!smtpOauthJson.value.trim()) {
    notify.error('SMTP OAuth', 'Cole o JSON do OAuth para aplicar.');
    return;
  }
  try {
    const data = JSON.parse(smtpOauthJson.value);
    const root = data.installed || data.web || data;
    if (root.client_id) configForm.value.SMTP_OAUTH_CLIENT_ID = root.client_id;
    if (root.client_secret) configForm.value.SMTP_OAUTH_CLIENT_SECRET = root.client_secret;
    if (data.refresh_token) configForm.value.SMTP_OAUTH_REFRESH_TOKEN = data.refresh_token;
    notify.success('SMTP OAuth', 'JSON aplicado com sucesso.');
  } catch (e) {
    notify.error('SMTP OAuth', 'JSON inválido. Verifique o conteúdo.');
  }
};

const handleSmtpOauthFileUpload = async (event) => {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    smtpOauthJson.value = text.trim();
    applySmtpOauthJson();
  } catch (e) {
    notify.error('SMTP OAuth', 'Não foi possível ler o JSON.');
  }
};

const startGdriveOAuth = async () => {
  try {
    const payload = {
      gdrive_oauth_client_id: configForm.value.GDRIVE_OAUTH_CLIENT_ID,
      gdrive_oauth_client_secret: configForm.value.GDRIVE_OAUTH_CLIENT_SECRET,
    };
    const res = await api.post('/setup_app/api/gdrive/oauth/start/', payload);
    if (res.success && res.auth_url) {
      window.open(res.auth_url, '_blank', 'noopener,noreferrer');
    } else {
      notify.error('Google Drive', res.message || 'Erro ao iniciar OAuth.');
    }
  } catch (e) { notify.error('Google Drive', e.message || 'Erro ao iniciar OAuth.'); }
};

const openGdriveFilePicker = () => {
  if (gdriveFileInput.value) {
    gdriveFileInput.value.value = '';
    gdriveFileInput.value.click();
  }
};

const handleGdriveFileUpload = async (event) => {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  try {
    const text = await file.text();
    JSON.parse(text);
    configForm.value.GDRIVE_CREDENTIALS_JSON = text.trim();
    gdriveJsonLocked.value = true;
    notify.success('Google Drive', 'JSON importado com sucesso.');
  } catch (e) {
    notify.error('Google Drive', 'JSON inválido. Verifique o arquivo.');
  }
};

const fetchServers = async () => {
  try {
    const res = await api.get('/setup_app/api/monitoring-servers/');
    servers.value = res.servers || [];
  } catch (e) { console.error(e); }
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
    serverForm.value = { name: '', server_type: 'zabbix', url: '', auth_token: '', is_active: true, extra_config_text: '{}' };
  }
  showServerModal.value = true;
};

const saveServer = async () => {
  let extraConfig = {};
  try {
    extraConfig = serverForm.value.extra_config_text ? JSON.parse(serverForm.value.extra_config_text) : {};
  } catch (e) {
    notify.error('Servidores', 'JSON inválido.');
    return;
  }
  const payload = { ...serverForm.value, extra_config: extraConfig };
  try {
    if (editingServer.value) {
      await api.patch(`/setup_app/api/monitoring-servers/${editingServer.value.id}/`, payload);
      notify.success('Servidores', 'Atualizado!');
    } else {
      await api.post('/setup_app/api/monitoring-servers/', payload);
      notify.success('Servidores', 'Criado!');
    }
    showServerModal.value = false;
    fetchServers();
  } catch (e) { notify.error('Servidores', 'Erro ao salvar servidor.'); }
};

const deleteServer = async (id) => {
  if (!confirm('Remover servidor?')) return;
  try {
    await api.delete(`/setup_app/api/monitoring-servers/${id}/`);
    fetchServers();
  } catch (e) { notify.error('Servidores', 'Erro ao remover.'); }
};


const fetchBackups = async () => {
  try {
    const res = await api.get('/setup_app/api/backups/');
    backups.value = res.backups || [];
    backupSettings.value = res.settings || backupSettings.value;
  } catch (e) { console.error(e); }
};

const createBackup = async () => {
  backupLoading.value = true;
  try {
    const res = await api.post('/setup_app/api/backups/', {});
    if (res.success) {
      notify.success('Backups', 'Backup iniciado!');
      if (res.gdrive_upload && res.gdrive_upload.success) {
        notify.success('Google Drive', res.gdrive_upload.message || 'Backup enviado.');
      } else if (res.gdrive_upload && res.gdrive_upload.success === false && res.gdrive_upload.message && configForm.value.GDRIVE_ENABLED) {
        notify.warning('Google Drive', res.gdrive_upload.message);
      }
      if (res.ftp_upload && res.ftp_upload.success) {
        notify.success('FTP', res.ftp_upload.message || 'Backup enviado.');
      } else if (res.ftp_upload && res.ftp_upload.success === false && res.ftp_upload.message && configForm.value.FTP_ENABLED) {
        notify.warning('FTP', res.ftp_upload.message);
      }
      setTimeout(fetchBackups, 2000);
    } else { notify.error('Backups', res.message); }
  } catch (e) { notify.error('Backups', 'Erro ao criar backup'); } 
  finally { backupLoading.value = false; }
};

const restoreBackup = async (file) => {
  if (!confirm(`Restaurar ${file.name}?`)) return;
  try {
    const res = await api.post('/setup_app/api/backups/restore/', { filename: file.name });
    if (res.success) notify.success('Backups', 'Restauração iniciada.');
    else notify.error('Backups', 'Erro ao restaurar.');
  } catch (e) { notify.error('Backups', 'Erro ao restaurar.'); }
};

const deleteBackup = async (file) => {
  if (!confirm(`Excluir ${file.name}?`)) return;
  try {
    const res = await api.post('/setup_app/api/backups/delete/', { filename: file.name });
    if (res.success) {
      notify.success('Backups', 'Removido.');
      fetchBackups();
    } else { notify.error('Backups', 'Erro ao excluir.'); }
  } catch (e) { notify.error('Backups', 'Erro ao excluir.'); }
};

const uploadBackupToCloud = async (file) => {
  try {
    const res = await api.post('/setup_app/api/backups/upload-cloud/', { filename: file.name });
    if (res.success) {
      notify.success('Backups', 'Envio iniciado.');
      if (res.gdrive_upload && res.gdrive_upload.success) {
        notify.success('Google Drive', res.gdrive_upload.message || 'Backup enviado.');
      } else if (res.gdrive_upload && res.gdrive_upload.success === false && res.gdrive_upload.message && configForm.value.GDRIVE_ENABLED) {
        notify.warning('Google Drive', res.gdrive_upload.message);
      }
      if (res.ftp_upload && res.ftp_upload.success) {
        notify.success('FTP', res.ftp_upload.message || 'Backup enviado.');
      } else if (res.ftp_upload && res.ftp_upload.success === false && res.ftp_upload.message && configForm.value.FTP_ENABLED) {
        notify.warning('FTP', res.ftp_upload.message);
      }
    } else {
      notify.error('Backups', res.message || 'Falha no envio.');
    }
  } catch (e) {
    notify.error('Backups', 'Erro ao enviar para nuvem.');
  }
};

const saveBackupSettings = async () => {
  try {
    await api.post('/setup_app/api/backups/settings/', {
      retention_days: backupSettings.value.retention_days,
      retention_count: backupSettings.value.retention_count,
    });
    notify.success('Backups', 'Retenção salva.');
    fetchBackups();
  } catch (e) { notify.error('Backups', 'Erro ao salvar retenção.'); }
};

const handleUploadBackup = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('file', file);
  try {
    const res = await api.postFormData('/setup_app/api/backups/', formData);
    if (res.success) {
      notify.success('Backups', 'Upload OK!');
      fetchBackups();
    } else { notify.error('Backups', 'Erro upload.'); }
  } catch (e) { notify.error('Backups', 'Erro upload.'); }
  finally { event.target.value = ''; }
};

const exportConfig = () => window.location.href = '/setup_app/api/export/';

const handleImportConfig = async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const formData = new FormData();
  formData.append('config_file', file);
  try {
    const res = await api.postFormData('/setup_app/api/import/', formData);
    if (res.success) {
      notify.success('Configurações', 'Importado!');
      fetchConfiguration();
    } else { notify.error('Configurações', 'Erro importação.'); }
  } catch (e) { notify.error('Configurações', 'Erro importação.'); }
  finally { event.target.value = ''; }
};

const openHistory = async () => {
  try {
    const res = await api.get('/setup_app/api/audit-history/?limit=100');
    auditEntries.value = res.audits || [];
    showHistory.value = true;
  } catch (e) { notify.error('Auditoria', 'Erro histórico.'); }
};

const closeHistory = () => showHistory.value = false;

const formatSize = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatDate = (iso) => iso ? new Date(iso).toLocaleString('pt-BR') : '-';

onMounted(() => {
  fetchConfiguration();
  fetchServers();
  fetchBackups();
  fetchGateways();
});
</script>

<style scoped>
/* ESTILO PADRÃO (Clean Form) */

.label-custom {
  @apply block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5;
}

/* Input Branco Puro no Light Mode, Cinza Escuro no Dark Mode */
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

.input-custom--prefixed {
  padding-left: 4rem;
}

/* Botões com ícones e sombra */
.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200;
}

.btn-secondary {
  @apply inline-flex items-center justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-gray-700 transition-all duration-200;
}

.btn-white {
  @apply inline-flex items-center rounded-md bg-white px-2.5 py-1.5 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:ring-gray-600 dark:hover:bg-gray-700 transition-all;
}

/* Cards de Resumo */
.stat-card {
  @apply p-4 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col;
}
.stat-label {
  @apply text-xs font-semibold text-gray-500 uppercase tracking-wide;
}
.stat-value {
  @apply text-lg font-bold;
}

/* Scrollbar */
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

/* Animations */
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
