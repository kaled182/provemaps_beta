<template>
  <div class="space-y-6 relative">
    <!-- Loading Overlay -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>

    <!-- Servidores Header -->
    <div class="flex items-start justify-between">
      <div>
        <h3 class="text-lg font-semibold text-gray-900 dark:text-white">Servidores de Monitoramento</h3>
        <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
          {{ serverCount?.total || 0 }} {{ (serverCount?.total || 0) === 1 ? 'servidor' : 'servidores' }} configurado{{ (serverCount?.total || 0) !== 1 ? 's' : '' }}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <div class="relative" ref="configMenuRef">
          <button
            type="button"
            class="btn-secondary flex items-center gap-2"
            @click="toggleConfigMenu"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
            <span>Configurações</span>
            <svg
              class="w-3 h-3 transition-transform"
              :class="showConfigMenu ? 'rotate-180' : 'rotate-0'"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <transition name="fade-scale">
            <div
              v-if="showConfigMenu"
              class="absolute right-0 mt-2 w-[600px] max-w-[calc(100vw-32px)] rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-xl z-50"
            >
              <div class="p-5 space-y-4">
                <div>
                  <h4 class="text-base font-semibold text-gray-900 dark:text-white">
                    Limites de Sinal Óptico por Distância
                  </h4>
                  <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                    O sistema detecta a categoria do enlace pelo comprimento do cabo no mapa e aplica os limites correspondentes. Valores em dBm (negativos).
                  </p>
                </div>

                <form @submit.prevent="saveOpticalThresholds">
                  <!-- Per-distance table -->
                  <div class="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
                    <table class="w-full text-sm">
                      <thead>
                        <tr class="bg-gray-50 dark:bg-gray-700/50">
                          <th class="text-left px-3 py-2 text-xs font-semibold text-gray-600 dark:text-gray-400 w-36">
                            Categoria SFP
                          </th>
                          <th class="text-center px-3 py-2 text-xs font-semibold text-amber-600 dark:text-amber-400">
                            Atenção (dBm)
                          </th>
                          <th class="text-center px-3 py-2 text-xs font-semibold text-red-600 dark:text-red-400">
                            Crítico (dBm)
                          </th>
                          <th class="text-left px-3 py-2 text-xs font-semibold text-gray-500 dark:text-gray-500">
                            Cor no mapa
                          </th>
                        </tr>
                      </thead>
                      <tbody class="divide-y divide-gray-100 dark:divide-gray-700">
                        <tr v-for="cat in distanceCategories" :key="cat.key" class="hover:bg-gray-50 dark:hover:bg-gray-700/30">
                          <td class="px-3 py-2">
                            <div class="font-medium text-gray-900 dark:text-white text-xs">{{ cat.label }}</div>
                            <div class="text-xs text-gray-500 dark:text-gray-500">{{ cat.description }}</div>
                          </td>
                          <td class="px-3 py-2">
                            <div class="relative">
                              <input
                                v-model="distanceThresholds[cat.key].warning"
                                type="number"
                                step="0.1"
                                class="input-custom pr-10 text-center text-sm py-1.5"
                                autocomplete="off"
                              />
                              <span class="absolute inset-y-0 right-2 flex items-center text-xs text-gray-400">dBm</span>
                            </div>
                          </td>
                          <td class="px-3 py-2">
                            <div class="relative">
                              <input
                                v-model="distanceThresholds[cat.key].critical"
                                type="number"
                                step="0.1"
                                class="input-custom pr-10 text-center text-sm py-1.5"
                                autocomplete="off"
                              />
                              <span class="absolute inset-y-0 right-2 flex items-center text-xs text-gray-400">dBm</span>
                            </div>
                          </td>
                          <td class="px-3 py-2">
                            <div class="flex items-center gap-1.5 text-xs">
                              <span class="inline-block w-3 h-3 rounded-full bg-green-500 flex-shrink-0"></span>
                              <span class="text-gray-500 dark:text-gray-400">&gt; {{ distanceThresholds[cat.key].warning }} verde</span>
                            </div>
                            <div class="flex items-center gap-1.5 text-xs mt-0.5">
                              <span class="inline-block w-3 h-3 rounded-full bg-amber-400 flex-shrink-0"></span>
                              <span class="text-gray-500 dark:text-gray-400">{{ distanceThresholds[cat.key].critical }} … {{ distanceThresholds[cat.key].warning }} âmbar</span>
                            </div>
                            <div class="flex items-center gap-1.5 text-xs mt-0.5">
                              <span class="inline-block w-3 h-3 rounded-full bg-red-500 flex-shrink-0"></span>
                              <span class="text-gray-500 dark:text-gray-400">&lt; {{ distanceThresholds[cat.key].critical }} vermelho</span>
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <p class="text-xs text-gray-500 dark:text-gray-500 mt-2">
                    Sinal nulo ou zero é sempre classificado como crítico (vermelho), independente da distância.
                  </p>

                  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between mt-3">
                    <button type="button" class="btn-secondary text-xs" @click="restoreOpticalDefaults">
                      Restaurar padrões industriais
                    </button>
                    <div class="flex gap-3">
                      <button
                        type="button"
                        class="btn-secondary"
                        :disabled="savingThresholds"
                        @click="reloadOpticalThresholds"
                      >
                        Recarregar
                      </button>
                      <button type="submit" class="btn-primary" :disabled="savingThresholds">
                        <svg
                          v-if="savingThresholds"
                          class="animate-spin -ml-1 mr-2 h-4 w-4"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span>Salvar limites</span>
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            </div>
          </transition>
        </div>

        <button @click="handleAddServer" class="btn-primary">
          <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
          </svg>
          Adicionar Servidor
        </button>
      </div>
    </div>

    <!-- Filter Tabs -->
    <div class="border-b border-gray-200 dark:border-gray-700">
      <nav class="-mb-px flex space-x-8">
        <button 
          v-for="filter in filters" 
          :key="filter.key"
          @click="activeFilter = filter.key"
          class="whitespace-nowrap pb-4 px-1 border-b-2 font-medium text-sm transition-colors"
          :class="activeFilter === filter.key 
            ? 'border-primary-500 text-primary-600 dark:text-primary-400' 
            : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'"
        >
          {{ filter.label }}
          <span class="ml-2 px-2 py-0.5 rounded-full text-xs" 
                :class="activeFilter === filter.key 
                  ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400' 
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'">
            {{ filter.count }}
          </span>
        </button>
      </nav>
    </div>

    <!-- Server List -->
    <div v-if="showZabbixCard || filteredServers.length > 0" class="grid gap-4">
      <!-- Zabbix Principal Card -->
      <div 
        v-if="showZabbixCard"
        class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3">
              <h4 class="text-base font-semibold text-gray-900 dark:text-white">
                Zabbix Principal
              </h4>
              <span 
                class="px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="zabbixUrl 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'"
              >
                {{ zabbixUrl ? 'Configurado' : 'Não configurado' }}
              </span>
              <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                Zabbix (Principal)
              </span>
            </div>
            
            <div class="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
              <p><span class="font-medium">URL:</span> {{ zabbixUrl || 'Não configurado' }}</p>
              <p v-if="zabbixUser"><span class="font-medium">Usuário:</span> {{ zabbixUser }}</p>
            </div>
          </div>

          <div class="flex items-center gap-2 ml-4">
            <button 
              @click="handleTestZabbix"
              :disabled="testingZabbix"
              class="btn-icon"
              title="Testar Zabbix"
            >
              <svg v-if="testingZabbix" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
            </button>
            <button 
              @click="openZabbixModal"
              class="btn-icon"
              title="Configurar Zabbix"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
            </button>
          </div>
        </div>

        <div v-if="zabbixTestResult" class="mt-3 p-3 rounded-md text-sm"
             :class="zabbixTestResult.success 
               ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
               : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400'">
          {{ zabbixTestResult.message }}
          <span v-if="zabbixTestResult.version" class="ml-2 text-xs opacity-80">(v{{ zabbixTestResult.version }})</span>
        </div>
      </div>

      <!-- Additional Servers -->
      <div 
        v-for="server in filteredServers" 
        :key="server.id"
        class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-5 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-3">
              <h4 class="text-base font-semibold text-gray-900 dark:text-white">
                {{ server.name }}
              </h4>
              <span 
                class="px-2.5 py-0.5 rounded-full text-xs font-medium"
                :class="server.is_active 
                  ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' 
                  : 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'"
              >
                {{ server.is_active ? 'Ativo' : 'Inativo' }}
              </span>
              <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                {{ serverTypeLabel(server.server_type) }}
              </span>
            </div>
            
            <div class="mt-2 space-y-1 text-sm text-gray-600 dark:text-gray-400">
              <p><span class="font-medium">URL:</span> {{ server.url }}</p>
              <p v-if="server.description" class="text-gray-500 dark:text-gray-500">{{ server.description }}</p>
            </div>
          </div>

          <div class="flex items-center gap-2 ml-4">
            <button 
              @click="handleTestConnection(server)" 
              :disabled="testing[server.id]"
              class="btn-icon"
              title="Testar Conexão"
            >
              <svg v-if="testing[server.id]" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
              </svg>
            </button>
            
            <button 
              @click="handleToggleStatus(server)" 
              class="btn-icon"
              :title="server.is_active ? 'Desativar' : 'Ativar'"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="server.is_active ? 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z' : 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'"/>
              </svg>
            </button>

            <button 
              @click="handleEditServer(server)" 
              class="btn-icon"
              title="Editar"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
            </button>

            <button 
              @click="handleDeleteServer(server)" 
              class="btn-icon text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
              title="Excluir"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Connection Test Result -->
        <div v-if="serverTestResults[server.id]" class="mt-3 p-3 rounded-md text-sm"
             :class="serverTestResults[server.id].success 
               ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
               : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400'">
          {{ serverTestResults[server.id].message }}
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="text-center py-12 bg-gray-50 dark:bg-gray-800/50 rounded-lg border-2 border-dashed border-gray-300 dark:border-gray-700">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"/>
      </svg>
      <p class="mt-2 text-sm text-gray-600 dark:text-gray-400">Nenhum servidor configurado</p>
      <button @click="handleAddServer" class="mt-4 btn-primary">
        Adicionar Primeiro Servidor
      </button>
    </div>

    <!-- Edit/Add Modal -->
    <ServerEditModal 
      v-if="showModal" 
      :server="editingServer"
      @close="showModal = false"
      @save="handleSaveServer"
    />

    <!-- Zabbix Config Modal -->
    <teleport to="body">
      <div v-if="showZabbixModal" class="fixed inset-0 z-50 overflow-y-auto">
        <div class="flex min-h-screen items-center justify-center p-4">
          <!-- Backdrop -->
          <div class="fixed inset-0 bg-black/50 dark:bg-black/70 transition-opacity" @click="showZabbixModal = false"></div>

          <!-- Modal -->
          <div class="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full p-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-white">
                Configurar Zabbix Principal
              </h3>
              <button @click="showZabbixModal = false" class="text-gray-400 hover:text-gray-500">
                <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
                </svg>
              </button>
            </div>

            <form @submit.prevent="saveZabbixConfig" class="space-y-4">
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="label-custom">Nome *</label>
                  <input 
                    v-model="zabbixForm.name" 
                    type="text" 
                    class="input-custom" 
                    placeholder="Ex: Zabbix Principal"
                    autocomplete="off"
                    required
                  />
                </div>

                <div>
                  <label class="label-custom">Tipo *</label>
                  <select v-model="zabbixForm.type" class="input-custom" required>
                    <option value="zabbix">Zabbix</option>
                  </select>
                </div>
              </div>

              <div>
                <label class="label-custom">URL *</label>
                <input 
                  v-model="zabbixForm.url" 
                  type="text" 
                  class="input-custom" 
                  placeholder="https://zabbix.example.com"
                  autocomplete="off"
                  required
                />
              </div>

              <div class="grid grid-cols-2 gap-4">
                <div>
                  <label class="label-custom">Usuário</label>
                  <input 
                    v-model="zabbixForm.username" 
                    type="text" 
                    class="input-custom" 
                    placeholder="Admin"
                    autocomplete="off"
                  />
                </div>

                <div>
                  <label class="label-custom">Senha</label>
                  <input 
                    v-model="zabbixForm.password" 
                    type="password" 
                    class="input-custom"
                    autocomplete="off"
                  />
                </div>
              </div>

              <div>
                <label class="label-custom">API Key (alternativa)</label>
                <input 
                  v-model="zabbixForm.api_key" 
                  type="text" 
                  class="input-custom" 
                  placeholder="Token de API (opcional)"
                  autocomplete="off"
                />
                <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Use API Key ou Usuário/Senha, não ambos
                </p>
              </div>

              <div>
                <label class="label-custom">Descrição</label>
                <textarea 
                  v-model="zabbixForm.description" 
                  class="input-custom resize-none" 
                  rows="3"
                  placeholder="Descrição opcional do servidor"
                ></textarea>
              </div>

              <div>
                <label class="label-custom">Configurações Extras (JSON)</label>
                <textarea 
                  v-model="zabbixForm.config_json" 
                  class="input-custom font-mono text-xs resize-none" 
                  rows="4"
                  placeholder='{"timeout": 30, "verify_ssl": true}'
                ></textarea>
              </div>

              <div v-if="zabbixTestResult" class="p-3 rounded-md text-sm"
                   :class="zabbixTestResult.success 
                     ? 'bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400' 
                     : 'bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400'">
                {{ zabbixTestResult.message }}
                <span v-if="zabbixTestResult.version" class="ml-2 text-xs opacity-80">(v{{ zabbixTestResult.version }})</span>
              </div>

              <div class="flex items-center">
                <input 
                  v-model="zabbixForm.is_active" 
                  type="checkbox" 
                  id="zabbix-active"
                  class="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500 dark:focus:ring-blue-600 dark:ring-offset-gray-800 focus:ring-2 dark:bg-gray-700 dark:border-gray-600"
                />
                <label for="zabbix-active" class="ml-2 text-sm font-medium text-gray-700 dark:text-gray-300">
                  Servidor ativo
                </label>
              </div>

              <div class="flex justify-between gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
                <button type="button" @click="clearZabbixForm" class="btn-secondary text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20">
                  Limpar Dados
                </button>
                <div class="flex gap-3">
                  <button type="button" @click="handleTestZabbix" :disabled="testingZabbix" class="btn-secondary">
                    <svg v-if="testingZabbix" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Testar Conexão</span>
                  </button>
                  <button type="button" @click="showZabbixModal = false" class="btn-secondary">
                    Cancelar
                  </button>
                  <button type="submit" :disabled="savingZabbix" class="btn-primary">
                    <svg v-if="savingZabbix" class="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Salvar
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useServerManagement } from '@/composables/useServerManagement'
import { useSystemConfig } from '@/composables/useSystemConfig'
import { useNotification } from '@/composables/useNotification'
import ServerEditModal from './ServerEditModal.vue'

// Composables
const {
  servers,
  loading,
  activeServers,
  inactiveServers,
  serverCount,
  serversByType,
  loadServers,
  saveServer,
  deleteServer,
  testServerConnection,
  toggleServerStatus,
  createEmptyServerForm,
} = useServerManagement()

const {
  config: systemConfig,
  loadSystemConfig,
  saveSystemConfig,
  testZabbix,
  testingZabbix,
  testResults: systemTestResults,
} = useSystemConfig()

const { error: notifyError } = useNotification()

// Local state
const activeFilter = ref('all')
const showModal = ref(false)
const editingServer = ref(null)
const testing = ref({})
const serverTestResults = ref({})
const showZabbixModal = ref(false)
const savingZabbix = ref(false)
const savingThresholds = ref(false)
const showConfigMenu = ref(false)
const configMenuRef = ref(null)
const zabbixTestResult = computed(() => systemTestResults.value?.zabbix || null)

// Per-distance-category threshold definitions
const distanceCategories = [
  { key: '10',  label: '≤ 10 km',  description: 'SFP LR / curta distância' },
  { key: '40',  label: '≤ 40 km',  description: 'SFP ER / média distância' },
  { key: '80',  label: '≤ 80 km',  description: 'SFP ZR / longa distância' },
  { key: '100', label: '> 80 km',  description: 'DWDM / EZR / ultra-longo' },
]

const DEFAULT_DISTANCE_THRESHOLDS = {
  '10':  { warning: -20.0, critical: -28.0 },
  '40':  { warning: -23.0, critical: -30.0 },
  '80':  { warning: -26.0, critical: -30.0 },
  '100': { warning: -28.0, critical: -35.0 },
}

const distanceThresholds = ref({
  '10':  { warning: -20.0, critical: -28.0 },
  '40':  { warning: -23.0, critical: -30.0 },
  '80':  { warning: -26.0, critical: -30.0 },
  '100': { warning: -28.0, critical: -35.0 },
})

const syncDistanceThresholdsFromConfig = () => {
  const saved = systemConfig.value?.OPTICAL_THRESHOLDS_BY_DISTANCE
  if (saved && typeof saved === 'object') {
    for (const cat of ['10', '40', '80', '100']) {
      if (saved[cat]) {
        distanceThresholds.value[cat] = {
          warning: Number(saved[cat].warning ?? DEFAULT_DISTANCE_THRESHOLDS[cat].warning),
          critical: Number(saved[cat].critical ?? DEFAULT_DISTANCE_THRESHOLDS[cat].critical),
        }
      }
    }
  }
}

const restoreOpticalDefaults = () => {
  for (const cat of ['10', '40', '80', '100']) {
    distanceThresholds.value[cat] = { ...DEFAULT_DISTANCE_THRESHOLDS[cat] }
  }
}

const reloadOpticalThresholds = async () => {
  if (savingThresholds.value) {
    return
  }
  await loadSystemConfig()
  syncDistanceThresholdsFromConfig()
}

const saveOpticalThresholds = async () => {
  // Validate: warning must be > critical for each category
  for (const cat of distanceCategories) {
    const entry = distanceThresholds.value[cat.key]
    const w = Number(entry.warning)
    const c = Number(entry.critical)
    if (!Number.isFinite(w) || !Number.isFinite(c)) {
      notifyError('Monitoramento', `Informe valores numéricos válidos para ${cat.label}.`)
      return
    }
    if (w < c) {
      notifyError('Monitoramento', `Em ${cat.label}: o nível de atenção (${w}) deve ser maior que o crítico (${c}).`)
      return
    }
  }

  savingThresholds.value = true
  try {
    const thresholdsPayload = {}
    for (const cat of ['10', '40', '80', '100']) {
      thresholdsPayload[cat] = {
        warning: Number(distanceThresholds.value[cat].warning),
        critical: Number(distanceThresholds.value[cat].critical),
      }
    }
    systemConfig.value.OPTICAL_THRESHOLDS_BY_DISTANCE = thresholdsPayload
    const saved = await saveSystemConfig()
    if (!saved) {
      notifyError('Monitoramento', 'Não foi possível salvar os limites ópticos.')
    } else {
      showConfigMenu.value = false
    }
  } catch (error) {
    console.error('[MonitoringServersTab] Error saving optical thresholds:', error)
    notifyError('Monitoramento', 'Não foi possível salvar os limites ópticos.')
  } finally {
    savingThresholds.value = false
  }
}

const toggleConfigMenu = () => {
  showConfigMenu.value = !showConfigMenu.value
}

const closeConfigMenu = () => {
  showConfigMenu.value = false
}

const handleOutsideClick = (event) => {
  if (!showConfigMenu.value) {
    return
  }
  if (!configMenuRef.value) {
    return
  }
  if (!configMenuRef.value.contains(event.target)) {
    showConfigMenu.value = false
  }
}

const handleEscapeKey = (event) => {
  if (event.key === 'Escape') {
    showConfigMenu.value = false
  }
}

// Zabbix form
const zabbixForm = ref({
  name: 'Zabbix Principal',
  type: 'zabbix',
  url: '',
  username: '',
  password: '',
  api_key: '',
  description: '',
  config_json: '{}',
  is_active: true
})

// Zabbix data
const zabbixUrl = computed(() => systemConfig.value?.ZABBIX_API_URL || '')
const zabbixUser = computed(() => systemConfig.value?.ZABBIX_API_USER || '')

// Show Zabbix card when on "all" or "zabbix" filter
const showZabbixCard = computed(() => {
  return activeFilter.value === 'all' || activeFilter.value === 'zabbix'
})

// Load system config on mount
onMounted(async () => {
  await loadSystemConfig()
  // Sync form with loaded config (initial load, will be updated when modal opens)
  zabbixForm.value.url = systemConfig.value?.ZABBIX_API_URL || ''
  zabbixForm.value.username = systemConfig.value?.ZABBIX_API_USER || ''
  zabbixForm.value.password = systemConfig.value?.ZABBIX_API_PASSWORD || ''
  zabbixForm.value.api_key = systemConfig.value?.ZABBIX_API_KEY || ''
  zabbixForm.value.description = systemConfig.value?.ZABBIX_DESCRIPTION || 'Servidor principal de monitoramento Zabbix'
  zabbixForm.value.config_json = systemConfig.value?.ZABBIX_CONFIG_JSON || '{}'
  zabbixForm.value.is_active = systemConfig.value?.ZABBIX_ACTIVE !== false
  syncDistanceThresholdsFromConfig()
})

onMounted(() => {
  document.addEventListener('click', handleOutsideClick)
  document.addEventListener('keydown', handleEscapeKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleOutsideClick)
  document.removeEventListener('keydown', handleEscapeKey)
})

// Open Zabbix modal
const openZabbixModal = () => {
  // Load current values from system config
  zabbixForm.value.name = 'Zabbix Principal'
  zabbixForm.value.type = 'zabbix'
  zabbixForm.value.url = systemConfig.value.ZABBIX_API_URL || ''
  zabbixForm.value.username = systemConfig.value.ZABBIX_API_USER || ''
  zabbixForm.value.password = systemConfig.value.ZABBIX_API_PASSWORD || ''
  zabbixForm.value.api_key = systemConfig.value.ZABBIX_API_KEY || ''
  zabbixForm.value.description = systemConfig.value.ZABBIX_DESCRIPTION || 'Servidor principal de monitoramento Zabbix'
  zabbixForm.value.config_json = systemConfig.value.ZABBIX_CONFIG_JSON || '{}'
  zabbixForm.value.is_active = systemConfig.value.ZABBIX_ACTIVE !== false
  showZabbixModal.value = true
}

// Save Zabbix config
const saveZabbixConfig = async (event) => {
  event?.preventDefault()
  
  // Validate JSON config
  if (zabbixForm.value.config_json.trim()) {
    try {
      JSON.parse(zabbixForm.value.config_json)
    } catch (e) {
      alert('JSON de configuração inválido')
      return
    }
  }
  
  savingZabbix.value = true
  try {
    // Update system config with Zabbix values
    systemConfig.value.ZABBIX_API_URL = zabbixForm.value.url
    systemConfig.value.ZABBIX_API_USER = zabbixForm.value.username
    systemConfig.value.ZABBIX_API_PASSWORD = zabbixForm.value.password
    systemConfig.value.ZABBIX_API_KEY = zabbixForm.value.api_key
    systemConfig.value.ZABBIX_DESCRIPTION = zabbixForm.value.description
    systemConfig.value.ZABBIX_CONFIG_JSON = zabbixForm.value.config_json
    systemConfig.value.ZABBIX_ACTIVE = zabbixForm.value.is_active
    
    await saveSystemConfig()
    showZabbixModal.value = false
  } catch (error) {
    console.error('[MonitoringTab] Error saving Zabbix config:', error)
  } finally {
    savingZabbix.value = false
  }
}

// Clear Zabbix form
const clearZabbixForm = () => {
  zabbixForm.value = {
    name: 'Zabbix Principal',
    type: 'zabbix',
    url: '',
    username: '',
    password: '',
    api_key: '',
    description: '',
    config_json: '{}',
    is_active: true
  }
}

// Navigate to System tab (fallback)
const goToSystemTab = () => {
  // Emit event to parent to change tab
  const event = new CustomEvent('change-tab', { detail: 'system' })
  window.dispatchEvent(event)
}

// Helper function
const getServersByType = (type) => {
  if (!servers.value) return []
  return servers.value.filter(s => s.server_type === type)
}

// Computed
const filters = computed(() => {
  const additionalZabbixCount = getServersByType('zabbix').length
  return [
    { key: 'all', label: 'Todos', count: (serverCount.value?.total || 0) + 1 }, // +1 for Zabbix Principal
    { key: 'active', label: 'Ativos', count: serverCount.value?.active || activeServers.value?.length || 0 },
    { key: 'inactive', label: 'Inativos', count: serverCount.value?.inactive || inactiveServers.value?.length || 0 },
    { key: 'zabbix', label: 'Zabbix', count: additionalZabbixCount + 1 }, // +1 for Zabbix Principal
    { key: 'prometheus', label: 'Prometheus', count: getServersByType('prometheus').length },
  ]
})

const filteredServers = computed(() => {
  switch (activeFilter.value) {
    case 'active':
      return activeServers.value || []
    case 'inactive':
      return inactiveServers.value || []
    case 'zabbix':
      return getServersByType('zabbix')
    case 'prometheus':
      return getServersByType('prometheus')
    default:
      return servers.value || []
  }
})

// Methods
const serverTypeLabel = (type) => {
  const labels = {
    zabbix: 'Zabbix',
    prometheus: 'Prometheus',
    grafana: 'Grafana',
    other: 'Outro'
  }
  return labels[type] || type
}

const handleAddServer = () => {
  closeConfigMenu()
  editingServer.value = createEmptyServerForm()
  showModal.value = true
}

const handleEditServer = (server) => {
  closeConfigMenu()
  editingServer.value = { ...server }
  showModal.value = true
}

const handleSaveServer = async (serverData) => {
  const success = await saveServer(serverData)
  if (success) {
    showModal.value = false
    editingServer.value = null
  }
}

const handleDeleteServer = async (server) => {
  closeConfigMenu()
  if (confirm(`Excluir servidor "${server.name}"?`)) {
    await deleteServer(server.id)
  }
}

const handleTestConnection = async (server) => {
  testing.value[server.id] = true
  try {
    const result = await testServerConnection(server.id)
    serverTestResults.value[server.id] = result
    
    // Clear result after 5 seconds
    setTimeout(() => {
      delete serverTestResults.value[server.id]
    }, 5000)
  } finally {
    testing.value[server.id] = false
  }
}

const handleToggleStatus = async (server) => {
  closeConfigMenu()
  await toggleServerStatus(server.id)
}

const handleTestZabbix = async () => {
  closeConfigMenu()
  const payload = showZabbixModal.value
    ? {
        zabbix_api_url: zabbixForm.value.url,
        zabbix_api_user: zabbixForm.value.username,
        zabbix_api_password: zabbixForm.value.password,
        zabbix_api_key: zabbixForm.value.api_key,
        auth_type: zabbixForm.value.api_key ? 'token' : 'login',
      }
    : {
        zabbix_api_url: systemConfig.value?.ZABBIX_API_URL || '',
        zabbix_api_user: systemConfig.value?.ZABBIX_API_USER || '',
        zabbix_api_password: systemConfig.value?.ZABBIX_API_PASSWORD || '',
        zabbix_api_key: systemConfig.value?.ZABBIX_API_KEY || '',
        auth_type: systemConfig.value?.ZABBIX_API_KEY ? 'token' : 'login',
      }

  await testZabbix(payload)
}

// Lifecycle
onMounted(async () => {
  console.log('[MonitoringServersTab] Mounting component, loading servers...')
  await loadServers()
  console.log('[MonitoringServersTab] Servers loaded:', servers.value)
})
</script>

<style scoped>
.btn-primary {
  @apply inline-flex items-center justify-center rounded-md bg-primary-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600 transition-all duration-200;
}

.btn-icon {
  @apply p-2 rounded-md text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background-color: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  border-radius: 0.5rem;
}

.loading-spinner {
  width: 2rem;
  height: 2rem;
  border: 4px solid #bfdbfe;
  border-top-color: #3b82f6;
  border-radius: 9999px;
  animation: spin 1s linear infinite;
}

.fade-scale-enter-active,
.fade-scale-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: translateY(-0.5rem) scale(0.98);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>

<style>
/* Estilos globais para inputs, labels e botões - modo claro e escuro */
.input-custom {
  width: 100%;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  background-color: #ffffff;
  padding: 0.5rem 0.75rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
  color: #111827;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-custom::placeholder {
  color: #9ca3af;
}

.input-custom:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

.label-custom {
  display: block;
  font-size: 0.875rem;
  line-height: 1.25rem;
  font-weight: 500;
  color: #374151;
  margin-bottom: 0.375rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: #2563eb;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
  font-weight: 600;
  color: #ffffff;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  transition: all 0.2s;
  border: none;
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background-color: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: #ffffff;
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  line-height: 1.25rem;
  font-weight: 600;
  color: #111827;
  box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  border: 1px solid #d1d5db;
  transition: all 0.2s;
  cursor: pointer;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #f9fafb;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Dark mode */
html.dark .input-custom,
.dark .input-custom {
  border-color: #374151 !important;
  background-color: #1f2937 !important;
  color: #e5e7eb !important;
}

html.dark .input-custom::placeholder,
.dark .input-custom::placeholder {
  color: #6b7280 !important;
}

html.dark .input-custom:focus,
.dark .input-custom:focus {
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2) !important;
}

html.dark .label-custom,
.dark .label-custom {
  color: #e5e7eb !important;
}

html.dark .btn-primary,
.dark .btn-primary {
  background-color: #2563eb;
}

html.dark .btn-primary:hover:not(:disabled),
.dark .btn-primary:hover:not(:disabled) {
  background-color: #1d4ed8;
}

html.dark .btn-secondary,
.dark .btn-secondary {
  background-color: #374151 !important;
  color: #f3f4f6 !important;
  border-color: #4b5563 !important;
}

html.dark .btn-secondary:hover:not(:disabled),
.dark .btn-secondary:hover:not(:disabled) {
  background-color: #4b5563 !important;
}

html.dark .loading-overlay,
.dark .loading-overlay {
  background-color: rgba(17, 24, 39, 0.8);
}

html.dark .loading-spinner,
.dark .loading-spinner {
  border-color: #1e3a8a;
  border-top-color: #60a5fa;
}
</style>
