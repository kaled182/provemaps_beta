/**
 * Cor CSS de um token do design system (tripleto RGB em `:root`) para APIs que pedem uma cor
 * literal (providers de mapa). Segue o tema ativo no momento da leitura.
 */
export function tokenColor(name, fallback = 'currentColor') {
  try {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    return v ? `rgb(${v.split(/[\s,]+/).join(', ')})` : fallback
  } catch {
    return fallback
  }
}
