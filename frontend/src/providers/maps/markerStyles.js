/**
 * Estilos dos marcadores de rota, partilhados por todos os providers.
 *
 * Antes cada provider tinha a sua cópia desta tabela (`_getMarkerConfig`);
 * ao entrar o terceiro (Leaflet) passou a viver aqui. Os valores são os que
 * já estavam em produção — hex porque o Google desenha o ícone num SVG em
 * data-URL, onde variáveis CSS não resolvem.
 *
 * @typedef {{color: string, size: number, label: string}} MarkerStyle
 */
export const MARKER_STYLES = Object.freeze({
  origin: Object.freeze({ color: '#22c55e', size: 32, label: 'A' }),
  destination: Object.freeze({ color: '#ef4444', size: 32, label: 'B' }),
  intermediate: Object.freeze({ color: '#3b82f6', size: 20, label: '' }),
  preview: Object.freeze({ color: '#f59e0b', size: 20, label: '' }),
  default: Object.freeze({ color: '#dc2626', size: 24, label: '' }),
});

/**
 * @param {string} [type] - 'origin' | 'destination' | 'intermediate' | 'preview' | 'default'
 * @returns {MarkerStyle}
 */
export function getMarkerConfig(type) {
  return MARKER_STYLES[type] || MARKER_STYLES.default;
}
