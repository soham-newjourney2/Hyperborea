import { useEffect, useState } from 'react'
import { getAsset, getPresets, runFlood, type Explanation, type FloodResult, type Preset } from '../lib/api'
import { KIND, SCENARIO } from '../lib/styles'
import { useApp } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

const STATE_COLOR: Record<string, string> = {
  overloaded: SCENARIO.drain_overloaded,
  impassable: SCENARIO.road_impassable,
  impaired: SCENARIO.road_impaired,
  above_plinth: SCENARIO.building_exposed,
  access_cut: SCENARIO.facility_cut,
  access_impaired: SCENARIO.facility_impaired,
}
const STATE_LABEL: Record<string, string> = {
  overloaded: 'overloaded',
  impassable: 'impassable',
  impaired: 'impaired',
  above_plinth: 'water above plinth',
  access_cut: 'access cut',
  access_impaired: 'access impaired',
}

function Slider({ label, unit, value, min, max, step, onChange }: {
  label: string; unit: string; value: number; min: number; max: number; step: number; onChange: (v: number) => void
}) {
  return (
    <label className="block text-[11px] text-slate-400">
      <span className="flex justify-between">
        {label}
        <span className="tabular-nums text-slate-100">
          {value} {unit}
        </span>
      </span>
      <input type="range" className="w-full accent-sky-400" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))} />
    </label>
  )
}

function Tile({ label, value, sub, tone }: { label: string; value: string | number; sub?: string; tone?: string }) {
  return (
    <div className="rounded border border-slate-800 bg-slate-900/60 px-2 py-1.5">
      <div className="text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="flex items-center gap-1.5 text-lg font-semibold tabular-nums text-slate-50">
        {tone && <span className="h-2 w-2 rounded-full" style={{ backgroundColor: tone }} />}
        {value}
      </div>
      {sub && <div className="text-[10px] text-slate-500">{sub}</div>}
    </div>
  )
}

function Why({ ex }: { ex: Explanation }) {
  return (
    <section className="space-y-2 rounded border border-amber-500/40 bg-slate-900/70 p-2.5">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-amber-300">Why? · {ex.trigger}</h3>
      <ol className="relative space-y-2 border-l border-slate-700 pl-3">
        {ex.path.map((s, i) => (
          <li key={i} className="relative">
            <span className="absolute -left-[17px] top-1 h-2 w-2 rounded-full bg-amber-400" />
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              {s.edge} · <span className="normal-case">{s.to.replace(/_osm_|_syn_/, ' ').slice(0, 28)}</span>
            </div>
            <div className="text-xs text-slate-100">{s.label}</div>
            <div className="font-mono text-[10px] text-slate-400">{s.formula}</div>
            <div className="text-[10px] text-slate-500">{s.rule}</div>
          </li>
        ))}
      </ol>
      <div className="rounded bg-slate-950/60 p-2 text-[11px]">
        <div className="flex items-baseline justify-between">
          <span className="text-slate-400">Risk index</span>
          <span className="text-base font-semibold tabular-nums text-slate-50">{ex.risk.index.toFixed(2)}</span>
        </div>
        <div className="font-mono text-[10px] text-slate-500">{ex.risk.formula} — {ex.risk.label}</div>
        <div className="mt-1 grid grid-cols-4 gap-1 text-[10px] text-slate-400">
          {Object.entries(ex.risk.components).map(([k, v]) => (
            <div key={k}>
              {k.slice(0, 1).toUpperCase()} {v} <span className="text-slate-600">w{ex.risk.weights[k]}</span>
            </div>
          ))}
        </div>
      </div>
      <details className="text-[11px] text-slate-400">
        <summary className="cursor-pointer text-slate-300">Inputs, assumptions & what would improve this</summary>
        <ul className="mt-1 space-y-0.5">
          {ex.inputs.map((i) => (
            <li key={i.name} className="flex items-center gap-1.5">
              <ProvenanceBadge status={i.data_status} small />
              {i.name}: {String(i.value)} {i.unit} <span className="text-slate-600">({i.source_id})</span>
            </li>
          ))}
        </ul>
        <p className="mt-1.5 font-semibold text-slate-300">Assumptions</p>
        <ul className="list-disc pl-4">{ex.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
        <p className="mt-1.5 font-semibold text-slate-300">Mitigation</p>
        <ul className="list-disc pl-4">{ex.mitigation.map((a) => <li key={a}>{a}</li>)}</ul>
        <p className="mt-1.5 font-semibold text-slate-300">Data that would improve this</p>
        <ul className="list-disc pl-4">{ex.improve.map((a) => <li key={a}>{a}</li>)}</ul>
        <p className="mt-1.5">Data status: {ex.data_status} · confidence {ex.confidence}</p>
      </details>
    </section>
  )
}

export default function DisasterLab() {
  const { flood, setFlood, selectedId, select, flyTo } = useApp()
  const [presets, setPresets] = useState<Preset[]>([])
  const [preset, setPreset] = useState<string | null>(flood?.params.preset ?? 'extreme')
  const [rain, setRain] = useState(flood?.params.rain_mm_h ?? 80)
  const [dur, setDur] = useState(flood?.params.duration_h ?? 2)
  const [cond, setCond] = useState(flood?.params.condition_scale ?? 1)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [ms, setMs] = useState<number | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    getPresets(ctrl.signal).then(setPresets).catch(() => {})
    return () => ctrl.abort()
  }, [])

  const choose = (p: Preset) => {
    setPreset(p.id)
    setRain(p.rain_mm_h)
    setDur(p.duration_h)
  }
  const run = async () => {
    setBusy(true)
    setErr(null)
    const t0 = performance.now()
    const p = presets.find((x) => x.id === preset)
    const custom = !p || p.rain_mm_h !== rain || p.duration_h !== dur
    try {
      const res: FloodResult = await runFlood(
        custom ? { rain_mm_h: rain, duration_h: dur, condition_scale: cond } : { preset, condition_scale: cond },
      )
      setFlood(res)
      setMs(Math.round(performance.now() - t0))
    } catch (e) {
      setErr(`Scenario failed: ${(e as Error).message}. Offline, only the plain heavy / extreme presets are available.`)
    } finally {
      setBusy(false)
    }
  }
  const pick = (id: string) => {
    select(id)
    getAsset(id).then((a) => flyTo(a.position[0], a.position[1])).catch(() => {})
  }

  const s = flood?.summary
  const ex = selectedId ? flood?.explanations[selectedId] : undefined
  return (
    <div className="space-y-3">
      <div className="rounded border border-amber-500/50 bg-amber-500/10 px-2.5 py-1.5 text-[11px] font-semibold text-amber-200">
        Scenario-based estimate — not a prediction · simulated drains, uniform design storms
      </div>

      <section className="space-y-2 rounded border border-slate-800 bg-slate-900/50 p-2.5">
        <div className="flex flex-wrap gap-1">
          {presets.map((p) => (
            <button key={p.id} onClick={() => choose(p)} title={p.description}
              className={`rounded px-2 py-0.5 text-xs ${preset === p.id && p.rain_mm_h === rain && p.duration_h === dur ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'border border-slate-700 text-slate-300 hover:border-sky-600'}`}>
              {p.title.split(' ')[0]} {p.rain_mm_h}×{p.duration_h}h
            </button>
          ))}
        </div>
        <Slider label="Rain intensity" unit="mm/h" value={rain} min={1} max={150} step={1} onChange={setRain} />
        <Slider label="Duration" unit="h" value={dur} min={0.5} max={12} step={0.5} onChange={setDur} />
        <Slider label="Drain condition (× siltation factor)" unit="×" value={cond} min={0.3} max={1.5} step={0.05} onChange={setCond} />
        <div className="flex items-center gap-2">
          <button onClick={run} disabled={busy}
            className="rounded bg-sky-500 px-3 py-1 text-xs font-semibold text-slate-950 hover:bg-sky-400 disabled:opacity-50">
            {busy ? 'Running…' : `Run ${(rain * dur).toFixed(0)} mm scenario`}
          </button>
          {flood && (
            <button onClick={() => setFlood(null)} className="rounded border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:border-slate-500">
              Clear
            </button>
          )}
          {ms !== null && flood && <span className="ml-auto text-[10px] text-slate-500">{flood.offline ? 'offline snapshot' : `${ms} ms`}</span>}
        </div>
        {err && <p className="text-[11px] text-amber-300">{err}</p>}
      </section>

      {s && flood && (
        <>
          <p className="text-[11px] text-slate-400">
            {flood.params.preset ? `Preset ${flood.params.preset}` : 'Custom'}: {flood.params.rain_mm_h} mm/h × {flood.params.duration_h} h,
            drain condition × {flood.params.condition_scale} · {flood.data_status}
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            <Tile label="Drains overloaded" value={`${s.drains_overloaded}/${s.drains_total}`} sub={`${s.drains_near_capacity} near capacity`} tone={SCENARIO.drain_overloaded} />
            <Tile label="Roads impassable" value={`${s.road_km_impassable} km`} sub={`${s.roads_impassable} edges · ${s.roads_impaired} impaired`} tone={SCENARIO.road_impassable} />
            <Tile label="Buildings above plinth" value={s.buildings_exposed} sub={`${s.catchments_ponded} catchments ponded`} tone={SCENARIO.building_exposed} />
            <Tile label="Facilities affected" value={s.facilities_affected} sub={`${s.facilities_access_cut} cut · ${s.facilities_access_impaired} impaired`} tone={SCENARIO.facility_impaired} />
          </div>

          {ex && <Why ex={ex} />}
          {selectedId && !ex && <p className="text-[11px] text-slate-500">Selected asset is not affected in this scenario.</p>}

          <section>
            <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Affected · by risk index</h3>
            <ul className="space-y-1">
              {flood.affected.slice(0, 40).map((a) => (
                <li key={a.asset_id}>
                  <button onClick={() => pick(a.asset_id)}
                    className={`flex w-full items-center gap-2 rounded border px-2 py-1 text-left text-xs ${selectedId === a.asset_id ? 'border-amber-500/60 bg-amber-500/10' : 'border-slate-800 bg-slate-900/50 hover:border-sky-600'}`}>
                    <span className="h-2 w-2 shrink-0 rounded-sm" style={{ backgroundColor: KIND[a.kind]?.color ?? '#64748b' }} />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-slate-100">{a.name || `${KIND[a.kind]?.label ?? a.kind} ${a.asset_id.split('_').slice(-2).join('_')}`}</span>
                      <span className="block text-[10px] text-slate-500">
                        <span style={{ color: STATE_COLOR[a.state] }}>● </span>
                        {STATE_LABEL[a.state] ?? a.state} · {a.detail}
                      </span>
                    </span>
                    <span className="shrink-0 tabular-nums text-slate-300">{a.risk.toFixed(2)}</span>
                  </button>
                </li>
              ))}
            </ul>
            {flood.affected.length > 40 && <p className="mt-1 text-[10px] text-slate-500">+ {flood.affected.length - 40} more (all shown on the map)</p>}
          </section>
        </>
      )}
    </div>
  )
}
