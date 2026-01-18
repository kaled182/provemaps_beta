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
      </header>

      <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="app-surface rounded-lg p-4 flex items-center justify-between">
          <div>
            <p class="text-xs app-text-tertiary uppercase">Total</p>
            <p class="text-2xl font-semibold app-text-primary">{{ totalUsers }}</p>
          </div>
          <div class="flex flex-col items-end gap-2">
            <span class="text-xs app-text-tertiary">Usuarios</span>
            <button type="button" class="app-btn-primary px-3 py-1 rounded-md text-xs" @click="openModal()">
              Novo Usuario
            </button>
          </div>
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

      <div class="app-surface rounded-lg overflow-hidden">
        <button
          class="w-full px-6 py-3 flex items-center justify-between border-b app-divider"
          @click="toggleUserSection('users')"
        >
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-lg bg-indigo-500/10 text-indigo-300 flex items-center justify-center text-xs font-semibold">
              US
            </div>
            <div class="text-left">
              <div class="font-semibold app-text-primary">Usuarios</div>
              <div class="text-xs app-text-tertiary">Lista de usuarios cadastrados.</div>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="app-badge app-badge-muted">{{ filteredUsers.length }}</span>
            <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedUserSections.users ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
          </div>
        </button>
        <div v-show="expandedUserSections.users">
          <div class="px-6 pt-3 pb-2 border-b app-divider flex flex-col gap-3 md:flex-row md:items-center">
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
                          {{ formatDepartmentLabel(user.profile) }}
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
                    <div class="inline-flex items-center gap-2">
                      <button
                        type="button"
                        class="app-btn px-2 py-2 rounded"
                        aria-label="Editar usuario"
                        title="Editar"
                        @click="openModal(user)"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16.5 3.5l4 4L7 21H3v-4L16.5 3.5z"/>
                        </svg>
                      </button>
                      <button
                        type="button"
                        class="app-btn-warning px-2 py-2 rounded"
                        :aria-label="user.is_active ? 'Desativar usuario' : 'Ativar usuario'"
                        :title="user.is_active ? 'Desativar' : 'Ativar'"
                        @click="toggleActive(user)"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2v10m6.36-7.36a9 9 0 1 1-12.72 0"/>
                        </svg>
                      </button>
                      <button
                        type="button"
                        class="app-btn-danger px-2 py-2 rounded"
                        :class="user.is_superuser ? 'opacity-50 cursor-not-allowed' : ''"
                        :disabled="user.is_superuser"
                        aria-label="Excluir usuario"
                        title="Excluir"
                        @click="confirmDelete(user)"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 7h12m-1 0l-1 12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 7m3 0V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                      </button>
                    </div>
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
        <div class="border-t app-divider">
          <div>
            <button
              class="w-full px-6 py-3 flex items-center justify-between"
              @click="toggleUserSection('departments')"
            >
              <div class="flex items-center gap-3">
                <div class="h-9 w-9 rounded-lg bg-sky-500/10 text-sky-300 flex items-center justify-center text-xs font-semibold">
                  DP
                </div>
                <div class="text-left">
                  <div class="font-semibold app-text-primary">Departamentos</div>
                  <div class="text-xs app-text-tertiary">Times cadastrados e distribuicao.</div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span class="app-badge app-badge-muted">{{ departmentStats.length }}</span>
                <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedUserSections.departments ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
              </div>
            </button>
            <div v-show="expandedUserSections.departments" class="px-6 pb-4">
              <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between mb-3">
                <div class="flex-1">
                  <label class="field-label">Novo departamento</label>
                  <input
                    v-model="departmentName"
                    type="text"
                    class="app-input w-full"
                    placeholder="Ex: NOC, Comercial, Suporte"
                  />
                </div>
                <button type="button" class="app-btn-primary px-4 py-2 rounded" @click="createDepartment">
                  Adicionar
                </button>
              </div>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div
                  v-for="dept in departmentStats"
                  :key="dept.name"
                  class="app-surface-muted rounded-lg p-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between"
                >
                  <div class="flex-1">
                    <div v-if="editingDepartmentId === dept.id" class="space-y-2">
                      <input
                        v-model="departmentEditForm.name"
                        type="text"
                        class="app-input w-full text-sm"
                        placeholder="Nome do departamento"
                      />
                      <input
                        v-model="departmentEditForm.description"
                        type="text"
                        class="app-input w-full text-sm"
                        placeholder="Descricao (opcional)"
                      />
                      <div class="flex items-center justify-between">
                        <span class="text-xs app-text-tertiary">Ativo</span>
                        <input
                          type="checkbox"
                          v-model="departmentEditForm.is_active"
                          class="field-checkbox-input"
                        />
                      </div>
                    </div>
                    <div v-else>
                      <div class="text-sm font-semibold app-text-primary">{{ dept.name }}</div>
                      <div class="text-xs app-text-tertiary">{{ dept.count }} usuario(s)</div>
                    </div>
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="app-badge app-badge-muted">Equipe</span>
                    <template v-if="editingDepartmentId === dept.id">
                      <button
                        type="button"
                        class="app-btn px-2 py-2 rounded"
                        aria-label="Cancelar edicao"
                        title="Cancelar"
                        @click="cancelEditDepartment"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                      </button>
                      <button
                        type="button"
                        class="app-btn-primary px-2 py-2 rounded"
                        aria-label="Salvar edicao"
                        title="Salvar"
                        @click="saveDepartmentEdit"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/>
                        </svg>
                      </button>
                    </template>
                    <template v-else>
                      <button
                        v-if="dept.canEdit"
                        type="button"
                        class="app-btn-primary px-2 py-2 rounded"
                        aria-label="Adicionar usuario existente"
                        title="Adicionar usuario existente"
                        @click="openAssignModal(dept)"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m8-10a4 4 0 1 0 0-8 4 4 0 0 0 0 8m10 5v-4m-2 2h4"/>
                        </svg>
                      </button>
                      <button
                        v-if="dept.canEdit"
                        type="button"
                        class="app-btn px-2 py-2 rounded"
                        aria-label="Editar departamento"
                        title="Editar"
                        @click="startEditDepartment(dept)"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16.5 3.5l4 4L7 21H3v-4L16.5 3.5z"/>
                        </svg>
                      </button>
                      <button
                        v-if="dept.canDelete"
                        type="button"
                        class="app-btn-danger px-2 py-2 rounded"
                        aria-label="Remover departamento"
                        title="Remover"
                        @click="requestRemoveDepartment(dept)"
                      >
                        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 7h12m-1 0l-1 12a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 7m3 0V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                      </button>
                    </template>
                  </div>
                </div>
              </div>
              <div v-if="departmentStats.length === 0" class="text-sm app-text-tertiary text-center py-6">
                Nenhum departamento cadastrado.
              </div>
            </div>
          </div>

          <div class="border-t app-divider">
            <button
              class="w-full px-6 py-3 flex items-center justify-between"
              @click="toggleUserSection('permissions')"
            >
              <div class="flex items-center gap-3">
                <div class="h-9 w-9 rounded-lg bg-emerald-500/10 text-emerald-300 flex items-center justify-center text-xs font-semibold">
                  PR
                </div>
                <div class="text-left">
                  <div class="font-semibold app-text-primary">Permissoes</div>
                  <div class="text-xs app-text-tertiary">Perfis de acesso e grupos.</div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <span class="app-badge app-badge-muted">{{ permissionStats.length }}</span>
                <svg class="h-4 w-4 text-gray-400 transition-transform" :class="expandedUserSections.permissions ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
              </div>
            </button>
            <div v-show="expandedUserSections.permissions" class="px-6 pb-4">
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div
                  v-for="perm in permissionStats"
                  :key="perm.name"
                  class="app-surface-muted rounded-lg p-3 flex items-center justify-between"
                >
                  <div>
                    <div class="text-sm font-semibold app-text-primary">{{ perm.name }}</div>
                    <div class="text-xs app-text-tertiary">{{ perm.count }} usuario(s)</div>
                  </div>
                  <span class="app-badge app-badge-info">Perfil</span>
                </div>
              </div>
              <div v-if="permissionStats.length === 0" class="text-sm app-text-tertiary text-center py-6">
                Nenhuma permissao configurada.
              </div>
            </div>
          </div>
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
              <label class="field-label">Departamentos</label>
              <select v-model="form.profile.departments" class="app-input w-full" multiple>
                <option v-for="dept in departmentOptions" :key="dept.id" :value="dept.id">
                  {{ dept.name }}
                </option>
              </select>
              <div class="text-xs app-text-tertiary mt-1">Selecione um ou mais departamentos.</div>
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

    <div v-if="showAssignModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60">
      <div class="app-surface rounded-lg w-full max-w-lg">
        <div class="px-6 py-4 border-b app-divider app-surface-muted flex items-center justify-between">
          <h3 class="text-lg font-semibold app-text-primary">
            Adicionar usuarios ao departamento
          </h3>
          <button class="app-btn px-2 py-1 rounded" @click="closeAssignModal">Fechar</button>
        </div>
        <div class="p-6 space-y-4">
          <div>
            <label class="field-label">Departamento</label>
            <div class="app-input w-full flex items-center justify-between">
              <span class="text-sm">{{ assignDepartment?.name || '-' }}</span>
              <span class="app-badge app-badge-muted">Equipe</span>
            </div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label class="flex items-center justify-between app-surface-muted rounded-lg px-3 py-2 text-sm">
              <span class="app-text-secondary">Somente sem departamento</span>
              <input type="checkbox" v-model="assignFilterNoDepartment" class="field-checkbox-input" />
            </label>
            <label class="flex items-center justify-between app-surface-muted rounded-lg px-3 py-2 text-sm">
              <span class="app-text-secondary">Somente nao adicionados</span>
              <input type="checkbox" v-model="assignFilterNotInDepartment" class="field-checkbox-input" />
            </label>
          </div>
          <div>
            <label class="field-label">Usuarios existentes</label>
            <select v-model="assignUserIds" class="app-input w-full" multiple>
              <option
                v-for="user in assignableUsers"
                :key="user.id"
                :value="user.id"
                :disabled="user.disabled"
              >
                {{ user.label }}
              </option>
            </select>
            <div class="text-xs app-text-tertiary mt-1">
              Selecione um ou mais usuarios para adicionar ao departamento.
            </div>
          </div>
          <div class="flex items-center justify-end gap-3">
            <button type="button" class="app-btn px-4 py-2 rounded" @click="closeAssignModal">
              Cancelar
            </button>
            <button type="button" class="app-btn-primary px-4 py-2 rounded" @click="assignUsersToDepartment">
              Adicionar
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showConfirmModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeConfirmModal"></div>
      <div class="app-surface rounded-lg w-full max-w-md relative z-10">
        <div class="px-6 py-4 border-b app-divider app-surface-muted flex items-center justify-between">
          <h3 class="text-lg font-semibold app-text-primary">{{ confirmTitle }}</h3>
          <button class="app-btn px-2 py-1 rounded" @click="closeConfirmModal">Fechar</button>
        </div>
        <div class="p-6 space-y-4">
          <p class="text-sm app-text-secondary">{{ confirmMessage }}</p>
          <div class="flex justify-end gap-3">
            <button type="button" class="app-btn px-4 py-2 rounded" @click="closeConfirmModal">Cancelar</button>
            <button type="button" class="app-btn-danger px-4 py-2 rounded" @click="confirmAction">
              Confirmar
            </button>
          </div>
        </div>
      </div>
    </div>

    <div v-if="showMoveDepartmentModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeMoveDepartmentModal"></div>
      <div class="app-surface rounded-lg w-full max-w-md relative z-10">
        <div class="px-6 py-4 border-b app-divider app-surface-muted flex items-center justify-between">
          <h3 class="text-lg font-semibold app-text-primary">Mover usuarios do departamento</h3>
          <button class="app-btn px-2 py-1 rounded" @click="closeMoveDepartmentModal">Fechar</button>
        </div>
        <div class="p-6 space-y-4">
          <p class="text-sm app-text-secondary">
            O departamento possui usuarios. Escolha para onde mover antes de remover.
          </p>
          <div>
            <label class="field-label">Mover usuarios para</label>
            <select v-model="moveDepartmentTarget" class="app-input w-full">
              <option value="">Sem departamento</option>
              <option v-for="dept in moveDepartmentOptions" :key="dept.id" :value="dept.id">
                {{ dept.name }}
              </option>
            </select>
          </div>
          <div class="flex justify-end gap-3 pt-2">
            <button type="button" class="app-btn px-4 py-2 rounded" @click="closeMoveDepartmentModal">
              Cancelar
            </button>
            <button type="button" class="app-btn-danger px-4 py-2 rounded" @click="confirmMoveDepartment">
              Remover departamento
            </button>
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

const defaultProfile = {
  phone_number: '',
  telegram_chat_id: '',
  notify_via_email: true,
  notify_via_whatsapp: false,
  notify_via_telegram: false,
  receive_critical_alerts: true,
  receive_warning_alerts: false,
  department: '',
  departments: [],
};

const users = ref([]);
const availableGroups = ref([]);
const departments = ref([]);
const searchQuery = ref('');
const statusFilter = ref('all');
const showModal = ref(false);
const showAssignModal = ref(false);
const isEditing = ref(false);
const activeTab = ref('profile');
const departmentName = ref('');
const editingDepartmentId = ref(null);
const departmentEditForm = ref({
  id: null,
  name: '',
  description: '',
  is_active: true,
});
const showConfirmModal = ref(false);
const confirmTitle = ref('');
const confirmMessage = ref('');
const confirmAction = ref(() => {});
const showMoveDepartmentModal = ref(false);
const departmentPendingRemoval = ref(null);
const moveDepartmentTarget = ref('');
const assignDepartment = ref(null);
const assignUserIds = ref([]);
const assignFilterNoDepartment = ref(false);
const assignFilterNotInDepartment = ref(true);
const expandedUserSections = ref({
  users: true,
  departments: true,
  permissions: false,
});

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
const departmentStats = computed(() => {
  const counts = new Map();
  const labels = new Map();
  let emptyCount = 0;
  users.value.forEach(user => {
    const names = getDepartmentNames(user.profile);
    if (!names.length) {
      emptyCount += 1;
      return;
    }
    names.forEach(dept => {
      const key = dept.toLowerCase();
      counts.set(key, (counts.get(key) || 0) + 1);
      if (!labels.has(key)) {
        labels.set(key, dept);
      }
    });
  });

  const items = departments.value.map(dept => {
    const key = (dept.name || '').trim().toLowerCase();
    return {
      id: dept.id,
      name: dept.name,
      description: dept.description || '',
      is_active: dept.is_active !== false,
      count: counts.get(key) || 0,
      hasUsers: (counts.get(key) || 0) > 0,
      canEdit: true,
      canDelete: true,
    };
  });

  if (departments.value.length === 0) {
    const fallback = Array.from(counts.entries()).map(([key, count]) => ({
      name: labels.get(key) || key || 'Sem departamento',
      count,
      canEdit: false,
      canDelete: false,
    }));
    if (emptyCount > 0) {
      fallback.push({ name: 'Sem departamento', count: emptyCount, canEdit: false, canDelete: false });
    }
    return fallback.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
  }

  const knownKeys = new Set(
    departments.value.map(dept => (dept.name || '').trim().toLowerCase()).filter(Boolean)
  );
  counts.forEach((count, key) => {
    if (!knownKeys.has(key)) {
      items.push({
        name: labels.get(key) || key || 'Sem departamento',
        count,
        canEdit: false,
        canDelete: false,
      });
    }
  });

  if (emptyCount > 0) {
    items.push({ name: 'Sem departamento', count: emptyCount, canEdit: false, canDelete: false });
  }

  return items.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
});

const departmentOptions = computed(() => {
  return departments.value
    .map(dept => ({ id: dept.id, name: (dept.name || '').trim() }))
    .filter(dept => dept.name)
    .sort((a, b) => a.name.localeCompare(b.name));
});
const moveDepartmentOptions = computed(() => {
  const currentId = departmentPendingRemoval.value?.id;
  return departments.value
    .filter(dept => dept.id !== currentId)
    .map(dept => ({ id: dept.id, name: dept.name }))
    .filter(dept => dept.name);
});
const assignableUsers = computed(() => {
  const deptName = (assignDepartment.value?.name || '').trim().toLowerCase();
  return users.value.map(user => {
    const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
    const label = fullName ? `${fullName} (@${user.username})` : `@${user.username}`;
    const existingDepartments = getDepartmentNames(user.profile).map(name => name.toLowerCase());
    const hasDepartments = existingDepartments.length > 0;
    const isInDepartment = deptName ? existingDepartments.includes(deptName) : false;
    return {
      id: user.id,
      label,
      hasDepartments,
      isInDepartment,
      disabled: isInDepartment,
    };
  }).filter(user => {
    if (assignFilterNoDepartment.value && user.hasDepartments) {
      return false;
    }
    if (assignFilterNotInDepartment.value && user.isInDepartment) {
      return false;
    }
    return true;
  });
});
const permissionStats = computed(() => {
  const counts = new Map();
  users.value.forEach(user => {
    let hasRole = false;
    if (user.is_superuser) {
      counts.set('Superuser', (counts.get('Superuser') || 0) + 1);
      hasRole = true;
    }
    if (user.is_staff) {
      counts.set('Staff', (counts.get('Staff') || 0) + 1);
      hasRole = true;
    }
    (user.groups || []).forEach(group => {
      counts.set(group.name, (counts.get(group.name) || 0) + 1);
      hasRole = true;
    });
    if (!hasRole) {
      counts.set('Padrao', (counts.get('Padrao') || 0) + 1);
    }
  });
  return Array.from(counts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
});

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
    profile: {
      ...defaultProfile,
      ...(user.profile || {}),
      departments: Array.isArray(user.profile?.departments) ? user.profile.departments : [],
    },
  }));
};

const fetchGroups = async () => {
  const data = await api.get('/api/groups/');
  availableGroups.value = data.groups || [];
};

const fetchDepartments = async () => {
  const data = await api.get('/api/departments/');
  departments.value = data.departments || [];
};

const loadData = async () => {
  try {
    await Promise.all([fetchUsers(), fetchGroups(), fetchDepartments()]);
  } catch (err) {
    notifyError('Erro ao carregar dados', err.message || String(err));
  }
};

const openModal = (user = null, presetDepartmentId = null) => {
  activeTab.value = 'profile';
  if (user) {
    isEditing.value = true;
    const departmentIds = getDepartmentIds(user.profile);
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
      profile: { ...defaultProfile, ...(user.profile || {}), departments: departmentIds },
    };
  } else {
    isEditing.value = false;
    const presetDepartments = presetDepartmentId ? [presetDepartmentId] : [];
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
      profile: { ...defaultProfile, departments: presetDepartments },
    };
  }
  showModal.value = true;
};

const closeModal = () => {
  showModal.value = false;
};

const openAssignModal = (dept) => {
  assignDepartment.value = dept;
  assignUserIds.value = [];
  showAssignModal.value = true;
};

const closeAssignModal = () => {
  showAssignModal.value = false;
  assignDepartment.value = null;
  assignUserIds.value = [];
};

const assignUsersToDepartment = async () => {
  if (!assignDepartment.value) {
    notifyError('Departamento invalido', 'Selecione um departamento valido.');
    return;
  }
  const selectedIds = Array.isArray(assignUserIds.value)
    ? assignUserIds.value.map(value => Number(value)).filter(value => !Number.isNaN(value))
    : [];
  if (!selectedIds.length) {
    notifyError('Selecione usuarios', 'Escolha pelo menos um usuario.');
    return;
  }

  try {
    const targetId = assignDepartment.value.id;
    await Promise.all(
      selectedIds.map(async (userId) => {
        const user = users.value.find(item => item.id === userId);
        if (!user) {
          return;
        }
        const currentIds = getDepartmentIds(user.profile);
        if (!currentIds.includes(targetId)) {
          currentIds.push(targetId);
        }
        await api.patch(`/api/users/${userId}/update/`, {
          profile: { departments: currentIds },
        });
      })
    );
    success('Usuarios adicionados', 'Departamentos atualizados com sucesso.');
    closeAssignModal();
    await fetchUsers();
    await fetchDepartments();
  } catch (err) {
    notifyError('Falha ao adicionar usuarios', err.message || String(err));
  }
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

    const profilePayload = {
      ...form.value.profile,
      departments: Array.isArray(form.value.profile.departments)
        ? form.value.profile.departments.map(value => Number(value)).filter(value => !Number.isNaN(value))
        : [],
    };
    const payload = { ...form.value, profile: profilePayload };

    if (isEditing.value) {
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
  openConfirmModal('Excluir usuario', `Excluir ${user.username}?`, async () => {
    try {
      const data = await api.delete(`/api/users/${user.id}/delete/`);
      success('Usuario removido', data?.message || 'Usuario removido.');
      await fetchUsers();
    } catch (err) {
      notifyError('Falha ao excluir usuario', err.message || String(err));
    } finally {
      closeConfirmModal();
    }
  });
};

const toggleUserSection = (section) => {
  expandedUserSections.value[section] = !expandedUserSections.value[section];
};

const createDepartment = async () => {
  const name = departmentName.value.trim();
  if (!name) {
    notifyError('Nome obrigatorio', 'Informe o nome do departamento.');
    return;
  }
  try {
    await api.post('/api/departments/', { name });
    departmentName.value = '';
    await fetchDepartments();
    success('Departamento criado', 'Departamento cadastrado com sucesso.');
  } catch (err) {
    notifyError('Falha ao criar departamento', err.message || String(err));
  }
};

const startEditDepartment = (dept) => {
  if (!dept?.id) return;
  editingDepartmentId.value = dept.id;
  departmentEditForm.value = {
    id: dept.id,
    name: dept.name || '',
    description: dept.description || '',
    is_active: dept.is_active !== false,
  };
};

const cancelEditDepartment = () => {
  editingDepartmentId.value = null;
  departmentEditForm.value = {
    id: null,
    name: '',
    description: '',
    is_active: true,
  };
};

const saveDepartmentEdit = async () => {
  const payload = {
    name: departmentEditForm.value.name.trim(),
    description: (departmentEditForm.value.description || '').trim(),
    is_active: !!departmentEditForm.value.is_active,
  };
  if (!payload.name) {
    notifyError('Nome obrigatorio', 'Informe o nome do departamento.');
    return;
  }
  try {
    await api.patch(`/api/departments/${departmentEditForm.value.id}/`, payload);
    await fetchDepartments();
    cancelEditDepartment();
    success('Departamento atualizado', 'Alteracoes salvas.');
  } catch (err) {
    notifyError('Falha ao atualizar departamento', err.message || String(err));
  }
};

const requestRemoveDepartment = (dept) => {
  if (!dept?.id) return;
  if (dept.count > 0) {
    departmentPendingRemoval.value = dept;
    moveDepartmentTarget.value = '';
    showMoveDepartmentModal.value = true;
    return;
  }
  openConfirmModal('Remover departamento', `Remover o departamento "${dept.name}"?`, async () => {
    try {
      await api.delete(`/api/departments/${dept.id}/`);
      await fetchDepartments();
      await fetchUsers();
      success('Departamento removido', 'Departamento removido com sucesso.');
    } catch (err) {
      notifyError('Falha ao remover departamento', err.message || String(err));
    } finally {
      closeConfirmModal();
    }
  });
};

const closeMoveDepartmentModal = () => {
  showMoveDepartmentModal.value = false;
  departmentPendingRemoval.value = null;
  moveDepartmentTarget.value = '';
};

const confirmMoveDepartment = async () => {
  const dept = departmentPendingRemoval.value;
  if (!dept?.id) return;
  try {
    const targetId = moveDepartmentTarget.value ? Number(moveDepartmentTarget.value) : null;
    await api.post(`/api/departments/${dept.id}/remove/`, {
      move_to: Number.isNaN(targetId) ? null : targetId,
    });
    await Promise.all([fetchDepartments(), fetchUsers()]);
    success('Departamento removido', 'Usuarios realocados e departamento removido.');
  } catch (err) {
    notifyError('Falha ao remover departamento', err.message || String(err));
  } finally {
    closeMoveDepartmentModal();
  }
};

const openConfirmModal = (title, message, action) => {
  confirmTitle.value = title;
  confirmMessage.value = message;
  confirmAction.value = action;
  showConfirmModal.value = true;
};

const closeConfirmModal = () => {
  showConfirmModal.value = false;
  confirmAction.value = () => {};
};

const getInitials = (name) => {
  if (!name) return 'UU';
  return name.slice(0, 2).toUpperCase();
};

const getDepartmentNames = (profile) => {
  const names = Array.isArray(profile?.departments)
    ? profile.departments.map(dept => dept?.name).filter(Boolean)
    : [];
  if (!names.length) {
    const legacy = (profile?.department || '').trim();
    if (legacy) names.push(legacy);
  }
  return names;
};

const formatDepartmentLabel = (profile) => {
  const names = getDepartmentNames(profile);
  return names.length ? names.join(', ') : 'Sem departamento';
};

const getDepartmentIds = (profile) => {
  const ids = Array.isArray(profile?.departments)
    ? profile.departments.map(dept => dept?.id).filter(Boolean)
    : [];
  if (ids.length) return ids;
  const legacy = (profile?.department || '').trim().toLowerCase();
  if (!legacy) return [];
  const match = departments.value.find(dept => (dept.name || '').trim().toLowerCase() === legacy);
  return match ? [match.id] : [];
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
