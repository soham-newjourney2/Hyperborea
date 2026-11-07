import { useEffect, useState } from 'react'
import { getRegions, type RegionInfo } from '../lib/api'
import { REGION, switchRegion } from '../lib/region'

// P16: pick a pilot. Regions without processed data are listed but disabled.
export default function RegionSwitcher() {
  const [regions, setRegions] = useState<RegionInfo[] | null>(null)
  useEffect(() => {
    const c = new AbortController()
    getRegions(c.signal).then((r) => setRegions(r.regions)).catch(() => {})
    return () => c.abort()
  }, [])
  if (!regions || regions.length < 2) return null
  return (
    <label className="flex items-center gap-1 text-[11px] text-slate-500">
      Pilot
      <select value={REGION} onChange={(e) => switchRegion(e.target.value)} aria-label="Pilot region"
        className="w-56 rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 text-xs text-slate-200 outline-none focus:border-sky-500">
        {regions.map((r) => (
          <option key={r.id} value={r.id} disabled={r.status !== 'ready' && r.id !== REGION}>
            {r.city} · {r.name}{r.status === 'ready' ? '' : ' (data pending)'}
          </option>
        ))}
      </select>
    </label>
  )
}
