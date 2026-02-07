<template>
  <Teleport to="body">
    <div
      v-if="show && cable"
      class="modal-overlay"
      @click.self="closeModal"
    >
      <div class="detail-modal-container" @click.stop>
          <!-- Header -->
          <div class="modal-header">
            <div class="header-content">
              <div class="cable-icon" :class="`status-${cableStatus}`">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                </svg>
              </div>
              <div class="cable-title">
                <h2>{{ cable?.name || 'Sem nome' }}</h2>
                <p class="cable-route">
                  {{ cable?.site_a_name || 'Site A' }} 
                  <svg class="arrow-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 8l4 4m0 0l-4 4m4-4H3" />
                  </svg>
                  {{ cable?.site_b_name || 'Site B' }}
                </p>
              </div>
            </div>
            <div class="header-actions">
              <button v-if="canEdit" class="btn-icon" @click="toggleEditMode" :title="isEditMode ? 'Cancelar Edição' : 'Editar Cabo'">
                <svg v-if="!isEditMode" class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                    d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                <svg v-else class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
              <button class="btn-icon close-btn" @click="closeModal" title="Fechar (ESC)">
                <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          <!-- Tabs -->
          <div class="tabs-header">
            <button
              v-for="tab in tabs"
              :key="tab.id"
              class="tab-button"
              :class="{ active: activeTab === tab.id }"
              @click="activeTab = tab.id"
            >
              <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="tab.icon" />
              </svg>
              {{ tab.label }}
            </button>
          </div>

          <!-- Body -->
          <div class="modal-body">
            <!-- Tab: Informações Gerais -->
            <div v-show="activeTab === 'info'" class="tab-content">
              <div class="info-grid">
                <!-- Status e Info Básica -->
                <div class="info-section">
                  <h3>Status e Informações</h3>
                  <div class="info-cards">
                    <div class="stat-card" :class="`status-${cableStatus}`">
                      <div class="stat-label">Status</div>
                      <div class="stat-value">{{ getStatusLabel(cableStatus) }}</div>
                      <div class="stat-detail">{{ cable?.original_status || 'N/A' }}</div>
                    </div>
                    <div class="stat-card">
                      <div class="stat-label">Distância</div>
                      <div class="stat-value">{{ formatDistance() }}</div>
                      <div class="stat-detail">{{ cable?.path_coordinates?.length || 0 }} pontos</div>
                    </div>
                    <div class="stat-card">
                      <div class="stat-label">Fibras</div>
                      <div class="stat-value">{{ cable?.fiber_count || 'N/A' }}</div>
                      <div class="stat-detail">{{ cable?.cable_type || 'Tipo não especificado' }}</div>
                    </div>
                    <div class="stat-card">
                      <div class="stat-label">Atenuação</div>
                      <div class="stat-value" :class="getAttenuationClass()">{{ formatAttenuation() }}</div>
                      <div class="stat-detail">{{ getAttenuationQuality() }}</div>
                    </div>
                  </div>
                </div>

                <!-- Detalhes do Cabo -->
                <div
                  class="info-section collapsible"
                  :class="{ 'is-collapsed': !showCableDetails }"
                >
                  <button
                    type="button"
                    class="collapsible-trigger"
                    @click="toggleCableDetails"
                  >
                    <h3>Detalhes do Cabo</h3>
                    <svg
                      class="icon"
                      :class="{ rotated: showCableDetails }"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 9l-7 7-7-7"
                      />
                    </svg>
                  </button>
                  <transition name="collapse">
                    <div
                      v-show="showCableDetails"
                      class="collapsible-content"
                    >
                      <div class="detail-list">
                        <div class="detail-item">
                          <span class="detail-label">ID</span>
                          <span class="detail-value">{{ cable.id }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">Nome</span>
                          <span class="detail-value">{{ cable.name }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">Site A</span>
                          <span class="detail-value">{{ cable.site_a_name || 'N/A' }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">Site B</span>
                          <span class="detail-value">{{ cable.site_b_name || 'N/A' }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">Tipo de Cabo</span>
                          <span class="detail-value">{{ cable.cable_type || 'N/A' }}</span>
                        </div>
                        <div class="detail-item">
                          <span class="detail-label">Quantidade de Fibras</span>
                          <span class="detail-value">{{ cable.fiber_count || 'N/A' }}</span>
                        </div>
                      </div>
                    </div>
                  </transition>
                </div>

                <!-- Observações -->
                <div v-if="cable.notes || cable.description" class="info-section full-width">
                  <h3>Observações</h3>
                  <div class="notes-box">
                    {{ cable?.notes || cable?.description || 'Sem notas' }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Tab: Nível Óptico -->
            <div v-show="activeTab === 'optical'" class="tab-content">
              <div class="optical-section">
                <div class="section-header">
                  <h3>Nível de Sinal Óptico</h3>
                  <div class="period-selector">
                    <button
                      v-for="period in opticalPeriods"
                      :key="period.value"
                      class="period-btn"
                      :class="{ active: selectedPeriod === period.value }"
                      @click="selectedPeriod = period.value"
                    >
                      {{ period.label }}
                    </button>
                  </div>
                </div>

                <div class="loading-state" v-if="isLoadingOptical">
                  <div class="spinner"></div>
                  <p>Carregando dados ópticos...</p>
                </div>

                <div class="empty-state" v-else-if="!opticalData || (!opticalData.origin && !opticalData.destination)">
                  <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p>Nenhum dado óptico disponível</p>
                  <small>Verifique se a porta possui medição configurada</small>
                </div>

                <!-- Gráficos separados por porta -->
                <div v-else class="port-charts-container">
                  
                  <!-- Porta de Origem -->
                  <div class="port-chart-panel" :class="{ collapsed: !expandedOrigin }">
                    <div class="panel-header" @click="expandedOrigin = !expandedOrigin">
                      <div class="port-info">
                        <div class="port-icon origin">
                          <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M5 12h14M5 12l4-4m-4 4l4 4" />
                          </svg>
                        </div>
                        <div class="port-details">
                          <h4>{{ opticalData?.portInfo?.origin?.device || 'Dispositivo Origem' }}</h4>
                          <p>{{ opticalData?.portInfo?.origin?.port || 'Porta não identificada' }}</p>
                        </div>
                      </div>
                      <button class="collapse-btn">
                        <svg class="icon" :class="{ rotated: expandedOrigin }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                    </div>
                    
                    <div class="panel-content" v-show="expandedOrigin">
                      <div class="optical-chart-container">
                        <canvas ref="originChartCanvas"></canvas>
                      </div>
                      <div class="optical-stats">
                        <div class="stat-box">
                          <div class="stat-icon good">RX</div>
                          <div class="stat-info">
                            <div class="stat-label">Médio</div>
                            <div class="stat-value">{{ formatDbm(opticalData?.stats?.origin?.avgRx) }}</div>
                          </div>
                        </div>
                        <div class="stat-box">
                          <div class="stat-icon info">TX</div>
                          <div class="stat-info">
                            <div class="stat-label">Médio</div>
                            <div class="stat-value">{{ formatDbm(opticalData?.stats?.origin?.avgTx) }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Porta de Destino -->
                  <div class="port-chart-panel" :class="{ collapsed: !expandedDestination }">
                    <div class="panel-header" @click="expandedDestination = !expandedDestination">
                      <div class="port-info">
                        <div class="port-icon destination">
                          <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                              d="M19 12H5m14 0l-4 4m4-4l-4-4" />
                          </svg>
                        </div>
                        <div class="port-details">
                          <h4>{{ opticalData?.portInfo?.destination?.device || 'Dispositivo Destino' }}</h4>
                          <p>{{ opticalData?.portInfo?.destination?.port || 'Porta não identificada' }}</p>
                        </div>
                      </div>
                      <button class="collapse-btn">
                        <svg class="icon" :class="{ rotated: expandedDestination }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                        </svg>
                      </button>
                    </div>
                    
                    <div class="panel-content" v-show="expandedDestination">
                      <div class="optical-chart-container">
                        <canvas ref="destinationChartCanvas"></canvas>
                      </div>
                      <div class="optical-stats">
                        <div class="stat-box">
                          <div class="stat-icon good">RX</div>
                          <div class="stat-info">
                            <div class="stat-label">Médio</div>
                            <div class="stat-value">{{ formatDbm(opticalData?.stats?.destination?.avgRx) }}</div>
                          </div>
                        </div>
                        <div class="stat-box">
                          <div class="stat-icon info">TX</div>
                          <div class="stat-info">
                            <div class="stat-label">Médio</div>
                            <div class="stat-value">{{ formatDbm(opticalData?.stats?.destination?.avgTx) }}</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                </div>
              </div>
            </div>

            <!-- Tab: Alarmes -->
            <div v-show="activeTab === 'alarms'" class="tab-content">
              <div class="alarms-section">
                <div class="section-header">
                  <h3>Alarmes e Eventos</h3>
                  <button class="btn-primary-small" @click="configureAlarms">
                    <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    Configurar Alarmes
                  </button>
                </div>

                <div class="alarms-list">
                  <div v-if="!alarms.length" class="empty-state">
                    <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <p>Nenhum alarme ativo</p>
                  </div>
                  <div v-for="alarm in alarms" :key="alarm.id" class="alarm-item" :class="`severity-${alarm.severity}`">
                    <div class="alarm-icon">
                      <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                    <div class="alarm-content">
                      <div class="alarm-title">{{ alarm.title }}</div>
                      <div class="alarm-description">{{ alarm.description }}</div>
                      <div class="alarm-time">{{ formatAlarmTime(alarm.timestamp) }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Tab: Histórico -->
            <div v-show="activeTab === 'history'" class="tab-content">
              <div class="history-section">
                <h3>Histórico de Manutenção</h3>
                <div class="timeline">
                  <div v-if="!historyEvents.length" class="empty-state">
                    <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                    <p>Nenhum evento registrado</p>
                  </div>
                  <div v-for="event in historyEvents" :key="event.id" class="timeline-item">
                    <div class="timeline-marker" :class="`type-${event.type}`"></div>
                    <div class="timeline-content">
                      <div class="event-header">
                        <span class="event-title">{{ event.title }}</span>
                        <span class="event-date">{{ formatEventDate(event.date) }}</span>
                      </div>
                      <div class="event-description">{{ event.description }}</div>
                      <div v-if="event.user" class="event-user">Por: {{ event.user }}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Configure Alarms Modal -->
          <div v-if="showAlarmModal" class="alarm-modal-backdrop" @click.self="closeAlarmModal">
            <div class="alarm-modal">
              <div class="alarm-modal-header">
                <h3>Configurar Alarmes</h3>
                <button class="close-btn" @click="closeAlarmModal">
                  <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div class="alarm-modal-content">
                <section class="saved-configs-section">
                  <h4>Configurações existentes</h4>
                  <div v-if="isLoadingAlarmConfigs" class="saved-configs-loading">
                    <span class="spinner small"></span>
                    <span>Carregando configurações...</span>
                  </div>
                  <div v-else-if="savedAlarmConfigs.length" class="saved-configs-list">
                    <div v-for="config in savedAlarmConfigs" :key="config.id" class="saved-config-card">
                      <div class="saved-config-header">
                        <span class="saved-config-target">{{ config.targetDisplay }}</span>
                        <span class="saved-config-level" :class="`level-${config.triggerLevel}`">{{ config.triggerLabel }}</span>
                      </div>
                      <div class="saved-config-channels">
                        <span v-for="channel in config.channels" :key="channel" class="saved-config-channel">
                          {{ channelLabelDictionary[channel] || channel }}
                        </span>
                      </div>
                      <div class="saved-config-meta">
                        <span>{{ formatPersistLabel(config.persistMinutes) }}</span>
                        <span v-if="config.createdAt">Atualizado {{ formatAlarmTime(config.createdAt) }}</span>
                      </div>
                      <p v-if="config.description" class="saved-config-notes">{{ config.description }}</p>
                    </div>
                  </div>
                  <div v-else class="saved-configs-empty">
                    Nenhuma configuração cadastrada para este cabo.
                  </div>
                </section>

                <section>
                  <h4>Alvo do Alarme</h4>
                  <div class="target-options">
                    <label class="target-option">
                      <input type="radio" value="department_group" v-model="alarmForm.target"
                        @change="resetTargetDetails" />
                      <span>Grupo de Departamento</span>
                    </label>
                    <label class="target-option">
                      <input type="radio" value="system_user" v-model="alarmForm.target"
                        @change="resetTargetDetails" />
                      <span>Usuário do Sistema</span>
                    </label>
                    <label class="target-option">
                      <input type="radio" value="contact" v-model="alarmForm.target"
                        @change="resetTargetDetails" />
                      <span>Contato Cadastrado</span>
                    </label>
                  </div>

                  <div class="target-selector" v-if="alarmForm.target === 'department_group'">
                    <label>Selecionar Grupo</label>
                    <select v-model="alarmForm.departmentGroup" :disabled="isContactsLoading && !departmentGroups.length">
                      <option disabled value="">{{ isContactsLoading && !departmentGroups.length ? 'Carregando grupos...' : 'Selecione um grupo' }}</option>
                      <option v-for="group in departmentGroups" :key="group.id" :value="group.id">
                        {{ group.name }} ({{ group.contact_count ?? 0 }} contatos)
                      </option>
                    </select>
                  </div>

                  <div class="target-selector" v-else-if="alarmForm.target === 'system_user'">
                    <label>Selecionar Usuário</label>
                    <select v-model="alarmForm.systemUser" :disabled="isContactsLoading && !systemUsers.length">
                      <option disabled value="">{{ isContactsLoading && !systemUsers.length ? 'Carregando usuários...' : 'Selecione um usuário' }}</option>
                      <option v-for="user in systemUsers" :key="user.id" :value="user.id">
                        {{ user.name }}<span v-if="user.email"> ({{ user.email }})</span>
                      </option>
                    </select>
                  </div>

                  <div class="target-selector" v-else-if="alarmForm.target === 'contact'">
                    <label>Selecionar Contato</label>
                    <select v-model="alarmForm.contact" :disabled="isContactsLoading && !contactOptions.length">
                      <option disabled value="">{{ isContactsLoading && !contactOptions.length ? 'Carregando contatos...' : 'Selecione um contato' }}</option>
                      <option v-for="contact in contactOptions" :key="contact.id" :value="contact.id">
                        {{ contact.name }} ({{ contact.summary }})
                      </option>
                    </select>
                  </div>
                </section>

                <section>
                  <h4>Tipos de Notificação</h4>
                  <div class="channel-grid">
                    <label v-for="channel in availableChannels" :key="channel.id" class="channel-option">
                      <input type="checkbox" :value="channel.id" v-model="alarmForm.channels" />
                      <span class="channel-icon" :class="channel.id">{{ channel.label }}</span>
                    </label>
                  </div>
                </section>

                <section>
                  <h4>Condições</h4>
                  <div class="conditions-grid">
                    <label>
                      <span>Acionar em nível</span>
                      <select v-model="alarmForm.triggerLevel">
                        <option value="warning">Atenção</option>
                        <option value="critical">Crítico</option>
                      </select>
                    </label>
                    <label>
                      <span>Persistência mínima</span>
                      <input type="number" min="0" step="1" v-model.number="alarmForm.persistMinutes" />
                      <small>Minutos de duração antes do disparo</small>
                    </label>
                  </div>
                </section>
              </div>

              <div class="alarm-modal-footer">
                <button class="btn-secondary" @click="closeAlarmModal">Cancelar</button>
                <button class="btn-primary" :disabled="!canSaveAlarm" @click="saveAlarmConfig">
                  <svg v-if="isSavingAlarm" class="icon spinning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span v-else>Salvar</span>
                  <span v-if="!isSavingAlarm"> configuração</span>
                </button>
              </div>
            </div>
          </div>

          <!-- Footer -->
          <div class="modal-footer">
            <button class="btn-secondary" @click="closeModal">
              Fechar
            </button>
            <button v-if="isEditMode" class="btn-primary" @click="saveChanges" :disabled="isSaving">
              <svg v-if="!isSaving" class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              <svg v-else class="icon spinning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              {{ isSaving ? 'Salvando...' : 'Salvar Alterações' }}
            </button>
          </div>
        </div>
      </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useEscapeKey } from '@/composables/useEscapeKey'
import Chart from 'chart.js/auto'
import { getCableOpticalHistory, getCableAlarms, createCableAlarm } from '@/services/fiberService'
import { useContactsStore } from '@/stores/contacts'
import { useAlertTemplatesStore } from '@/stores/alertTemplates'

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  cable: {
    type: Object,
    default: null
  },
  canEdit: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['close', 'save'])

// Estado
const activeTab = ref('info')
const isEditMode = ref(false)
const isSaving = ref(false)
const originChartCanvas = ref(null)
const destinationChartCanvas = ref(null)
const expandedOrigin = ref(true)
const expandedDestination = ref(false)
const showCableDetails = ref(true)
let originChart = null
let destinationChart = null
let originChartRetry = 0
let destinationChartRetry = 0
const MAX_CHART_RETRIES = 6

const contactsStore = useContactsStore()
const alertTemplatesStore = useAlertTemplatesStore()

const { templates: alertTemplates, loading: templatesLoading, meta: templateMeta } = storeToRefs(alertTemplatesStore)

const contacts = computed(() => contactsStore.contacts || [])
const departmentGroups = computed(() => contactsStore.groups || [])

const buildContactSummary = (contact) => {
  if (!contact) return 'Sem detalhes'
  const parts = []
  if (contact.phone) parts.push(contact.phone)
  if (contact.email) parts.push(contact.email)
  if (contact.company) parts.push(contact.company)
  return parts.join(' • ') || 'Sem detalhes'
}

const contactOptions = computed(() => contacts.value.map(contact => ({
  id: contact.id,
  name: contact.name || 'Contato sem nome',
  summary: buildContactSummary(contact)
})))

const systemUsers = computed(() => contacts.value
  .filter(contact => contact.user)
  .map(contact => ({
    id: contact.user,
    name: contact.user_name || contact.name || 'Usuário do sistema',
    email: contact.email || contact.company || null,
    contactId: contact.id
  })))

const isContactsLoading = computed(() => contactsStore.loading)

// Aguarda canvas ficar disponível antes de criar o gráfico
const waitForCanvas = async (canvasRef, retries = 6, delay = 80) => {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    if (canvasRef.value) {
      return canvasRef.value
    }
    await nextTick()
    if (delay > 0) {
      await new Promise(resolve => setTimeout(resolve, delay))
    }
  }

  return null
}

// Tabs
const tabs = [
  {
    id: 'info',
    label: 'Informações',
    icon: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
  },
  {
    id: 'optical',
    label: 'Nível Óptico',
    icon: 'M13 10V3L4 14h7v7l9-11h-7z'
  },
  {
    id: 'alarms',
    label: 'Alarmes',
    icon: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9'
  },
  {
    id: 'history',
    label: 'Histórico',
    icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z'
  }
]

// Períodos para o gráfico óptico
const opticalPeriods = [
  { value: 1, label: '1h' },
  { value: 6, label: '6h' },
  { value: 24, label: '24h' },
  { value: 168, label: '7d' },
  { value: 720, label: '30d' }
]

// Estados para dados reais
const alarms = ref([])
const historyEvents = ref([])
const opticalData = ref(null)
const opticalStats = ref(null)
const isLoadingOptical = ref(false)
const showAlarmModal = ref(false)
const isSavingAlarm = ref(false)
const savedAlarmConfigs = ref([])
const isLoadingAlarmConfigs = ref(false)

const TEMPLATE_CATEGORY = 'optical_level'

const createDefaultAlarmForm = () => ({
  target: 'department_group',
  departmentGroup: '',
  systemUser: '',
  contact: '',
  channels: [],
  triggerLevel: 'warning',
  persistMinutes: 0,
  templates: {},
})

const alarmForm = ref(createDefaultAlarmForm())

const availableChannels = [
  { id: 'email', label: 'E-mail' },
  { id: 'whatsapp', label: 'WhatsApp' },
  { id: 'sms', label: 'SMS' },
  { id: 'telegram', label: 'Telegram' }
]

const channelLabelDictionary = availableChannels.reduce((acc, channel) => {
  acc[channel.id] = channel.label
  return acc
}, {})

const templatesLoaded = ref(false)

const ensureTemplateDataLoaded = async () => {
  if (templatesLoaded.value) {
    return
  }
  try {
    await alertTemplatesStore.loadTemplates({ category: TEMPLATE_CATEGORY, is_active: 'true' })
  } finally {
    templatesLoaded.value = true
  }
}

const templateOptionsByChannel = computed(() => {
  const grouped = {}
  const list = alertTemplates.value || []
  availableChannels.forEach(channel => {
    grouped[channel.id] = list
      .filter(template => template.category === TEMPLATE_CATEGORY && template.channel === channel.id && template.is_active !== false)
      .map(template => ({
        id: template.id,
        name: template.name,
        label: template.is_default ? `${template.name} (Padrão)` : template.name,
        isDefault: Boolean(template.is_default),
      }))
  })
  return grouped
})

const hasTemplatesAvailable = computed(() => {
  return availableChannels.some(channel => (templateOptionsByChannel.value[channel.id] || []).length > 0)
})

const getDefaultTemplateIdForChannel = (channelId) => {
  const options = templateOptionsByChannel.value[channelId] || []
  if (!options.length) return null
  const preferred = options.find(option => option.isDefault)
  return (preferred || options[0]).id
}

const syncTemplatesSelection = () => {
  if (!alarmForm.value) return
  const selectedChannels = Array.isArray(alarmForm.value.channels) ? [...alarmForm.value.channels] : []
  const currentTemplates = { ...(alarmForm.value.templates || {}) }
  let changed = false

  Object.keys(currentTemplates).forEach(channel => {
    if (!selectedChannels.includes(channel)) {
      delete currentTemplates[channel]
      changed = true
    }
  })

  selectedChannels.forEach(channel => {
    const options = templateOptionsByChannel.value[channel] || []
    if (!options.length) {
      if (currentTemplates[channel]) {
        delete currentTemplates[channel]
        changed = true
      }
      return
    }
    const exists = options.some(option => option.id === currentTemplates[channel])
    if (!exists) {
      const defaultId = getDefaultTemplateIdForChannel(channel)
      if (defaultId) {
        currentTemplates[channel] = defaultId
        changed = true
      }
    }
  })

  if (changed) {
    alarmForm.value.templates = currentTemplates
  }
}

watch(
  () => [...alarmForm.value.channels],
  () => {
    syncTemplatesSelection()
  }
)

watch(
  templateOptionsByChannel,
  () => {
    syncTemplatesSelection()
  },
  { deep: true }
)

// Fechar modal com ESC
useEscapeKey(() => {
  if (props.show && !isEditMode.value) {
    closeModal()
  }
})

const closeModal = () => {
  if (isEditMode.value) {
    const confirm = window.confirm('Deseja descartar as alterações?')
    if (!confirm) return
    isEditMode.value = false
  }
  originChartRetry = 0
  destinationChartRetry = 0
  showAlarmModal.value = false
  emit('close')
}

const toggleEditMode = () => {
  isEditMode.value = !isEditMode.value
}

const toggleCableDetails = () => {
  showCableDetails.value = !showCableDetails.value
}

// Carregar dados ópticos reais
const loadOpticalData = async () => {
  if (!props.cable?.id) return
  
  isLoadingOptical.value = true
  console.log('[FiberCableDetailModal] Carregando dados ópticos para cabo', props.cable.id)
  
  try {
    // Converter período selecionado para horas
    const periodHours = selectedPeriod.value
    console.log(`[FiberCableDetailModal] Buscando histórico de ${periodHours} horas`)
    
    // Buscar histórico real do Zabbix para ambas as portas
    const historyData = await getCableOpticalHistory(props.cable.id, periodHours)
    
    if (historyData && (historyData.origin || historyData.destination)) {
      console.log('[FiberCableDetailModal] Histórico recebido do Zabbix:', historyData)
      
      // Dados já vêm formatados do service
      opticalData.value = historyData
      
      console.log('[FiberCableDetailModal] Dados formatados:', opticalData.value)
      
      // Criar gráficos após carregar dados
      await nextTick()
      if (activeTab.value === 'optical') {
        await createOpticalCharts()
      }
    } else {
      console.warn('[FiberCableDetailModal] Sem dados ópticos disponíveis no histórico')
      opticalData.value = null
    }
  } catch (error) {
    console.error('[FiberCableDetailModal] Erro ao carregar dados ópticos:', error)
    opticalData.value = null
  } finally {
    isLoadingOptical.value = false
  }
}

const saveChanges = async () => {
  isSaving.value = true
  try {
    // TODO: Implementar salvamento no backend
    await new Promise(resolve => setTimeout(resolve, 1000))
    emit('save', props.cable)
    isEditMode.value = false
  } catch (error) {
    console.error('Erro ao salvar:', error)
    alert('Erro ao salvar alterações')
  } finally {
    isSaving.value = false
  }
}

const resetAlarmForm = () => {
  alarmForm.value = createDefaultAlarmForm()
  syncTemplatesSelection()
}

const ensureContactDataLoaded = async () => {
  const loaders = []
  if (!contactsStore.contacts.length) {
    loaders.push(contactsStore.loadContacts({ is_active: true }))
  }
  if (!contactsStore.groups.length) {
    loaders.push(contactsStore.loadGroups())
  }
  if (loaders.length) {
    await Promise.allSettled(loaders)
  }
}

const normalizeChannels = (channels) => {
  if (!channels) return []
  if (Array.isArray(channels)) return channels.filter(Boolean)
  if (typeof channels === 'string') {
    return channels.split(',').map(item => item.trim()).filter(Boolean)
  }
  if (typeof channels === 'object') {
    return Object.keys(channels).filter(key => channels[key])
  }
  return []
}

const levelLabelMap = {
  warning: 'Atenção',
  critical: 'Crítico',
  info: 'Informativo',
  alert: 'Alerta'
}

const getLevelLabel = (level) => levelLabelMap[level] || level?.toUpperCase?.() || 'Alarme'

const normalizeAlarmConfig = (config) => {
  if (!config) return null
  const triggerLevel = String(config.trigger_level || config.level || config.severity || 'warning').toLowerCase()
  const channels = normalizeChannels(
    config.channels ||
    config.notification_channels ||
    config.alarm_channels ||
    config.notifications
  )
  const persistRaw = config.persist_minutes ?? config.persist_for ?? config.duration_minutes ?? 0
  const persistMinutes = Number.isFinite(Number(persistRaw)) ? Number(persistRaw) : 0
  const targetType = config.target_type || config.target?.type || config.target || 'department_group'
  const targetName = config.target_display || config.target_name || config.target?.name || config.name || 'Configuração de alarme'
  const templatesMeta = config.templates || config.metadata?.templates || {}
  const templateBindings = templatesMeta?.bindings || {}
  const templateSnapshots = templatesMeta?.snapshots || {}
  const channelDetails = channels.map(channel => ({
    id: channel,
    label: channelLabelDictionary[channel] || channel.toUpperCase(),
    templateId: templateBindings[channel] || null,
    templateName: templateSnapshots?.[channel]?.name || null,
  }))

  return {
    id: config.id || config.uuid || `${targetType}-${targetName}-${channels.join('-')}`,
    targetType,
    targetDisplay: targetName,
    channels,
    channelDetails,
    triggerLevel,
    triggerLabel: getLevelLabel(triggerLevel),
    persistMinutes,
    createdAt: config.created_at || config.updated_at || config.timestamp || null,
    description: config.description || config.notes || '',
    templates: templatesMeta,
    raw: config
  }
}

const loadCableAlarmConfigs = async (cableId = props.cable?.id) => {
  if (!cableId) {
    savedAlarmConfigs.value = []
    return
  }
  isLoadingAlarmConfigs.value = true
  try {
    const response = await getCableAlarms(cableId)
    const payload = response?.results || response?.data || response || []
    const configs = Array.isArray(payload) ? payload : []
    savedAlarmConfigs.value = configs
      .map(normalizeAlarmConfig)
      .filter(Boolean)
  } catch (error) {
    console.error('[FiberCableDetailModal] Erro ao carregar configurações de alarmes:', error)
    savedAlarmConfigs.value = []
  } finally {
    isLoadingAlarmConfigs.value = false
  }
}

const setDefaultTargetSelection = () => {
  const target = alarmForm.value.target
  if (target === 'department_group' && !alarmForm.value.departmentGroup && departmentGroups.value.length) {
    alarmForm.value.departmentGroup = departmentGroups.value[0].id
  }
  if (target === 'system_user' && !alarmForm.value.systemUser && systemUsers.value.length) {
    alarmForm.value.systemUser = systemUsers.value[0].id
  }
  if (target === 'contact' && !alarmForm.value.contact && contactOptions.value.length) {
    alarmForm.value.contact = contactOptions.value[0].id
  }
}

const configureAlarms = async () => {
  await Promise.all([
    ensureContactDataLoaded(),
    ensureTemplateDataLoaded(),
  ])
  resetAlarmForm()
  setDefaultTargetSelection()
  syncTemplatesSelection()
  await loadCableAlarmConfigs()
  console.debug('[FiberCableDetailModal] Abrindo modal de alarmes')
  showAlarmModal.value = true
}

const closeAlarmModal = () => {
  if (isSavingAlarm.value) {
    return
  }
  console.debug('[FiberCableDetailModal] Fechando modal de alarmes')
  showAlarmModal.value = false
}

const resetTargetDetails = () => {
  alarmForm.value.departmentGroup = ''
  alarmForm.value.systemUser = ''
  alarmForm.value.contact = ''
  nextTick(() => {
    setDefaultTargetSelection()
  })
}

const canSaveAlarm = computed(() => {
  if (!alarmForm.value.target) {
    return false
  }
  if (!alarmForm.value.channels.length) {
    return false
  }
  if (alarmForm.value.target === 'department_group' && !alarmForm.value.departmentGroup) {
    return false
  }
  if (alarmForm.value.target === 'system_user' && !alarmForm.value.systemUser) {
    return false
  }
  if (alarmForm.value.target === 'contact' && !alarmForm.value.contact) {
    return false
  }
  return true
})

const saveAlarmConfig = async () => {
  if (!canSaveAlarm.value || !props.cable?.id) {
    return
  }

  isSavingAlarm.value = true
  try {
    const payload = {
      target: alarmForm.value.target,
      department_group: alarmForm.value.target === 'department_group' ? alarmForm.value.departmentGroup : null,
      system_user: alarmForm.value.target === 'system_user' ? alarmForm.value.systemUser : null,
      contact: alarmForm.value.target === 'contact' ? alarmForm.value.contact : null,
      channels: [...alarmForm.value.channels],
      trigger_level: alarmForm.value.triggerLevel,
      persist_minutes: alarmForm.value.persistMinutes ?? 0,
      template_category: TEMPLATE_CATEGORY,
    }

    const templatePayload = {}
    if (alarmForm.value.templates) {
      Object.entries(alarmForm.value.templates).forEach(([channel, templateId]) => {
        if (!alarmForm.value.channels.includes(channel)) {
          return
        }
        if (templateId) {
          templatePayload[channel] = templateId
        }
      })
    }

    if (Object.keys(templatePayload).length > 0) {
      payload.templates = templatePayload
    }

    await createCableAlarm(props.cable.id, payload)
    await loadCableAlarmConfigs(props.cable.id)
    showAlarmModal.value = false
  } catch (error) {
    console.error('[FiberCableDetailModal] Falha ao salvar configuração de alarme:', error)
    window.alert(error?.message || 'Não foi possível salvar a configuração de alarme.')
  } finally {
    isSavingAlarm.value = false
  }
}

// Computeds
const cableStatus = computed(() => {
  if (!props.cable) return 'unknown'
  return String(props.cable.status || 'unknown').toLowerCase()
})

// Cálculo de atenuação baseado na distância
const calculatedAttenuation = computed(() => {
  if (!props.cable) return null
  
  // Fórmula básica: atenuação = distância_km * fator_atenuação
  // Fibra monomodo típica: ~0.3 dB/km em 1550nm
  // Fibra multimodo típica: ~2.5 dB/km em 850nm
  
  const distance = parseFloat(props.cable.length_km) || 0
  const attenuationFactor = props.cable.cable_type?.toLowerCase().includes('multimodo') ? 2.5 : 0.3
  
  // Adicionar perdas por conectores/emendas (estimativa: 0.5 dB por conexão)
  const connectionLoss = (props.cable.path_coordinates?.length || 2) * 0.1
  
  return (distance * attenuationFactor) + connectionLoss
})

const selectedPeriod = ref(24) // horas

// Níveis ópticos computados dos dados reais
const averageOpticalLevel = computed(() => {
  if (!opticalStats.value || opticalStats.value.avgRx === null || opticalStats.value.avgTx === null) return null
  return ((opticalStats.value.avgRx + opticalStats.value.avgTx) / 2).toFixed(2)
})

const minOpticalLevel = computed(() => {
  if (!opticalStats.value || opticalStats.value.minRx === null || opticalStats.value.minTx === null) return null
  return Math.min(opticalStats.value.minRx, opticalStats.value.minTx).toFixed(2)
})

const maxOpticalLevel = computed(() => {
  if (!opticalStats.value || opticalStats.value.maxRx === null || opticalStats.value.maxTx === null) return null
  return Math.max(opticalStats.value.maxRx, opticalStats.value.maxTx).toFixed(2)
})

const getStatusLabel = (status) => {
  const labels = {
    online: 'ONLINE',
    offline: 'OFFLINE',
    warning: 'ATENÇÃO',
    critical: 'CRÍTICO',
    unknown: 'DESCONHECIDO',
    up: 'OPERACIONAL',
    down: 'INOPERANTE'
  }
  return labels[status] || 'DESCONHECIDO'
}

const formatDistance = () => {
  if (!props.cable) return 'N/A'
  if (props.cable.length_km) {
    return `${props.cable.length_km} km`
  }
  if (props.cable.length_meters) {
    return `${props.cable.length_meters} m`
  }
  return 'N/A'
}

const formatAttenuation = () => {
  if (calculatedAttenuation.value === null) return 'N/A'
  return `${calculatedAttenuation.value.toFixed(2)} dB`
}

const getAttenuationClass = () => {
  if (calculatedAttenuation.value === null) return ''
  if (calculatedAttenuation.value <= 3.0) return 'good'
  if (calculatedAttenuation.value <= 10.0) return 'warning'
  return 'critical'
}

const getAttenuationQuality = () => {
  if (calculatedAttenuation.value === null) return 'N/A'
  if (calculatedAttenuation.value <= 3.0) return 'Excelente'
  if (calculatedAttenuation.value <= 5.0) return 'Bom'
  if (calculatedAttenuation.value <= 10.0) return 'Regular'
  return 'Crítico'
}

const formatOpticalLevel = (value) => {
  if (value === null || value === undefined) return 'N/A'
  return `${value.toFixed(2)} dBm`
}

const formatAlarmTime = (timestamp) => {
  if (!timestamp) return 'N/A'
  const date = new Date(timestamp)
  return date.toLocaleString('pt-BR')
}

const formatPersistLabel = (minutes) => {
  if (!minutes) return 'Disparo imediato'
  if (minutes === 1) return 'Persistência mínima: 1 minuto'
  return `Persistência mínima: ${minutes} minutos`
}

const formatEventDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('pt-BR')
}

// Criar/atualizar gráficos ópticos (dois gráficos separados)
const createOpticalCharts = async () => {
  console.log('[FiberCableDetailModal] createOpticalCharts chamado')
  
  if (expandedOrigin.value && opticalData.value?.origin) {
    await createOriginChart()
  }
  
  if (expandedDestination.value && opticalData.value?.destination) {
    await createDestinationChart()
  }
}

const createOriginChart = async () => {
  const canvasEl = await waitForCanvas(originChartCanvas)

  if (!canvasEl || !opticalData.value?.origin) {
    if (originChartRetry < MAX_CHART_RETRIES) {
      originChartRetry += 1
      console.warn('[FiberCableDetailModal] Canvas origem não encontrado, tentando novamente...', {
        attempt: originChartRetry,
        hasCanvas: !!canvasEl,
        hasData: !!opticalData.value?.origin
      })
      setTimeout(() => {
        createOriginChart()
      }, 150)
    } else {
      console.error('[FiberCableDetailModal] Falha ao obter canvas origem após múltiplas tentativas', {
        attempts: originChartRetry,
        hasCanvas: !!canvasEl,
        hasData: !!opticalData.value?.origin
      })
      originChartRetry = 0
    }
    return
  }
  
  try {
    originChartRetry = 0
    const ctx = canvasEl.getContext('2d')
    
    if (originChart) {
      originChart.destroy()
    }
    
    const originData = opticalData.value.origin
    console.log('[FiberCableDetailModal] Criando gráfico origem com', originData.labels.length, 'pontos')

    const datasets = [
      {
        label: 'RX (dBm)',
        data: originData.rxData,
        borderColor: '#3b82f6',
        backgroundColor: 'transparent',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        spanGaps: true,
        order: 1
      },
      {
        label: 'TX (dBm)',
        data: originData.txData,
        borderColor: '#10b981',
        backgroundColor: 'transparent',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        spanGaps: true,
        order: 1
      }
    ]

    if (originData.warningLine) {
      datasets.push({
        label: 'Atenção',
        data: originData.warningLine,
        borderColor: '#fbbf24',
        borderDash: [6, 6],
        borderWidth: 1.5,
        fill: false,
        pointRadius: 0,
        tension: 0,
        spanGaps: true,
        order: 5
      })
    }

    if (originData.criticalLine) {
      datasets.push({
        label: 'Crítico',
        data: originData.criticalLine,
        borderColor: '#f87171',
        borderDash: [6, 6],
        borderWidth: 1.5,
        fill: false,
        pointRadius: 0,
        tension: 0,
        spanGaps: true,
        order: 5
      })
    }

    originChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: originData.labels,
        datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: '#94a3b8'
            }
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: '#3b82f6',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#94a3b8',
              maxRotation: 45,
              minRotation: 45
            }
          },
          y: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#94a3b8',
              callback: (value) => `${value} dBm`
            }
          }
        }
      }
    })
    
    console.log('[FiberCableDetailModal] Gráfico origem criado com sucesso')
  } catch (error) {
    console.error('[FiberCableDetailModal] Erro ao criar gráfico origem:', error)
  }
}

const createDestinationChart = async () => {
  const canvasEl = await waitForCanvas(destinationChartCanvas)

  if (!canvasEl || !opticalData.value?.destination) {
    if (destinationChartRetry < MAX_CHART_RETRIES) {
      destinationChartRetry += 1
      console.warn('[FiberCableDetailModal] Canvas destino não encontrado, tentando novamente...', {
        attempt: destinationChartRetry,
        hasCanvas: !!canvasEl,
        hasData: !!opticalData.value?.destination
      })
      setTimeout(() => {
        createDestinationChart()
      }, 150)
    } else {
      console.error('[FiberCableDetailModal] Falha ao obter canvas destino após múltiplas tentativas', {
        attempts: destinationChartRetry,
        hasCanvas: !!canvasEl,
        hasData: !!opticalData.value?.destination
      })
      destinationChartRetry = 0
    }
    return
  }
  
  try {
    destinationChartRetry = 0
    const ctx = canvasEl.getContext('2d')
    
    if (destinationChart) {
      destinationChart.destroy()
    }
    
    const destinationData = opticalData.value.destination
    console.log('[FiberCableDetailModal] Criando gráfico destino com', destinationData.labels.length, 'pontos')

    const datasets = [
      {
        label: 'RX (dBm)',
        data: destinationData.rxData,
        borderColor: '#f59e0b',
        backgroundColor: 'transparent',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        spanGaps: true,
        order: 1
      },
      {
        label: 'TX (dBm)',
        data: destinationData.txData,
        borderColor: '#ec4899',
        backgroundColor: 'transparent',
        borderWidth: 2,
        fill: false,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        spanGaps: true,
        order: 1
      }
    ]

    if (destinationData.warningLine) {
      datasets.push({
        label: 'Atenção',
        data: destinationData.warningLine,
        borderColor: '#fbbf24',
        borderDash: [6, 6],
        borderWidth: 1.5,
        fill: false,
        pointRadius: 0,
        tension: 0,
        spanGaps: true,
        order: 5
      })
    }

    if (destinationData.criticalLine) {
      datasets.push({
        label: 'Crítico',
        data: destinationData.criticalLine,
        borderColor: '#f87171',
        borderDash: [6, 6],
        borderWidth: 1.5,
        fill: false,
        pointRadius: 0,
        tension: 0,
        spanGaps: true,
        order: 5
      })
    }

    destinationChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: destinationData.labels,
        datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            labels: {
              color: '#94a3b8'
            }
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#fff',
            bodyColor: '#fff',
            borderColor: '#f59e0b',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#94a3b8',
              maxRotation: 45,
              minRotation: 45
            }
          },
          y: {
            grid: {
              color: 'rgba(255, 255, 255, 0.1)'
            },
            ticks: {
              color: '#94a3b8',
              callback: (value) => `${value} dBm`
            }
          }
        }
      }
    })
    
    console.log('[FiberCableDetailModal] Gráfico destino criado com sucesso')
  } catch (error) {
    console.error('[FiberCableDetailModal] Erro ao criar gráfico destino:', error)
  }
}

// Helper para formatar valores dBm
const formatDbm = (value) => {
  if (value === null || value === undefined || isNaN(value)) return 'N/A'
  return `${value.toFixed(2)} dBm`
}

// Watch para recriar gráficos quando expandir/colapsar
watch(expandedOrigin, async (isExpanded) => {
  if (isExpanded && opticalData.value?.origin) {
    await createOriginChart()
  }
})

watch(expandedDestination, async (isExpanded) => {
  if (isExpanded && opticalData.value?.destination) {
    await createDestinationChart()
  }
})

watch(departmentGroups, (groups) => {
  if (groups.length) {
    setDefaultTargetSelection()
  }
})

watch(systemUsers, (users) => {
  if (users.length) {
    setDefaultTargetSelection()
  }
})

watch(contactOptions, (options) => {
  if (options.length) {
    setDefaultTargetSelection()
  }
})

watch(() => alarmForm.value.target, () => {
  setDefaultTargetSelection()
})

watch(() => props.cable?.id, (cableId) => {
  if (cableId && props.show) {
    loadCableAlarmConfigs(cableId)
  } else if (!cableId) {
    savedAlarmConfigs.value = []
  }
})

// Watch para carregar dados quando modal abrir ou cabo mudar
watch(() => [props.show, props.cable], async ([show, cable]) => {
  if (show && cable) {
    showCableDetails.value = true
    await Promise.allSettled([
      loadOpticalData(),
      loadCableAlarmConfigs(cable.id)
    ])
  }
})

// Watch para criar gráficos quando mudar para tab optical
watch(activeTab, async (newTab) => {
  if (newTab === 'optical' && opticalData.value && props.show) {
    await nextTick()
    await createOpticalCharts()
  }
})

// Watch para recriar gráficos quando mudar período
watch(selectedPeriod, async () => {
  if (props.show && activeTab.value === 'optical') {
    await loadOpticalData()
  }
})

onMounted(() => {
  if (props.show && activeTab.value === 'optical' && opticalData.value) {
    nextTick(async () => {
      await createOpticalCharts()
    })
  }
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
  padding: 20px;
}

.detail-modal-container {
  background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
  max-width: 1000px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

/* Header */
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.05) 0%, transparent 100%);
}

.header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.cable-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.cable-icon.status-online {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.cable-icon.status-offline {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.cable-icon.status-warning {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.cable-icon .icon {
  width: 32px;
  height: 32px;
  color: white;
}

.cable-title h2 {
  margin: 0;
  color: white;
  font-size: 22px;
  font-weight: 700;
  line-height: 1.3;
}

.cable-route {
  margin: 6px 0 0 0;
  color: #94a3b8;
  font-size: 14px;
  line-height: 1.3;
  display: flex;
  align-items: center;
  gap: 8px;
}

.arrow-icon {
  width: 16px;
  height: 16px;
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.btn-icon:hover {
  background: rgba(59, 130, 246, 0.2);
  border-color: rgba(59, 130, 246, 0.3);
  color: #60a5fa;
}

.btn-icon.close-btn:hover {
  background: rgba(239, 68, 68, 0.2);
  border-color: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
}

.btn-icon .icon {
  width: 20px;
  height: 20px;
}

/* Tabs */
.tabs-header {
  display: flex;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  padding: 0 24px;
  overflow-x: auto;
}

.tab-button {
  padding: 16px 20px;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-button .icon {
  width: 18px;
  height: 18px;
}

.tab-button:hover {
  color: #cbd5e1;
  background: rgba(255, 255, 255, 0.05);
}

.tab-button.active {
  color: #60a5fa;
  border-bottom-color: #3b82f6;
}

/* Body */
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.tab-content {
  animation: fadeIn 0.3s;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Info Grid */
.info-grid {
  display: grid;
  gap: 24px;
}

.info-section {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
}

.info-section.full-width {
  grid-column: 1 / -1;
}

.info-section h3 {
  margin: 0 0 16px 0;
  color: white;
  font-size: 16px;
  font-weight: 700;
}

.info-section.collapsible {
  padding: 0;
}

.info-section.collapsible h3 {
  margin: 0;
}

.collapsible-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: transparent;
  border: none;
  color: inherit;
  padding: 20px;
  cursor: pointer;
  border-radius: 12px 12px 0 0;
  transition: background 0.2s ease;
}

.info-section.collapsible.is-collapsed .collapsible-trigger {
  border-radius: 12px;
}

.collapsible-trigger:hover {
  background: rgba(255, 255, 255, 0.05);
}

.collapsible-trigger .icon {
  width: 18px;
  height: 18px;
  transition: transform 0.2s ease;
}

.collapsible-trigger .icon.rotated {
  transform: rotate(180deg);
}

.collapsible-content {
  padding: 0 20px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 0 0 12px 12px;
  overflow: hidden;
}

.collapse-enter-active,
.collapse-leave-active {
  overflow: hidden;
  transition: height 0.2s ease, opacity 0.2s ease;
}

.collapse-enter-from,
.collapse-leave-to {
  height: 0;
  opacity: 0;
}

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-card {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.stat-card.status-online {
  border-color: rgba(16, 185, 129, 0.3);
  background: rgba(16, 185, 129, 0.1);
}

.stat-card.status-offline {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.1);
}

.stat-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.stat-value {
  color: white;
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.stat-value.good {
  color: #10b981;
}

.stat-value.warning {
  color: #f59e0b;
}

.stat-value.critical {
  color: #ef4444;
}

.stat-detail {
  color: #94a3b8;
  font-size: 12px;
}

/* Detail List */
.detail-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
}

.detail-label {
  color: #94a3b8;
  font-size: 13px;
  font-weight: 500;
}

.detail-value {
  color: white;
  font-size: 14px;
  font-weight: 600;
}

/* Notes */
.notes-box {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  color: #cbd5e1;
  font-size: 14px;
  line-height: 1.6;
}

/* Optical Section */
.optical-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}

.section-header h3 {
  margin: 0;
  color: white;
  font-size: 18px;
  font-weight: 700;
}

.period-selector {
  display: flex;
  gap: 8px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 4px;
}

.period-btn {
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: #94a3b8;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.period-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
}

.period-btn.active {
  background: #3b82f6;
  color: white;
}

.optical-chart-container {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 20px;
  height: 300px;
}

.port-charts-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.port-chart-panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.port-chart-panel.collapsed {
  background: rgba(255, 255, 255, 0.02);
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s ease;
}

.panel-header:hover {
  background: rgba(255, 255, 255, 0.05);
}

.port-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.port-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.port-icon.origin {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
}

.port-icon.destination {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
}

.port-icon .icon {
  width: 20px;
  height: 20px;
  color: white;
}

.port-details h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #e2e8f0;
}

.port-details p {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: #94a3b8;
}

.collapse-btn {
  background: transparent;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.collapse-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #e2e8f0;
}

.collapse-btn .icon {
  width: 20px;
  height: 20px;
  transition: transform 0.3s ease;
}

.collapse-btn .icon.rotated {
  transform: rotate(180deg);
}

.panel-content {
  padding: 0 20px 20px 20px;
}

.optical-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.stat-box {
  display: flex;
  align-items: center;
  gap: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-weight: 700;
  font-size: 14px;
}

.stat-icon.good {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.stat-icon.warning {
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
}

.stat-icon.info {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.stat-icon .icon {
  width: 24px;
  height: 24px;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-info .stat-label {
  color: #94a3b8;
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
}

.stat-info .stat-value {
  color: white;
  font-size: 18px;
  font-weight: 700;
}

/* Empty State and Loading */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: #64748b;
  text-align: center;
  background: rgba(255, 255, 255, 0.02);
  border: 1px dashed rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  min-height: 300px;
}

.empty-state .icon {
  width: 64px;
  height: 64px;
  margin-bottom: 16px;
  color: #475569;
}

.empty-state p {
  margin: 0;
  color: #94a3b8;
  font-size: 16px;
  font-weight: 600;
}

.empty-state small {
  display: block;
  margin-top: 8px;
  color: #64748b;
  font-size: 13px;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 24px;
  color: #94a3b8;
  text-align: center;
  min-height: 300px;
}

.loading-state p {
  margin: 16px 0 0 0;
  color: #94a3b8;
  font-size: 14px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid rgba(59, 130, 246, 0.2);
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner.small {
  width: 20px;
  height: 20px;
  border-width: 3px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Alarm Section */
.alarms-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.btn-primary-small {
  padding: 10px 16px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-primary-small:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.btn-primary-small .icon {
  width: 16px;
  height: 16px;
}

.alarm-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.65);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 11000;
  padding: 24px;
}

.alarm-modal {
  width: min(560px, 100%);
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.98) 0%, rgba(15, 23, 42, 0.92) 100%);
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 25px 60px -15px rgba(15, 23, 42, 0.6);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow: hidden;
}

.alarm-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.08) 0%, transparent 100%);
}

.alarm-modal-header h3 {
  margin: 0;
  color: #e2e8f0;
  font-size: 18px;
  font-weight: 600;
}

.alarm-modal-header .close-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.alarm-modal-header .close-btn:hover {
  background: rgba(248, 113, 113, 0.15);
  border-color: rgba(248, 113, 113, 0.4);
  color: #fca5a5;
}

.alarm-modal-content {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  color: #cbd5f5;
  overflow-y: auto;
}

.alarm-modal-content section {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  padding: 18px 20px;
}

.saved-configs-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.saved-configs-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #cbd5f5;
  font-size: 13px;
}

.saved-configs-empty {
  border: 1px dashed rgba(148, 163, 184, 0.35);
  border-radius: 12px;
  padding: 16px;
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  background: rgba(15, 23, 42, 0.45);
}

.saved-configs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.saved-config-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.55);
}

.saved-config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.saved-config-target {
  color: #e2e8f0;
  font-weight: 600;
  font-size: 14px;
}

.saved-config-level {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.18);
  border: 1px solid rgba(59, 130, 246, 0.4);
  color: #bfdbfe;
}

.saved-config-level.level-warning {
  background: rgba(245, 158, 11, 0.18);
  border-color: rgba(245, 158, 11, 0.4);
  color: #fbbf24;
}

.saved-config-level.level-critical {
  background: rgba(239, 68, 68, 0.22);
  border-color: rgba(239, 68, 68, 0.45);
  color: #f87171;
}

.saved-config-channels {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.saved-config-channel {
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.3);
  color: #bfdbfe;
  font-size: 12px;
  font-weight: 500;
}

.saved-config-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  color: #94a3b8;
  font-size: 12px;
}

.saved-config-notes {
  margin: 0;
  color: #cbd5f5;
  font-size: 13px;
  line-height: 1.4;
}

.alarm-modal-content h4 {
  margin: 0 0 12px 0;
  font-size: 15px;
  font-weight: 600;
  color: #e2e8f0;
}

.target-options {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.target-option {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.18);
  cursor: pointer;
  transition: all 0.2s;
  color: #cbd5f5;
  font-size: 13px;
}

.target-option input {
  accent-color: #3b82f6;
}

.target-option:hover {
  border-color: rgba(59, 130, 246, 0.4);
  background: rgba(59, 130, 246, 0.12);
}

.target-selector {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.target-selector select {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 10px 12px;
  color: #e2e8f0;
}

.channel-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.channel-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.18);
  color: #cbd5f5;
  font-size: 13px;
}

.channel-option input {
  accent-color: #3b82f6;
}

.channel-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
  background: #cbd5f5;
}

.channel-icon.email {
  background: #bae6fd;
}

.channel-icon.whatsapp {
  background: #86efac;
}

.channel-icon.sms {
  background: #fef08a;
}

.channel-icon.telegram {
  background: #c7d2fe;
}

.conditions-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
}

.conditions-grid label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: #cbd5f5;
}

.conditions-grid select,
.conditions-grid input {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  padding: 10px 12px;
  color: #e2e8f0;
}

.conditions-grid small {
  color: #94a3b8;
  font-size: 12px;
}

.alarm-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 18px 24px;
  border-top: 1px solid rgba(148, 163, 184, 0.15);
  background: linear-gradient(180deg, transparent 0%, rgba(15, 23, 42, 0.85) 100%);
}

.alarms-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alarm-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-left: 3px solid;
  border-radius: 8px;
}

.alarm-item.severity-critical {
  border-left-color: #ef4444;
  background: rgba(239, 68, 68, 0.05);
}

.alarm-item.severity-warning {
  border-left-color: #f59e0b;
  background: rgba(245, 158, 11, 0.05);
}

.alarm-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.alarm-icon .icon {
  width: 20px;
  height: 20px;
  color: #ef4444;
}

.alarm-content {
  flex: 1;
}

.alarm-title {
  color: white;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.alarm-description {
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 8px;
}

.alarm-time {
  color: #64748b;
  font-size: 12px;
}

/* History Section */
.history-section h3 {
  margin: 0 0 24px 0;
  color: white;
  font-size: 18px;
  font-weight: 700;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.timeline-item {
  display: flex;
  gap: 16px;
  padding: 20px 0;
  border-left: 2px solid rgba(255, 255, 255, 0.1);
  margin-left: 8px;
  position: relative;
}

.timeline-item:last-child {
  border-left-color: transparent;
}

.timeline-marker {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #3b82f6;
  border: 3px solid #0f172a;
  flex-shrink: 0;
  margin-left: -9px;
  position: relative;
  z-index: 1;
}

.timeline-marker.type-maintenance {
  background: #f59e0b;
}

.timeline-marker.type-repair {
  background: #ef4444;
}

.timeline-marker.type-installation {
  background: #10b981;
}

.timeline-content {
  flex: 1;
  padding-bottom: 8px;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  flex-wrap: wrap;
  gap: 8px;
}

.event-title {
  color: white;
  font-size: 15px;
  font-weight: 600;
}

.event-date {
  color: #64748b;
  font-size: 13px;
}

.event-description {
  color: #94a3b8;
  font-size: 13px;
  line-height: 1.5;
  margin-bottom: 8px;
}

.event-user {
  color: #64748b;
  font-size: 12px;
  font-style: italic;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 48px 20px;
  color: #64748b;
}

.empty-state .icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

/* Footer */
.modal-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(0, 0, 0, 0.2);
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.btn-secondary,
.btn-primary {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.1);
  color: #cbd5e1;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary .icon,
.btn-secondary .icon {
  width: 18px;
  height: 18px;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Animação do modal - DESABILITADA TEMPORARIAMENTE */
/*
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s;
}

.modal-enter-active .detail-modal-container,
.modal-leave-active .detail-modal-container {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .detail-modal-container,
.modal-leave-to .detail-modal-container {
  transform: scale(0.95) translateY(20px);
  opacity: 0;
}
*/

/* Scrollbar */
.modal-body::-webkit-scrollbar {
  width: 8px;
}

.modal-body::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Responsivo */
@media (max-width: 768px) {
  .detail-modal-container {
    max-width: 100%;
    max-height: 100vh;
    border-radius: 0;
  }
  
  .info-cards {
    grid-template-columns: 1fr;
  }
  
  .tabs-header {
    padding: 0 16px;
  }
  
  .tab-button {
    padding: 14px 16px;
    font-size: 13px;
  }
  
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
