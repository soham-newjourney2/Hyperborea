import { describe, expect, it } from 'vitest'
import { apiUrl, snapshotName } from './api'

describe('apiUrl', () => {
  it('joins base and path with one slash', () => {
    expect(apiUrl('health', 'http://x/api')).toBe('http://x/api/health')
    expect(apiUrl('/health', 'http://x/api/')).toBe('http://x/api/health')
  })
})

describe('snapshotName', () => {
  it('maps API paths to snapshot files (matches scripts/make_snapshots.py)', () => {
    expect(snapshotName('health')).toBe('health.json')
    expect(snapshotName('/region')).toBe('region.json')
    expect(snapshotName('layers')).toBe('layers.json')
    expect(snapshotName('layers/buildings?in_pilot=true')).toBe('layer_buildings_pilot.json')
    expect(snapshotName('layers/facilities')).toBe('layer_facilities.json')
    expect(snapshotName('weather/forecast')).toBe('weather_forecast.json')
    expect(snapshotName('climate/summary')).toBe('climate_summary.json')
    expect(snapshotName('scenarios/presets')).toBe('scenarios_presets.json')
    expect(snapshotName('environment/landcover')).toBe('environment_landcover.json')
    expect(snapshotName('infra-health?type=transformer&top=10')).toBe('infra_health_transformer.json')
  })
  it('returns null for endpoints without snapshots', () => {
    expect(snapshotName('assets/bld_osm_w1')).toBeNull()
    expect(snapshotName('scenarios/flood')).toBeNull()
    expect(snapshotName('infra-health?type=building')).toBeNull()
  })
})
