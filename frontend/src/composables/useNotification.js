/**
 * Composable para notificações toast
 * Sistema simples de notificações para feedback visual
 * @module useNotification
 */

import { ref } from 'vue';

// Estado global compartilhado entre componentes
const notifications = ref([]);
let notificationId = 0;

export function useNotification() {
  /**
   * Adiciona uma notificação
   * @param {Object} options - Opções da notificação
   * @param {string} options.type - Tipo: 'success', 'error', 'warning', 'info'
   * @param {string} options.title - Título da notificação
   * @param {string} options.message - Mensagem detalhada
   * @param {number} options.duration - Duração em ms (padrão: 5000)
   */
  function notify({ type = 'info', title, message, duration = 5000 }) {
    const id = ++notificationId;
    const notification = {
      id,
      type,
      title,
      message,
      visible: true,
    };

    notifications.value.push(notification);

    // Remove automaticamente após a duração
    if (duration > 0) {
      setTimeout(() => {
        remove(id);
      }, duration);
    }

    return id;
  }

  /**
   * Remove uma notificação
   * @param {number} id - ID da notificação
   */
  function remove(id) {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index > -1) {
      notifications.value.splice(index, 1);
    }
  }

  /**
   * Notificação de sucesso
   * @param {string} title - Título
   * @param {string} message - Mensagem
   */
  function success(title, message = '') {
    return notify({ type: 'success', title, message });
  }

  /**
   * Notificação de erro
   * @param {string} title - Título
   * @param {string} message - Mensagem de erro
   */
  function error(title, message = '') {
    return notify({ type: 'error', title, message, duration: 8000 });
  }

  /**
   * Notificação de aviso
   * @param {string} title - Título
   * @param {string} message - Mensagem
   */
  function warning(title, message = '') {
    return notify({ type: 'warning', title, message });
  }

  /**
   * Notificação informativa
   * @param {string} title - Título
   * @param {string} message - Mensagem
   */
  function info(title, message = '') {
    return notify({ type: 'info', title, message });
  }

  return {
    notifications,
    notify,
    remove,
    success,
    error,
    warning,
    info,
  };
}
