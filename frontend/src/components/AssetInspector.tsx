import { useEffect, useState } from 'react'
import { getLandcover, type Landcover } from '../lib/api'
import { HEIGHT_STATUS } from '../lib/provenance'
import { UNITS } from '../lib/styles'
import { useApp } from '../store'
import InfraHealth from './InfraHealth'
import ProvenanceBadge, { Chip } from './ProvenanceBadge'

const HIDDEN_ATTRS = new Set(['height_status', 'u', 'v', 'key', 'formula', 'buildings', 'facilities', 'transformers', 'parameters'])

function CatchmentCover({ id }: { id: string }) {
  const [s, setS] = useState<Landcover | null>(null)
  useEffect(() => {
    getLandcover().then(setS).catch(() => {})
  }, [])
  const c = s?.per_catchment[id]
  if (!c) return null
  return (
    <section className="rounded border border-slate-800 bg-slate-900/60 p-2 text-xs">
      <h4 className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Land cover (ESA WorldCover 2021, observed)</h4>
      <div className="grid grid-cols-4 gap-1 tabular-nums">
        <div><div className="text-[9px] text-slate-500">BUILT-UP</div>{c.built_up_pct}%</div>
        <div><div className="text-[9px] text-slate-500">GREEN</div>{c.green_pct}%</div>
        <div><div className="text-[9px] text-slate-500">WATER</div>{c.water_pct}%</div>
        <div><div className="text-[9px] text-slate-500">NDVI</div>{c.ndvi_mean ?? '—'}</div>
      </div>
    </section>
  )
}

function CapacityBlock({ t }: { t: Record<string, unknown> }) {
  const n = Number(t.manning_n)
  const d = Number(t.diameter_m)
  const S = Number(t.slope)
  const A = (Math.PI * d * d) / 4
  const R = d / 4
  return (
    <section className="rounded border border-dashed border-purple-500/40 bg-slate-900/60 p-2 text-xs">
      <h4 className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Capacity (Manning, full flow)</h4>
      <div className="font-mono text-[11px] text-slate-300">Q = (1/n) · A · R^(2/3) · S^(1/2)</div>
      <div className="mt-1 font-mono text-[11px] leading-relaxed text-slate-400">
        n = {n} · d = {d} m → A = {A.toFixed(3)} m², R = {R.toFixed(3)} m
        <br />S = {S} ({String(t.slope_source)})
        <br />Q = <span className="text-slate-100">{fmt(t.capacity_m3s)} m³/s</span> × condition {fmt(t.condition_factor)}
        {' = '}
        <span className="font-semibold text-sky-300">{fmt(t.effective_capacity_m3s)} m³/s</span>
      </div>
      <p className="mt-1 text-[10px] text-slate-500">Drains to {String(t.drains_to)} · {String(t.n_upstream)} drains upstream</p>
    </section>
  )
}

function fmt(v: unknown): string {
  if (v === null || v === undefined || v === '') return '—'
  if (typeof v === 'number') {
    if (Number.isInteger(v)) return v.toLocaleString()
    const a = Math.abs(v) // small hydraulic values (slope 0.002, Q 0.46 m³/s) need more decimals
    return v.toLocaleString(undefined, { maximumFractionDigits: a < 0.01 ? 4 : a < 10 ? 3 : 1 })
  }
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[7.5rem_minmax(0,1fr)] gap-2 py-0.5 text-xs">
      <dt className="truncate text-slate-500" title={k}>{k}</dt>
      <dd className="text-slate-200 [overflow-wrap:anywhere]">{v}</dd>
    </div>
  )
}

export default function AssetInspector() {
  const { selectedId, selected } = useApp()
  if (!selectedId)
    return (
      <div className="space-y-3">
        <p className="text-sm text-slate-500">Click a building, road or facility on the map.</p>
        <InfraHealth />
      </div>
    )
  if (!selected) return <p className="text-sm text-slate-500">Loading {selectedId}…</p>
  const a = selected
  const hs = a.attrs.height_status ? HEIGHT_STATUS[String(a.attrs.height_status)] : undefined
  const attrs = Object.entries(a.attrs).filter(
    ([k, v]) => !HIDDEN_ATTRS.has(k) && !(hs && k === 'height_m') && v !== null && v !== '',
  )
  return (
    <div className="space-y-3">
      <div>
        <div className="text-sm font-semibold text-slate-100">{a.name || <span className="italic text-slate-400">Unnamed</span>}</div>
        <div className="text-xs text-slate-400">
          {a.asset_type.replace(/_/g, ' ')} · {a.layer} · {a.in_pilot ? 'inside pilot' : 'buffer'}
        </div>
      </div>

      {hs && (
        <div className="rounded border border-slate-800 bg-slate-900/60 p-2">
          <div className="text-2xl font-semibold tabular-nums text-slate-100">
            {fmt(a.attrs.height_m)} <span className="text-sm font-normal text-slate-400">m</span>
          </div>
          <Chip style={hs} small />
        </div>
      )}

      {a.layer === 'drains' && <CapacityBlock t={a.attrs} />}
      {a.layer === 'catchments' && <CatchmentCover id={a.asset_id} />}

      <button
        onClick={() => useApp.getState().setRightTab('relations')}
        className="w-full rounded border border-slate-800 bg-slate-900/60 px-2 py-1.5 text-left text-xs text-slate-300 hover:border-sky-600"
      >
        <span className="font-semibold text-sky-300">{a.relationships?.length ?? 0}</span> typed relationships
        {a.relationships?.length ? ` (${[...new Set(a.relationships.map((r) => r.type))].join(', ')})` : ''} → explore
      </button>

      <dl>
        {attrs.map(([k, v]) => (
          <Row key={k} k={k} v={`${fmt(v)}${UNITS[k] && v !== null ? ` ${UNITS[k]}` : ''}`} />
        ))}
      </dl>

      <section className="rounded border border-slate-800 bg-slate-900/60 p-2">
        <h4 className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Provenance</h4>
        <div className="mb-1.5">
          <ProvenanceBadge status={a.data_status} />
        </div>
        <dl>
          <Row k="source" v={a.source_id} />
          <Row k="observed at" v={fmt(a.observed_at)} />
          <Row k="ingested at" v={fmt(a.ingested_at)} />
          <Row k="confidence" v={fmt(a.confidence)} />
          <Row k="assumptions" v={a.assumptions || '—'} />
          <Row k="asset id" v={<code className="text-[11px]">{a.asset_id}</code>} />
        </dl>
      </section>
    </div>
  )
}
