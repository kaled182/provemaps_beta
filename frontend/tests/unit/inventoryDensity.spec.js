/**
 * EV-0054 — Inventário: cabeçalho numa linha com abas em PT-BR, tabelas densas
 * (~36 px por linha), números em mono tabular, cores por tokens (sem pares dark:)
 * e uma só barra de ação em massa.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
// EV-0100: import estático (não `await import()` dentro do teste) — a transformação do SFC
// corre na recolha do ficheiro e não conta para os 5 s do teste; na suite completa, com a
// máquina carregada, o import dinâmico estourava o timeout.
import InventoryView from '@/components/Inventory/InventoryView.vue'

vi.mock('@/components/Inventory/InventoryManager.vue', () => ({ default: { render: () => null } }))
vi.mock('@/components/Inventory/Groups/DeviceGroupsManager.vue', () => ({ default: { render: () => null } }))
vi.mock('@/components/Inventory/DevicesList.vue', () => ({ default: { render: () => null } }))
vi.mock('@/components/Inventory/FiberCablesList.vue', () => ({ default: { render: () => null } }))
vi.mock('@/components/Inventory/PortsList.vue', () => ({ default: { render: () => null } }))

const dir = resolve(__dirname, '../../src/components/Inventory')
const read = (f) => readFileSync(resolve(dir, f), 'utf8')
const template = (sfc) => sfc.slice(sfc.indexOf('<template>'), sfc.lastIndexOf('</template>'))
const LISTS = ['DevicesList.vue', 'FiberCablesList.vue', 'PortsList.vue', 'InventoryManager.vue']

describe('Inventário denso e no tema (EV-0054)', () => {
  it('abas em PT-BR', () => {
    const w = mount(InventoryView)
    const labels = w.findAll('[data-testid^="inventory-tab-"]').map((b) => b.text())
    expect(labels).toEqual(['Sites', 'Grupos', 'Dispositivos', 'Cabos', 'Portas'])
    expect(w.text()).not.toMatch(/Device Groups|Fiber Cables|Sites, POPs e infraestrutura/)
    w.unmount()
  })

  for (const file of LISTS) {
    it(`${file}: células densas e sem cores presas a um tema`, () => {
      const t = template(read(file))
      expect(t).not.toMatch(/<t[dh][^>]*class="[^"]*\b(px-5 py-4|px-6 py-4|p-4)\b/)
      expect(t).not.toMatch(/(^|\s|")dark:/)
      expect(t).not.toMatch(/\b(text|bg|border|divide)-(gray|slate)-\d/)
    })
  }

  it('IP, HostID, IDs do Zabbix e metragem em mono tabular', () => {
    expect(read('DevicesList.vue')).toMatch(/font-mono text-sm tabular-nums[^>]*>\{\{ device\.primary_ip/)
    expect(read('DevicesList.vue')).toMatch(/font-mono tabular-nums">\s*\{\{ device\.zabbix_hostid/)
    expect(read('PortsList.vue')).toMatch(/font-mono text-xs tabular-nums[^>]*>\{\{ port\.zabbix_itemid/)
    expect(read('FiberCablesList.vue')).toMatch(/font-mono text-sm tabular-nums[^>]*>\{\{ formatLength/)
  })

  it('uma só barra de ação em massa nos dispositivos', () => {
    const t = template(read('DevicesList.vue'))
    expect(t.match(/v-if="selectedIds\.size > 0"/g)).toHaveLength(1)
  })
})
