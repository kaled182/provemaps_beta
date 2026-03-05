// apiClient.js - Centralized API communication for Fiber Route Builder
// Responsibilities:
//  - Provide small, composable async functions for backend interaction
//  - Normalize error handling and JSON parsing
//  - Abstract fetch & CSRF details
//  - Keep responses as-is (caller shapes UI)

const API_BASE = '/api/v1/inventory';

function getCsrfToken() {
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

  if (!cookieValue) {
    console.warn('[apiClient] CSRF token not found in window.CSRF_TOKEN or cookie');
  }

  return cookieValue || '';
}

async function request(path, { method = 'GET', headers = {}, body, skipJson } = {}) {
  const url = `${API_BASE}${path}`;
  const finalHeaders = {
    'Accept': 'application/json',
    ...headers,
  };
  // Attach CSRF token for state-changing methods
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCsrfToken();
    if (!csrfToken) {
      console.error('[apiClient] Cannot perform', method, 'request - CSRF token is missing');
    }
    finalHeaders['X-CSRFToken'] = csrfToken;
    if (body && !finalHeaders['Content-Type']) {
      finalHeaders['Content-Type'] = 'application/json';
    }
  }
  const response = await fetch(url, {
    method,
    headers: finalHeaders,
    credentials: 'same-origin',
    cache: 'no-store',
    body,
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const dataErr = await response.json();
      detail = dataErr.error || dataErr.detail || JSON.stringify(dataErr);
    } catch (_) { /* ignore */ }
    throw new Error(detail);
  }
  if (response.status === 204 || skipJson) return null;
  try {
    return await response.json();
  } catch (e) {
    throw new Error('Invalid JSON response');
  }
}

// Fiber list
export async function fetchFibers() {
  // Endpoint returns { fibers: [...] }
  return await request('/fibers/');
}

// Fiber detail
export async function fetchFiber(id) {
  return await request(`/fibers/${id}/`);
}

// Manual create fiber (includes endpoints + path)
export async function createFiberManual(payload) {
  return await request('/fibers/manual-create/', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

// Update entire fiber (metadata or path combined)
export async function updateFiber(id, payload) {
  return await request(`/fibers/${id}/`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

// Delete fiber
export async function removeFiber(id) {
  await request(`/fibers/${id}/`, { method: 'DELETE', skipJson: true });
  return true;
}

// Device ports
export async function fetchDevicePorts(deviceId) {
  return await request(`/devices/${deviceId}/ports/`);
}

export { getCsrfToken }; // Export for external use if needed
