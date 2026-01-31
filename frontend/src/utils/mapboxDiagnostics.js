const DEFAULT_STYLE_CANDIDATES = [
  { key: 'mapbox-streets-v12', label: 'Mapbox Streets v12', url: 'mapbox://styles/mapbox/streets-v12' },
  { key: 'mapbox-streets-v11', label: 'Mapbox Streets v11', url: 'mapbox://styles/mapbox/streets-v11' },
  { key: 'mapbox-outdoors-v12', label: 'Mapbox Outdoors v12', url: 'mapbox://styles/mapbox/outdoors-v12' },
  { key: 'mapbox-light-v11', label: 'Mapbox Light v11', url: 'mapbox://styles/mapbox/light-v11' },
  { key: 'mapbox-dark-v11', label: 'Mapbox Dark v11', url: 'mapbox://styles/mapbox/dark-v11' },
  { key: 'mapbox-satellite-streets-v12', label: 'Mapbox Satellite Streets v12', url: 'mapbox://styles/mapbox/satellite-streets-v12' },
  { key: 'mapbox-satellite-v9', label: 'Mapbox Satellite v9', url: 'mapbox://styles/mapbox/satellite-v9' },
  { key: 'mapbox-navigation-day-v1', label: 'Mapbox Navigation Day v1', url: 'mapbox://styles/mapbox/navigation-day-v1' },
  { key: 'mapbox-navigation-night-v1', label: 'Mapbox Navigation Night v1', url: 'mapbox://styles/mapbox/navigation-night-v1' }
]

const STYLE_TEST_TIMEOUT_MS = 20000

const createHiddenSandbox = () => {
  const wrapper = document.createElement('div')
  wrapper.style.position = 'fixed'
  wrapper.style.top = '-9999px'
  wrapper.style.left = '-9999px'
  wrapper.style.width = '0'
  wrapper.style.height = '0'
  wrapper.style.zIndex = '-1'
  wrapper.style.opacity = '0'
  document.body.appendChild(wrapper)
  return wrapper
}

const createStyleContainer = (wrapper) => {
  const container = document.createElement('div')
  container.style.width = '320px'
  container.style.height = '320px'
  container.style.margin = '0'
  container.style.padding = '0'
  container.style.background = '#1f2937'
  wrapper.appendChild(container)
  return container
}

const waitForMapLoad = (map) => {
  return new Promise((resolve) => {
    let finished = false

    const conclude = (result) => {
      if (finished) return
      finished = true
      try {
        map.remove()
      } catch (removeError) {
        console.warn('[MapboxDiagnostics] Falha ao remover mapa de teste:', removeError)
      }
      resolve(result)
    }

    const timeoutId = window.setTimeout(() => {
      conclude({ success: false, error: 'timeout', details: 'Tempo limite ao aguardar evento load' })
    }, STYLE_TEST_TIMEOUT_MS)

    map.once('load', () => {
      window.clearTimeout(timeoutId)
      conclude({ success: true })
    })

    map.once('error', (event) => {
      window.clearTimeout(timeoutId)
      let details = null
      try {
        details = event?.error ? JSON.stringify(event.error, Object.getOwnPropertyNames(event.error)) : null
      } catch (stringifyError) {
        details = String(stringifyError)
      }
      conclude({
        success: false,
        error: event?.error?.message || 'unknown',
        details
      })
    })
  })
}

export const runMapboxStyleDiagnostics = async ({
  mapboxgl,
  token,
  styles = DEFAULT_STYLE_CANDIDATES,
  center = [-47.9292, -15.7801],
  zoom = 12,
  verbose = true
} = {}) => {
  if (!mapboxgl) {
    throw new Error('mapboxgl não informado para diagnóstico')
  }

  if (!token) {
    throw new Error('Token Mapbox não informado para diagnóstico')
  }

  const wrapper = createHiddenSandbox()
  const results = []

  try {
    mapboxgl.accessToken = token

    for (const entry of styles) {
      const styleMeta = typeof entry === 'string' ? { key: entry, label: entry, url: entry } : entry
      const container = createStyleContainer(wrapper)
      const startedAt = performance.now()

      let outcome
      try {
        const map = new mapboxgl.Map({
          container,
          style: styleMeta.url,
          center,
          zoom,
          attributionControl: false,
          logoPosition: 'bottom-right',
          interactive: false,
          cooperativeGestures: false,
          pitch: 0,
          bearing: 0,
          fadeDuration: 0
        })

        outcome = await waitForMapLoad(map)
      } catch (error) {
        let details = null
        try {
          details = error ? JSON.stringify(error, Object.getOwnPropertyNames(error)) : null
        } catch (stringifyError) {
          details = String(stringifyError)
        }

        outcome = {
          success: false,
          error: error?.message || 'init-error',
          details
        }
      }

      const duration = performance.now() - startedAt
      const result = {
        key: styleMeta.key,
        label: styleMeta.label,
        url: styleMeta.url,
        success: outcome.success,
        duration: Number(duration.toFixed(2)),
        error: outcome.error || null,
        details: outcome.details || null
      }

      results.push(result)

      // Limpar container filho para próxima iteração
      wrapper.removeChild(container)

      if (verbose) {
        if (result.success) {
          console.log(`[MapboxDiagnostics] ✅ ${styleMeta.label} carregado em ${result.duration}ms`)
        } else {
          console.warn(`[MapboxDiagnostics] ❌ ${styleMeta.label} falhou: ${result.error}`, result.details)
        }
      }
    }
  } finally {
    document.body.removeChild(wrapper)
  }

  if (verbose) {
    console.table(results.map(({ key, label, success, duration, error }) => ({ key, label, success, duration, error })))
  }

  return results
}

export const MAPBOX_STYLE_DIAGNOSTICS_DEFAULTS = DEFAULT_STYLE_CANDIDATES
