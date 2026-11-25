/**
 * O mapa segue o tema da interface (EV-0045).
 *
 * O tema vive na classe `.dark` / `data-theme` do `<html>` (stores/ui.js). A
 * factory liga cada mapa a essa fonte: tema inicial na criação e
 * `IMap.setTheme()` a cada troca, até `destroy()`. Os componentes não precisam
 * de vigiar o tema para o fundo do mapa.
 * @module mapTheme
 */

/** @returns {'light'|'dark'} */
export function currentDocumentTheme(doc = typeof document !== 'undefined' ? document : null) {
  const root = doc?.documentElement;
  if (!root) return 'light';
  if (root.classList.contains('dark') || root.getAttribute('data-theme') === 'dark') return 'dark';
  return 'light';
}

/**
 * Chama `map.setTheme(tema)` sempre que o tema do documento muda.
 * @param {{setTheme: Function}} map
 * @returns {() => void} desliga o observador
 */
export function followDocumentTheme(map, doc = typeof document !== 'undefined' ? document : null) {
  const root = doc?.documentElement;
  if (!root || typeof MutationObserver === 'undefined') return () => {};
  let last = currentDocumentTheme(doc);
  const observer = new MutationObserver(() => {
    const next = currentDocumentTheme(doc);
    if (next === last) return;
    last = next;
    try {
      map.setTheme(next);
    } catch (e) {
      console.warn('[mapTheme] setTheme falhou:', e);
    }
  });
  observer.observe(root, { attributes: true, attributeFilter: ['class', 'data-theme'] });
  return () => observer.disconnect();
}

// ── Mapbox ──────────────────────────────────────────────────────────────
const MB = 'mapbox://styles/mapbox/';
const MAPBOX_DARK = `${MB}dark-v11`;
const MAPBOX_LIGHT = `${MB}light-v11`;
const MAPBOX_STREETS = `${MB}streets-v12`;
const NAV_DAY = `${MB}navigation-day-v1`;
const NAV_NIGHT = `${MB}navigation-night-v1`;

/**
 * Variante do estilo Mapbox para o tema. Só os estilos «de base» trocam
 * (streets/light/dark/navigation); satélite, outdoors e estilos próprios ficam
 * como estão — quem os escolheu quer aquele mapa.
 * @param {string} styleUrl estilo configurado (já resolvido para URL)
 * @param {'light'|'dark'|undefined} theme
 * @returns {string}
 */
export function mapboxStyleForTheme(styleUrl, theme) {
  if (!theme) return styleUrl;
  const dark = theme === 'dark';
  switch (styleUrl) {
    case MAPBOX_STREETS:
    case MAPBOX_LIGHT:
    case MAPBOX_DARK:
      return dark ? MAPBOX_DARK : (styleUrl === MAPBOX_DARK ? MAPBOX_LIGHT : styleUrl);
    case NAV_DAY:
    case NAV_NIGHT:
      return dark ? NAV_NIGHT : NAV_DAY;
    default:
      return styleUrl;
  }
}

// ── Leaflet / OSM ───────────────────────────────────────────────────────
/**
 * Os tiles públicos do OSM só existem em claro; no escuro inverte-se a camada
 * de tiles (os cabos e marcadores ficam fora dela). Evita um 2.º servidor de
 * tiles e o respetivo host no CSP.
 */
export const OSM_DARK_FILTER = 'invert(1) hue-rotate(180deg) brightness(0.95) contrast(0.9)';
