import { useEffect, useRef, useState } from 'react'
import { getInfraHealth, type InfraHealthResponse } from '../lib/api'
import { useApp } from '../store'

const TYPES = [
  { id: 'drain', label: 'Drains', layer: 'drains' },
  { id: 'transformer', label: 'Transformers', layer: 'transformers' },
  { id: 'road', label: 'Roads', layer: 'roads' },
] as const
// condition index: low = needs attention (status colours, always with the number)
const tone = (v: number) => (v < 40 ? '#ef4444' : v < 60 ? '#f59e0b' : '#22c55e')

export default function InfraHealth() {
  const select = useApp((s) => s.select)
  const flyTo = useApp((s) => s.flyTo)
  const selected = useApp((s) => s.selected)
  // Fly once the picked asset's detail is known. It can arrive late: offline it is built from the layer's own
  // features, and the layer may only start loading because of this click.
  const pendingFly = useRef<string | null>(null)
  useEffect(() => {
    if (selected && selected.asset_id === pendingFly.current) {
      pendingFly.current = null
      flyTo(selected.position[0], selected.position[1])
    }
  }, [selected, flyTo])
  const pick = (assetId: string) => {
    const st = useApp.getState()
    const layer = TYPES.find((t) => t.id === type)!.layer
    if (!st.visible[layer]) st.toggle(layer) // a hidden layer can be neither highlighted nor located
    if (st.selected?.asset_id === assetId) return flyTo(st.selected.position[0], st.selected.position[1])
    pendingFly.current = assetId
    select(assetId)
  }
  const [type, setType] = useState<(typeof TYPES)[number]['id']>('drain')
  const [data, setData] = useState<InfraHealthResponse | null>(null)
  useEffect(() => {
    const c = new AbortController()
    getInfraHealth(type, 10, c.signal).then(setData).catch(() => {})
    return () => c.abort()
  }, [type])
  const shown = data?.type === type ? data : null
  return (
    <section className="space-y-2">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">Infrastructure health · needs attention first</h3>
      <div className="flex gap-1 text-xs">
        {TYPES.map((t) => (
          <button key={t.id} onClick={() => setType(t.id)}
            className={`rounded px-2 py-0.5 ${type === t.id ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'text-slate-400 hover:text-slate-200'}`}>
            {t.label}
          </button>
        ))}
      </div>
      {!shown ? <p className="text-xs text-slate-500">Loading…</p> : (
        <>
          <ol className="space-y-1">
            {shown.items.map((i, k) => (
              <li key={i.asset_id}>
                <button
                  onClick={() => pick(i.asset_id)}
                  className="w-full rounded border border-slate-800 bg-slate-900/50 px-2 py-1 text-left hover:border-sky-600"
                >
                  <div className="flex items-center gap-2 text-xs">
                    <span className="w-4 text-right tabular-nums text-slate-500">{k + 1}</span>
                    <span className="min-w-0 flex-1 truncate text-slate-100">{i.name || i.asset_id.split('_').slice(-3).join('_')}</span>
                    <span className="tabular-nums font-semibold" style={{ color: tone(i.health_index) }}>{i.health_index}</span>
                  </div>
                  <div className="ml-6 mt-0.5 h-1 rounded bg-slate-800">
                    <div className="h-1 rounded" style={{ width: `${i.health_index}%`, backgroundColor: tone(i.health_index) }} />
                  </div>
                  <div className="ml-6 mt-0.5 text-[10px] text-slate-500">{i.reasons.join(' · ')}</div>
                </button>
              </li>
            ))}
          </ol>
          <p className="text-[10px] leading-snug text-slate-500">
            {shown.label}. {shown.formula}; weights {Object.entries(shown.weights).map(([k, w]) => `${k} ${w}`).join(', ')}.
            Simulated inputs: {shown.simulated_inputs.join(', ')} (no real asset records).
          </p>
        </>
      )}
    </section>
  )
}
