import { useEffect, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getOptimiseConfig, postOptimise, type OptimiseConfig, type OptimiseResult } from '../lib/api'
import { useApp } from '../store'

// P23: best upgrades per budget. Assumed unit costs + value weights are shown, never hidden.
const AXIS = { fontSize: 10, fill: '#94a3b8' }
const KIND = { drain_upsize: 'Drain', plinth_raise: 'Plinth', detention: 'Detention' } as Record<string, string>
const fmt = (sym: string, v: number) =>
  sym === '₹' ? `₹${v >= 1e7 ? `${(v / 1e7).toFixed(2)} cr` : `${(v / 1e5).toFixed(1)} L`}` : `${sym}${Math.round(v).toLocaleString()}`

export default function OptimiserCard() {
  const { setFlood, select } = useApp()
  const [cfg, setCfg] = useState<OptimiseConfig | null>(null)
  const [preset, setPreset] = useState('extreme')
  const [budget, setBudget] = useState<number | null>(null)
  const [res, setRes] = useState<OptimiseResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => {
    const c = new AbortController()
    getOptimiseConfig(c.signal).then((x) => { setCfg(x); setBudget(x.default_budget) }).catch(() => {})
    return () => c.abort()
  }, [])
  if (!cfg || budget == null) return null // optimiser needs the live API
  const run = async (withMap: boolean) => {
    setBusy(true)
    setErr(null)
    try {
      const r = await postOptimise({ preset, budget, with_map: withMap })
      setRes(r)
      if (withMap && r.after_result) setFlood(r.after_result)
    } catch (e) {
      setErr(`Optimiser failed: ${(e as Error).message}`)
    } finally {
      setBusy(false)
    }
  }
  const sym = cfg.symbol
  const rows: [string, string][] = [['buildings_exposed', 'Buildings above plinth'], ['buildings_power_loss', 'Buildings without power'],
    ['transformers_shutdown', 'Transformers shut down'], ['facilities_affected', 'Facilities affected'], ['road_km_impassable', 'Road km impassable']]
  return (
    <section className="space-y-2 rounded border border-emerald-500/40 bg-emerald-500/5 p-2.5">
      <h3 className="text-[11px] font-semibold uppercase tracking-wider text-emerald-200">Upgrade optimiser · best fixes per budget</h3>
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-300">
        <select value={preset} onChange={(e) => setPreset(e.target.value)} aria-label="Scenario to protect against"
          className="rounded border border-slate-700 bg-slate-900 px-1 py-0.5 text-xs text-slate-100">
          {['moderate', 'design', 'heavy', 'extreme'].map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <label className="flex flex-1 items-center gap-1">
          Budget {fmt(sym, budget)}
          <input type="range" className="flex-1 accent-emerald-400" min={cfg.budget_step} max={cfg.default_budget * 5}
            step={cfg.budget_step} value={budget} onChange={(e) => setBudget(Number(e.target.value))} />
        </label>
        <button onClick={() => run(false)} disabled={busy}
          className="rounded bg-emerald-500 px-2 py-0.5 text-xs font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-50">
          {busy ? 'Optimising…' : 'Optimise'}
        </button>
      </div>
      {err && <p className="text-[11px] text-red-300">{err}</p>}
      {res && (
        <>
          <p className="text-xs text-emerald-200">
            {fmt(sym, res.spent)} of {fmt(sym, res.budget)} → risk score {res.objective_before} → {res.objective_after}
            {' '}(<b>−{res.risk_removed_pct}%</b>) · {res.plan.length} fixes from {res.candidates_considered} candidates
          </p>
          <table className="w-full text-[11px] tabular-nums">
            <thead className="text-slate-500"><tr><th className="text-left font-normal">metric</th><th className="font-normal">before</th><th className="font-normal">after</th></tr></thead>
            <tbody className="text-slate-200">
              {rows.map(([k, l]) => <tr key={k}><td className="text-left text-slate-400">{l}</td><td className="text-center">{res.before[k] ?? 0}</td><td className="text-center">{res.after[k] ?? 0}</td></tr>)}
            </tbody>
          </table>
          <div className="h-20" role="img" aria-label="Risk score versus cumulative cost">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={res.curve} margin={{ top: 4, right: 6, bottom: 0, left: 0 }}>
                <XAxis dataKey="cost" tick={AXIS} tickFormatter={(v: number) => fmt(sym, v)} tickLine={false} />
                <YAxis tick={AXIS} width={34} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => [String(v), 'risk score']} labelFormatter={(v) => fmt(sym, Number(v))} />
                <Line type="stepAfter" dataKey="objective" stroke="#34d399" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <ol className="max-h-40 space-y-0.5 overflow-y-auto text-[11px]">
            {res.plan.map((p) => (
              <li key={p.step}>
                <button onClick={() => select(p.asset_id)} className="flex w-full gap-1.5 rounded px-1 text-left hover:bg-slate-800/60">
                  <span className="w-4 shrink-0 text-slate-500">{p.step}</span>
                  <span className="w-16 shrink-0 text-emerald-300">{KIND[p.kind] ?? p.kind}</span>
                  <span className="min-w-0 flex-1 truncate text-slate-300">{p.label}</span>
                  <span className="shrink-0 text-slate-400">{fmt(sym, p.cost)}</span>
                </button>
              </li>
            ))}
          </ol>
          <button onClick={() => run(true)} disabled={busy}
            className="rounded border border-emerald-500/60 px-2 py-0.5 text-[11px] text-emerald-200 hover:bg-emerald-500/10 disabled:opacity-50">
            Show "after upgrades" on map
          </button>
          <p className="text-[10px] leading-snug text-slate-500">
            {res.label}. Risk score = {res.objective_formula}. Unit costs ({res.currency}): drain upsize {fmt(sym, res.unit_costs.drain_upsize_per_m)}/m ·
            plinth raise {fmt(sym, res.unit_costs.plinth_raise_per_transformer)} each · detention {fmt(sym, res.unit_costs.detention_per_m3)}/m³ — config/costs.yaml.
          </p>
        </>
      )}
    </section>
  )
}
