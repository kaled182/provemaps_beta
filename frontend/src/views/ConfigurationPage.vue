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
          <input type="file" class="hidden" @change="handleImportConfig" accept=".json">
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

        <div v-if="activeTab === 'general'" class="space-y-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-100 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/50">
              <h3 class="text-sm font-bold text-gray-900 dark:text-white uppercase tracking-wide">Status Operacional</h3>
            </div>
            <div class="p-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              <div class="stat-card group">
                <div class="flex items-center justify-between">
                  <span class="stat-label">Zabbix API</span>
                  <svg class="w-5 h-5 text-gray-300 group-hover:text-blue-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                </div>
                <span class="stat-value text-blue-600 dark:text-blue-400 mt-2 truncate" :title="configForm.ZABBIX_API_URL">
                  {{ configForm.ZABBIX_API_URL ? 'Conectado' : 'Pendente' }}
                </span>
                <span class="text-xs text-gray-400 truncate mt-1 block">{{ configForm.ZABBIX_API_URL || '--' }}</span>
              </div>

              <div class="stat-card group">
                <div class="flex items-center justify-between">
                  <span class="stat-label">Banco de Dados</span>
                  <svg class="w-5 h-5 text-gray-300 group-hover:text-purple-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/></svg>
                </div>
                <span class="stat-value text-purple-600 dark:text-purple-400 mt-2">{{ configForm.DB_HOST || 'localhost' }}</span>
                <span class="text-xs text-gray-400">PostgreSQL / PostGIS</span>
              </div>

              <div class="stat-card group">
                <div class="flex items-center justify-between">
                  <span class="stat-label">Mapas</span>
                  <svg class="w-5 h-5 text-gray-300 group-hover:text-green-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>
                </div>
                <span class="stat-value text-green-600 dark:text-green-400 mt-2 uppercase">{{ configForm.MAP_PROVIDER || 'Google' }}</span>
                <span class="text-xs text-gray-400">Provedor Ativo</span>
              </div>

              <div class="stat-card group">
                <div class="flex items-center justify-between">
                  <span class="stat-label">Snapshots</span>
                  <svg class="w-5 h-5 text-gray-300 group-hover:text-orange-500 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2"/></svg>
                </div>
                <span class="stat-value text-gray-900 dark:text-white mt-2">{{ backups.length }}</span>
                <span class="text-xs text-gray-400">Arquivos Salvos</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="activeTab === 'monitoring'" class="space-y-6">
          
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

        <div v-if="activeTab === 'maps'" class="space-y-6">
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

        <div v-if="activeTab === 'system'" class="space-y-6">
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
                  <input v-model="configForm.DEBUG" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500 h-4 w-4">
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
                    <input v-model="configForm.DB_USER" type="text" class="input-custom font-mono" autocomplete="off">
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

        <div v-if="activeTab === 'backups'" class="space-y-6">
          <div class="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
            <div class="p-6 border-b border-gray-200 dark:border-gray-700 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <h2 class="text-lg font-bold text-gray-900 dark:text-white">Snapshots do Banco</h2>
                <p class="text-sm text-gray-500 dark:text-gray-400">Backups de segurança do PostGIS (Geoespacial).</p>
              </div>
              
              <div class="flex flex-wrap gap-3">
                <label class="btn-white cursor-pointer">
                  <input type="file" class="hidden" @change="handleUploadBackup" accept=".zip">
                  <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/></svg>
                  Upload Externo
                </label>
                <button @click="showBackupConfig = true" class="btn-white">
                  <svg class="w-4 h-4 mr-2 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11.983 5.25a2.25 2.25 0 013.182 0l3.585 3.585a2.25 2.25 0 010 3.182l-6.592 6.592a2.25 2.25 0 01-1.591.659H7.5A2.25 2.25 0 015.25 17.5v-2.067c0-.597.237-1.17.659-1.592l6.592-6.591z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 7l8 8"/></svg>
                  Configurar
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
                <input v-model="backupSettings.retention_days" type="number" class="input-custom mt-1">
              </div>
              <div class="w-full sm:w-32">
                <label class="label-custom">Max Arquivos</label>
                <input v-model="backupSettings.retention_count" type="number" class="input-custom mt-1">
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
                <input v-model="serverForm.name" type="text" class="input-custom mt-1" placeholder="Ex: Zabbix Core">
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
                <input v-model="serverForm.url" type="url" class="input-custom mt-1" placeholder="http://10.0.0.1/api">
              </div>
              <div>
                <label class="label-custom">Token / Chave</label>
                <input v-model="serverForm.auth_token" type="password" class="input-custom mt-1">
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

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useNotification } from '@/composables/useNotification';
import { useApi } from '@/composables/useApi';

const Icons = {
  Cog: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
  Server: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 00-2-2m-2-4h.01M17 16h.01"/></svg>' },
  Map: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/></svg>' },
  Terminal: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>' },
  Database: { template: '<svg fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/></svg>' },
};

const notify = useNotification();
const api = useApi();
const activeTab = ref('general');
const showHistory = ref(false);
const auditEntries = ref([]);

const navItems = [
  { id: 'general', label: 'Geral', icon: Icons.Cog },
  { id: 'monitoring', label: 'Monitoramento', icon: Icons.Server },
  { id: 'maps', label: 'Mapas', icon: Icons.Map },
  { id: 'system', label: 'Sistema', icon: Icons.Terminal },
  { id: 'backups', label: 'Backups', icon: Icons.Database },
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
});

const servers = ref([]);
const showServerModal = ref(false);
const editingServer = ref(null);
const serverForm = ref({ name: '', server_type: 'zabbix', url: '', auth_token: '', is_active: true, extra_config_text: '{}' });
const backups = ref([]);
const backupLoading = ref(false);
const backupSettings = ref({ retention_days: '', retention_count: '' });
const showBackupConfig = ref(false);
const backupPasswordSnapshot = ref('');

// API ACTIONS
const fetchConfiguration = async () => {
  try {
    const res = await api.get('/setup_app/api/config/');
    if (res.success && res.configuration) {
      configForm.value = { ...configForm.value, ...res.configuration };
      backupPasswordSnapshot.value = configForm.value.BACKUP_ZIP_PASSWORD || '';
    }
  } catch (e) { console.error(e); }
};

const saveConfiguration = async () => {
  try {
    const res = await api.post('/setup_app/api/config/update/', configForm.value);
    notify.success('Configurações', res.message || 'Configurações salvas!');
    if (res.backup_warning) {
      notify.warning('Backups', res.backup_message || 'Backup não gerado automaticamente.');
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
