import { describe, expect, it } from 'vitest'
import { DEFAULT_REGION, regionQuery, withRegion } from './region'

describe('region query', () => {
  it('leaves default-region URLs unchanged (pre-P16 URLs + snapshot names)', () => {
    expect(regionQuery(DEFAULT_REGION)).toBe('')
    expect(withRegion('http://x/api/layers', DEFAULT_REGION)).toBe('http://x/api/layers')
  })
  it('appends ?region= / &region= for other pilots', () => {
    expect(withRegion('http://x/api/layers', 'pune_kharadi')).toBe('http://x/api/layers?region=pune_kharadi')
    expect(withRegion('http://x/api/layers/roads?in_pilot=true', 'london_stratford'))
      .toBe('http://x/api/layers/roads?in_pilot=true&region=london_stratford')
  })
})
