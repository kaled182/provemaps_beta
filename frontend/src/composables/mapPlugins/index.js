/**
 * Registry de plugins do mapa
 * 
 * Registra todos os plugins disponíveis para uso com useMapService
 */

import { registerMapPlugin } from '@/composables/useMapService';
import createSegmentsPlugin from './segmentsPlugin';
import createDevicesPlugin from './devicesPlugin';
import createDrawingPlugin from './drawingPlugin';
import createContextMenuPlugin from './contextMenuPlugin';

// Registra plugins globalmente
registerMapPlugin('segments', createSegmentsPlugin);
registerMapPlugin('devices', createDevicesPlugin);
registerMapPlugin('drawing', createDrawingPlugin);
registerMapPlugin('contextMenu', createContextMenuPlugin);

console.log('[MapPlugins] Registered: segments, devices, drawing, contextMenu');

export {
  createSegmentsPlugin,
  createDevicesPlugin,
  createDrawingPlugin,
  createContextMenuPlugin
};
