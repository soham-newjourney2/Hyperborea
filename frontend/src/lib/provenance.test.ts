import { describe, expect, it } from 'vitest'
import { STATUS_STYLES, statusStyle } from './provenance'
import { capacityColor, runoffColor } from './styles'

describe('statusStyle', () => {
  it('maps each data_status to its colour', () => {
    expect(statusStyle('observed').color).toBe('#3b82f6')
    expect(statusStyle('curated').color).toBe('#14b8a6')
    expect(statusStyle('modelled').color).toBe('#f59e0b')
    expect(statusStyle('simulated').color).toBe('#a855f7')
    expect(statusStyle('unknown').color).toBe('#64748b')
  })

  it('only simulated is dashed', () => {
    expect(Object.entries(STATUS_STYLES).filter(([, s]) => s.dashed).map(([k]) => k)).toEqual(['simulated'])
  })

  it('falls back to unknown for missing or unrecognised status', () => {
    expect(statusStyle(undefined)).toBe(STATUS_STYLES.unknown)
    expect(statusStyle(null)).toBe(STATUS_STYLES.unknown)
    expect(statusStyle('made-up')).toBe(STATUS_STYLES.unknown)
  })
})


describe('drainage ramps', () => {
  it('clamp to the ramp ends', () => {
    expect(capacityColor(0.01)).toBe('#1e3a8a')
    expect(capacityColor(100)).toBe('#a5f3fc')
    expect(runoffColor(0.4)).toBe('#422006')
    expect(runoffColor(0.9)).toBe('#fbbf24')
  })
})
