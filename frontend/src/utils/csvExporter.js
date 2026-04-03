/**
 * Utilitário para exportar dados para CSV
 * @module csvExporter
 */

/**
 * Converte array de objetos para CSV
 * @param {Array} data - Array de objetos
 * @param {Array} columns - Colunas a incluir {key, label}
 * @returns {string} String CSV
 */
export function arrayToCSV(data, columns) {
  if (!data || !data.length) return '';
  
  // Header
  const header = columns.map(col => col.label).join(',');
  
  // Rows
  const rows = data.map(item => {
    return columns.map(col => {
      let value = item[col.key];
      
      // Trata valores nulos/undefined
      if (value === null || value === undefined) {
        value = '';
      }
      
      // Trata objetos e arrays
      if (typeof value === 'object') {
        value = JSON.stringify(value);
      }
      
      // Escapa aspas duplas e envolve em aspas se contiver vírgula
      value = String(value).replace(/"/g, '""');
      if (value.includes(',') || value.includes('\n') || value.includes('"')) {
        value = `"${value}"`;
      }
      
      return value;
    }).join(',');
  });
  
  return [header, ...rows].join('\n');
}

/**
 * Download de arquivo CSV
 * @param {string} content - Conteúdo CSV
 * @param {string} filename - Nome do arquivo
 */
export function downloadCSV(content, filename = 'export.csv') {
  // Adiciona BOM para UTF-8 (para Excel abrir corretamente)
  const BOM = '\uFEFF';
  const blob = new Blob([BOM + content], { type: 'text/csv;charset=utf-8;' });
  
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  URL.revokeObjectURL(url);
}

/**
 * Exporta inventário de dispositivos para CSV
 * @param {Array} groups - Array de grupos com devices
 * @returns {void}
 */
export function exportInventoryToCSV(groups) {
  const devices = [];
  
  // Flatten grupos em devices
  groups.forEach(group => {
    if (group.devices && Array.isArray(group.devices)) {
      group.devices.forEach(device => {
        devices.push({
          ...device,
          group_name: group.group_name
        });
      });
    }
  });
  
  const columns = [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Nome' },
    { key: 'primary_ip', label: 'IP' },
    { key: 'site_name', label: 'Site' },
    { key: 'group_name', label: 'Grupo' },
    { key: 'category', label: 'Categoria' },
    { key: 'vendor', label: 'Fabricante' },
    { key: 'model', label: 'Modelo' },
    { key: 'zabbix_hostid', label: 'Zabbix ID' },
    { key: 'enable_screen_alert', label: 'Alerta Tela' },
    { key: 'enable_whatsapp_alert', label: 'Alerta WhatsApp' },
    { key: 'enable_email_alert', label: 'Alerta Email' }
  ];
  
  const csv = arrayToCSV(devices, columns);
  const timestamp = new Date().toISOString().split('T')[0];
  downloadCSV(csv, `inventario_${timestamp}.csv`);
}

/**
 * Exporta preview do Zabbix para CSV
 * @param {Array} hosts - Array de hosts do Zabbix
 * @returns {void}
 */
export function exportZabbixPreviewToCSV(hosts) {
  const columns = [
    { key: 'zabbix_id', label: 'Zabbix ID' },
    { key: 'name', label: 'Nome' },
    { key: 'ip', label: 'IP' },
    { key: 'group_name', label: 'Grupo Zabbix' },
    { key: 'is_imported', label: 'Já Importado' }
  ];
  
  const csv = arrayToCSV(hosts, columns);
  const timestamp = new Date().toISOString().split('T')[0];
  downloadCSV(csv, `zabbix_preview_${timestamp}.csv`);
}
