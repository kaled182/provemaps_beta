<template>
  <transition name="modal-fade">
    <div v-if="visible" class="notify-overlay" @click.self="$emit('close')">
      <div class="notify-modal">

        <!-- Header -->
        <div class="nm-header">
          <div class="nm-title">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.41 2 2 0 0 1 3.6 1.23h3a2 2 0 0 1 2 1.72c.13 1 .36 1.97.72 2.9a2 2 0 0 1-.45 2.11L7.91 9A16 16 0 0 0 14 15.08l.96-.96a2 2 0 0 1 2.11-.45c.93.35 1.9.59 2.9.72a2 2 0 0 1 1.72 2.03z"/>
            </svg>
            Notificar Responsáveis
          </div>
          <button class="nm-close" @click="$emit('close')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

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

      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
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
.notify-overlay {
  position: fixed;
  inset: 0;
  z-index: 9200;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}

.notify-modal {
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  background: rgba(15, 23, 42, 0.98);
  border: 1px solid rgba(245, 158, 11, 0.35);
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
  overflow: hidden;
}

/* Header */
.nm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.nm-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.88rem;
  font-weight: 700;
  color: #f59e0b;
}

.nm-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 7px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.15s;
}
.nm-close:hover { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border-color: rgba(239, 68, 68, 0.3); }

/* Context */
.nm-context {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(245, 158, 11, 0.06);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
}
.nm-ctx-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.75rem;
  color: #fbbf24;
  font-weight: 600;
}
.nm-ctx-sep { color: rgba(255, 255, 255, 0.25); font-size: 0.75rem; }

/* Loading / error */
.nm-loading, .nm-error {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 24px 16px;
  font-size: 0.82rem;
  color: rgba(255, 255, 255, 0.5);
  justify-content: center;
}
.nm-error { color: #fca5a5; }

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
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 6px;
}
.nm-label-hint {
  font-size: 0.68rem;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  color: rgba(255, 255, 255, 0.35);
  margin-left: 6px;
}
.nm-textarea {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  color: #e2e8f0;
  font-size: 0.82rem;
  padding: 10px 12px;
  resize: none;
  outline: none;
  font-family: inherit;
  transition: border-color 0.15s;
  box-sizing: border-box;
}
.nm-textarea:focus { border-color: rgba(245, 158, 11, 0.5); }
.nm-textarea::placeholder { color: rgba(255, 255, 255, 0.25); }

/* Tabs */
.nm-tabs {
  display: flex;
  gap: 0;
  padding: 12px 16px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
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
  color: rgba(255, 255, 255, 0.45);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.nm-tab.active { color: #f59e0b; border-bottom-color: #f59e0b; }
.nm-tab-count {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  padding: 1px 6px;
  font-size: 0.68rem;
  font-weight: 700;
}
.nm-tab.active .nm-tab-count { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }

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
  color: rgba(255, 255, 255, 0.3);
}
.nm-empty-hint { color: rgba(239, 68, 68, 0.7); }

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
  color: #f59e0b;
}
.nm-group-label--secondary {
  color: rgba(255, 255, 255, 0.3);
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: 4px;
}

.nm-recipient {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  transition: background 0.12s;
}
.nm-recipient:hover { background: rgba(255, 255, 255, 0.03); }
.nm-recipient.selected { background: rgba(245, 158, 11, 0.05); }
.nm-recipient--primary {
  background: rgba(245, 158, 11, 0.04);
  border-left: 2px solid rgba(245, 158, 11, 0.4);
}
.nm-recipient--primary.selected { background: rgba(245, 158, 11, 0.09); }

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
  color: #e2e8f0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nm-badge-primary {
  font-size: 0.62rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #fbbf24;
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 4px;
  padding: 1px 5px;
  flex-shrink: 0;
}
.nm-rec-type {
  font-size: 0.68rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.nm-rec-detail {
  font-size: 0.72rem;
  color: rgba(255, 255, 255, 0.35);
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
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.35);
}
.nm-ch--email.active   { background: rgba(59, 130, 246, 0.18); border-color: rgba(59, 130, 246, 0.45); color: #93c5fd; }
.nm-ch--whatsapp.active { background: rgba(16, 185, 129, 0.18); border-color: rgba(16, 185, 129, 0.45); color: #6ee7b7; }
.nm-ch--telegram.active { background: rgba(56, 189, 248, 0.18); border-color: rgba(56, 189, 248, 0.45); color: #7dd3fc; }
.nm-ch:hover { border-color: rgba(255, 255, 255, 0.25); color: rgba(255, 255, 255, 0.6); }

/* Footer */
.nm-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}
.nm-sel-count {
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.35);
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
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.6);
}
.nm-btn--secondary:hover { background: rgba(255, 255, 255, 0.1); }
.nm-btn--primary {
  background: #f59e0b;
  border-color: #f59e0b;
  color: #0f172a;
}
.nm-btn--primary:hover:not(:disabled) { background: #fbbf24; }
.nm-btn--primary:disabled { opacity: 0.45; cursor: not-allowed; }

/* Transition */
.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity 0.2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

/* Spin animation */
.spin { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Light theme overrides */
:root[data-theme="light"] .notify-modal {
  background: rgba(255, 255, 255, 0.98);
  border-color: rgba(245, 158, 11, 0.4);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}
:root[data-theme="light"] .nm-header {
  border-bottom-color: rgba(0, 0, 0, 0.08);
}
:root[data-theme="light"] .nm-close {
  background: rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.1);
  color: rgba(0, 0, 0, 0.4);
}
:root[data-theme="light"] .nm-close:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.3);
}
:root[data-theme="light"] .nm-context {
  border-bottom-color: rgba(0, 0, 0, 0.06);
}
</style>
