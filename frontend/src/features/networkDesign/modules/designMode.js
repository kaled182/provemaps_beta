/**
 * Projeto de Rede (EV-0138): estado partilhado entre o construtor legado (fiberRouteBuilder)
 * e a camada Vue (DesignLayer) — modo da barra, último clique direito, eventos e snap.
 */
import { reactive, ref } from 'vue';

/** 'select' | 'trace' | 'site' | 'ceo' | 'cto' | 'pole' | 'slack' | 'measure' | 'move' */
export const designMode = ref('select');

/** Último clique direito: no mapa vazio e num cabo (com o ponto clicado). */
export const lastMapContext = ref(null);
export const lastCableContext = ref(null);

const bus = new EventTarget();

export function emitDesign(type, detail) {
    bus.dispatchEvent(new CustomEvent(type, { detail }));
}

export function onDesign(type, handler) {
    const fn = (e) => handler(e.detail);
    bus.addEventListener(type, fn);
    return () => bus.removeEventListener(type, fn);
}

/** Os cliques no mapa só desenham rota no modo «Traçar» ou com uma rota já em edição. */
export function routeClicksEnabled({ editing }) {
    return editing || designMode.value === 'trace';
}

let snapProvider = null;

/** A camada Vue regista o snap (sites e CEOs próximos); o construtor pede-o a cada ponto. */
export function setSnapProvider(fn) {
    snapProvider = fn;
}

export function snapPoint(lat, lng) {
    const hit = snapProvider ? snapProvider(lat, lng) : null;
    return hit || { lat, lng };
}

/** EV-0139: camadas do projeto ligáveis no painel «Camadas». */
export const designLayers = reactive({ sites: true, ceos: true, ctos: true, poles: true, slacks: true });

/** Zoom a partir do qual CTOs e postes deixam de agrupar e mostram rótulos. */
export const LABEL_ZOOM = 16;
