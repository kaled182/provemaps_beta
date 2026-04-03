/**
 * Composable para gerenciar o fechamento de modais com a tecla ESC
 * 
 * @example
 * // Uso básico - fecha sempre que ESC é pressionada
 * useEscapeKey(() => close())
 * 
 * @example
 * // Com controle de estado - só fecha quando modal está aberto
 * useEscapeKey(() => close(), { isOpen: computed(() => props.isOpen) })
 * 
 * @example
 * // Ignorar ESC quando modal filho está aberto
 * useEscapeKey(() => close(), { 
 *   isOpen: computed(() => props.isOpen),
 *   shouldIgnore: showChildModal 
 * })
 * 
 * @param {Function} closeCallback - Função a ser chamada quando ESC for pressionada
 * @param {Object} options - Opções adicionais
 * @param {Ref<boolean>} options.isOpen - Ref que indica se o modal está aberto (gerencia listener automaticamente)
 * @param {Ref<boolean>} options.shouldIgnore - Ref que indica se deve ignorar ESC (ex: quando modal filho está aberto)
 */
import { watch, onUnmounted } from 'vue'

export function useEscapeKey(closeCallback, options = {}) {
  const { isOpen, shouldIgnore } = options

  const handleEscKey = (event) => {
    if (event.key === 'Escape') {
      // Se shouldIgnore foi fornecido e está true, não faz nada
      if (shouldIgnore && shouldIgnore.value) {
        return
      }
      
      // Se isOpen foi fornecido, só fecha se estiver aberto
      if (isOpen && !isOpen.value) {
        return
      }
      
      closeCallback()
    }
  }

  // Se isOpen foi fornecido, gerencia automaticamente o listener
  if (isOpen) {
    watch(isOpen, (newValue) => {
      if (newValue) {
        document.addEventListener('keydown', handleEscKey)
      } else {
        document.removeEventListener('keydown', handleEscKey)
      }
    })
  } else {
    // Caso contrário, adiciona o listener imediatamente
    document.addEventListener('keydown', handleEscKey)
  }

  // Cleanup ao desmontar componente
  onUnmounted(() => {
    document.removeEventListener('keydown', handleEscKey)
  })

  return {
    handleEscKey
  }
}

