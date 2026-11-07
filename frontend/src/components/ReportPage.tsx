import { useEffect, useState } from 'react'
import { getReport, type DevCompare, type Report } from '../lib/api'

// Print-optimised report (light theme). Data from GET /report/{result_id}; map image + last development comparison
// are handed over from the main app via localStorage (per viewer, optional).
const read = (k: string) => {
  try {
    return localStorage.getItem(k)
  } catch {
    return null
  }
}

function download(name: string, text: string, type: string) {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(new Blob([text], { type }))
  a.download = name
  a.click()
  URL.revokeObjectURL(a.href)
}

export default function ReportPage({ id }: { id: string }) {
  const [r, setR] = useState<Report | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const img = read(`hyperborea.report.img.${id}`)
  const dev = (() => {
    try {
      return JSON.parse(read('hyperborea.report.dev') ?? 'null') as DevCompare | null
    } catch {
      return null
    }
  })()
  useEffect(() => {
    getReport(id).then(setR).catch((e: Error) => setErr(`Report unavailable: ${e.message}. Run the scenario again in the app (results are kept in the API's memory).`))
  }, [id])
  if (err) return <p className="p-8 text-sm text-red-700">{err}</p>
  if (!r) return <p className="p-8 text-sm text-slate-600">Loading report…</p>
  const s = r.summary
  const csv = ['asset_id,kind,name,state,risk_index,detail',
    ...r.affected.map((a) => [a.asset_id, a.kind, a.name ?? '', a.state, a.risk, a.detail].map((v) => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n')
  const tiles: [string, string | number][] = [
    ['Drains overloaded', `${s.drains_overloaded} / ${s.drains_total}`], ['Roads impassable', `${s.roads_impassable} (${s.road_km_impassable} km)`],
    ['Buildings above plinth', s.buildings_exposed], ['Facilities affected', s.facilities_affected],
    ['Transformers shut down', s.transformers_shutdown ?? '—'], ['Buildings without power', s.buildings_power_loss ?? '—'],
    ['Buildings isolated from hospitals', s.buildings_hospital_isolated ?? '—'], ['Mean extra hospital drive', s.hospital_mean_delta_min !== undefined ? `${s.hospital_mean_delta_min} min` : '—'],
  ]
  return (
    <div className="report min-h-full bg-white text-slate-900">
      <div className="no-print sticky top-0 flex gap-2 border-b border-slate-200 bg-slate-50 px-8 py-2 text-sm">
        <button onClick={() => window.print()} className="rounded bg-slate-900 px-3 py-1 text-white">Print / Save as PDF</button>
        <button onClick={() => download(`hyperborea_${id}.json`, JSON.stringify(r, null, 1), 'application/json')} className="rounded border border-slate-300 px-3 py-1">Download JSON</button>
        <button onClick={() => download(`hyperborea_${id}_affected.csv`, csv, 'text/csv')} className="rounded border border-slate-300 px-3 py-1">Download CSV</button>
      </div>
      <article className="mx-auto max-w-4xl space-y-5 px-8 py-6 text-[13px] leading-relaxed">
        <header className="border-b-2 border-slate-900 pb-3">
          <h1 className="text-2xl font-bold">{r.title}</h1>
          <p className="mt-1 font-semibold text-amber-700">{r.label} · data status: {r.data_status}</p>
          <p className="text-slate-600">
            Scenario: {r.params.preset ?? 'custom'} — {r.params.rain_mm_h} mm/h × {r.params.duration_h} h, drain condition × {r.params.condition_scale} ·
            result {r.result_id} · generated {r.generated_at.replace('T', ' ').slice(0, 16)} UTC
          </p>
        </header>
        {img && <img src={img} alt="Map of the scenario at the time the report was opened" className="w-full rounded border border-slate-300" />}
        <section>
          <h2 className="mb-1 text-base font-bold">Summary</h2>
          <p>{r.narrative}</p>
          <div className="mt-2 grid grid-cols-4 gap-2">
            {tiles.map(([k, v]) => (
              <div key={k} className="rounded border border-slate-300 p-2">
                <div className="text-[10px] uppercase text-slate-500">{k}</div>
                <div className="text-lg font-semibold tabular-nums">{v}</div>
              </div>
            ))}
          </div>
        </section>
        <section>
          <h2 className="mb-1 text-base font-bold">Affected assets (top {r.affected.length} of {r.affected_total}, by risk index — not a probability)</h2>
          <table className="w-full border-collapse text-[11px]">
            <thead><tr className="border-b border-slate-400 text-left"><th className="py-1">Asset</th><th>Kind</th><th>State</th><th className="pr-3 text-right">Risk</th><th>Detail</th></tr></thead>
            <tbody>
              {r.affected.map((a) => (
                <tr key={a.asset_id} className="border-b border-slate-200 align-top">
                  <td className="py-0.5 pr-2">{a.name ?? <code className="text-[10px]">{a.asset_id}</code>}</td>
                  <td className="pr-2">{a.kind}</td><td className="pr-2">{a.state.replace(/_/g, ' ')}</td>
                  <td className="pr-3 text-right tabular-nums">{a.risk.toFixed(2)}</td><td>{a.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
        {dev && (
          <section>
            <h2 className="mb-1 text-base font-bold">Development comparison (screening — not an approval)</h2>
            <table className="w-full border-collapse text-[11px]">
              <thead><tr className="border-b border-slate-400 text-left"><th className="py-1">Dimension</th>{dev.options.map((o) => <th key={o.name}>{o.name}</th>)}</tr></thead>
              <tbody>
                {dev.table.map((row) => (
                  <tr key={row.dimension} className="border-b border-slate-200">
                    <td className="py-0.5">{row.dimension.replace(/_/g, ' ')}</td>
                    {dev.options.map((o) => <td key={o.name}>{row[o.name].replace(/_/g, ' ')}</td>)}
                  </tr>
                ))}
                <tr><td className="py-0.5 font-semibold">Verdict</td>{dev.options.map((o) => <td key={o.name} className="font-semibold">{dev.verdicts[o.name]}</td>)}</tr>
              </tbody>
            </table>
          </section>
        )}
        <section className="grid grid-cols-2 gap-4">
          <div>
            <h2 className="mb-1 text-base font-bold">Assumptions</h2>
            <ul className="list-disc pl-5">{r.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
            <h2 className="mb-1 mt-3 text-base font-bold">Simulated parts</h2>
            <ul className="list-disc pl-5">{r.simulated_parts.map((a) => <li key={a}>{a}</li>)}</ul>
          </div>
          <div>
            <h2 className="mb-1 text-base font-bold">Limitations</h2>
            <ul className="list-disc pl-5">{r.limitations.map((a) => <li key={a}>{a}</li>)}</ul>
            <h2 className="mb-1 mt-3 text-base font-bold">Attributions</h2>
            <ul className="list-disc pl-5">{r.attributions.map((a) => <li key={a}>{a}</li>)}</ul>
          </div>
        </section>
        <footer className="border-t border-slate-300 pt-2 text-[10px] text-slate-500">
          Hyperborea prototype (FIRE 2026 SustAI). Scenario-based estimates for planning discussion only.
        </footer>
      </article>
    </div>
  )
}
