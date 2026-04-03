<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal">
      <header class="modal-header">
        <div>
          <h3>{{ headerTitle }}</h3>
          <p class="subtitle">Personalize a mensagem enviada quando a condição é acionada.</p>
        </div>
        <button class="btn-icon" type="button" @click="handleClose" title="Fechar">
          <i class="fas fa-times"></i>
        </button>
      </header>

      <form class="modal-body" @submit.prevent="submitForm">
        <div class="grid">
          <label>
            Nome do modelo
            <input v-model.trim="form.name" type="text" required maxlength="120" placeholder="Ex.: Alerta nível óptico crítico" />
          </label>

          <label>
            Categoria
            <select v-model="form.category" required @change="handleCategoryChange">
              <option v-for="option in categories" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label>
            Canal
            <select v-model="form.channel" required>
              <option v-for="option in channels" :key="option.value" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>

          <label>
            Status
            <select v-model="form.is_active">
              <option :value="true">Ativo</option>
              <option :value="false">Inativo</option>
            </select>
          </label>
        </div>

        <label>
          Descrição (opcional)
          <textarea v-model.trim="form.description" rows="2" maxlength="200" placeholder="Resumo do objetivo deste modelo"></textarea>
        </label>

        <div v-if="form.channel === 'smtp'" class="grid">
          <label>
            Assunto do e-mail
            <input v-model.trim="form.subject" type="text" maxlength="140" placeholder="Ex.: Alerta de nível óptico - {{site_name}}" />
          </label>
        </div>

        <label>
          Conteúdo da mensagem
          <textarea
            ref="messageInput"
            v-model="form.content"
            rows="8"
            required
            placeholder="Digite a mensagem que será enviada"
          ></textarea>
        </label>

        <div class="placeholders">
          <div class="placeholders-header">
            <h4>Variáveis disponíveis</h4>
            <span class="hint">Clique para inserir a variável na mensagem.</span>
          </div>
          <div class="placeholder-chips">
            <button
              v-for="placeholder in categoryPlaceholders"
              :key="placeholder.key"
              class="chip"
              type="button"
              @click="insertPlaceholder(placeholder.key)"
            >
              {{ placeholder.label }}
            </button>
          </div>
          <ul class="placeholder-descriptions">
            <li v-for="placeholder in categoryPlaceholders" :key="placeholder.key">
              <strong>{{ placeholder.key }}</strong>
              <span>{{ placeholder.description }}</span>
            </li>
          </ul>
        </div>

        <section class="preview">
          <div class="preview-header">
            <h4>Pré-visualização</h4>
            <span class="hint">Valores simulados para revisão rápida.</span>
          </div>
          <pre>{{ previewContent }}</pre>
        </section>

        <footer class="modal-footer">
          <button class="btn-secondary" type="button" @click="handleClose">Cancelar</button>
          <button class="btn-primary" type="submit">
            <i class="fas fa-save"></i>
            Salvar modelo
          </button>
        </footer>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, nextTick } from 'vue'

const props = defineProps({
  template: {
    type: Object,
    default: null,
  },
  channels: {
    type: Array,
    default: () => [],
  },
  categories: {
    type: Array,
    default: () => [],
  },
  placeholderCatalog: {
    type: Object,
    default: () => ({}),
  },
})

const emit = defineEmits(['close', 'save'])

const DEFAULT_CONTENTS = {
  optical_level: [
    'Alerta de nível óptico {{alarm_level}}',
    '{{site_name}} · {{device_name}} · Porta {{port_name}}',
    '',
    'Medida atual: {{signal_level}} (limite {{signal_threshold}})',
    'Contatos: {{contact_name}} · {{contact_phone}}',
    '',
    'Horário do incidente: {{incident_time}}',
  ].join('\n'),
}

const SAMPLE_VALUES = {
  site_name: 'Vila Rica',
  device_name: 'OLT Huawei 01',
  port_name: 'xGigabitEthernet0/0/2',
  signal_level: '-28.5 dBm',
  signal_threshold: '-26 dBm',
  contact_name: 'João Silva',
  contact_phone: '+55 61 99999-0000',
  incident_time: '31/01/2026 16:04',
  alarm_level: 'Crítico',
  link_description: 'Último lançamento',
  link_length: '12.4 km',
}

const messageInput = ref(null)

const form = reactive({
  id: null,
  name: '',
  category: 'optical_level',
  channel: 'whatsapp',
  description: '',
  subject: '',
  content: DEFAULT_CONTENTS.optical_level,
  is_active: true,
})

const headerTitle = computed(() => (form.id ? 'Editar modelo' : 'Novo modelo'))

const categoryPlaceholders = computed(() => {
  const catalog = props.placeholderCatalog[form.category] || []
  return catalog.map(item => ({
    key: item.key,
    label: item.label || item.key,
    description: item.description || '',
  }))
})

const previewContent = computed(() => {
  if (!form.content) return ''
  let preview = form.content
  categoryPlaceholders.value.forEach(({ key }) => {
    const value = SAMPLE_VALUES[key] || `{{${key}}}`
    const pattern = new RegExp(`{{\\s*${key}\\s*}}`, 'g')
    preview = preview.replace(pattern, value)
  })
  return preview
})

const hydrateForm = (template) => {
  if (!template) {
    resetForm()
    return
  }
  form.id = template.id || null
  form.name = template.name || ''
  form.category = template.category || form.category
  form.channel = template.channel || form.channel
  form.description = template.description || ''
  form.subject = template.subject || ''
  form.content = template.content || getDefaultContent(form.category)
  form.is_active = typeof template.is_active === 'boolean' ? template.is_active : true
}

const getDefaultContent = (category) => {
  if (DEFAULT_CONTENTS[category]) return DEFAULT_CONTENTS[category]
  return 'Mensagem do alerta: {{placeholder}}'
}

const resetForm = () => {
  form.id = null
  form.name = ''
  form.category = props.categories[0]?.value || 'optical_level'
  form.channel = props.channels[0]?.value || 'whatsapp'
  form.description = ''
  form.subject = ''
  form.content = getDefaultContent(form.category)
  form.is_active = true
}

const handleCategoryChange = () => {
  if (!form.content) {
    form.content = getDefaultContent(form.category)
  }
}

const insertPlaceholder = (key) => {
  const token = `{{${key}}}`
  const textarea = messageInput.value
  if (!textarea) {
    form.content = `${form.content || ''}${token}`
    return
  }
  const { selectionStart, selectionEnd, value } = textarea
  const start = selectionStart || 0
  const end = selectionEnd || 0
  form.content = `${value.slice(0, start)}${token}${value.slice(end)}`
  nextTick(() => {
    textarea.focus()
    const cursor = start + token.length
    textarea.setSelectionRange(cursor, cursor)
  })
}

const handleClose = () => {
  emit('close')
}

const submitForm = () => {
  const payload = {
    id: form.id || undefined,
    name: form.name.trim(),
    category: form.category,
    channel: form.channel,
    description: form.description?.trim() || '',
    subject: form.subject?.trim() || '',
    content: form.content,
    is_active: form.is_active,
  }
  emit('save', payload)
}

watch(
  () => props.template,
  (template) => {
    hydrateForm(template)
  },
  { immediate: true }
)

watch(
  () => props.categories,
  (categories) => {
    if (!form.category && categories.length) {
      form.category = categories[0].value
      form.content = getDefaultContent(form.category)
    }
  },
  { immediate: true }
)

watch(
  () => props.channels,
  (channels) => {
    if (!form.channel && channels.length) {
      form.channel = channels[0].value
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  z-index: 1000;
}

.modal {
  width: min(820px, 100%);
  max-height: 92vh;
  background: var(--surface-card);
  color: var(--text-primary);
  border-radius: 18px;
  border: 1px solid var(--border-primary);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 28px 20px;
  border-bottom: 1px solid var(--border-primary);
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  margin: 6px 0 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

.btn-icon {
  background: transparent;
  border: none;
  color: var(--text-tertiary);
  font-size: 18px;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
}

.btn-icon:hover {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

.modal-body {
  padding: 24px 28px 28px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px 18px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

input,
select,
textarea {
  border-radius: 10px;
  border: 1px solid var(--border-primary);
  background: var(--surface-muted);
  color: var(--text-primary);
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
  transition: border 0.2s ease, box-shadow 0.2s ease;
}

input:focus,
select:focus,
textarea:focus {
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px var(--status-online-light);
}

textarea {
  resize: vertical;
  min-height: 140px;
}

.placeholders {
  border: 1px solid var(--border-primary);
  border-radius: 14px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: var(--bg-secondary);
}

.placeholders-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.placeholders h4,
.preview-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.hint {
  font-size: 12px;
  color: var(--text-tertiary);
}

.placeholder-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  border: 1px solid rgba(96, 165, 250, 0.45);
  background: rgba(59, 130, 246, 0.08);
  color: #60a5fa;
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s ease, transform 0.2s ease;
}

.chip:hover {
  background: rgba(59, 130, 246, 0.16);
  transform: translateY(-1px);
}

.placeholder-descriptions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px 12px;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 12px;
  color: var(--text-tertiary);
}

.placeholder-descriptions strong {
  display: block;
  color: var(--text-secondary);
  margin-bottom: 2px;
}

.preview {
  border: 1px solid var(--border-primary);
  border-radius: 16px;
  padding: 18px;
  background: var(--bg-secondary);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

pre {
  margin: 0;
  font-size: 13px;
  font-family: 'JetBrains Mono', 'Fira Mono', monospace;
  white-space: pre-wrap;
  color: var(--text-primary);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 12px;
}

.btn-secondary {
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid var(--border-primary);
  background: var(--surface-muted);
  color: var(--text-secondary);
  cursor: pointer;
}

.btn-secondary:hover {
  background: var(--menu-item-hover);
  color: var(--text-primary);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 18px;
  border-radius: 10px;
  border: none;
  cursor: pointer;
  background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%);
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 14px 32px rgba(37, 99, 235, 0.28);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 38px rgba(37, 99, 235, 0.38);
}

@media (max-width: 720px) {
  .modal {
    margin: 0 8px;
  }

  .modal-body {
    padding: 20px;
  }

  .placeholder-descriptions {
    grid-template-columns: 1fr;
  }
}
</style>
