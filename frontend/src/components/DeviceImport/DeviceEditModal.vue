<template>
  <div class="fixed inset-0 z-50 overflow-y-auto" aria-labelledby="modal-title" role="dialog" aria-modal="true">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      
      <div class="fixed inset-0 bg-gray-500 dark:bg-gray-900/80 bg-opacity-75 transition-opacity" @click="$emit('close')"></div>
      <span class="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

      <div class="inline-block align-bottom bg-white dark:bg-gray-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
        
        <!-- Header -->
        <div class="bg-white dark:bg-gray-800 px-4 pt-5 pb-4 sm:p-6 border-b border-gray-100 dark:border-gray-700 flex justify-between items-center">
          <div>
            <h3 class="text-lg leading-6 font-bold text-gray-900 dark:text-white flex items-center">
              <i :class="isBatch ? 'fas fa-layer-group text-indigo-600 dark:text-indigo-400' : 'fas fa-server text-gray-500 dark:text-gray-400'" class="mr-2"></i>
              {{ modalTitle }}
            </h3>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
              {{ readOnly ? 'Visualização de dados de importação e configurações atuais.' : (isBatch ? 'Defina as configurações comuns para todos os itens selecionados.' : 'Dados de identificação e monitoramento.') }}
            </p>
          </div>
          <button @click="$emit('close')" class="text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none">
            <span class="sr-only">Fechar</span>
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>

        <!-- Content -->
        <!-- READONLY MODE: Ver Detalhes -->
        <div v-if="readOnly" class="px-6 py-6 space-y-6">
          
          <!-- Status de Sincronia -->
          <div class="bg-green-50 dark:bg-green-900/20 border-l-4 border-green-400 p-4 rounded-r">
            <div class="flex">
              <div class="flex-shrink-0">
                <i class="fas fa-check-circle text-green-500 text-2xl"></i>
              </div>
              <div class="ml-3">
                <h4 class="text-sm font-bold text-green-800 dark:text-green-300">
                  Dispositivo Importado e Sincronizado
                </h4>
                <p class="text-sm text-green-700 dark:text-green-400 mt-1">
                  Este equipamento está vinculado ao Zabbix e sendo monitorado.
                  <span v-if="activeDevices[0]?.zabbix_hostid || activeDevices[0]?.zabbix_id" class="font-mono bg-green-100 dark:bg-green-800 px-2 py-0.5 rounded ml-2">
                    ID: {{ activeDevices[0].zabbix_hostid || activeDevices[0].zabbix_id }}
                  </span>
                </p>
              </div>
            </div>
          </div>

          <!-- Comparativo Lado a Lado -->
          <div class="grid grid-cols-2 gap-4">
            
            <!-- Dados Atuais (Sistema) -->
            <div class="p-4 bg-gray-50 dark:bg-gray-700/50 rounded border border-gray-200 dark:border-gray-600">
              <h4 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-3 flex items-center">
                <i class="fas fa-database mr-2 text-indigo-500"></i>
                Dados no Sistema
              </h4>
              <div class="space-y-2">
                <div>
                  <p class="text-xs text-gray-500 dark:text-gray-400">Nome</p>
                  <p class="font-bold text-gray-900 dark:text-white">{{ formState.name }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 dark:text-gray-400">IP de Gerência</p>
                  <p class="text-sm text-gray-700 dark:text-gray-300 font-mono">{{ formState.ip_address }}</p>
                </div>
                <div>
                  <p class="text-xs text-gray-500 dark:text-gray-400">Grupo</p>
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300">
                    {{ formState.group || 'Sem grupo' }}
                  </span>
                </div>
                <div>
                  <p class="text-xs text-gray-500 dark:text-gray-400">Categoria</p>
                  <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium" 
                    :class="{
                      'bg-indigo-100 dark:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300': formState.category === 'backbone',
                      'bg-green-100 dark:bg-green-900/50 text-green-800 dark:text-green-300': formState.category === 'gpon',
                      'bg-purple-100 dark:bg-purple-900/50 text-purple-800 dark:text-purple-300': formState.category === 'dwdm'
                    }">
                    {{ formState.category.toUpperCase() }}
                  </span>
                </div>
              </div>
            </div>
            
            <!-- Ações Rápidas -->
            <div class="flex flex-col justify-center items-center border-2 border-dashed border-gray-300 dark:border-gray-600 rounded p-4 space-y-3">
              <i class="fas fa-tools text-gray-300 dark:text-gray-600 text-4xl mb-2"></i>
              <p class="text-sm text-gray-600 dark:text-gray-400 text-center">Ações disponíveis</p>
              
              <button 
                @click="openDashboard" 
                class="w-full inline-flex justify-center items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none transition-colors"
              >
                <i class="fas fa-chart-line mr-2"></i> Abrir Dashboard
              </button>
              
              <button 
                @click="enableEditMode" 
                class="w-full inline-flex justify-center items-center px-4 py-2 border border-indigo-300 dark:border-indigo-600 rounded-md shadow-sm text-sm font-medium text-indigo-700 dark:text-indigo-400 bg-white dark:bg-gray-700 hover:bg-indigo-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
              >
                <i class="fas fa-edit mr-2"></i> Editar Configurações
              </button>
              
              <button 
                v-if="showSyncButton"
                @click="handleSyncFromZabbix"
                :disabled="syncingFromZabbix"
                class="w-full inline-flex justify-center items-center px-4 py-2 border border-green-300 dark:border-green-600 rounded-md shadow-sm text-sm font-medium text-green-700 dark:text-green-400 bg-white dark:bg-gray-700 hover:bg-green-50 dark:hover:bg-gray-600 focus:outline-none transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                title="Sincronizar dados e grupos do Zabbix"
              >
                <i class="fas fa-sync-alt mr-2" :class="{ 'fa-spin': syncingFromZabbix }"></i> 
                {{ syncingFromZabbix ? 'Sincronizando...' : 'Sincronizar Zabbix' }}
              </button>
              
              <button 
                v-if="showSyncButton"
                @click="showInterfacesModal = true" 
                class="w-full inline-flex justify-center items-center px-4 py-2 border border-blue-300 dark:border-blue-600 rounded-md shadow-sm text-sm font-medium text-blue-700 dark:text-blue-400 bg-white dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
                title="Ver interfaces do dispositivo"
              >
                <i class="fas fa-network-wired mr-2"></i> Ver Interfaces
              </button>
            </div>
          </div>

          <!-- Canais de Alerta Ativos -->
          <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 border border-gray-200 dark:border-gray-600">
            <h4 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-3">
              Canais de Alerta Configurados
            </h4>
            <div class="flex items-center gap-4">
              <div v-if="formState.alerts.screen" class="flex items-center text-sm text-gray-700 dark:text-gray-300">
                <i class="fas fa-desktop text-indigo-500 mr-2"></i>
                Dashboard Map
              </div>
              <div v-if="formState.alerts.whatsapp" class="flex items-center text-sm text-gray-700 dark:text-gray-300">
                <i class="fab fa-whatsapp text-green-500 mr-2"></i>
                WhatsApp Ops
              </div>
              <div v-if="!formState.alerts.screen && !formState.alerts.whatsapp" class="text-sm text-gray-500 dark:text-gray-400 italic">
                Nenhum canal de alerta configurado
              </div>
            </div>
          </div>
        </div>

        <!-- EDIT MODE (conteúdo original) -->
        <div v-else class="px-6 py-6 space-y-8">
          
          <!-- Seleção de Categoria -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-3">
              Categoria {{ isBatch ? 'dos Equipamentos' : '(Mapa)' }}
            </label>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              
              <!-- Card Backbone -->
              <div 
                @click="setCategory('backbone')"
                class="cursor-pointer border-2 rounded-lg p-3 flex flex-col items-center text-center transition-all duration-200 hover:shadow-md h-24 justify-center"
                :class="getCardClass('backbone')"
              >
                <div class="h-10 w-10 rounded-full flex items-center justify-center mb-2 text-2xl bg-indigo-100 dark:bg-indigo-900 text-indigo-600 dark:text-indigo-400">
                  🖥️
                </div>
                <span class="font-bold text-gray-900 dark:text-white text-sm">Backbone</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 mt-1">Routers, Switches L3</span>
              </div>

              <!-- Card GPON -->
              <div 
                @click="setCategory('gpon')"
                class="cursor-pointer border-2 rounded-lg p-3 flex flex-col items-center text-center transition-all duration-200 hover:shadow-md h-24 justify-center"
                :class="getCardClass('gpon')"
              >
                <div class="h-10 w-10 rounded-full flex items-center justify-center mb-2 text-2xl bg-green-100 dark:bg-green-900 text-green-600 dark:text-green-400">
                  📡
                </div>
                <span class="font-bold text-gray-900 dark:text-white text-sm">GPON / FTTx</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 mt-1">OLTs, Splitters, ONUs</span>
              </div>

              <!-- Card DWDM -->
              <div 
                @click="setCategory('dwdm')"
                class="cursor-pointer border-2 rounded-lg p-3 flex flex-col items-center text-center transition-all duration-200 hover:shadow-md h-24 justify-center"
                :class="getCardClass('dwdm')"
              >
                <div class="h-10 w-10 rounded-full flex items-center justify-center mb-2 text-2xl bg-purple-100 dark:bg-purple-900 text-purple-600 dark:text-purple-400">
                  🔬
                </div>
                <span class="font-bold text-gray-900 dark:text-white text-sm">DWDM</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 mt-1">Transponders, Amplificadores</span>
              </div>

            </div>
          </div>

          <div class="border-t border-gray-200 dark:border-gray-700"></div>

          <!-- Grid 2 Colunas: Destino + Alertas -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <!-- Coluna Esquerda: Destino -->
            <div class="space-y-4">
              <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Destino</h4>

              <!-- Local (Site) - NOVO -->
              <div>
                <div class="flex justify-between items-center mb-1">
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">
                    <i class="fas fa-map-marker-alt text-red-500 mr-1"></i> Local (Site)
                  </label>
                  <button 
                    @click="openMapPicker"
                    type="button"
                    class="text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 dark:hover:text-indigo-300 focus:outline-none"
                  >
                    <i class="fas fa-map mr-1"></i> Abrir no Mapa
                  </button>
                </div>

                <!-- Modo: Lista de Seleção -->
                <div v-if="!isCreatingSite">
                  <select 
                    v-model="selectedSiteProxy" 
                    @change="handleSiteChange"
                    class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md"
                    :class="{'text-gray-400 dark:text-gray-500': !selectedSiteProxy}"
                  >
                    <option value="" disabled>Selecione o local...</option>
                    <option v-for="site in availableSites" :key="site.id" :value="site.id">{{ site.display_name }}</option>
                    <option disabled>──────────────</option>
                    <option value="__CREATE_NEW__" class="text-red-600 font-medium">📍 Criar Novo Site...</option>
                  </select>
                </div>

                <!-- Modo: Criar Novo Site -->
                <div v-else class="animate-fade-in space-y-2">
                  <div class="flex rounded-md shadow-sm">
                    <input 
                      ref="newSiteInput"
                      v-model="newSiteName" 
                      type="text" 
                      class="flex-1 min-w-0 block w-full px-3 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 focus:ring-red-500 focus:border-red-500 sm:text-sm bg-red-50 dark:bg-red-900/20 text-gray-900 dark:text-white placeholder-red-400 dark:placeholder-red-500" 
                      placeholder="Nome do novo local..." 
                    />
                    <button 
                      @click="cancelSiteCreation"
                      type="button" 
                      class="inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 dark:border-gray-600 rounded-r-md bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 text-sm"
                    >
                      <i class="fas fa-undo"></i>
                    </button>
                  </div>
                  <div v-if="tempCoordinates" class="flex items-center text-xs text-gray-600 dark:text-gray-300 bg-gray-50 dark:bg-gray-700 p-2 rounded border border-gray-200 dark:border-gray-600">
                    <i class="fas fa-crosshairs mr-2 text-red-500"></i>
                    Lat: {{ tempCoordinates.lat.toFixed(6) }}, Lng: {{ tempCoordinates.lng.toFixed(6) }}
                  </div>
                  <p class="text-xs text-red-600 dark:text-red-400">
                    <i class="fas fa-info-circle"></i> Clique em "Abrir no Mapa" para definir a localização.
                  </p>
                </div>
              </div>

              <!-- Grupo de Monitoramento -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-1">
                  Grupo de Monitoramento
                </label>
                
                <!-- Modo: Lista de Seleção (Padrão) -->
                <div v-if="!isCreatingGroup">
                  <select 
                    v-model="selectedGroupProxy" 
                    @change="handleGroupChange"
                    class="block w-full pl-3 pr-10 py-2 text-base border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md transition-shadow"
                    :class="{'text-gray-400 dark:text-gray-500': !selectedGroupProxy}"
                  >
                    <option value="" disabled>Escolha um grupo existente ou crie novo...</option>
                    <option v-for="grp in filteredGroups" :key="grp" :value="grp">{{ grp }}</option>
                    <option disabled>──────────────</option>
                    <option value="__CREATE_NEW__" class="text-indigo-600 font-medium">➕ Criar Novo Grupo...</option>
                  </select>
                  
                  <p v-if="!selectedGroupProxy && !isBatch" class="mt-1 text-xs text-indigo-600 dark:text-indigo-400 animate-pulse">
                    <i class="fas fa-info-circle"></i> Dica: Role até o final da lista para criar um novo grupo
                  </p>
                  <p v-else-if="selectedGroupProxy && !isBatch" class="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Vincula o device às regras de alerta deste grupo.
                  </p>
                  <p v-else-if="isBatch" class="mt-1 text-xs text-orange-600 dark:text-orange-400">
                    <i class="fas fa-exclamation-triangle mr-1"></i> Todos os {{ activeDevices.length }} devices serão movidos para este grupo.
                  </p>
                </div>

                <!-- Modo: Criar Novo Grupo -->
                <div v-else class="animate-fade-in">
                  <div class="flex rounded-md shadow-sm">
                    <input 
                      ref="newGroupInput"
                      v-model="newGroupName" 
                      type="text" 
                      class="flex-1 min-w-0 block w-full px-3 py-2 rounded-l-md border border-gray-300 dark:border-gray-600 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm bg-indigo-50 dark:bg-indigo-900/30 text-gray-900 dark:text-white placeholder-indigo-400 dark:placeholder-indigo-500" 
                      placeholder="Digite o nome do novo grupo..." 
                    />
                    <button 
                      @click="cancelCreation"
                      type="button" 
                      class="inline-flex items-center px-3 py-2 border border-l-0 border-gray-300 dark:border-gray-600 rounded-r-md bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600 focus:outline-none focus:ring-1 focus:ring-indigo-500 text-sm transition-colors"
                      title="Voltar para lista"
                    >
                      <i class="fas fa-undo mr-1"></i> Lista
                    </button>
                  </div>
                  <p class="mt-1 text-xs text-indigo-600 dark:text-indigo-400">
                    <i class="fas fa-info-circle"></i> Este grupo será criado ao salvar.
                  </p>
                </div>
              </div>

              <!-- Lista de Dispositivos (Modo Batch) -->
              <div v-if="isBatch" class="bg-gray-50 dark:bg-gray-700/50 rounded-md p-3 border border-gray-200 dark:border-gray-600 max-h-40 overflow-y-auto">
                <h5 class="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-2 sticky top-0 bg-gray-50 dark:bg-gray-700/50">
                  Itens selecionados ({{ activeDevices.length }})
                </h5>
                <ul class="text-xs text-gray-600 dark:text-gray-300 space-y-1">
                  <li v-for="(dev, idx) in activeDevices" :key="idx" class="truncate">
                    <i class="fas fa-check text-green-500 dark:text-green-400 mr-1"></i> 
                    <strong>{{ dev.name }}</strong> 
                    <span class="text-gray-400 dark:text-gray-500">({{ dev.ip || dev.ip_address }})</span>
                  </li>
                </ul>
              </div>

              <!-- Campos Individuais (Modo Single) -->
              <div v-else class="space-y-4">
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">Nome do Host</label>
                  <input 
                    v-model="formState.name" 
                    type="text" 
                    class="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 px-3" 
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-200">IP de Gerência</label>
                  <div class="mt-1 flex rounded-md shadow-sm">
                    <span class="inline-flex items-center px-3 rounded-l-md border border-r-0 border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 text-sm">
                      <i class="fas fa-globe"></i>
                    </span>
                    <input 
                      v-model="formState.ip_address" 
                      type="text" 
                      class="flex-1 min-w-0 block w-full px-3 py-2 rounded-none rounded-r-md border border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 text-gray-500 dark:text-gray-400 sm:text-sm focus:ring-indigo-500 focus:border-indigo-500 cursor-not-allowed" 
                      readonly 
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- Coluna Direita: Canais de Alerta -->
            <div class="space-y-4">
              <h4 class="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">Canais de Alerta</h4>
              
              <div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 space-y-3 border border-gray-200 dark:border-gray-600">
                
                <!-- Dashboard Alert Toggle -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <i class="fas fa-desktop text-gray-400 dark:text-gray-500 w-6"></i>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-200">Dashboard Map</span>
                  </div>
                  <button 
                    @click="formState.alerts.screen = !formState.alerts.screen"
                    type="button" 
                    class="relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none"
                    :class="formState.alerts.screen ? getCategoryColorClass() : 'bg-gray-200 dark:bg-gray-600'"
                  >
                    <span 
                      aria-hidden="true" 
                      class="translate-x-0 pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200" 
                      :class="{'translate-x-5': formState.alerts.screen}"
                    ></span>
                  </button>
                </div>

                <!-- WhatsApp Alert Toggle -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center">
                    <i class="fab fa-whatsapp text-green-500 dark:text-green-400 w-6"></i>
                    <span class="text-sm font-medium text-gray-700 dark:text-gray-200">WhatsApp Ops</span>
                  </div>
                  <button 
                    @click="formState.alerts.whatsapp = !formState.alerts.whatsapp"
                    type="button" 
                    class="relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none"
                    :class="formState.alerts.whatsapp ? 'bg-green-500 dark:bg-green-600' : 'bg-gray-200 dark:bg-gray-600'"
                  >
                    <span 
                      aria-hidden="true" 
                      class="translate-x-0 pointer-events-none inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200" 
                      :class="{'translate-x-5': formState.alerts.whatsapp}"
                    ></span>
                  </button>
                </div>

                <!-- Info condicional WhatsApp -->
                <div v-if="formState.alerts.whatsapp" class="mt-2 pt-2 border-t border-gray-200 dark:border-gray-600 animate-fade-in">
                  <p class="text-xs text-gray-500 dark:text-gray-400">
                    Será enviado para o grupo padrão da categoria <strong class="text-gray-700 dark:text-gray-300">{{ formState.category.toUpperCase() }}</strong>.
                  </p>
                </div>

                <!-- Info Zabbix ID (Modo Single) -->
                <div v-if="!isBatch" class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-600 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>Origem Zabbix:</span>
                  <span class="font-mono bg-gray-200 dark:bg-gray-600 dark:text-gray-200 px-2 py-0.5 rounded">
                    {{ activeDevices[0]?.zabbix_hostid || activeDevices[0]?.zabbix_id || 'Manual' }}
                  </span>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- Footer Actions -->
        <div class="bg-gray-50 dark:bg-gray-800 px-4 py-3 sm:px-6 border-t border-gray-200 dark:border-gray-700">
          <!-- READONLY MODE FOOTER -->
          <div v-if="readOnly" class="flex justify-end">
            <button 
              @click="$emit('close')"
              type="button" 
              class="inline-flex justify-center items-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
            >
              <i class="fas fa-times mr-2"></i>
              Fechar
            </button>
          </div>
          
          <!-- EDIT MODE FOOTER -->
          <div v-else class="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
            <!-- Left: Interfaces button (only for single device with zabbix_id) -->
            <div>
              <button 
                v-if="!isBatch && activeDevices.length > 0 && (activeDevices[0].zabbix_hostid || activeDevices[0].zabbix_id)"
                @click="showInterfacesModal = true" 
                type="button" 
                class="inline-flex items-center px-4 py-2 border border-blue-300 dark:border-blue-600 rounded-md shadow-sm text-sm font-medium text-blue-700 dark:text-blue-400 bg-white dark:bg-gray-700 hover:bg-blue-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
                title="Ver interfaces e níveis de sinal do dispositivo"
              >
                <i class="fas fa-network-wired mr-2"></i>
                Ver Interfaces
              </button>
            </div>
            
            <!-- Right: Action buttons -->
            <div class="flex flex-col-reverse sm:flex-row gap-2">
              <button 
                @click="$emit('close')"
                type="button" 
                class="inline-flex justify-center items-center rounded-md border border-gray-300 dark:border-gray-600 shadow-sm px-4 py-2 bg-white dark:bg-gray-700 text-sm font-medium text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none transition-colors"
              >
                Cancelar
              </button>
              <button 
                @click="handleSave"
                type="button" 
                class="inline-flex justify-center items-center rounded-md border border-transparent shadow-sm px-4 py-2 text-sm font-medium text-white focus:outline-none transition-colors"
                :class="saveButtonClass"
              >
                <i :class="isBatch ? 'fas fa-cloud-download-alt' : 'fas fa-save'" class="mr-2"></i> 
                {{ isBatch ? `Importar ${activeDevices.length} Dispositivos` : 'Confirmar Importação' }}
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Modal de Mapa (Overlay) -->
    <div v-if="showMapPicker" class="fixed inset-0 z-[60] overflow-y-auto flex items-center justify-center">
      <div class="fixed inset-0 bg-black bg-opacity-60" @click="showMapPicker = false"></div>
      <div class="bg-white dark:bg-gray-800 w-full max-w-4xl h-[600px] rounded-lg shadow-2xl relative z-[70] flex flex-col m-4">
        <div class="p-4 border-b dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900 rounded-t-lg">
          <div>
            <h3 class="font-bold text-gray-800 dark:text-white flex items-center">
              <i class="fas fa-map-marked-alt text-red-500 mr-2"></i>
              Definir Localização do Site
            </h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Clique no mapa para posicionar o marcador no local exato.</p>
          </div>
          <button @click="showMapPicker = false" class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
        <div class="flex-1 relative bg-gray-200 dark:bg-gray-900">
          <!-- Google Maps Container -->
          <div ref="mapContainer" class="absolute inset-0 w-full h-full"></div>
          
          <!-- Loading overlay -->
          <div v-if="mapLoading" class="absolute inset-0 flex flex-col items-center justify-center bg-white dark:bg-gray-900 bg-opacity-90 z-10">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-red-600 mb-4"></div>
            <p class="text-sm text-gray-600 dark:text-gray-300">Carregando mapa...</p>
          </div>
          
          <!-- Error overlay -->
          <div v-if="mapError" class="absolute inset-0 flex flex-col items-center justify-center bg-white dark:bg-gray-900 z-10 p-6">
            <i class="fas fa-exclamation-triangle text-yellow-500 text-5xl mb-4"></i>
            <p class="text-gray-700 dark:text-gray-300 font-medium mb-2">Erro ao carregar o mapa</p>
            <p class="text-sm text-gray-500 dark:text-gray-400 text-center">{{ mapError }}</p>
            <button @click="initializeMap" class="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
              <i class="fas fa-redo mr-2"></i>Tentar Novamente
            </button>
          </div>
        </div>
        <div class="p-4 border-t dark:border-gray-700 bg-white dark:bg-gray-800 rounded-b-lg flex justify-between items-center">
          <div class="text-sm text-gray-600 dark:text-gray-300 font-mono">
            <span class="text-gray-500 dark:text-gray-400">Latitude:</span> <strong class="text-red-600">{{ mapLat.toFixed(6) }}</strong>
            <span class="mx-3">|</span>
            <span class="text-gray-500 dark:text-gray-400">Longitude:</span> <strong class="text-red-600">{{ mapLng.toFixed(6) }}</strong>
          </div>
          <button @click="confirmLocation" class="px-5 py-2 bg-red-600 text-white rounded shadow hover:bg-red-700 transition-colors font-medium">
            <i class="fas fa-check mr-2"></i>
            Confirmar Localização
          </button>
        </div>
      </div>
    </div>

    <!-- Modal: Interfaces Importadas -->
    <div v-if="showInterfacesModal" class="fixed inset-0 z-[60] overflow-y-auto flex items-center justify-center">
      <div class="fixed inset-0 bg-black bg-opacity-60" @click="showInterfacesModal = false"></div>
      <div class="bg-white dark:bg-gray-800 w-full max-w-3xl rounded-lg shadow-2xl relative z-[70] flex flex-col m-4 max-h-[80vh]">
        <div class="p-4 border-b dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-900 rounded-t-lg">
          <div>
            <h3 class="font-bold text-gray-800 dark:text-white flex items-center">
              <i class="fas fa-network-wired text-blue-500 mr-2"></i>
              Interfaces do Dispositivo
            </h3>
            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {{ activeDevices.length > 0 ? activeDevices[0].name : '' }}
            </p>
          </div>
          <button @click="showInterfacesModal = false" class="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
            <i class="fas fa-times text-xl"></i>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <!-- Loading state -->
          <div v-if="loadingInterfaces" class="flex flex-col items-center justify-center py-12">
            <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
            <p class="text-sm text-gray-600 dark:text-gray-300">Carregando interfaces...</p>
          </div>

          <!-- Empty state -->
          <div v-else-if="!interfacesData || interfacesData.length === 0" class="flex flex-col items-center justify-center py-12">
            <i class="fas fa-inbox text-gray-300 dark:text-gray-600 text-5xl mb-4"></i>
            <p class="text-gray-600 dark:text-gray-300 font-medium">Nenhuma interface encontrada</p>
            <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Este dispositivo não possui interfaces cadastradas.</p>
          </div>

          <!-- Interfaces list -->
          <div v-else class="space-y-3">
            <div 
              v-for="(iface, index) in interfacesData" 
              :key="index"
              class="border dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-750 hover:shadow-md transition-shadow"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center">
                    <i class="fas fa-ethernet text-blue-500 mr-2"></i>
                    <h4 class="font-medium text-gray-800 dark:text-white">{{ iface.name }}</h4>
                    <span 
                      v-if="iface.status === 'up'" 
                      class="ml-2 px-2 py-0.5 text-xs bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded-full"
                    >
                      <i class="fas fa-check-circle mr-1"></i>UP
                    </span>
                    <span 
                      v-else 
                      class="ml-2 px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded-full"
                    >
                      <i class="fas fa-times-circle mr-1"></i>DOWN
                    </span>
                  </div>
                  <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">{{ iface.description || 'Sem descrição' }}</p>
                  
                  <!-- Signal levels -->
                  <div v-if="iface.rx_power || iface.tx_power" class="mt-3 grid grid-cols-2 gap-3">
                    <div v-if="iface.rx_power" class="bg-blue-50 dark:bg-blue-900/20 p-2 rounded">
                      <p class="text-xs text-gray-500 dark:text-gray-400">RX Power</p>
                      <p class="text-sm font-medium text-gray-800 dark:text-white">
                        {{ iface.rx_power }} dBm
                      </p>
                    </div>
                    <div v-if="iface.tx_power" class="bg-green-50 dark:bg-green-900/20 p-2 rounded">
                      <p class="text-xs text-gray-500 dark:text-gray-400">TX Power</p>
                      <p class="text-sm font-medium text-gray-800 dark:text-white">
                        {{ iface.tx_power }} dBm
                      </p>
                    </div>
                  </div>

                  <!-- Bandwidth -->
                  <div v-if="iface.speed" class="mt-2">
                    <p class="text-xs text-gray-500 dark:text-gray-400">
                      <i class="fas fa-tachometer-alt mr-1"></i>
                      Velocidade: <span class="font-medium text-gray-700 dark:text-gray-300">{{ iface.speed }}</span>
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="p-4 border-t dark:border-gray-700 bg-white dark:bg-gray-800 rounded-b-lg flex justify-end">
          <button @click="showInterfacesModal = false" class="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors">
            <i class="fas fa-times mr-2"></i>Fechar
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
```

<script setup>
import { reactive, ref, computed, watch, nextTick, onUnmounted } from 'vue';
import { loadGoogleMaps } from '@/utils/googleMapsLoader';
import { useApi } from '@/composables/useApi';

// Props polimórficas: suporta array (batch) OU objeto único (legacy)
const props = defineProps({
  devices: { type: Array, default: () => [] }, // Modo Batch
  device: { type: Object, default: null },     // Modo Single (Legacy support)
  isNew: { type: Boolean, default: false },    // Legacy flag
  readOnly: { type: Boolean, default: false }, // Modo readonly (Ver Detalhes)
  availableGroups: { type: Array, default: () => [] },
  availableSites: { type: Array, default: () => [] } // Lista de Sites do backend
});

const emit = defineEmits(['close', 'save', 'edit']);

// API composable
const api = useApi();

// Estado do Formulário (compartilhado entre single e batch)
const formState = reactive({
  category: 'backbone',
  site: '',   // ID do Site
  group: '',
  alerts: { screen: true, whatsapp: false },
  name: '',       // Apenas para single mode
  ip_address: ''  // Apenas para single mode
});

// Variáveis de Controle de Interface - Grupo
const isCreatingGroup = ref(false);
const newGroupName = ref('');
const selectedGroupProxy = ref('');
const newGroupInput = ref(null);

// Variáveis de Controle de Interface - Site
const isCreatingSite = ref(false);
const newSiteName = ref('');
const selectedSiteProxy = ref('');
const newSiteInput = ref(null);
const showMapPicker = ref(false);
const tempCoordinates = ref(null); // { lat: ..., lng: ... }
const mapLat = ref(-23.5505); // Coordenada padrão São Paulo
const mapLng = ref(-46.6333);

// Google Maps state
const mapContainer = ref(null);
const mapInstance = ref(null);
const mapMarker = ref(null);
const mapLoading = ref(false);
const mapError = ref(null);

// Interfaces Modal state
const showInterfacesModal = ref(false);
const interfacesData = ref([]);
const loadingInterfaces = ref(false);

// Sync from Zabbix state
const syncingFromZabbix = ref(false);

// --- LÓGICA DE INICIALIZAÇÃO ---

// Detecta se estamos em modo Batch ou Single
const isBatch = computed(() => props.devices && props.devices.length > 1);

// Normaliza a lista de devices em uso
const activeDevices = computed(() => {
  if (isBatch.value) return props.devices;
  if (props.device) return [props.device];
  return props.devices.length ? [props.devices[0]] : [];
});

// Debug: mostrar botão sync
const showSyncButton = computed(() => {
  const hasDevice = activeDevices.value.length > 0;
  const device = activeDevices.value[0];
  const hasId = device?.id;
  const isNumber = typeof device?.id === 'number';
  
  console.log('[DeviceEditModal] Sync button visibility check:', {
    hasDevice,
    deviceId: device?.id,
    hasId,
    isNumber,
    shouldShow: hasDevice && hasId && isNumber
  });
  
  return hasDevice && hasId && isNumber;
});

// Watch para carregar dados quando o modal abre
watch(() => [props.device, props.devices], () => {
  // Reset estado de criação
  isCreatingGroup.value = false;
  isCreatingSite.value = false;
  newGroupName.value = '';
  newSiteName.value = '';
  tempCoordinates.value = null;
  
  if (isBatch.value) {
    // Lógica BATCH: Usa defaults
    formState.category = 'backbone';
    formState.site = '';
    formState.group = '';
    formState.alerts = { screen: true, whatsapp: false };
    selectedSiteProxy.value = '';
    selectedGroupProxy.value = '';
  } else if (activeDevices.value.length > 0) {
    // Lógica SINGLE: Copia dados do primeiro device
    const singleDev = activeDevices.value[0];
    
    console.log('[DeviceEditModal] Loading single device data:', {
      id: singleDev.id,
      name: singleDev.name,
      group_name: singleDev.group_name,
      monitoring_group: singleDev.monitoring_group,
      category: singleDev.category,
      readOnly: props.readOnly
    });
    
    // Site: backend retorna 'site' como ID numérico
    const siteId = typeof singleDev.site === 'number' ? singleDev.site : '';
    
    // Grupo: usar sempre o nome (group_name) para compatibilidade com import API
    const groupName = singleDev.group_name || '';
    
    Object.assign(formState, {
      category: singleDev.category || 'backbone',
      site: siteId,
      group: groupName,
      alerts: singleDev.alerts || { screen: true, whatsapp: false },
      name: singleDev.name,
      ip_address: singleDev.ip_address || singleDev.primary_ip || singleDev.ip
    });
    
    console.log('[DeviceEditModal] formState after loading:', {
      category: formState.category,
      group: formState.group,
      site: formState.site
    });
    
    selectedSiteProxy.value = siteId;
    selectedGroupProxy.value = groupName;
  }
}, { immediate: true });

// --- LÓGICA DE UI ---

const modalTitle = computed(() => {
  if (props.readOnly) return 'Detalhes do Dispositivo';
  return isBatch.value 
    ? `Importação em Lote (${activeDevices.value.length} itens)` 
    : (props.isNew ? 'Classificar e Importar Dispositivo' : 'Editar Configurações');
});

const filteredGroups = computed(() => {
  const term = formState.category.toLowerCase();
  if (!props.availableGroups.length) return [];
  
  return props.availableGroups.filter(g => {
    const gName = g.toLowerCase();
    if (term === 'backbone') return !gName.includes('olt') && !gName.includes('dwdm');
    if (term === 'gpon') return gName.includes('olt') || gName.includes('gpon') || gName.includes('ftth') || gName.includes('acesso');
    if (term === 'dwdm') return gName.includes('dwdm') || gName.includes('opt') || gName.includes('óptico');
    return true;
  });
});

const setCategory = (cat) => {
  formState.category = cat;
};

const handleGroupChange = async () => {
  if (selectedGroupProxy.value === '__CREATE_NEW__') {
    isCreatingGroup.value = true;
    selectedGroupProxy.value = '';
    newGroupName.value = '';
    await nextTick();
    newGroupInput.value?.focus();
  } else {
    formState.group = selectedGroupProxy.value;
    isCreatingGroup.value = false;
  }
};

const cancelCreation = () => {
  isCreatingGroup.value = false;
  selectedGroupProxy.value = formState.group || '';
};

// --- FUNÇÕES DE SITE ---

const handleSiteChange = async () => {
  if (selectedSiteProxy.value === '__CREATE_NEW__') {
    isCreatingSite.value = true;
    selectedSiteProxy.value = '';
    newSiteName.value = '';
    tempCoordinates.value = null;
    await nextTick();
    newSiteInput.value?.focus();
  } else {
    formState.site = selectedSiteProxy.value;
    isCreatingSite.value = false;
  }
};

const cancelSiteCreation = () => {
  isCreatingSite.value = false;
  selectedSiteProxy.value = formState.site || '';
  tempCoordinates.value = null;
};

const openMapPicker = async () => {
  // Se está editando site existente, carrega coordenadas
  if (!isCreatingSite.value && selectedSiteProxy.value) {
    const selectedSite = props.availableSites.find(s => s.id === selectedSiteProxy.value);
    if (selectedSite && selectedSite.lat && selectedSite.lng) {
      mapLat.value = selectedSite.lat;
      mapLng.value = selectedSite.lng;
      console.log('[DeviceEditModal] Loaded existing site coords:', selectedSite.lat, selectedSite.lng);
    }
  }
  
  if (!isCreatingSite.value) {
    isCreatingSite.value = true;
    selectedSiteProxy.value = '';
  }
  
  showMapPicker.value = true;
};

const confirmLocation = () => {
  tempCoordinates.value = { lat: mapLat.value, lng: mapLng.value };
  showMapPicker.value = false;
  nextTick(() => newSiteInput.value?.focus());
};

// --- GOOGLE MAPS FUNCTIONS ---

const initializeMap = async () => {
  mapLoading.value = true;
  mapError.value = null;

  try {
    console.log('[DeviceEditModal] Initializing Google Maps...');
    
    // Carrega API do Google Maps
    await loadGoogleMaps();
    
    if (!window.google?.maps) {
      throw new Error('Google Maps API not available');
    }

    // Aguarda o container estar disponível no DOM
    await nextTick();
    
    if (!mapContainer.value) {
      throw new Error('Map container not found');
    }

    console.log('[DeviceEditModal] Creating map instance...');

    // Cria instância do mapa
    mapInstance.value = new window.google.maps.Map(mapContainer.value, {
      center: { lat: mapLat.value, lng: mapLng.value },
      zoom: 15,
      mapTypeControl: true,
      streetViewControl: false,
      fullscreenControl: true,
      zoomControl: true,
      mapTypeId: 'roadmap',
      styles: [
        {
          featureType: 'poi',
          elementType: 'labels',
          stylers: [{ visibility: 'off' }]
        }
      ]
    });

    // Cria marcador
    mapMarker.value = new window.google.maps.Marker({
      position: { lat: mapLat.value, lng: mapLng.value },
      map: mapInstance.value,
      draggable: true,
      animation: window.google.maps.Animation.DROP,
      title: 'Posição do Site'
    });

    // Event: arrastar marcador
    mapMarker.value.addListener('dragend', (event) => {
      const newLat = event.latLng.lat();
      const newLng = event.latLng.lng();
      mapLat.value = newLat;
      mapLng.value = newLng;
      console.log('[DeviceEditModal] Marker dragged to:', newLat, newLng);
    });

    // Event: clicar no mapa
    mapInstance.value.addListener('click', (event) => {
      const newLat = event.latLng.lat();
      const newLng = event.latLng.lng();
      mapLat.value = newLat;
      mapLng.value = newLng;
      
      // Move o marcador
      mapMarker.value.setPosition(event.latLng);
      
      // Anima marcador
      mapMarker.value.setAnimation(window.google.maps.Animation.BOUNCE);
      setTimeout(() => {
        mapMarker.value.setAnimation(null);
      }, 750);
      
      console.log('[DeviceEditModal] Map clicked:', newLat, newLng);
    });

    console.log('[DeviceEditModal] ✅ Map initialized successfully');
    mapLoading.value = false;

  } catch (error) {
    console.error('[DeviceEditModal] Error initializing map:', error);
    mapError.value = error.message || 'Erro ao carregar o mapa';
    mapLoading.value = false;
  }
};

// Watch para inicializar o mapa quando o modal abrir
watch(showMapPicker, async (isOpen) => {
  if (isOpen) {
    // Sempre recria o mapa para usar as coordenadas atualizadas
    if (mapInstance.value) {
      mapInstance.value = null;
    }
    await nextTick(); // Aguarda o DOM renderizar
    await initializeMap();
  }
});

// --- INTERFACES FUNCTIONS ---

const fetchInterfaces = async () => {
  if (!activeDevices.value.length) {
    interfacesData.value = [];
    return;
  }

  const device = activeDevices.value[0];
  const deviceId = device.id;
  
  // Se não tiver ID real (modo readonly com fallback), não busca
  if (!deviceId || typeof deviceId !== 'number') {
    console.warn('[DeviceEditModal] Cannot fetch interfaces: invalid device ID', deviceId);
    interfacesData.value = [];
    return;
  }

  loadingInterfaces.value = true;

  try {
    console.log('[DeviceEditModal] Fetching interfaces for device:', deviceId);
    
    // Chamada à API com dados em tempo real do Zabbix
    const response = await api.get(`/api/v1/inventory/devices/${deviceId}/ports/live/`);
    
    if (response.ports) {
      // Dados já vêm formatados do backend com status e sinais ópticos
      interfacesData.value = response.ports.map(port => ({
        id: port.id,
        name: port.name,
        description: port.description || '',
        status: port.status || 'unknown',
        speed: port.speed || '',
        rx_power: port.rx_power,
        tx_power: port.tx_power,
        fiber_cable_id: port.fiber_cable_id,
        zabbix_item_key: port.zabbix_item_key
      }));
      
      console.log('[DeviceEditModal] Interfaces loaded:', interfacesData.value.length);
    } else {
      interfacesData.value = [];
    }
  } catch (error) {
    console.error('[DeviceEditModal] Error fetching interfaces:', error);
    notifyError('Erro', 'Não foi possível carregar as interfaces do dispositivo.');
    interfacesData.value = [];
  } finally {
    loadingInterfaces.value = false;
  }
};

// Watch para carregar interfaces quando modal abrir
watch(showInterfacesModal, async (isOpen) => {
  if (isOpen) {
    await fetchInterfaces();
  }
});

// Cleanup ao desmontar componente
onUnmounted(() => {
  if (mapMarker.value) {
    mapMarker.value.setMap(null);
    mapMarker.value = null;
  }
  mapInstance.value = null;
});

// --- SALVAMENTO ---

// Função para abrir dashboard do dispositivo (modo readonly)
const openDashboard = () => {
  const device = activeDevices.value[0];
  if (!device) {
    console.error('[DeviceEditModal] No device available');
    return;
  }
  
  // Tenta usar id primeiro, depois zabbix_id como fallback
  const deviceId = device.id || device.zabbix_id;
  
  if (deviceId) {
    console.log('[DeviceEditModal] Opening dashboard for device:', deviceId);
    // TODO: Ajustar rota quando dashboard estiver implementado
    // Por enquanto, abre uma URL placeholder
    const dashboardUrl = `/monitoring/device/${deviceId}`;
    window.open(dashboardUrl, '_blank');
  } else {
    console.error('[DeviceEditModal] Device has no ID:', device);
    alert('Não foi possível abrir o dashboard: dispositivo sem ID.');
  }
};

// Função para sair do modo readonly e entrar em edição
const enableEditMode = () => {
  const device = activeDevices.value[0];
  if (!device) {
    console.error('[DeviceEditModal] No device available for edit');
    return;
  }
  
  console.log('[DeviceEditModal] Enabling edit mode for device:', device);
  
  // Emite evento 'edit' para o componente pai trocar o modo
  emit('edit', device);
};

// Função para forçar sincronização com Zabbix (modo readonly)
const handleSyncFromZabbix = async () => {
  const device = activeDevices.value[0];
  if (!device || !device.id) {
    console.error('[DeviceEditModal] No valid device ID for sync');
    alert('Dispositivo sem ID válido para sincronização.');
    return;
  }

  const confirmMsg = `Deseja sincronizar "${device.name || 'este dispositivo'}" com os dados atuais do Zabbix?\n\nIsso irá:\n• Atualizar nome e IP\n• Aplicar regras de auto-associação\n• Sincronizar grupos do Zabbix\n• Atualizar site/localização`;
  
  if (!confirm(confirmMsg)) {
    return;
  }

  syncingFromZabbix.value = true;

  try {
    console.log('[DeviceEditModal] Syncing device with Zabbix:', device.id);
    
    const response = await api.post(`/api/v1/devices/${device.id}/sync/`, {});
    console.log('[DeviceEditModal] Sync successful:', response);

    alert('✅ Dispositivo sincronizado com sucesso!\n\nO sistema foi atualizado com os dados mais recentes do Zabbix.');
    
    // Fecha modal e pede refresh para o pai
    emit('close');
    // Aguarda um pouco e dispara evento de refresh via window (para DeviceImportManager pegar)
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('device-sync-complete', { detail: { deviceId: device.id } }));
    }, 100);

  } catch (error) {
    console.error('[DeviceEditModal] Sync failed:', error);
    alert(`❌ Erro ao sincronizar com Zabbix:\n\n${error.message}\n\nVerifique se o dispositivo ainda existe no Zabbix.`);
  } finally {
    syncingFromZabbix.value = false;
  }
};

const handleSave = () => {
  // Tratamento do Site
  let finalSite = formState.site;
  let isNewSite = false;
  let siteCoordinates = null;

  if (isCreatingSite.value) {
    if (!newSiteName.value.trim()) {
      alert('Por favor, digite o nome do novo local/site.');
      return;
    }
    if (!tempCoordinates.value) {
      alert('Por favor, clique em "Abrir no Mapa" para definir a localização do site.');
      return;
    }
    finalSite = newSiteName.value.trim();
    isNewSite = true;
    siteCoordinates = tempCoordinates.value;
  } else {
    finalSite = selectedSiteProxy.value;
  }

  // Validação de Site
  if (!finalSite) {
    alert('Selecione um local/site para o dispositivo.');
    return;
  }

  // Tratamento do Grupo
  let finalGroup = formState.group;
  let isNewGroup = false;

  if (isCreatingGroup.value) {
    if (!newGroupName.value.trim()) {
      alert('Por favor, digite o nome do novo grupo.');
      return;
    }
    finalGroup = newGroupName.value.trim();
    isNewGroup = true;
  } else {
    finalGroup = selectedGroupProxy.value;
  }

  // Validação de Grupo
  if (!finalGroup) {
    alert('Selecione um grupo de monitoramento.');
    return;
  }

  // Prepara o Payload de Saída
  if (isBatch.value) {
    // Em Batch, aplicamos as configurações comuns a TODOS os itens originais
    const batchPayload = activeDevices.value.map(dev => ({
      ...dev, // Mantém dados originais (ID Zabbix, IP, etc)
      category: formState.category,
      site: finalSite,
      is_new_site: isNewSite,
      site_coordinates: siteCoordinates,
      group: finalGroup,
      is_new_group: isNewGroup,
      alerts: { ...formState.alerts }
    }));
    
    emit('save', { mode: 'batch', devices: batchPayload });
  } else {
    // Em Single, mandamos o objeto único atualizado
    const singlePayload = {
      ...activeDevices.value[0],
      name: formState.name, // Nome pode ter sido editado
      category: formState.category,
      site: finalSite,
      is_new_site: isNewSite,
      site_coordinates: siteCoordinates,
      group: finalGroup,
      is_new_group: isNewGroup,
      alerts: { ...formState.alerts }
    };
    
    emit('save', singlePayload);
  }
};

// --- ESTILOS ---

const getCardClass = (cat) => {
  const isActive = formState.category === cat;
  const colors = {
    backbone: isActive 
      ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-900/20 ring-1 ring-indigo-500' 
      : 'border-gray-200 dark:border-gray-600 hover:border-indigo-300 dark:hover:border-indigo-400',
    gpon: isActive 
      ? 'border-green-500 bg-green-50 dark:bg-green-900/20 ring-1 ring-green-500' 
      : 'border-gray-200 dark:border-gray-600 hover:border-green-300 dark:hover:border-green-400',
    dwdm: isActive 
      ? 'border-purple-500 bg-purple-50 dark:bg-purple-900/20 ring-1 ring-purple-500' 
      : 'border-gray-200 dark:border-gray-600 hover:border-purple-300 dark:hover:border-purple-400'
  };
  return colors[cat];
};

const getCategoryColorClass = () => {
  const colors = {
    backbone: 'bg-indigo-600 dark:bg-indigo-500',
    gpon: 'bg-green-600 dark:bg-green-500',
    dwdm: 'bg-purple-600 dark:bg-purple-500'
  };
  return colors[formState.category] || 'bg-indigo-600';
};

const saveButtonClass = computed(() => {
  if (formState.category === 'gpon') return 'bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600';
  if (formState.category === 'dwdm') return 'bg-purple-600 hover:bg-purple-700 dark:bg-purple-500 dark:hover:bg-purple-600';
  return 'bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600';
});
</script>

<style scoped>
.input-standard {
  @apply block w-full rounded-md border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 px-3 border;
}
.animate-fade-in {
  animation: fadeIn 0.2s ease-in-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-2px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
