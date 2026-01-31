<template>
  <div class="modal-overlay" @click="$emit('close')">
    <div class="modal-dialog" @click.stop>
      <header class="modal-header">
        <h3>Importar Contatos</h3>
        <button type="button" class="btn-close" @click="$emit('close')">&times;</button>
      </header>

      <div class="modal-body">
        <section
          class="dropzone"
          :class="{ 'dropzone-active': isDragging, 'dropzone-has-file': selectedFile }"
          @dragover.prevent="handleDragOver"
          @dragleave.prevent="handleDragLeave"
          @drop.prevent="handleDrop"
        >
          <input ref="fileInput" class="file-input" type="file" accept=".csv,.xls,.xlsx" @change="handleFileChange" />

          <div class="dropzone-content">
            <i class="fas fa-file-upload"></i>
            <p v-if="!selectedFile">
              Arraste e solte um arquivo CSV ou Excel aqui, ou
              <button type="button" class="link-button" @click="triggerFilePicker">selecione um arquivo</button>
            </p>
            <p v-else class="selected-file">
              <strong>{{ selectedFile.name }}</strong>
              <span>({{ formatSize(selectedFile.size) }})</span>
            </p>
            <small>Formatos aceitos: CSV, XLS, XLSX • Tamanho máximo: 5MB</small>
          </div>
        </section>

        <div v-if="errorMessage" class="alert-error">
          <i class="fas fa-exclamation-triangle"></i>
          <span>{{ errorMessage }}</span>
        </div>

        <div class="form-group">
          <label for="import-group">Adicionar ao grupo</label>
          <select id="import-group" v-model="selectedGroup" class="form-control">
            <option value="">Nenhum grupo</option>
            <option v-for="group in groups" :key="group.id" :value="group.id">{{ group.name }}</option>
          </select>
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input v-model="updateExisting" type="checkbox" />
            Atualizar contatos existentes
          </label>
          <small class="form-hint">Quando marcado, contatos com o mesmo telefone serão atualizados.</small>
        </div>

        <section class="instructions">
          <h4>Instruções</h4>
          <ul>
            <li>A primeira linha do arquivo deve conter o cabeçalho.</li>
            <li>Campos suportados: <code>name</code>, <code>phone</code>, <code>email</code>, <code>company</code>, <code>position</code>, <code>notes</code>.</li>
            <li>O telefone deve incluir DDD. Exemplo: <code>61999999999</code> ou <code>+5561999999999</code>.</li>
          </ul>
        </section>
      </div>

      <footer class="modal-footer">
        <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="!selectedFile" @click="handleImport">
          <i class="fas fa-upload"></i>
          Importar
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  groups: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['close', 'import'])

const fileInput = ref(null)
const selectedFile = ref(null)
const selectedGroup = ref('')
const updateExisting = ref(false)
const isDragging = ref(false)
const errorMessage = ref('')

const supportedMimeTypes = new Set([
  'text/csv',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
])

const formatSize = (bytes) => {
  const units = ['B', 'KB', 'MB', 'GB']
  if (!bytes) {
    return '0 B'
  }
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  const size = bytes / 1024 ** exponent
  return `${size.toFixed(1)} ${units[exponent]}`
}

const validateFile = (file) => {
  errorMessage.value = ''
  if (!file) {
    return false
  }
  const isValidType = supportedMimeTypes.has(file.type) || ['csv', 'xls', 'xlsx'].some((ext) => file.name.toLowerCase().endsWith(ext))
  if (!isValidType) {
    errorMessage.value = 'Formato inválido. Utilize CSV, XLS ou XLSX.'
    return false
  }
  if (file.size > 5 * 1024 * 1024) {
    errorMessage.value = 'Arquivo excede o limite de 5MB.'
    return false
  }
  return true
}

const processFile = (file) => {
  if (validateFile(file)) {
    selectedFile.value = file
  } else {
    selectedFile.value = null
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}

const triggerFilePicker = () => {
  fileInput.value?.click()
}

const handleFileChange = (event) => {
  const file = event.target.files?.[0]
  processFile(file || null)
}

const handleDragOver = () => {
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleDrop = (event) => {
  isDragging.value = false
  const file = event.dataTransfer?.files?.[0]
  processFile(file || null)
}

const handleImport = () => {
  if (!selectedFile.value) {
    errorMessage.value = 'Selecione um arquivo antes de importar.'
    return
  }
  emit('import', selectedFile.value, selectedGroup.value || null, updateExisting.value)
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.modal-dialog {
  width: 100%;
  max-width: 620px;
  background: var(--surface-card, #ffffff);
  border-radius: 12px;
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.32);
  overflow: hidden;
}

.modal-header,
.modal-footer {
  background: var(--bg-secondary, #f8fafc);
  border-color: var(--border-secondary, #cbd5e1);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border-secondary, #cbd5e1);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--text-primary, #0f172a);
}

.btn-close {
  background: none;
  border: none;
  font-size: 28px;
  color: var(--text-tertiary, #94a3b8);
  cursor: pointer;
  line-height: 1;
}

.btn-close:hover {
  color: var(--text-primary, #0f172a);
}

.modal-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dropzone {
  position: relative;
  border: 2px dashed var(--border-secondary, #cbd5e1);
  border-radius: 12px;
  padding: 32px 24px;
  background: var(--bg-secondary, #f8fafc);
  text-align: center;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.dropzone-active {
  border-color: var(--accent-primary, #2563eb);
  background: rgba(37, 99, 235, 0.08);
}

.dropzone-has-file {
  border-color: var(--accent-info, #38bdf8);
}

.file-input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.dropzone-content {
  position: relative;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--text-secondary, #475569);
}

.dropzone-content i {
  font-size: 32px;
  color: var(--accent-primary, #2563eb);
}

.dropzone-content p {
  margin: 0;
  line-height: 1.5;
}

.dropzone-content small {
  color: var(--text-tertiary, #94a3b8);
}

.link-button {
  pointer-events: auto;
  background: none;
  border: none;
  color: var(--accent-primary, #2563eb);
  cursor: pointer;
  font-weight: 600;
  text-decoration: underline;
}

.selected-file {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.selected-file span {
  color: var(--text-tertiary, #94a3b8);
  font-size: 13px;
}

.alert-error {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 14px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.1);
  color: var(--accent-danger, #dc2626);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: 500;
  color: var(--text-primary, #0f172a);
}

.form-control {
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid var(--border-secondary, #cbd5e1);
  background: var(--surface-card, #ffffff);
  color: var(--text-primary, #0f172a);
  font-size: 14px;
}

.form-control:focus {
  outline: none;
  border-color: var(--accent-primary, #2563eb);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary, #475569);
  font-weight: 500;
}

.checkbox-label input[type='checkbox'] {
  width: 16px;
  height: 16px;
}

.form-hint {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
}

.instructions {
  padding: 16px;
  border-radius: 8px;
  background: var(--bg-secondary, #f8fafc);
  border: 1px solid var(--border-secondary, #cbd5e1);
}

.instructions h4 {
  margin: 0 0 8px;
  font-size: 15px;
  color: var(--text-primary, #0f172a);
}

.instructions ul {
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary, #475569);
  line-height: 1.5;
}

.instructions code {
  background: var(--surface-highlight, #e2e8f0);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 22px;
  border-top: 1px solid var(--border-secondary, #cbd5e1);
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 18px;
  border-radius: 6px;
  border: none;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.btn-primary {
  background: var(--accent-primary, #2563eb);
  color: #fff;
}

.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.btn-primary:not(:disabled):hover {
  background: var(--accent-primary-dark, #1e40af);
}

.btn-secondary {
  background: var(--bg-secondary, #f8fafc);
  color: var(--text-primary, #0f172a);
  border: 1px solid var(--border-secondary, #cbd5e1);
}

.btn-secondary:hover {
  background: var(--surface-highlight, #f1f5f9);
}

@media (max-width: 768px) {
  .modal-dialog {
    max-width: 92vw;
  }

  .dropzone {
    padding: 26px 18px;
  }
}
</style>