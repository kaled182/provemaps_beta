/**
 * EV-0145 — botão direito num cabo do Projeto de Rede abre só o menu de contexto; o painel
 * «Detalhes do cabo» fica fechado até «Ver detalhes».
 */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'

vi.mock('@/features/networkDesign/modules/apiClient.js', () => ({
  fetchFibers: vi.fn(),
  fetchFiber: vi.fn(async (id) => ({ id, name: 'MANDI - VLP', path: [], folder: null })),
  createFiberManual: vi.fn(),
  updateFiber: vi.fn(),
  removeFiber: vi.fn(),
  validateNearbyCables: vi.fn(),
}))
vi.mock('@/features/networkDesign/modules/contextMenu.js', () => ({
  initContextMenu: vi.fn(),
  showContextMenu: vi.fn(),
  hideContextMenu: vi.fn(),
  updateContextMenuState: vi.fn(),
  cleanupContextMenu: vi.fn(),
}))

import { _makeCableEditableForTest as makeCableEditable } from '@/features/networkDesign/fiberRouteBuilder.js'
import { showContextMenu } from '@/features/networkDesign/modules/contextMenu.js'
import { fetchFiber } from '@/features/networkDesign/modules/apiClient.js'

describe('clique direito num cabo (EV-0145)', () => {
  it('carrega o cabo e abre o menu, sem abrir o painel de detalhes', async () => {
    document.body.innerHTML = '<div id="cableDetailsPanel" class="nd-panel-hidden"></div><span id="cableDetailName"></span>'
    const h = {}
    const poly = { addListener: (e, cb) => (h[e] = cb), set: vi.fn() }
    makeCableEditable(poly, 12, 'MANDI - VLP')
    await h.rightclick({ lat: -10, lng: -50, clientX: 300, clientY: 200 })
    await flushPromises()
    expect(fetchFiber).toHaveBeenCalledWith(12)
    expect(showContextMenu).toHaveBeenCalledWith(300, 200)
    const panel = document.getElementById('cableDetailsPanel')
    expect(panel.classList.contains('nd-panel-hidden')).toBe(true)
    // os dados ficam prontos para «Ver detalhes»
    expect(document.getElementById('cableDetailName').textContent).toBe('MANDI - VLP')
  })
})
