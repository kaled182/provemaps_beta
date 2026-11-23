<template>
  <Teleport to="body">
    <Transition name="bm-fade">
      <div
        v-if="show"
        class="bm-backdrop"
        :style="{ zIndex }"
        data-testid="base-modal"
        @mousedown.self="requestClose"
      >
        <section
          ref="panel"
          class="bm-panel"
          :class="`bm-${size}`"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          @keydown.esc.stop.prevent="requestClose"
        >
          <!-- Cabeçalho compacto numa linha -->
          <header class="bm-header">
            <span v-if="icon || $slots.icon" class="bm-icon" :class="`bm-icon-${status}`" aria-hidden="true">
              <slot name="icon"><component :is="icon" :size="18" weight="bold" /></slot>
            </span>
            <div class="bm-titles">
              <h2 :id="titleId" class="bm-title">{{ title }}</h2>
              <span v-if="subtitle" class="bm-subtitle">{{ subtitle }}</span>
              <slot name="badges" />
            </div>
            <div class="bm-actions">
              <slot name="header-actions" />
              <button type="button" class="bm-close" title="Fechar (Esc)" data-testid="base-modal-close" @click="requestClose">
                <PhX :size="16" weight="bold" />
              </button>
            </div>
          </header>

          <div class="bm-body" :class="{ 'bm-body-flush': flush }">
            <slot />
          </div>

          <!-- Aviso de alterações por guardar: substitui o window.confirm -->
          <footer v-if="confirmingDiscard || $slots.footer" class="bm-footer">
            <div v-if="confirmingDiscard" class="bm-discard" role="alert" data-testid="base-modal-discard">
              <PhWarning :size="16" class="bm-discard-icon" />
              <span>Há alterações por guardar.</span>
              <button type="button" class="bm-btn" data-testid="base-modal-keep" @click="confirmingDiscard = false">
                Continuar a editar
              </button>
              <button type="button" class="bm-btn bm-btn-danger" data-testid="base-modal-discard-confirm" @click="discard">
                Descartar alterações
              </button>
            </div>
            <slot v-else name="footer" />
          </footer>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
/**
 * Modal único do produto (EV-0064). Superfície e bordas por tokens (dois temas),
 * cabeçalho compacto numa linha com ícone na cor do estado, tamanhos padronizados.
 *
 * Fechar com `dirty=true` não usa `window.confirm`: mostra um aviso no rodapé
 * («Continuar a editar» / «Descartar alterações»). Esc, clique fora e o X passam
 * todos por aqui. Emite `close` só quando fecha de facto.
 */
import { nextTick, ref, watch, onBeforeUnmount } from 'vue'
import { PhX, PhWarning } from '@phosphor-icons/vue'

const props = defineProps({
  show: { type: Boolean, default: false },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  /** componente de ícone (phosphor) */
  icon: { type: [Object, Function], default: null },
  /** cor do ícone: online | attention | critical | neutral */
  status: { type: String, default: 'neutral' },
  /** detail (max-w-5xl) | md (max-w-2xl) | sm (max-w-md) */
  size: { type: String, default: 'detail' },
  /** há edição com alterações por guardar */
  dirty: { type: Boolean, default: false },
  /** corpo sem padding (quando o conteúdo tem abas/grelhas próprias) */
  flush: { type: Boolean, default: false },
  /** camada; um modal aberto por cima de outro BaseModal passa um valor maior */
  zIndex: { type: Number, default: 3000 },
})
const emit = defineEmits(['close'])

const titleId = `bm-title-${Math.random().toString(36).slice(2, 10)}`
const panel = ref(null)
const confirmingDiscard = ref(false)
let previousFocus = null

function requestClose() {
  if (props.dirty) {
    confirmingDiscard.value = true
    return
  }
  emit('close')
}

function discard() {
  confirmingDiscard.value = false
  emit('close')
}

watch(
  () => props.show,
  async (open) => {
    confirmingDiscard.value = false
    if (open) {
      previousFocus = document.activeElement
      document.body.style.overflow = 'hidden'
      await nextTick()
      panel.value?.focus()
    } else {
      document.body.style.overflow = ''
      previousFocus?.focus?.()
    }
  },
  { immediate: true },
)

watch(
  () => props.dirty,
  (d) => {
    if (!d) confirmingDiscard.value = false
  },
)

onBeforeUnmount(() => {
  document.body.style.overflow = ''
})

defineExpose({ requestClose })
</script>

<style scoped>
.bm-backdrop {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(0 0 0 / 0.6);
  backdrop-filter: blur(4px);
}
.bm-panel {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-height: 88vh;
  border-radius: 12px;
  border: 1px solid rgb(var(--n-200));
  background: rgb(var(--surface));
  color: rgb(var(--n-900));
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.15), 0 8px 10px -6px rgb(0 0 0 / 0.1);
  outline: none;
}
.bm-detail { max-width: 64rem; } /* max-w-5xl */
.bm-md { max-width: 42rem; }
.bm-sm { max-width: 28rem; }

.bm-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid rgb(var(--n-200));
  flex-shrink: 0;
}
.bm-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  flex-shrink: 0;
}
.bm-icon-online { background: rgb(var(--success) / 0.14); color: rgb(var(--success)); }
.bm-icon-attention { background: rgb(var(--warning) / 0.16); color: rgb(var(--warning)); }
.bm-icon-critical { background: rgb(var(--danger) / 0.14); color: rgb(var(--danger)); }
.bm-icon-neutral { background: rgb(var(--primary-500) / 0.14); color: rgb(var(--primary-600)); }
.bm-titles {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 10px;
  min-width: 0;
  flex: 1;
}
.bm-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bm-subtitle {
  font-size: 12px;
  color: rgb(var(--n-500));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.bm-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.bm-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 8px;
  color: rgb(var(--n-500));
}
.bm-close:hover {
  background: rgb(var(--n-100));
  color: rgb(var(--n-900));
}
.bm-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 20px;
}
.bm-body-flush { padding: 0; }
.bm-footer {
  flex-shrink: 0;
  padding: 10px 20px;
  border-top: 1px solid rgb(var(--n-200));
}
.bm-discard {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
}
.bm-discard-icon { color: rgb(var(--warning)); }
.bm-discard span { flex: 1; min-width: 160px; }
.bm-btn {
  padding: 5px 10px;
  border-radius: 6px;
  border: 1px solid rgb(var(--n-300));
  font-size: 13px;
  font-weight: 500;
  color: rgb(var(--n-800));
}
.bm-btn:hover { background: rgb(var(--n-100)); }
.bm-btn-danger {
  border-color: rgb(var(--danger) / 0.5);
  color: rgb(var(--danger));
}
.bm-btn-danger:hover { background: rgb(var(--danger) / 0.1); }

.bm-fade-enter-active,
.bm-fade-leave-active { transition: opacity 0.15s ease; }
.bm-fade-enter-from,
.bm-fade-leave-to { opacity: 0; }
</style>
