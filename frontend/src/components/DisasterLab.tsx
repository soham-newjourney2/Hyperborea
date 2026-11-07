import { useEffect, useState } from 'react'
import { getAsset, getExplainStatus, getModels, getPresets, getQuickscan, postExplain, runFlood, type ExplainResponse, type Explanation,
  type FloodResult, type ModelCard, type Preset, type QuickScan } from '../lib/api'
import { KIND, PROB_STOPS, SCENARIO } from '../lib/styles'
import { useApp } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

const STATE_COLOR: Record<string, string> = {
  overloaded: SCENARIO.drain_overloaded,
  impassable: SCENARIO.road_impassable,
  impaired: SCENARIO.road_impaired,
  above_plinth: SCENARIO.building_exposed,
  access_cut: SCENARIO.facility_cut,
  access_impaired: SCENARIO.facility_impaired,
  power_loss: SCENARIO.facility_cut,
  shutdown: SCENARIO.road_impassable,
}
const STATE_LABEL: Record<string, string> = {
  overloaded: 'overloaded',
  impassable: 'impassable',
  impaired: 'impaired',
  above_plinth: 'water above plinth',
  access_cut: 'access cut',
  access_impaired: 'access impaired',
  power_loss: 'power lost (backup unknown)',
  shutdown: 'shut down (flooded)',
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

function Plain({ resultId, assetId }: { resultId: string; assetId: string | null }) {
  const [mode, setMode] = useState<'template' | 'llm'>('template')
  const [llmOk, setLlmOk] = useState<string | null>(null)
  const [out, setOut] = useState<ExplainResponse | null>(null)
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    const c = new AbortController()
    getExplainStatus(c.signal).then((s) => setLlmOk(s.llm.available ? s.llm.model : '')).catch(() => setLlmOk(''))
    return () => c.abort()
  }, [])
  const run = (m: 'template' | 'llm') => {
    setMode(m)
    setBusy(true)
    postExplain(resultId, assetId, m).then(setOut).catch(() => setOut(null)).finally(() => setBusy(false))
  }
  return (
    <div className="rounded border border-slate-700 bg-slate-950/60 p-2 text-[11px]">
      <div className="mb-1 flex items-center gap-1">
        <span className="font-semibold text-slate-300">Plain-language explanation</span>
        <button onClick={() => run('template')} className={`ml-auto rounded px-1.5 ${mode === 'template' ? 'bg-sky-500/20 text-sky-300' : 'text-slate-400'}`}>Template</button>
        <button onClick={() => run('llm')} disabled={!llmOk} title={llmOk ? `local ${llmOk} via Ollama` : 'Local LLM not installed / not running (hosted mode uses the template)'}
          className={`rounded px-1.5 disabled:opacity-40 ${mode === 'llm' ? 'bg-sky-500/20 text-sky-300' : 'text-slate-400'}`}>Local LLM</button>
      </div>
      {busy && <p className="text-slate-500">{mode === 'llm' ? 'Local LLM writing (≈5 s)…' : 'Writing…'}</p>}
      {!busy && !out && <p className="text-slate-500">Choose Template (deterministic) or Local LLM (grounded: numbers checked against the engine facts).</p>}
      {!busy && out && (
        <>
          <p className="leading-relaxed text-slate-200">{out.text}</p>
          <p className="mt-1 text-[10px] text-slate-500">
            {out.mode === 'llm' ? `Local LLM ${out.model} · grounding passed` : 'Deterministic template'}
            {out.fallback_reason ? ` · LLM answer rejected → template (${out.fallback_reason})` : ''}
          </p>
        </>
      )}
    </div>
  )
}

function Why({ ex, resultId }: { ex: Explanation; resultId: string }) {
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
      <Plain key={ex.asset_id} resultId={resultId} assetId={ex.asset_id} />
      {ex.also?.map((a) => (
        <div key={a.title} className="rounded border border-slate-700 p-2">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-400">Also · {a.title} chain</p>
          <ol className="space-y-1 text-[11px] text-slate-300">
            {a.path.slice(-3).map((s, i) => <li key={i}>→ {s.label}</li>)}
          </ol>
        </div>
      ))}
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

function ModelCardDrawer({ onClose }: { onClose: () => void }) {
  const [cards, setCards] = useState<ModelCard[] | null>(null)
  useEffect(() => {
    const c = new AbortController()
    getModels(c.signal).then(setCards).catch(() => setCards([]))
    return () => c.abort()
  }, [])
  const s = cards?.find((m) => m.id === 'ml_surrogate')
  const m = s?.metrics as { surrogate: Record<string, number>; baseline: Record<string, number | string>;
    training: Record<string, unknown>; permutation_importance_auc: Record<string, number>; sklearn: string } | undefined
  const limits = s?.card_markdown?.split('## Limitations')[1]?.trim().split('\n- ').map((x) => x.replace(/^- /, '')) ?? []
  return (
    <section className="space-y-2 rounded border border-sky-600/50 bg-slate-900/80 p-2.5 text-[11px]">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold uppercase tracking-wider text-sky-300">Model card · flood surrogate</h3>
        <button onClick={onClose} className="text-slate-500 hover:text-slate-200">×</button>
      </div>
      {!m ? <p className="text-slate-500">{cards ? 'Model card unavailable.' : 'Loading…'}</p> : (
        <>
          <p className="text-slate-300">scikit-learn {m.sklearn} HistGradientBoostingClassifier · trained on {String(m.training.engine_runs)} simulated
            engine runs ({Number(m.training.rows).toLocaleString()} drain-rows) · {String(m.training.split)}</p>
          <table className="w-full tabular-nums">
            <thead><tr className="text-left text-slate-500"><th></th><th>Precision</th><th>Recall</th><th>F1</th><th>ROC-AUC</th></tr></thead>
            <tbody>
              <tr><td className="text-slate-300">Surrogate</td>{(['precision', 'recall', 'f1', 'roc_auc'] as const).map((k) => <td key={k} className="text-slate-100">{m.surrogate[k]}</td>)}</tr>
              <tr><td className="text-slate-400">Baseline</td>{(['precision', 'recall', 'f1', 'roc_auc'] as const).map((k) => <td key={k} className="text-slate-400">{String(m.baseline[k])}</td>)}</tr>
            </tbody>
          </table>
          <p className="text-slate-500">Baseline: {String(m.baseline.rule)} · held-out spatial blocks</p>
          <p className="font-semibold text-slate-300">Feature importance (Δ ROC-AUC)</p>
          <ul>{Object.entries(m.permutation_importance_auc).slice(0, 5).map(([k, v]) => <li key={k} className="flex justify-between text-slate-400"><span>{k}</span><span className="tabular-nums">{v}</span></li>)}</ul>
          <p className="font-semibold text-slate-300">Limitations</p>
          <ul className="list-disc pl-4 text-slate-400">{limits.map((l) => <li key={l}>{l}</li>)}</ul>
          <p className="text-slate-500">Licence: MIT (model, ours) · scikit-learn BSD-3 · runs on CPU, no GPU or torch.</p>
        </>
      )}
    </section>
  )
}

function QuickScanPanel({ rain, dur, cond }: { rain: number; dur: number; cond: number }) {
  const setQuick = useApp((s) => s.setQuick)
  const [q, setQ] = useState<QuickScan | null>(null)
  const [check, setCheck] = useState<QuickScan['vs_engine'] | null>(null)
  const [card, setCard] = useState(false)
  useEffect(() => {
    const c = new AbortController()
    const t = setTimeout(() => {
      getQuickscan(rain, dur, cond, false, c.signal)
        .then((r) => {
          setQ(r)
          setCheck(null)
          setQuick(r.probabilities)
        })
        .catch(() => {})
    }, 120) // debounce slider drags
    return () => {
      clearTimeout(t)
      c.abort()
    }
  }, [rain, dur, cond, setQuick])
  useEffect(() => () => setQuick(null), [setQuick])
  return (
    <section className="space-y-2 rounded border border-sky-600/50 bg-sky-500/5 p-2.5 text-[11px]">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold uppercase tracking-wider text-sky-300">AI quick-scan · instant</h3>
        <button onClick={() => setCard((v) => !v)} className="text-sky-300 underline">model card</button>
      </div>
      <p className="text-slate-400">{q?.label ?? 'Surrogate of the rule engine, trained on simulated runs — not validated on real events'}</p>
      {q && (
        <div className="grid grid-cols-3 gap-1.5 tabular-nums">
          <div className="rounded bg-slate-900/70 px-1.5 py-1"><div className="text-[9px] text-slate-500">PREDICTED</div><div className="text-base text-slate-50">{q.predicted_overloads}</div><div className="text-[10px] text-slate-500">drains p ≥ 0.5</div></div>
          <div className="rounded bg-slate-900/70 px-1.5 py-1"><div className="text-[9px] text-slate-500">EXPECTED</div><div className="text-base text-slate-50">{q.expected_overloads}</div><div className="text-[10px] text-slate-500">Σ probability</div></div>
          <div className="rounded bg-slate-900/70 px-1.5 py-1"><div className="text-[9px] text-slate-500">INFERENCE</div><div className="text-base text-slate-50">{q.inference_ms} ms</div><div className="text-[10px] text-slate-500">{q.drains} drains</div></div>
        </div>
      )}
      <div className="h-2 rounded" style={{ background: `linear-gradient(90deg, ${PROB_STOPS.join(',')})` }} />
      <div className="flex justify-between text-[10px] text-slate-500"><span>p = 0</span><span>0.5</span><span>1 overload probability</span></div>
      <div className="flex items-center gap-2">
        <button onClick={() => getQuickscan(rain, dur, cond, true).then((r) => setCheck(r.vs_engine ?? null)).catch(() => {})}
          className="rounded border border-slate-700 px-2 py-0.5 text-slate-200 hover:border-sky-500">Check vs full engine</button>
        {check && <span className="text-slate-300">agreement {check.agreement_pct}% · F1 {check.f1} · engine {check.engine_overloads} vs AI {check.surrogate_overloads}</span>}
      </div>
      {card && <ModelCardDrawer onClose={() => setCard(false)} />}
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
  const [ai, setAi] = useState(() => new URLSearchParams(window.location.search).get('ai') === '1') // ?ai=1

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
          {flood && !flood.offline && (
            <button onClick={() => {
              const img = useApp.getState().captureMap?.()
              try {
                if (img) localStorage.setItem(`hyperborea.report.img.${flood.result_id}`, img)
              } catch { /* storage full / blocked: report without map image */ }
              window.open(`${window.location.pathname}?report=${flood.result_id}`, '_blank')
            }} className="rounded border border-sky-600 px-2 py-1 text-xs text-sky-300 hover:bg-sky-500/10">
              Open report
            </button>
          )}
          {ms !== null && flood && <span className="ml-auto text-[10px] text-slate-500">{flood.offline ? 'offline snapshot' : `${ms} ms`}</span>}
        </div>
        {err && <p className="text-[11px] text-amber-300">{err}</p>}
        <label className="flex items-center gap-2 border-t border-slate-800 pt-2 text-[11px] text-slate-300">
          <input type="checkbox" className="accent-sky-400" checked={ai} onChange={() => setAi((v) => !v)} />
          AI quick-scan — instant surrogate map while you move the sliders
        </label>
      </section>

      {ai && <QuickScanPanel rain={rain} dur={dur} cond={cond} />}

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
            <Tile label="Facilities affected" value={s.facilities_affected} sub={`${s.facilities_power_loss ?? 0} power lost · ${s.facilities_access_impaired} access impaired`} tone={SCENARIO.facility_impaired} />
            <Tile label="Transformers shut down" value={s.transformers_shutdown ?? 0} sub="simulated network, plinth 0.6 m" tone={SCENARIO.road_impassable} />
            <Tile label="Buildings without power" value={s.buildings_power_loss ?? 0} sub="supplied by a flooded transformer" tone="#64748b" />
            {s.buildings_hospital_slower !== undefined && (
              <Tile label="Hospital access" value={`+${s.hospital_mean_delta_min ?? 0} min`}
                sub={`${s.buildings_hospital_slower} slower · ${s.buildings_hospital_isolated} isolated (free-flow)`} tone="#d946ef" />
            )}
          </div>

          {ex && <Why ex={ex} resultId={flood.result_id} />}
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
