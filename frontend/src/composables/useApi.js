/**
 * Composable para requisições HTTP com suporte a CSRF token do Django
 * @module useApi
 */

/**
 * Obtém o CSRF token do cookie ou do meta tag
 * @returns {string} CSRF token
 */
export function getCsrfToken() {
  // Tenta pegar do window (definido no base_spa.html)
  if (window.CSRF_TOKEN) {
    return window.CSRF_TOKEN;
  }

  // Fallback: busca no cookie
  const name = 'csrftoken';
  const cookieValue = document.cookie
    .split('; ')
    .find(row => row.startsWith(`${name}=`))
    ?.split('=')[1];

  return cookieValue || '';
}

/**
 * Headers padrão para requisições autenticadas
 * @returns {Object} Headers com CSRF token
 */
export function getAuthHeaders() {
  return {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken(),
  };
}

/**
 * Composable para requisições de API
 */
export function useApi() {
  /**
   * Realiza requisição GET
   * @param {string} url - URL do endpoint
   * @returns {Promise<any>} Resposta da API
   */
  async function get(url) {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin', // Inclui cookies de sessão
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Realiza requisição POST
   * @param {string} url - URL do endpoint
   * @param {Object} data - Dados a enviar
   * @returns {Promise<any>} Resposta da API
   */
  async function post(url, data) {
    const response = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders(),
      credentials: 'same-origin',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Realiza requisição POST com FormData (para uploads)
   * @param {string} url - URL do endpoint
   * @param {FormData} formData - FormData com arquivos/campos
   * @returns {Promise<any>} Resposta da API
   */
  async function postFormData(url, formData) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        // NÃO definir Content-Type - deixa o browser configurar com boundary
      },
      credentials: 'same-origin',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Realiza requisição PUT
   * @param {string} url - URL do endpoint
   * @param {Object} data - Dados a enviar
   * @returns {Promise<any>} Resposta da API
   */
  async function put(url, data) {
    const response = await fetch(url, {
      method: 'PUT',
      headers: getAuthHeaders(),
      credentials: 'same-origin',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  /**
   * Realiza requisição DELETE
   * @param {string} url - URL do endpoint
   * @returns {Promise<any>} Resposta da API
   */
  async function del(url) {
    const response = await fetch(url, {
      method: 'DELETE',
      headers: getAuthHeaders(),
      credentials: 'same-origin',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    // Algumas deleções retornam 204 (sem corpo). Evitamos falha de JSON vazio.
    const text = await response.text();
    return text ? JSON.parse(text) : null;
  }

  /**
   * Realiza requisição PATCH
   * @param {string} url - URL do endpoint
   * @param {Object} data - Dados a enviar
   * @returns {Promise<any>} Resposta da API
   */
  async function patch(url, data) {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: getAuthHeaders(),
      credentials: 'same-origin',
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  return {
    get,
    post,
    postFormData,
    put,
    patch,
    delete: del,
  };
}
