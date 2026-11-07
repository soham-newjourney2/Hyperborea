import { useEffect, useState } from 'react'
import {
  assessDevelopment,
  compareDevelopment,
  getPresets,
  type DevCheck,
  type DevCompare,
  type DevRequest,
  type Preset,
} from '../lib/api'
import { useApp } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

const SITES = [
  { id: 'S1', label: 'S1 · construction plot' },
  { id: 'S2', label: 'S2 · industrial (flood-prone)' },
  { id: 'S3', label: 'S3 · commercial plot' },
]
const UPGRADES = [
  { id: 'detention', label: 'On-site detention / RWH tank (no net increase in peak runoff)' },
  { id: 'drain_upsize', label: 'Upsize receiving drain one pipe size' },
  { id: 'transformer', label: 'New dedicated transformer sized for the building (simulated network)' },
]
// Status colours always paired with the word (never colour alone).
const STATUS: Record<string, { label: string; color: string }> = {
  pass: { label: 'Pass', color: '#22c55e' },
  conditional: { label: 'Conditional', color: '#f59e0b' },
  fail: { label: 'Fail', color: '#ef4444' },
  insufficient_data: { label: 'Insufficient data', color: '#64748b' },
}
const DIM_LABEL: Record<string, string> = {
  drainage: 'Drainage', flood_exposure: 'Flood exposure', road_access: 'Road access',
  critical_facilities: 'Critical facilities', electrical: 'Electrical', water_supply: 'Water supply', land_use: 'Land use',
}
const LINK = new URLSearchParams(window.location.search) // ?develop=S2&upgrades=detention,drain_upsize
const LINK_SITE = LINK.get('develop')
const LINK_UPS = (LINK.get('upgrades') ?? '').split(',').filter(Boolean)

const verdictTone = (v: string) =>
  v.startsWith('Suitable') ? STATUS.pass.color : v.startsWith('Conditionally') ? STATUS.conditional.color
    : v.startsWith('Potentially') ? STATUS.fail.color : STATUS.insufficient_data.color

function StatusChip({ s }: { s: string }) {
  const st = STATUS[s] ?? STATUS.insufficient_data
  return (
    <span className="inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 py-px text-[10px] font-medium"
      style={{ color: st.color, backgroundColor: `${st.color}1f`, boxShadow: `inset 0 0 0 1px ${st.color}66` }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: st.color }} />
      {st.label}
    </span>
  )
}

function CheckRow({ c, keyDim }: { c: DevCheck; keyDim: boolean }) {
  return (
    <li className="rounded border border-slate-800 bg-slate-900/50 px-2 py-1.5">
      <div className="flex items-center gap-2 text-xs text-slate-100">
        <span className="font-medium">{DIM_LABEL[c.dimension] ?? c.dimension}</span>
        {keyDim && <span className="text-[9px] uppercase tracking-wider text-slate-500">key</span>}
        <span className="ml-auto flex items-center gap-1">
          {c.value !== undefined && (
            <span className="tabular-nums text-[11px] text-slate-300">
              {typeof c.value === 'number' ? c.value.toLocaleString() : c.value} {c.unit}
            </span>
          )}
          <StatusChip s={c.status} />
        </span>
      </div>
      <p className="mt-0.5 text-[11px] leading-snug text-slate-400">{c.detail}</p>
      {c.threshold && <p className="text-[10px] text-slate-500">Rule: {c.threshold}</p>}
      <div className="mt-0.5 flex items-center gap-1 text-[10px] text-slate-500">
        <ProvenanceBadge status={c.data_status} small />
        {c.source_ids.join(', ')}
        {c.note && <span>· {c.note}</span>}
      </div>
    </li>
  )
}

function CompareView({ cmp }: { cmp: DevCompare }) {
  const names = cmp.options.map((o) => o.name)
  return (
    <section className="space-y-2 rounded border border-sky-700/50 bg-slate-900/60 p-2.5">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-sky-300">
        Compare · {cmp.label}{cmp.offline ? ' (offline snapshot)' : ''}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="py-1 pr-2 font-medium">Dimension</th>
              {names.map((n) => <th key={n} className="py-1 pr-2 font-medium">{n.split(' · ')[0]}</th>)}
            </tr>
          </thead>
          <tbody>
            {cmp.table.map((row) => (
              <tr key={row.dimension} className="border-t border-slate-800">
                <td className="py-1 pr-2 text-slate-300">{DIM_LABEL[row.dimension] ?? row.dimension}</td>
                {names.map((n) => <td key={n} className="py-1 pr-2"><StatusChip s={row[n]} /></td>)}
              </tr>
            ))}
            <tr className="border-t border-slate-700">
              <td className="py-1 pr-2 text-slate-300">Index</td>
              {names.map((n) => <td key={n} className="py-1 pr-2 tabular-nums text-slate-100">{cmp.index[n]?.toFixed(2) ?? '—'}</td>)}
            </tr>
          </tbody>
        </table>
      </div>
      <ul className="space-y-1">
        {names.map((n) => (
          <li key={n} className="text-[11px]">
            <span className="text-slate-400">{n}: </span>
            <span style={{ color: verdictTone(cmp.verdicts[n]) }}>{cmp.verdicts[n]}</span>
          </li>
        ))}
      </ul>
      {Object.entries(cmp.what_changed).map(([k, notes]) => (
        <div key={k}>
          <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">What changed · {k}</p>
          <ul className="list-disc pl-4 text-[11px] text-slate-300">{notes.map((t) => <li key={t}>{t}</li>)}</ul>
        </div>
      ))}
    </section>
  )
}

export default function DevelopmentPanel() {
  const { dev, setDev, drawn, drawing, startDraw, toggle, visible } = useApp()
  const [presets, setPresets] = useState<Preset[]>([])
  const [site, setSite] = useState<string | null>(LINK_SITE ?? 'S2')
  const [use, setUse] = useState<'residential' | 'commercial'>('commercial')
  const [floors, setFloors] = useState(10)
  const [ups, setUps] = useState<string[]>(LINK_UPS)
  const [design, setDesign] = useState('design')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [cmp, setCmp] = useState<DevCompare | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    getPresets(ctrl.signal).then(setPresets).catch(() => {})
    if (!useApp.getState().visible.sites) useApp.getState().toggle('sites')
    return () => ctrl.abort()
  }, [])

  // Demo deep link: ?tab=develop&develop=S2&upgrades=detention,drain_upsize → assess + compare on load.
  useEffect(() => {
    const s = LINK_SITE
    const u = LINK_UPS
    if (!s) return
    const base: DevRequest = { site_id: s, use: 'commercial', floors: 10, upgrades: u, design_preset: 'design' }
    assessDevelopment(base).then(setDev).catch(() => {})
    compareDevelopment([
      { ...base, upgrades: [], label: `A · ${s} as proposed` },
      { ...base, upgrades: u.length ? u : ['detention', 'drain_upsize', 'transformer'], label: `B · ${s} + upgrades` },
      { ...base, site_id: s === 'S1' ? 'S3' : 'S1', upgrades: [], label: `C · alternative site ${s === 'S1' ? 'S3' : 'S1'}` },
    ]).then(setCmp).catch(() => {})
  }, [setDev])

  const source = drawn ? 'drawn' : site
  const req = (over: Partial<DevRequest> = {}): DevRequest => ({
    ...(drawn ? { geometry: { type: 'Polygon', coordinates: [[...drawn, drawn[0]]] } } : { site_id: site }),
    use, floors, upgrades: ups, design_preset: design, ...over,
  })
  const run = async () => {
    setBusy(true)
    setErr(null)
    try {
      setDev(await assessDevelopment(req()))
    } catch (e) {
      setErr(`Assessment failed: ${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }
  const compare = async () => {
    setBusy(true)
    setErr(null)
    const alt = site === 'S1' || drawn ? 'S3' : 'S1'
    const bUps = ups.length ? ups : ['detention', 'drain_upsize', 'transformer']
    try {
      const res = await compareDevelopment([
        { ...req({ upgrades: [] }), label: `A · ${source} as proposed` },
        { ...req({ upgrades: bUps }), label: `B · ${source} + upgrades` },
        { site_id: alt, use, floors, upgrades: [], design_preset: design, label: `C · alternative site ${alt}` },
      ])
      setCmp(res)
      try {
        localStorage.setItem('hyperborea.report.dev', JSON.stringify(res)) // shown in the scenario report
      } catch { /* ignore */ }
    } catch (e) {
      setErr(`Compare failed: ${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="rounded border border-purple-500/50 bg-purple-500/10 px-2.5 py-1.5 text-[11px] font-semibold text-purple-200">
        Screening assessment — not an approval · no statutory FAR / bye-law checks
      </div>

      <section className="space-y-2 rounded border border-slate-800 bg-slate-900/50 p-2.5 text-xs">
        <div className="flex flex-wrap gap-1">
          {SITES.map((s) => (
            <button key={s.id} onClick={() => { setSite(s.id); useApp.setState({ drawn: null }); setDev(null) }}
              className={`rounded px-2 py-0.5 ${!drawn && site === s.id ? 'bg-purple-500/20 text-purple-200 ring-1 ring-purple-500/60' : 'border border-slate-700 text-slate-300 hover:border-purple-500'}`}>
              {s.label}
            </button>
          ))}
          <button onClick={startDraw}
            className={`rounded px-2 py-0.5 ${drawing || drawn ? 'bg-purple-500/20 text-purple-200 ring-1 ring-purple-500/60' : 'border border-slate-700 text-slate-300 hover:border-purple-500'}`}>
            {drawing ? 'Drawing…' : drawn ? 'Redraw footprint' : 'Draw footprint'}
          </button>
        </div>
        {!visible.sites && (
          <button className="text-[10px] text-slate-500 underline" onClick={() => toggle('sites')}>show candidate sites</button>
        )}
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Use</span>
          {(['commercial', 'residential'] as const).map((u) => (
            <button key={u} onClick={() => setUse(u)}
              className={`rounded px-2 py-0.5 ${use === u ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'text-slate-400 hover:text-slate-200'}`}>
              {u}
            </button>
          ))}
        </div>
        <label className="block text-[11px] text-slate-400">
          <span className="flex justify-between">Floors <span className="tabular-nums text-slate-100">{floors} ({(floors * 3.2).toFixed(0)} m)</span></span>
          <input type="range" min={1} max={40} value={floors} onChange={(e) => setFloors(Number(e.target.value))} className="w-full accent-purple-400" />
        </label>
        <fieldset className="space-y-0.5">
          <legend className="mb-0.5 text-[11px] text-slate-400">Upgrades (option B)</legend>
          {UPGRADES.map((u) => (
            <label key={u.id} className="flex items-start gap-1.5 text-[11px] text-slate-300">
              <input type="checkbox" className="mt-0.5 accent-purple-400" checked={ups.includes(u.id)}
                onChange={() => setUps((p) => (p.includes(u.id) ? p.filter((x) => x !== u.id) : [...p, u.id]))} />
              {u.label}
            </label>
          ))}
        </fieldset>
        <label className="flex items-center gap-2 text-[11px] text-slate-400">
          Design storm
          <select value={design} onChange={(e) => setDesign(e.target.value)}
            className="rounded border border-slate-700 bg-slate-950 px-1 py-0.5 text-slate-200">
            {presets.map((p) => <option key={p.id} value={p.id}>{p.title} · {p.rain_mm_h} mm/h × {p.duration_h} h</option>)}
          </select>
        </label>
        <div className="flex gap-2">
          <button onClick={run} disabled={busy || drawing || (!site && !drawn)}
            className="rounded bg-purple-500 px-3 py-1 font-semibold text-slate-950 hover:bg-purple-400 disabled:opacity-50">
            {busy ? 'Working…' : 'Assess'}
          </button>
          <button onClick={compare} disabled={busy || drawing}
            className="rounded border border-sky-600 px-3 py-1 text-sky-300 hover:bg-sky-500/10 disabled:opacity-50">
            Compare A / B / C
          </button>
          {dev && <button onClick={() => { setDev(null); setCmp(null) }} className="ml-auto text-[11px] text-slate-500 underline">clear</button>}
        </div>
        {err && <p className="text-[11px] text-amber-300">{err}</p>}
      </section>

      {dev && (
        <section className="space-y-2">
          <div className="rounded border-l-4 bg-slate-900/70 px-2.5 py-2" style={{ borderColor: verdictTone(dev.verdict) }}>
            <div className="text-sm font-semibold" style={{ color: verdictTone(dev.verdict) }}>{dev.verdict}</div>
            <div className="text-[11px] text-slate-400">
              {dev.params.site_id ?? 'Drawn footprint'} · {dev.params.use} · {dev.params.floors} floors · design storm '{dev.params.design_preset}'
              {dev.params.upgrades.length ? ` · upgrades: ${dev.params.upgrades.join(', ')}` : ''}
            </div>
            <div className="mt-1 text-[11px] text-slate-300">
              Index <span className="font-semibold tabular-nums">{dev.index.value?.toFixed(2) ?? '—'}</span>
              <span className="text-slate-500"> — {dev.index.label}</span>
            </div>
            <div className="text-[10px] text-slate-500">
              weights: {Object.entries(dev.index.weights).map(([k, w]) => `${DIM_LABEL[k] ?? k} ${w}`).join(' · ')}
            </div>
          </div>
          <dl className="grid grid-cols-3 gap-1.5 text-[11px]">
            {[
              ['Footprint', `${dev.derived.footprint_m2.toLocaleString()} m²`],
              ['Built-up', `${dev.derived.built_up_area_m2.toLocaleString()} m²`],
              ['Height', `${dev.derived.height_m} m`],
              ['Occupants', dev.derived.occupants.toLocaleString()],
              ['Water', `${dev.derived.water_kl_day} kL/day`],
              ['Electrical', `${dev.derived.electrical_kva} kVA`],
              ['Added runoff', `${(dev.derived.added_runoff_m3s * 1000).toFixed(1)} L/s`],
              ['Detention tank', dev.derived.detention_tank_m3 ? `${dev.derived.detention_tank_m3} m³` : '—'],
              ['Design rain', `${dev.derived.design_rain_mm_h} mm/h`],
            ].map(([k, v]) => (
              <div key={k} className="rounded bg-slate-900/60 px-1.5 py-1">
                <dt className="text-[9px] uppercase tracking-wider text-slate-500">{k}</dt>
                <dd className="tabular-nums text-slate-100">{v}</dd>
              </div>
            ))}
          </dl>
          <ul className="space-y-1">
            {dev.checks.map((c) => <CheckRow key={c.dimension} c={c} keyDim={dev.key_dimensions.includes(c.dimension)} />)}
          </ul>
          <details className="text-[11px] text-slate-400">
            <summary className="cursor-pointer text-slate-300">Assumptions</summary>
            <ul className="mt-1 list-disc pl-4">{dev.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
          </details>
        </section>
      )}

      {cmp && <CompareView cmp={cmp} />}
    </div>
  )
}
