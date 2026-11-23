<template>
  <BaseModal
    :show="visible"
    title="Notificar responsáveis"
    :icon="PhPhone"
    :z-index="9200"
    size="md"
    flush
    @close="$emit('close')"
  >
    <!-- Context summary -->
    <div class="nm-context">
      <span class="nm-ctx-item">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
        {{ cables.length }} cabo(s) afetado(s)
      </span>
      <span class="nm-ctx-sep">·</span>
      <span class="nm-ctx-item">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/></svg>
        {{ devices.length }} equipamento(s) afetado(s)
      </span>
    </div>

    <!-- Loading / error state -->
    <div v-if="loading" class="nm-loading">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
        <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
      </svg>
      Carregando destinatários…
    </div>

    <div v-else-if="loadError" class="nm-error">
      {{ loadError }}
    </div>

    <template v-else>
      <!-- Message -->
      <div class="nm-section">
        <label class="nm-label">
          Mensagem
          <span class="nm-label-hint">(opcional — em branco envia "ENLACE OFF.")</span>
        </label>
        <textarea
          v-model="message"
          class="nm-textarea"
          rows="3"
          placeholder='Deixe em branco para usar "ENLACE OFF." ou descreva o motivo…'
        ></textarea>
      </div>

      <!-- Tabs: Users / Responsáveis -->
      <div class="nm-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          :class="['nm-tab', { active: activeTab === tab.key }]"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
          <span class="nm-tab-count">{{ tab.count }}</span>
        </button>
      </div>

      <!-- Recipients list -->
      <div class="nm-list">
        <div v-if="currentList.length === 0" class="nm-empty">
          Nenhum destinatário disponível
          <span v-if="!smtpEnabled" class="nm-empty-hint">— SMTP não configurado</span>
        </div>

        <template v-else>
          <!-- Primary responsibles section (auto-detected from cables) -->
          <div v-if="primaryInCurrentTab.length > 0" class="nm-group-label">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
            Responsável(is) dos cabos afetados
          </div>

          <div
            v-for="rec in primaryInCurrentTab"
            :key="`primary-${rec.type}-${rec.id}`"
            class="nm-recipient nm-recipient--primary"
            :class="{ selected: isSelected(rec) }"
          >
            <div class="nm-rec-info">
              <div class="nm-rec-name-row">
                <span class="nm-rec-name">{{ rec.name }}</span>
                <span class="nm-badge-primary">Responsável</span>
              </div>
              <span v-if="rec.type_label" class="nm-rec-type">{{ rec.type_label }}</span>
              <span v-if="rec.email" class="nm-rec-detail">{{ rec.email }}</span>
              <span v-if="rec.phone" class="nm-rec-detail">{{ rec.phone }}</span>
            </div>
            <div class="nm-channels">
              <button
                v-for="ch in rec.channels"
                :key="ch"
                :class="['nm-ch', `nm-ch--${ch}`, { active: isChannelSelected(rec, ch) }]"
                :title="channelLabel(ch)"
                @click="toggleChannel(rec, ch)"
              >
                <svg v-if="ch === 'email'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                </svg>
                <svg v-else-if="ch === 'whatsapp'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <svg v-else-if="ch === 'telegram'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
                {{ channelLabel(ch) }}
              </button>
            </div>
          </div>

          <!-- Divider when there are additional recipients -->
          <div v-if="primaryInCurrentTab.length > 0 && secondaryInCurrentTab.length > 0" class="nm-group-label nm-group-label--secondary">
            Adicionar mais destinatários
          </div>

          <!-- Other recipients -->
          <div
            v-for="rec in secondaryInCurrentTab"
            :key="`${rec.type}-${rec.id}`"
            class="nm-recipient"
            :class="{ selected: isSelected(rec) }"
          >
            <div class="nm-rec-info">
              <span class="nm-rec-name">{{ rec.name }}</span>
              <span v-if="rec.type_label" class="nm-rec-type">{{ rec.type_label }}</span>
              <span v-if="rec.email" class="nm-rec-detail">{{ rec.email }}</span>
              <span v-if="rec.phone" class="nm-rec-detail">{{ rec.phone }}</span>
            </div>
            <div class="nm-channels">
              <button
                v-for="ch in rec.channels"
                :key="ch"
                :class="['nm-ch', `nm-ch--${ch}`, { active: isChannelSelected(rec, ch) }]"
                :title="channelLabel(ch)"
                @click="toggleChannel(rec, ch)"
              >
                <svg v-if="ch === 'email'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                </svg>
                <svg v-else-if="ch === 'whatsapp'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <svg v-else-if="ch === 'telegram'" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
                </svg>
                {{ channelLabel(ch) }}
              </button>
            </div>
          </div>
        </template>
      </div>

      <!-- Footer -->
      <div class="nm-footer">
        <span class="nm-sel-count">{{ totalSelectedCount }} destinatário(s) selecionado(s)</span>
        <div class="nm-footer-actions">
          <button class="nm-btn nm-btn--secondary" @click="$emit('close')">Cancelar</button>
          <button
            class="nm-btn nm-btn--primary"
            :disabled="!canSend || sending"
            @click="send"
          >
            <svg v-if="sending" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            {{ sending ? 'Enviando…' : 'Enviar' }}
          </button>
        </div>
      </div>
    </template>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { PhPhone } from '@phosphor-icons/vue'
import BaseModal from '@/components/Common/BaseModal.vue'
import { getCsrfToken } from '@/composables/useApi.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
  cables: { type: Array, default: () => [] },
  devices: { type: Array, default: () => [] },
})

const emit = defineEmits(['close', 'sent'])

// ── State ──────────────────────────────────────────────────────────────────
const loading = ref(false)
const loadError = ref('')
const sending = ref(false)
const smtpEnabled = ref(false)
const users = ref([])
const responsibles = ref([])
const contacts = ref([])
const message = ref('')
const activeTab = ref('users')

// selections: Map<`type-id`, Set<channel>>
const selections = ref(new Map())

// ── Primary responsibles (extracted from affected cables) ─────────────────
const primaryUserIds = computed(() => {
  const ids = new Set()
  for (const c of props.cables) {
    if (c.responsible_user_id) ids.add(c.responsible_user_id)
  }
  return ids
})

const primaryResponsibleIds = computed(() => {
  const ids = new Set()
  for (const c of props.cables) {
    if (c.responsible_id) ids.add(c.responsible_id)
  }
  return ids
})

// ── Computed ───────────────────────────────────────────────────────────────
const tabs = computed(() => [
  { key: 'users', label: 'Usuários do sistema', count: users.value.length },
  { key: 'responsibles', label: 'Responsáveis', count: responsibles.value.length },
  { key: 'contacts', label: 'Contatos da agenda', count: contacts.value.length },
])

const currentList = computed(() => {
  if (activeTab.value === 'users') return users.value
  if (activeTab.value === 'responsibles') return responsibles.value
  return contacts.value
})

// Responsibles auto-detected from cables, shown first in cada aba.
// Contatos da agenda não têm vínculo direto com o cabo, então a lista
// "primary" fica vazia na aba contacts (todos aparecem como "secundários").
const primaryInCurrentTab = computed(() => {
  if (activeTab.value === 'users') {
    return users.value.filter(u => primaryUserIds.value.has(u.id))
  }
  if (activeTab.value === 'responsibles') {
    return responsibles.value.filter(r => primaryResponsibleIds.value.has(r.id))
  }
  return [] // contacts
})

// All other recipients (not primary) for the current tab
const secondaryInCurrentTab = computed(() => {
  const primKeys = new Set(primaryInCurrentTab.value.map(r => recKey(r)))
  return currentList.value.filter(r => !primKeys.has(recKey(r)))
})

function recKey(rec) {
  return `${rec.type}-${rec.id}`
}

function isSelected(rec) {
  return (selections.value.get(recKey(rec))?.size ?? 0) > 0
}

function isChannelSelected(rec, ch) {
  return selections.value.get(recKey(rec))?.has(ch) ?? false
}

function toggleChannel(rec, ch) {
  const key = recKey(rec)
  const next = new Map(selections.value)
  if (!next.has(key)) next.set(key, new Set())
  const set = new Set(next.get(key))
  if (set.has(ch)) set.delete(ch)
  else set.add(ch)
  next.set(key, set)
  selections.value = next
}

const totalSelectedCount = computed(() => {
  let count = 0
  for (const set of selections.value.values()) {
    if (set.size > 0) count++
  }
  return count
})

// Mensagem é opcional — se vazia, o backend usa o default "ENLACE OFF."
// e ainda inclui Cabos afetados com Origem/Destino. Só exige destinatário.
const canSend = computed(() => totalSelectedCount.value > 0)

function channelLabel(ch) {
  return { email: 'E-mail', whatsapp: 'WhatsApp', telegram: 'Telegram' }[ch] || ch
}

// ── Load recipients ────────────────────────────────────────────────────────
async function loadRecipients() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetch('/api/v1/inventory/maintenance-alert/recipients/', {
      credentials: 'include'
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    smtpEnabled.value = data.smtp_enabled
    users.value = data.users || []
    responsibles.value = data.responsibles || []
    contacts.value = data.contacts || []

    // Build initial selections
    const next = new Map()

    // Primary users (responsible_user of affected cables) → select ALL available channels
    const pUserIds = new Set(props.cables.map(c => c.responsible_user_id).filter(Boolean))
    for (const u of users.value) {
      if (pUserIds.has(u.id)) {
        // Select all available channels for primary responsibles
        next.set(recKey(u), new Set(u.channels))
      } else {
        // For other users, respect their notification preferences
        const set = new Set()
        if (u.notify_via_email && u.channels.includes('email')) set.add('email')
        if (u.notify_via_whatsapp && u.channels.includes('whatsapp')) set.add('whatsapp')
        if (u.notify_via_telegram && u.channels.includes('telegram')) set.add('telegram')
        if (set.size > 0) next.set(recKey(u), set)
      }
    }

    // Primary responsibles (responsible FK of affected cables) → select ALL available channels
    const pRespIds = new Set(props.cables.map(c => c.responsible_id).filter(Boolean))
    for (const r of responsibles.value) {
      if (pRespIds.has(r.id)) {
        next.set(recKey(r), new Set(r.channels))
      }
    }

    selections.value = next
  } catch (e) {
    loadError.value = 'Erro ao carregar destinatários: ' + e.message
  } finally {
    loading.value = false
  }
}

// ── Send ───────────────────────────────────────────────────────────────────
async function send() {
  if (!canSend.value) return
  sending.value = true
  try {
    const recipients = []
    for (const [key, channelSet] of selections.value.entries()) {
      if (channelSet.size === 0) continue
      const [type, id] = key.split('-')
      recipients.push({ type, id: parseInt(id), channels: Array.from(channelSet) })
    }

    const res = await fetch('/api/v1/inventory/maintenance-alert/send/', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({
        message: message.value.trim(),
        recipients,
        cables: props.cables.map(c => ({ id: c.id, name: c.name, status: c.status })),
        devices: props.devices.map(d => ({ id: d.id, name: d.name, site_name: d.site_name })),
      }),
    })
    const result = await res.json()
    if (!res.ok) throw new Error(result.error || `HTTP ${res.status}`)
    emit('sent', result)
  } catch (e) {
    emit('sent', { ok: false, error: e.message })
  } finally {
    sending.value = false
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────
// `immediate: true` cobre o caso em que o componente é montado já com
// visible=true (parent usa lazy v-if → não há transição false→true).
watch(() => props.visible, (val) => {
  if (val) {
    message.value = ''
    activeTab.value = 'users'
    selections.value = new Map()
    loadRecipients()
  }
}, { immediate: true })
</script>

<style scoped>

/* Context */
.nm-context {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgb(var(--warning) / 0.06);
  border-bottom: 1px solid rgb(var(--n-200));
  flex-shrink: 0;
}
.nm-ctx-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.75rem;
  color: rgb(var(--warning));
  font-weight: 600;
}
.nm-ctx-sep { color: rgb(var(--n-500)); font-size: 0.75rem; }

/* Loading / error */
.nm-loading, .nm-error {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 16px;
  font-size: 0.82rem;
  color: rgb(var(--n-600));
  justify-content: center;
}
.nm-error { color: rgb(var(--danger)); }

/* Section */
.nm-section {
  padding: 14px 16px 0;
  flex-shrink: 0;
}
.nm-label {
  display: block;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: rgb(var(--n-600));
  margin-bottom: 6px;
}
.nm-label-hint {
  font-size: 0.68rem;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  color: rgb(var(--n-500));
  margin-left: 6px;
}
.nm-textarea {
  width: 100%;
  background: rgb(var(--n-50));
  border: 1px solid rgb(var(--n-200));
  border-radius: 8px;
  color: rgb(var(--n-900));
  font-size: 0.82rem;
  padding: 10px 12px;
  resize: none;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
  box-sizing: border-box;
}
.nm-textarea:focus { border-color: rgb(var(--warning) / 0.5); }
.nm-textarea::placeholder { color: rgb(var(--n-400)); }

/* Tabs */
.nm-tabs {
  display: flex;
  gap: 0;
  padding: 12px 16px 0;
  border-bottom: 1px solid rgb(var(--n-200));
  flex-shrink: 0;
}
.nm-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: rgb(var(--n-600));
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.nm-tab.active { color: rgb(var(--warning)); border-bottom-color: rgb(var(--warning)); }
.nm-tab-count {
  background: rgb(var(--n-100));
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 0.68rem;
  font-weight: 700;
}
.nm-tab.active .nm-tab-count { background: rgb(var(--warning) / 0.2); color: rgb(var(--warning)); }

/* List */
.nm-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}
.nm-empty {
  padding: 24px 16px;
  text-align: center;
  font-size: 0.78rem;
  color: rgb(var(--n-500));
}
.nm-empty-hint { color: rgb(var(--danger) / 0.7); }

/* Group labels */
.nm-group-label {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px 4px;
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgb(var(--warning));
}
.nm-group-label--secondary {
  color: rgb(var(--n-500));
  padding-top: 12px;
  border-top: 1px solid rgb(var(--n-200));
  margin-top: 4px;
}

.nm-recipient {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid rgb(var(--n-200));
  transition: background 0.12s;
}
.nm-recipient:hover { background: rgb(var(--n-50)); }
.nm-recipient.selected { background: rgb(var(--warning) / 0.05); }
.nm-recipient--primary {
  background: rgb(var(--warning) / 0.04);
  border-left: 2px solid rgb(var(--warning) / 0.4);
}
.nm-recipient--primary.selected { background: rgb(var(--warning) / 0.09); }

.nm-rec-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}
.nm-rec-name-row {
  display: flex;
  align-items: center;
  gap: 7px;
}
.nm-rec-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: rgb(var(--n-900));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nm-badge-primary {
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: rgb(var(--warning));
  background: rgb(var(--warning) / 0.15);
  border: 1px solid rgb(var(--warning) / 0.3);
  border-radius: 4px;
  padding: 1px 5px;
  flex-shrink: 0;
}
.nm-rec-type {
  font-size: 0.68rem;
  color: rgb(var(--n-500));
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.nm-rec-detail {
  font-size: 0.72rem;
  color: rgb(var(--n-500));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Channel chips */
.nm-channels {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}
.nm-ch {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.68rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  background: rgb(var(--n-50));
  border: 1px solid rgb(var(--n-200));
  color: rgb(var(--n-500));
}
.nm-ch--email.active   { background: rgb(var(--info) / 0.18); border-color: rgb(var(--info) / 0.45); color: rgb(var(--info)); }
.nm-ch--whatsapp.active { background: rgb(var(--success) / 0.18); border-color: rgb(var(--success) / 0.45); color: rgb(var(--success)); }
.nm-ch--telegram.active { background: rgb(var(--info) / 0.18); border-color: rgb(var(--info) / 0.45); color: rgb(var(--info)); }
.nm-ch:hover { border-color: rgb(var(--n-300)); color: rgb(var(--n-700)); }

/* Footer */
.nm-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid rgb(var(--n-200));
  flex-shrink: 0;
}
.nm-sel-count {
  font-size: 0.75rem;
  color: rgb(var(--n-500));
}
.nm-footer-actions { display: flex; gap: 8px; }

.nm-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  border: 1px solid transparent;
}
.nm-btn--secondary {
  background: rgb(var(--n-100));
  border-color: rgb(var(--n-200));
  color: rgb(var(--n-700));
}
.nm-btn--secondary:hover { background: rgb(var(--n-100)); }
.nm-btn--primary {
  background: rgb(var(--warning));
  border-color: rgb(var(--warning));
  color: #0f172a; /* texto escuro fixo sobre o âmbar, nos dois temas */
}
.nm-btn--primary:hover:not(:disabled) { background: rgb(var(--warning)); }
.nm-btn--primary:disabled { opacity: 0.45; cursor: not-allowed; }

/* Spin animation */
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
