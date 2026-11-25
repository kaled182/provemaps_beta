/**
 * EV-0061 — a lista de cabos não inventa ocupação: lê `occupancy` do backend e,
 * sem fibras cadastradas, a barra e os KPIs dizem «sem dados».
 */
import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const sfc = readFileSync(resolve(__dirname, '../../src/components/Inventory/FiberCablesList.vue'), 'utf8')

describe('ocupação dos cabos (EV-0061)', () => {
  it('não lê mais o used_strands que ninguém produz nem cai em 0', () => {
    expect(sfc).not.toContain('used_strands')
    expect(sfc).not.toMatch(/fiber_count: c\.fiber_count \|\| [^,]*0,/)
    expect(sfc).toContain('occupancy: c.occupancy || null')
  })

  it('barra só com ocupação real; senão «sem dados»', () => {
    expect(sfc).toMatch(/<CapacityBar v-if="cable\.occupancy"/)
    expect(sfc).toMatch(/<span v-else[^>]*>sem dados<\/span>/)
  })

  it('KPIs mostram «sem dados» quando nenhum cabo tem fibras', () => {
    expect(sfc).toMatch(/saturatedCables === null \? 'sem dados'/)
    expect(sfc).toMatch(/averageOccupancy === null \? 'sem dados'/)
    expect(sfc).toMatch(/if \(!values\.length\) return null;/)
  })
})
