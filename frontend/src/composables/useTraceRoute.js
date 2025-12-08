/**
 * Composable for Trace Route functionality
 * 
 * Provides methods to trace optical paths and analyze power budgets.
 */

import { ref } from 'vue';
import { useApi } from '@/composables/useApi';

export function useTraceRoute() {
  const api = useApi();
  const loading = ref(false);
  const error = ref(null);
  const traceResult = ref(null);

  /**
   * Trace the optical path starting from a fiber strand
   * 
   * @param {number} strandId - ID of the starting fiber strand
   * @returns {Promise<Object>} Trace result with path, power budget, etc.
   */
  async function traceFromStrand(strandId) {
    loading.value = true;
    error.value = null;
    traceResult.value = null;

    try {
      const response = await api.get(`/api/v1/inventory/trace-route/?strand_id=${strandId}`);
      traceResult.value = response;
      return response;
    } catch (err) {
      error.value = err.message || 'Erro ao rastrear caminho óptico';
      throw err;
    } finally {
      loading.value = false;
    }
  }

  /**
   * Export trace result as PDF report
   * 
   * @param {Object} trace - Trace result object
   */
  function exportTracePDF(trace) {
    // TODO: Implement PDF export
    console.log('Exportando trace:', trace);
    
    // For now, generate a simple text report
    const report = generateTextReport(trace);
    downloadTextFile(report, `trace-route-${trace.trace_id}.txt`);
  }

  /**
   * Generate text report from trace result
   * 
   * @param {Object} trace - Trace result
   * @returns {string} Text report
   */
  function generateTextReport(trace) {
    const lines = [];
    
    lines.push('═══════════════════════════════════════════════════');
    lines.push('           RELATÓRIO DE TRACE ROUTE');
    lines.push('═══════════════════════════════════════════════════');
    lines.push('');
    lines.push(`Trace ID: ${trace.trace_id}`);
    lines.push(`Status: ${trace.status}`);
    lines.push('');
    
    // Summary
    lines.push('RESUMO:');
    lines.push(`  Origem: ${trace.source?.device_name || 'N/A'} - ${trace.source?.port_name || 'N/A'}`);
    lines.push(`  Destino: ${trace.destination?.device_name || 'N/A'} - ${trace.destination?.port_name || 'N/A'}`);
    lines.push(`  Distância Total: ${trace.total_distance_km?.toFixed(2)} km`);
    lines.push(`  Perda Total: ${trace.total_loss_db?.toFixed(2)} dB`);
    lines.push(`  Fusões: ${trace.fusion_count}`);
    lines.push(`  Conectores: ${trace.connector_count}`);
    lines.push('');
    
    // Power Budget
    lines.push('ORÇAMENTO DE POTÊNCIA:');
    lines.push(`  TX Power: ${trace.power_budget?.tx_power_dbm} dBm`);
    lines.push(`  RX Sensitivity: ${trace.power_budget?.rx_sensitivity_dbm} dBm`);
    lines.push(`  Margem Disponível: ${trace.power_budget?.available_margin_db?.toFixed(2)} dB`);
    lines.push(`  Margem Mínima: ${trace.power_budget?.required_margin_db} dB`);
    lines.push(`  ${trace.power_budget?.message}`);
    lines.push('');
    
    // Path
    lines.push('CAMINHO ÓPTICO:');
    trace.path?.forEach((step, index) => {
      lines.push(`  ${index + 1}. ${step.name}`);
      
      if (step.type === 'fiber_strand') {
        lines.push(`     └─ Distância: ${step.details.distance_km?.toFixed(2)} km`);
        lines.push(`     └─ Tubo: ${step.details.tube_number}`);
        lines.push(`     └─ Cor: ${step.details.fiber_color}`);
      }
      
      if (step.loss_db) {
        lines.push(`     └─ Perda: ${step.loss_db.toFixed(2)} dB`);
      }
      
      lines.push('');
    });
    
    lines.push('═══════════════════════════════════════════════════');
    lines.push(`Gerado em: ${new Date().toLocaleString('pt-BR')}`);
    
    return lines.join('\n');
  }

  /**
   * Download text file
   * 
   * @param {string} content - File content
   * @param {string} filename - File name
   */
  function downloadTextFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Calculate if a link is viable based on power budget
   * 
   * @param {Object} powerBudget - Power budget object
   * @returns {boolean} True if link is viable
   */
  function isLinkViable(powerBudget) {
    if (!powerBudget) return false;
    return powerBudget.is_viable === true || powerBudget.status === 'OK';
  }

  /**
   * Get color for power budget status
   * 
   * @param {Object} powerBudget - Power budget object
   * @returns {string} Color class name
   */
  function getPowerBudgetColor(powerBudget) {
    if (!powerBudget) return 'gray';
    return isLinkViable(powerBudget) ? 'green' : 'yellow';
  }

  return {
    // State
    loading,
    error,
    traceResult,

    // Methods
    traceFromStrand,
    exportTracePDF,
    isLinkViable,
    getPowerBudgetColor,
  };
}
