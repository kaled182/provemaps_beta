/**
 * EV-0055 — Vídeo: cabeçalhos numa linha (sem subtítulo), tabela de câmeras densa,
 * cores por tokens; superfícies sempre escuras (pré-visualização, fundos de modal)
 * continuam escuras.
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const dir = resolve(__dirname, '../../src/views/video')
const read = (f) => readFileSync(resolve(dir, f), 'utf8')
const template = (sfc) => sfc.slice(sfc.indexOf('<template>'), sfc.lastIndexOf('</template>'))
const PAGES = ['VideoManagementView.vue', 'VideoCamerasView.vue', 'VideoMosaicsView.vue', 'VideoGatewaysView.vue', 'VideoGroupsView.vue']

describe('Vídeo compacto e no tema (EV-0055)', () => {
  for (const file of PAGES) {
    it(`${file}: sem pares dark: nem subtítulos explicativos`, () => {
      const t = template(read(file))
      expect(t).not.toMatch(/(^|\s|["'])dark:/)
      expect(t).not.toMatch(/Gestão de câmeras e streaming|Visualização em grade de múltiplas|Transcodificação e streaming com|Câmeras e mosaicos de vídeo/)
      expect(t).not.toMatch(/h-\[calc\(100vh-64px\)\]/)
    })
  }

  it('tabela de câmeras com células densas', () => {
    const t = template(read('VideoCamerasView.vue'))
    expect(t).not.toMatch(/<td class="px-4 py-3/)
    expect(t).toMatch(/<td class="px-3 py-1\.5/)
  })

  it('a pré-visualização do vídeo continua sempre escura', () => {
    const t = template(read('VideoCamerasView.vue'))
    expect(t).toMatch(/bg-gray-900\/40/)
    expect(t).toMatch(/text-gray-200/)
  })
})
