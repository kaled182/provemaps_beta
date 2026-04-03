/**
 * Plugin de Menu de Contexto - Para Network Design
 * 
 * Adiciona menu de contexto (right-click) ao mapa com ações customizadas.
 */

export default function createContextMenuPlugin(context, options = {}) {
  const { map, google } = context;
  const {
    menuItems = [],
    onItemClick = null
  } = options;

  // Estado interno
  let menuElement = null;
  let clickListener = null;
  let currentPosition = null;

  /**
   * Inicializa o menu de contexto
   */
  function init() {
    // Cria elemento do menu
    menuElement = createMenuElement();
    document.body.appendChild(menuElement);

    // Adiciona listener de right-click
    clickListener = map.addListener('rightclick', (event) => {
      showMenu(event.latLng, event.domEvent);
    });

    // Fecha menu ao clicar fora
    document.addEventListener('click', hideMenu);

    console.log('[ContextMenuPlugin] Initialized with', menuItems.length, 'items');
  }

  /**
   * Cria elemento HTML do menu
   * @returns {HTMLElement}
   */
  function createMenuElement() {
    const menu = document.createElement('div');
    menu.id = 'contextMenu';
    menu.className = 'context-menu';
    menu.style.cssText = `
      position: fixed;
      background: white;
      border: 1px solid #e5e7eb;
      border-radius: 6px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      padding: 4px 0;
      z-index: 10000;
      display: none;
      min-width: 180px;
    `;

    return menu;
  }

  /**
   * Exibe o menu de contexto
   * @param {google.maps.LatLng} latLng - Posição do clique
   * @param {MouseEvent} domEvent - Evento DOM original
   */
  function showMenu(latLng, domEvent) {
    if (!menuElement) return;

    currentPosition = latLng;

    // Limpa menu anterior
    menuElement.innerHTML = '';

    // Adiciona items
    menuItems.forEach(item => {
      if (item.separator) {
        const separator = document.createElement('div');
        separator.style.cssText = 'height: 1px; background: #e5e7eb; margin: 4px 0;';
        menuElement.appendChild(separator);
        return;
      }

      const menuItem = document.createElement('div');
      menuItem.className = 'context-menu-item';
      menuItem.textContent = item.label;
      menuItem.style.cssText = `
        padding: 8px 16px;
        cursor: pointer;
        font-size: 14px;
        color: #374151;
        transition: background-color 0.15s;
      `;

      // Hover effect
      menuItem.addEventListener('mouseenter', () => {
        menuItem.style.backgroundColor = '#f3f4f6';
      });
      menuItem.addEventListener('mouseleave', () => {
        menuItem.style.backgroundColor = 'transparent';
      });

      // Click handler
      menuItem.addEventListener('click', (e) => {
        e.stopPropagation();
        hideMenu();

        if (item.action) {
          item.action({ latLng, position: currentPosition });
        }

        if (onItemClick) {
          onItemClick(item.id || item.label, { latLng, position: currentPosition });
        }
      });

      menuElement.appendChild(menuItem);
    });

    // Posiciona menu
    menuElement.style.left = `${domEvent.clientX}px`;
    menuElement.style.top = `${domEvent.clientY}px`;
    menuElement.style.display = 'block';

    // Ajusta se sair da tela
    setTimeout(() => {
      const rect = menuElement.getBoundingClientRect();
      if (rect.right > window.innerWidth) {
        menuElement.style.left = `${window.innerWidth - rect.width - 10}px`;
      }
      if (rect.bottom > window.innerHeight) {
        menuElement.style.top = `${window.innerHeight - rect.height - 10}px`;
      }
    }, 0);
  }

  /**
   * Esconde o menu
   */
  function hideMenu() {
    if (menuElement) {
      menuElement.style.display = 'none';
    }
    currentPosition = null;
  }

  /**
   * Adiciona um item ao menu
   * @param {Object} item - { id, label, action }
   */
  function addMenuItem(item) {
    menuItems.push(item);
  }

  /**
   * Remove um item do menu
   * @param {string} itemId - ID do item
   */
  function removeMenuItem(itemId) {
    const index = menuItems.findIndex(item => item.id === itemId);
    if (index !== -1) {
      menuItems.splice(index, 1);
    }
  }

  /**
   * Cleanup do plugin
   */
  function cleanup() {
    if (clickListener) {
      google.maps.event.removeListener(clickListener);
      clickListener = null;
    }

    if (menuElement) {
      document.removeEventListener('click', hideMenu);
      menuElement.remove();
      menuElement = null;
    }
  }

  // Auto-init
  init();

  return {
    showMenu,
    hideMenu,
    addMenuItem,
    removeMenuItem,
    cleanup,
    // Getters
    get currentPosition() {
      return currentPosition;
    }
  };
}
