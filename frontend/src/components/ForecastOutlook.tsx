import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getWarning, runFlood, type FloodResult, type WarningOutlook } from '../lib/api'
import { useApp } from '../store'
import { LEVEL_STYLE } from '../lib/styles'

// P21: 72 h forecast → cascade outlook (Disaster tab). Bars = forecast rain per hour; red bars = hours where the
// ML quick-scan expects overloaded drains; shaded = worst burst that the full engine ran.
const AXIS = { fontSize: 10, fill: '#94a3b8' }

export default function ForecastOutlook() {
  const setFlood = useApp((s) => s.setFlood)
  const [w, setW] = useState<WarningOutlook | null>(null)
  const [err, setErr] = useState(false)
  const [busy, setBusy] = useState(false)
  const [demo, setDemo] = useState(false) // synthetic burst when the real forecast is dry (labelled DEMO)
  useEffect(() => {
    const c = new AbortController()
    getWarning(c.signal, demo).then(setW).catch((e: Error) => e.name !== 'AbortError' && setErr(true))
    return () => c.abort()
  }, [demo])
  if (err) return <p className="text-[11px] text-slate-500">72 h outlook unavailable (needs the API or a snapshot).</p>
  if (!w) return <p className="text-[11px] text-slate-500">Loading 72 h outlook…</p>
  const st = LEVEL_STYLE[w.level] ?? LEVEL_STYLE.none
  const data = w.timeline.map((h, i) => ({ ...h, i, t: h.time.slice(5, 13).replace('T', ' ') }))
  const win = w.window
  const showOnMap = async () => {
    if (!win) return
    setBusy(true)
    try {
      const res: FloodResult = await runFlood({ rain_mm_h: win.rain_mm_h, duration_h: win.hours, condition_scale: 1 })
      setFlood(res)
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className={`space-y-2 rounded border p-2.5 ${st.box}`}>
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-300">Next {w.hours} h · live outlook</h3>
        <span className={`text-xs font-semibold ${st.text}`}>{w.demo ? 'DEMO · ' : ''}{st.label}</span>
      </div>
      <p className={`text-xs ${st.text}`}>{w.headline}</p>
      <button onClick={() => setDemo(!demo)} className="text-[10px] text-sky-300 underline-offset-2 hover:underline">
        {demo ? '← back to the real forecast' : w.level === 'none' ? 'Dry forecast — try a demo burst (synthetic rain)' : 'Try a demo burst (synthetic rain)'}
      </button>
      <div className="h-28" role="img" aria-label="Forecast rain per hour with expected drain overloads">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="#1e293b" />
            {win && <ReferenceArea x1={data[win.start]?.t} x2={data[Math.min(win.start + win.hours - 1, data.length - 1)]?.t}
              fill="#f59e0b" fillOpacity={0.15} stroke="none" />}
            <XAxis dataKey="t" tick={AXIS} tickLine={false} interval={23} tickFormatter={(t: string) => t.slice(0, 5)} />
            <YAxis tick={AXIS} tickLine={false} axisLine={false} width={30} allowDecimals={false}
              label={{ value: 'mm/h', angle: -90, position: 'insideLeft', fontSize: 9, fill: '#64748b' }} />
            <Tooltip content={({ active, payload }) => {
              const p = active && payload?.[0]?.payload
              if (!p) return null
              return (
                <div className="rounded border border-slate-700 bg-slate-950/95 px-2 py-1 text-[11px] text-slate-200">
                  <div className="font-semibold">{p.rain_mm_h} mm/h · {p.time.replace('T', ' ')}</div>
                  <div className="text-slate-400">probability {p.probability_pct ?? '—'}%{p.unlikely ? ' (unlikely)' : ''} ·
                    AI quick-scan: {p.drains_overloaded_est} drains overloaded</div>
                </div>
              )
            }} />
            <Bar dataKey="rain_mm_h" isAnimationActive={false}>
              {data.map((d) => <Cell key={d.i} fill={d.drains_overloaded_est > 0 ? '#ef4444' : d.unlikely ? '#334155' : '#38bdf8'} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {win && w.summary && (
        <div className="flex items-center justify-between gap-2 text-[11px] text-slate-300">
          <span>Worst burst: {win.rain_mm_h} mm/h × {win.hours} h ({win.total_mm} mm) · {w.summary.drains_overloaded}/{w.summary.drains_total} drains ·
            {' '}{w.summary.buildings_power_loss ?? 0} buildings without power</span>
          <button onClick={showOnMap} disabled={busy}
            className="shrink-0 rounded bg-sky-500 px-2 py-0.5 text-[11px] font-semibold text-slate-950 hover:bg-sky-400 disabled:opacity-50">
            {busy ? 'Running…' : 'Show on map'}
          </button>
        </div>
      )}
      <p className="text-[10px] leading-snug text-slate-500">
        {w.label}. Rain: Open-Meteo forecast (fetched {w.forecast_fetched_at.slice(0, 16).replace('T', ' ')} UTC{w.forecast_stale ? ', stale' : ''}).
        Hourly bars use the ML surrogate; the worst burst is run through the full engine. Levels and thresholds: config/warning.yaml.
      </p>
    </section>
  )
}
