import { useEffect, useMemo, useState } from 'react'
import { getAccessSummary, type AccessSummary } from '../lib/api'
import { ACCESS_ISOLATED, accessColor, deltaColor, ACCESS_STOPS, DELTA_STOPS } from '../lib/styles'
import { useApp, type AccessCat } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

const CATS: { id: AccessCat; label: string; range: number }[] = [
  { id: 'hospital', label: 'Hospital', range: 6 },
  { id: 'fire', label: 'Fire station', range: 12 },
  { id: 'metro', label: 'Metro / rail', range: 8 },
]
const DELTA_RANGE = 8
const LINK_MODE = new URLSearchParams(window.location.search).get('access') === 'delta' // ?access=delta

function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded border border-slate-800 bg-slate-900/60 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-lg font-semibold tabular-nums text-slate-50">{value}</div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  )
}

export default function AccessPanel() {
  const { flood, accessView, setAccessView } = useApp()
  const [cat, setCat] = useState<AccessCat>(accessView?.cat ?? 'hospital')
  const [mode, setMode] = useState<'baseline' | 'delta'>(accessView?.mode ?? (LINK_MODE ? 'delta' : 'baseline'))
  const [data, setData] = useState<AccessSummary | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const effMode = mode === 'delta' && flood ? 'delta' : 'baseline'
  const resultId = effMode === 'delta' ? flood?.result_id : undefined

  useEffect(() => {
    const c = new AbortController()
    getAccessSummary(resultId, c.signal)
      .then((d) => {
        setData(d)
        setErr(null)
      })
      .catch((e: Error) => e.name !== 'AbortError' && setErr('Accessibility unavailable (needs the API; no offline snapshot for scenarios).'))
    return () => c.abort()
  }, [resultId])

  const range = CATS.find((c) => c.id === cat)!.range
  const shown = data && (data.result_id ?? undefined) === resultId ? data : null
  const colors = useMemo(() => {
    if (!shown) return null
    const c = shown.categories[cat]
    const out: Record<string, string> = {}
    for (const [b, m] of Object.entries(c.minutes)) {
      if (m === null) out[b] = ACCESS_ISOLATED
      else if (effMode === 'delta') out[b] = deltaColor((c.delta?.[b] ?? 0) / DELTA_RANGE)
      else out[b] = accessColor(m / range)
    }
    return out
  }, [shown, cat, effMode, range])

  useEffect(() => {
    if (colors) setAccessView({ cat, mode: effMode, colors })
  }, [colors, cat, effMode, setAccessView])
  // leaving the tab keeps the map view; "Hide" clears it explicitly

  const c = shown?.categories[cat]
  const st = c ? ('stats' in c && c.stats ? c.stats : c.scenario) : null
  return (
    <div className="space-y-3">
      <div className="rounded border border-sky-600/50 bg-sky-500/10 px-2.5 py-1.5 text-[11px] font-semibold text-sky-200">
        Free-flow travel-time estimate — not live traffic · OSM roads, maxspeed or assumed class speeds
      </div>
      <div className="flex flex-wrap items-center gap-1 text-xs">
        {CATS.map((x) => (
          <button key={x.id} onClick={() => setCat(x.id)}
            className={`rounded px-2 py-0.5 ${cat === x.id ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'text-slate-400 hover:text-slate-200'}`}>
            {x.label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1 text-xs">
        <span className="text-[11px] text-slate-400">Show</span>
        {(['baseline', 'delta'] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)} disabled={m === 'delta' && !flood}
            className={`rounded px-2 py-0.5 disabled:opacity-40 ${effMode === m ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'text-slate-400 hover:text-slate-200'}`}>
            {m === 'baseline' ? 'Baseline' : `Δ under scenario${flood ? ` (${flood.params.preset ?? 'custom'})` : ''}`}
          </button>
        ))}
        <button onClick={() => setAccessView(null)} className="ml-auto text-[11px] text-slate-500 underline">hide on map</button>
      </div>
      {!flood && <p className="text-[10px] text-slate-500">Run a rainfall scenario in the Disaster tab to see the Δ view.</p>}
      {err && <p className="text-xs text-amber-300">{err}</p>}

      {c && st && (
        <>
          <div className="grid grid-cols-2 gap-1.5">
            <Tile label="Median drive" value={`${st.median_min ?? '—'} min`} sub={`p90 ${st.p90_min ?? '—'} · max ${st.max_min ?? '—'} min`} />
            <Tile label="No route (isolated)" value={String(st.isolated)} sub={`of ${st.n} buildings`} />
            {'newly_isolated' in c && c.newly_isolated !== undefined && (
              <>
                <Tile label="Newly isolated" value={String(c.newly_isolated)} sub="lost every route" />
                <Tile label="Slower trips" value={String(c.buildings_slower)} sub={`mean +${c.mean_delta_min} · max +${c.max_delta_min} min`} />
              </>
            )}
          </div>
          <div>
            <div className="h-2 rounded" style={{ background: `linear-gradient(90deg, ${(effMode === 'delta' ? DELTA_STOPS : ACCESS_STOPS).join(',')})` }} />
            <div className="mt-0.5 flex justify-between text-[10px] text-slate-500">
              {effMode === 'delta' ? <><span>no change</span><span>+{DELTA_RANGE / 2}</span><span>≥ +{DELTA_RANGE} min</span></>
                : <><span>0 min</span><span>{range / 2}</span><span>≥ {range} min</span></>}
            </div>
            <p className="mt-0.5 flex items-center gap-1 text-[10px] text-slate-500">
              <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: ACCESS_ISOLATED }} /> no drive route (flagged, never counted as 0)
            </p>
          </div>
          {shown?.facilities_no_hospital_route && shown.facilities_no_hospital_route.length > 0 && (
            <section className="rounded border border-amber-500/40 bg-slate-900/60 p-2 text-[11px] text-amber-200">
              {shown.facilities_no_hospital_route.length} pilot facilit{shown.facilities_no_hospital_route.length === 1 ? 'y' : 'ies'} lose every
              drive route to a hospital: {shown.facilities_no_hospital_route.map((f) => `${f.name ?? 'unnamed'} (${f.type.replace(/_/g, ' ')})`).join(', ')}
            </section>
          )}
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
            <ProvenanceBadge status={shown!.data_status} small /> source {shown!.source_id} · building → nearest graph node; walking leg ignored
          </div>
        </>
      )}
    </div>
  )
}
