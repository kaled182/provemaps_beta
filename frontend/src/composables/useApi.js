/**
 * Composable para requisições HTTP com suporte a CSRF token do Django
 * @module useApi
 */

// EV-0072: o Django chama o cookie `mapsprovefiber_csrftoken` (settings/base.py,
// CSRF_COOKIE_NAME). Antes procurava-se `csrftoken=` no início do cookie — nunca
// encontrava, e quem não tinha o window.CSRF_TOKEN (CronTab) mandava o cabeçalho vazio → 403.
export const CSRF_COOKIE_NAMES = ['mapsprovefiber_csrftoken', 'csrftoken']

export function readCookie(name, cookieString = typeof document === 'undefined' ? '' : document.cookie) {
  const row = cookieString
    .split(';')
    .map((c) => c.trim())
    .find((c) => c.startsWith(`${name}=`))
  return row ? decodeURIComponent(row.slice(name.length + 1)) : ''
}

/** Token CSRF: o injetado pelo base_spa.html; senão o cookie pelo nome real. Único ponto de leitura. */
export function getCsrfToken() {
  if (typeof window !== 'undefined' && window.CSRF_TOKEN) return window.CSRF_TOKEN
  for (const name of CSRF_COOKIE_NAMES) {
    const value = readCookie(name)
    if (value) return value
  }
  console.warn('[useApi] CSRF token não encontrado (window.CSRF_TOKEN nem cookie)')
  return ''
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
  async function get(url, params = null) {
    let finalUrl = url;
    if (params && typeof params === 'object') {
      const search = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') {
          return;
        }
        search.append(key, String(value));
      });
      const query = search.toString();
      if (query) {
        finalUrl = `${url}${url.includes('?') ? '&' : '?'}${query}`;
      }
    }

    const response = await fetch(finalUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'same-origin', // Inclui cookies de sessão
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      const message =
        error.message ||
        error.error ||
        error.detail ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
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
      const message =
        error.message ||
        error.error ||
        error.detail ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
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
      const message =
        error.message ||
        error.error ||
        error.detail ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
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
      const message =
        error.message ||
        error.error ||
        error.detail ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
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
      const message =
        error.message ||
        error.error ||
        error.detail ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
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
      const message =
        error.message ||
        error.error ||
        error.detail ||
        `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(message);
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
