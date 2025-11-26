/**
 * Utilitários de validação para formulários
 * @module validators
 */

/**
 * Valida endereço IPv4
 * @param {string} ip - Endereço IP
 * @returns {boolean} True se válido
 */
export function isValidIPv4(ip) {
  if (!ip || typeof ip !== 'string') return false;
  
  const parts = ip.split('.');
  if (parts.length !== 4) return false;
  
  return parts.every(part => {
    const num = parseInt(part, 10);
    return num >= 0 && num <= 255 && part === num.toString();
  });
}

/**
 * Valida endereço IPv6
 * @param {string} ip - Endereço IP
 * @returns {boolean} True se válido
 */
export function isValidIPv6(ip) {
  if (!ip || typeof ip !== 'string') return false;
  
  const ipv6Regex = /^(([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|::([0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:)$/;
  return ipv6Regex.test(ip);
}

/**
 * Valida endereço IP (IPv4 ou IPv6)
 * @param {string} ip - Endereço IP
 * @returns {boolean} True se válido
 */
export function isValidIP(ip) {
  return isValidIPv4(ip) || isValidIPv6(ip);
}

/**
 * Valida nome de dispositivo
 * @param {string} name - Nome do dispositivo
 * @returns {boolean} True se válido
 */
export function isValidDeviceName(name) {
  if (!name || typeof name !== 'string') return false;
  
  // Nome deve ter entre 1 e 120 caracteres
  // Pode conter letras, números, hífen, underscore e ponto
  const nameRegex = /^[a-zA-Z0-9._-]{1,120}$/;
  return nameRegex.test(name);
}

/**
 * Valida nome de grupo
 * @param {string} groupName - Nome do grupo
 * @returns {boolean} True se válido
 */
export function isValidGroupName(groupName) {
  if (!groupName || typeof groupName !== 'string') return false;
  
  // Grupo deve ter entre 1 e 255 caracteres
  return groupName.length >= 1 && groupName.length <= 255;
}

/**
 * Valida objeto de dispositivo completo
 * @param {Object} device - Objeto do dispositivo
 * @returns {Object} {valid: boolean, errors: string[]}
 */
export function validateDevice(device) {
  const errors = [];
  
  if (!device.name || !isValidDeviceName(device.name)) {
    errors.push('Nome do dispositivo inválido (1-120 caracteres alfanuméricos)');
  }
  
  if (device.ip && !isValidIP(device.ip)) {
    errors.push('Endereço IP inválido');
  }
  
  if (device.ip_address && !isValidIP(device.ip_address)) {
    errors.push('Endereço IP inválido');
  }
  
  if (!device.category || !['backbone', 'gpon', 'dwdm', 'access'].includes(device.category)) {
    errors.push('Categoria inválida');
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Valida múltiplos dispositivos
 * @param {Array} devices - Array de dispositivos
 * @returns {Object} {valid: boolean, deviceErrors: Object}
 */
export function validateDevices(devices) {
  const deviceErrors = {};
  let allValid = true;
  
  devices.forEach((device, index) => {
    const result = validateDevice(device);
    if (!result.valid) {
      deviceErrors[index] = result.errors;
      allValid = false;
    }
  });
  
  return {
    valid: allValid,
    deviceErrors
  };
}
