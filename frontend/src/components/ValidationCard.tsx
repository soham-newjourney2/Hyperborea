import { useEffect, useState } from 'react'
import { getValidation, type Validation } from '../lib/api'
import { useApp } from '../store'

// P22: engine vs a real flood seen by Sentinel-1. Shows every run, the naive baseline and the limitations — even when
// the engine loses (that is the point of validating).
const pct = (v: number | null | undefined) => (v == null ? '—' : `${Math.round(v * 100)}%`)

export default function ValidationCard() {
  const { visible, toggle, layers } = useApp()
  const [v, setV] = useState<Validation | null>(null)
  const [missing, setMissing] = useState(false)
  useEffect(() => {
    const c = new AbortController()
    getValidation(c.signal).then(setV).catch((e: Error) => e.name !== 'AbortError' && setMissing(true))
    return () => c.abort()
  }, [])
  if (missing) return null // region without a scored event
  if (!v) return <p className="text-[11px] text-slate-500">Loading validation…</p>
  const o = v.observed
  const hasLayer = layers.some((l) => l.id === 'sar_flood')
  return (
    <section className="space-y-2 rounded border border-violet-500/40 bg-violet-500/5 p-2.5">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-violet-200">Validation · {v.event}</h3>
        {hasLayer && (
          <label className="flex items-center gap-1 text-[11px] text-slate-300">
            <input type="checkbox" className="accent-violet-400" checked={Boolean(visible.sar_flood)} onChange={() => toggle('sar_flood')} />
            radar flood map
          </label>
        )}
      </div>
      <p className="text-[11px] leading-snug text-slate-300">
        Sentinel-1 radar on {o.post_date} vs dry-season passes: {o.catchments_flooded} of {o.catchments_compared} catchments show
        flooding (urban brightening {pct(o.urban_brightening_share_post)} of pixels near buildings; control pass {o.control_date}:
        {' '}{pct(o.urban_brightening_share_control)} — the signal is event-related).
      </p>
      <table className="w-full text-[11px]">
        <thead className="text-slate-500">
          <tr><th className="text-left font-normal">Rain input</th><th className="font-normal">flagged</th><th className="font-normal">hit rate</th>
            <th className="font-normal">false alarms</th><th className="font-normal">AUC engine / low ground</th></tr>
        </thead>
        <tbody className="tabular-nums text-slate-200">
          {Object.entries(v.runs).map(([k, r]) => (
            <tr key={k} className="border-t border-slate-800">
              <td className="py-0.5 pr-1 text-left text-slate-300">{r.label}</td>
              <td className="text-center">{r.predicted_flooded}</td>
              <td className="text-center">{pct(r.engine.pod)} <span className="text-slate-500">/ {pct(r.baseline_lowest_ground.pod)}</span></td>
              <td className="text-center">{pct(r.engine.far)} <span className="text-slate-500">/ {pct(r.baseline_lowest_ground.far)}</span></td>
              <td className="text-center">{r.auc_engine_depth ?? '—'} <span className="text-slate-500">/ {r.auc_lowest_ground ?? '—'}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-[11px] font-medium text-amber-200">
        Honest result: the screening engine does not reproduce this regional flood (AUC ≈ 0.5); simply ranking by low ground
        does better. Next step: route overflow downhill + add lake/river inflows.
      </p>
      <ul className="list-disc space-y-0.5 pl-4 text-[10px] leading-snug text-slate-500">
        <li>Grey numbers = naive baseline (same number of lowest-lying catchments). Rain: {v.rain.station_source}; ERA5 at this cell
          gave only {v.rain.era5_event_total_mm} mm (peak {v.rain.era5_peak_mm_h} mm/h).</li>
        {v.limitations.map((l) => <li key={l}>{l}</li>)}
      </ul>
    </section>
  )
}
