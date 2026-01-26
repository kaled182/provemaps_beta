/**
 * Testes para fiberService.js
 * Valida formatação de dados e cálculos
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { 
  formatOpticalDataForChart, 
  calculateOpticalStats 
} from '@/services/fiberService'

describe('fiberService', () => {
  describe('formatOpticalDataForChart', () => {
    it('deve formatar dados Zabbix para Chart.js corretamente', () => {
      const historyData = {
        rx_history: [
          { clock: 1706212800, value: -10.5 },
          { clock: 1706216400, value: -11.2 },
          { clock: 1706220000, value: -10.8 }
        ],
        tx_history: [
          { clock: 1706212800, value: -9.8 },
          { clock: 1706216400, value: -10.1 },
          { clock: 1706220000, value: -9.9 }
        ]
      }

      const result = formatOpticalDataForChart(historyData)

      // Validar estrutura
      expect(result).toHaveProperty('labels')
      expect(result).toHaveProperty('rxData')
      expect(result).toHaveProperty('txData')

      // Validar quantidade de pontos
      expect(result.labels).toHaveLength(3)
      expect(result.rxData).toHaveLength(3)
      expect(result.txData).toHaveLength(3)

      // Validar valores RX
      expect(result.rxData).toEqual([-10.5, -11.2, -10.8])

      // Validar valores TX
      expect(result.txData).toEqual([-9.8, -10.1, -9.9])

      // Validar que labels são timestamps formatados
      expect(result.labels[0]).toMatch(/\d{2}:\d{2}/)
    })

    it('deve retornar null se dados inválidos', () => {
      expect(formatOpticalDataForChart(null)).toBeNull()
      expect(formatOpticalDataForChart({})).toBeNull()
      expect(formatOpticalDataForChart({ rx_history: null })).toBeNull()
    })

    it('deve lidar com arrays vazios', () => {
      const historyData = {
        rx_history: [],
        tx_history: []
      }

      const result = formatOpticalDataForChart(historyData)
      
      expect(result.labels).toHaveLength(0)
      expect(result.rxData).toHaveLength(0)
      expect(result.txData).toHaveLength(0)
    })
  })

  describe('calculateOpticalStats', () => {
    it('deve calcular estatísticas corretamente', () => {
      const historyData = {
        rx_history: [
          { clock: 1706212800, value: -10.0 },
          { clock: 1706216400, value: -12.0 },
          { clock: 1706220000, value: -11.0 }
        ],
        tx_history: [
          { clock: 1706212800, value: -8.0 },
          { clock: 1706216400, value: -10.0 },
          { clock: 1706220000, value: -9.0 }
        ]
      }

      const result = calculateOpticalStats(historyData)

      // Validar estrutura
      expect(result).toHaveProperty('rx')
      expect(result).toHaveProperty('tx')

      // Validar RX
      expect(result.rx.avg).toBeCloseTo(-11.0, 1)
      expect(result.rx.min).toBe(-12.0)
      expect(result.rx.max).toBe(-10.0)

      // Validar TX
      expect(result.tx.avg).toBeCloseTo(-9.0, 1)
      expect(result.tx.min).toBe(-10.0)
      expect(result.tx.max).toBe(-8.0)
    })

    it('deve retornar null se dados inválidos', () => {
      expect(calculateOpticalStats(null)).toBeNull()
      expect(calculateOpticalStats({})).toBeNull()
    })

    it('deve lidar com um único ponto de dados', () => {
      const historyData = {
        rx_history: [{ clock: 1706212800, value: -10.5 }],
        tx_history: [{ clock: 1706212800, value: -9.5 }]
      }

      const result = calculateOpticalStats(historyData)

      expect(result.rx.avg).toBe(-10.5)
      expect(result.rx.min).toBe(-10.5)
      expect(result.rx.max).toBe(-10.5)
      
      expect(result.tx.avg).toBe(-9.5)
      expect(result.tx.min).toBe(-9.5)
      expect(result.tx.max).toBe(-9.5)
    })
  })
})
