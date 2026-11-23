/**
 * Lê todas as páginas de uma lista DRF (`{results, next}`) — ou devolve o array
 * se o endpoint não paginar. `next` absoluto é reduzido a caminho+query.
 * @param {{get: Function}} api resultado de useApi()
 * @param {string} url
 */
export async function fetchAllPages(api, url) {
  const out = []
  let next = url
  while (next) {
    const data = await api.get(next)
    if (Array.isArray(data)) return data
    out.push(...(data?.results || []))
    if (!data?.next) break
    const u = new URL(data.next, window.location.origin)
    next = u.pathname + u.search
  }
  return out
}
