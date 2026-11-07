import { Suspense, lazy, useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceArea, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getAir, getAsset, getLandcover, getWater, type AirQuality, type Landcover, type WaterResponse } from '../lib/api'
import { useApp } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

const WeatherPanel = lazy(() => import('./WeatherPanel'))
type Sub = 'weather' | 'air' | 'water' | 'land'
const LINK_SUB = new URLSearchParams(window.location.search).get('env') as Sub | null // ?env=air|water|land

// NAQI PM2.5 bands (CPCB 2014) — official category colours, used only as faint context bands + labelled.
const PM25_BANDS: [number, number, string, string][] = [
  [0, 30, '#00B050', 'Good'], [30, 60, '#92D050', 'Satisfactory'], [60, 90, '#FFFF00', 'Moderate'],
  [90, 120, '#FF9900', 'Poor'], [120, 250, '#FF0000', 'Very Poor'], [250, 400, '#C00000', 'Severe'],
]
const POL_LABEL: Record<string, string> = { pm2_5: 'PM2.5', pm10: 'PM10', nitrogen_dioxide: 'NO₂', ozone: 'O₃' }
const AXIS = { fontSize: 10, fill: '#94a3b8' }
const GRID = '#1e293b'

function Card({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded border border-slate-800 bg-slate-900/50 p-2.5">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  )
}

function Air() {
  const [a, setA] = useState<AirQuality | null>(null)
  const [err, setErr] = useState(false)
  useEffect(() => {
    const c = new AbortController()
    getAir(c.signal)
      .then((x) => {
        setA(x)
        setErr(false)
      })
      .catch((e: Error) => e.name !== 'AbortError' && setErr(true)) // StrictMode double-mount aborts the first call
    return () => c.abort()
  }, [])
  if (err) return <p className="text-xs text-amber-300">Air quality unavailable (no snapshot).</p>
  if (!a) return <p className="text-xs text-slate-500">Loading air quality…</p>
  const nowKey = a.window.to
  const series = a.hourly.map((h) => ({ ...h, t: h.time.slice(5, 13).replace('T', ' ') }))
  return (
    <div className="space-y-2.5">
      <Card title="Air quality · pilot (24 h)" right={<ProvenanceBadge status={a.data_status} small />}>
        <div className="flex items-center gap-3">
          <div className="rounded px-2 py-1 text-center" style={{ backgroundColor: `${a.color}26`, boxShadow: `inset 0 0 0 1px ${a.color}` }}>
            <div className="text-2xl font-semibold tabular-nums text-slate-50">{a.naqi ?? '—'}</div>
            <div className="text-[10px] uppercase tracking-wider text-slate-300">NAQI</div>
          </div>
          <div>
            <div className="text-sm font-semibold" style={{ color: a.color ?? undefined }}>{a.category}</div>
            <div className="text-[11px] text-slate-400">dominant {POL_LABEL[a.dominant ?? ''] ?? '—'}</div>
            {a.stale && <div className="text-[10px] text-amber-300">stale · {a.stale_reason ?? a.origin}</div>}
          </div>
        </div>
        <dl className="mt-2 grid grid-cols-4 gap-1 text-[11px]">
          {Object.entries(a.means_ugm3).map(([k, v]) => (
            <div key={k} className="rounded bg-slate-950/50 px-1.5 py-1">
              <dt className="text-[9px] uppercase tracking-wider text-slate-500">{POL_LABEL[k]}</dt>
              <dd className="tabular-nums text-slate-100">{v ?? '—'} <span className="text-slate-500">µg/m³</span></dd>
              <dd className="text-[10px] text-slate-500">sub-index {a.sub_index[k] ?? '—'}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-1.5 text-[10px] leading-snug text-slate-500">
          {a.note}. Window {a.window.from.replace('T', ' ')} → {a.window.to.replace('T', ' ')} IST · fetched {a.fetched_at.slice(0, 16).replace('T', ' ')} UTC.
          Categories: CPCB NAQI (2014).
        </p>
      </Card>
      <Card title="PM2.5 · hourly, past 24 h + 72 h forecast" right={<span className="text-[10px] text-slate-500">µg/m³</span>}>
        <div className="h-40" role="img" aria-label="Hourly PM2.5 with NAQI category bands">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 4, right: 8, bottom: 0, left: -18 }}>
              {PM25_BANDS.map(([lo, hi, col, name]) => (
                <ReferenceArea key={name} y1={lo} y2={hi} fill={col} fillOpacity={0.07} stroke="none" ifOverflow="hidden" />
              ))}
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="t" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval={23} tickFormatter={(t: string) => t.slice(0, 5)} />
              <YAxis tick={AXIS} tickLine={false} axisLine={false} width={40} domain={[0, (m: number) => Math.max(150, Math.ceil(m / 50) * 50)]} />
              <ReferenceLine x={nowKey.slice(5, 13).replace('T', ' ')} stroke="#64748b" strokeDasharray="3 3"
                label={{ value: 'now', position: 'insideTopRight', fontSize: 9, fill: '#94a3b8' }} />
              <Tooltip
                content={({ active, payload }) => {
                  const p = active && payload?.[0]?.payload
                  if (!p) return null
                  const band = PM25_BANDS.find(([lo, hi]) => p.pm2_5 >= lo && p.pm2_5 < hi)
                  return (
                    <div className="rounded border border-slate-700 bg-slate-950/95 px-2 py-1 text-[11px] text-slate-200">
                      <div className="font-semibold">{p.pm2_5} µg/m³ · {band?.[3] ?? ''} band</div>
                      <div className="text-slate-400">{p.time.replace('T', ' ')} IST (hourly value, not 24-h mean)</div>
                    </div>
                  )
                }}
              />
              <Line type="monotone" dataKey="pm2_5" stroke="#e2e8f0" strokeWidth={2} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
        <ul className="mt-1 flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-slate-400">
          {PM25_BANDS.map(([lo, hi, col, name]) => (
            <li key={name} className="flex items-center gap-1">
              <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: col, opacity: 0.7 }} />
              {name} {lo}–{hi}
            </li>
          ))}
        </ul>
        <p className="mt-1 text-[10px] text-slate-500">{a.attribution}</p>
      </Card>
    </div>
  )
}

function Water() {
  const { visible, toggle, select, flyTo } = useApp()
  const [w, setW] = useState<WaterResponse | null>(null)
  useEffect(() => {
    const c = new AbortController()
    getWater(c.signal).then(setW).catch(() => {})
    if (!useApp.getState().visible.water_quality) useApp.getState().toggle('water_quality')
    return () => c.abort()
  }, [])
  if (!w) return <p className="text-xs text-slate-500">Loading water points…</p>
  return (
    <div className="space-y-2.5">
      <div className={`rounded border px-2.5 py-1.5 text-[11px] font-semibold ${w.demo ? 'border-purple-500/60 bg-purple-500/10 text-purple-200' : 'border-teal-500/60 bg-teal-500/10 text-teal-200'}`}>
        {w.banner} · {w.note}
      </div>
      <label className="flex items-center gap-2 text-[11px] text-slate-300">
        <input type="checkbox" className="accent-sky-400" checked={Boolean(visible.water_quality)} onChange={() => toggle('water_quality')} />
        Show points on the map
      </label>
      <ul className="space-y-1">
        {w.points.features.map((f) => {
          const a = f.properties.attrs as { sample_date: string; parameters: { parameter: string; value: number; unit: string }[] }
          return (
            <li key={f.properties.asset_id}>
              <button
                onClick={() => {
                  select(f.properties.asset_id)
                  getAsset(f.properties.asset_id).then((x) => flyTo(x.position[0], x.position[1])).catch(() => {})
                }}
                className="w-full rounded border border-slate-800 bg-slate-900/50 px-2 py-1 text-left text-xs hover:border-sky-600"
              >
                <div className="flex items-center gap-1.5 text-slate-100">
                  <span className="truncate">{f.properties.name}</span>
                  <span className="ml-auto"><ProvenanceBadge status={f.properties.data_status} small /></span>
                </div>
                <div className="mt-0.5 text-[10px] tabular-nums text-slate-400">
                  {a.parameters.map((p) => `${p.parameter === 'ph' ? 'pH' : p.parameter.toUpperCase()} ${p.value} ${p.unit === 'pH units' ? '' : p.unit}`).join(' · ')} · sampled {a.sample_date}
                </div>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

function Land() {
  const { overlays, setOverlay, visible, toggle } = useApp()
  const [s, setS] = useState<Landcover | null>(null)
  useEffect(() => {
    let live = true
    getLandcover().then((x) => live && setS(x)).catch(() => {})
    return () => {
      live = false
    }
  }, [])
  if (!s) return <p className="text-xs text-slate-500">Loading land cover…</p>
  const classes = Object.values(s.worldcover.classes)
  const colorOf = (label: string) => classes.find((c) => c.label === label)?.color ?? '#64748b'
  return (
    <div className="space-y-2.5">
      <Card title="Overlays on the map">
        {(['worldcover', 'ndvi'] as const).map((k) => (
          <label key={k} className="flex items-center gap-2 text-[11px] text-slate-300">
            <input type="checkbox" className="accent-sky-400" checked={overlays[k]} onChange={() => setOverlay(k, !overlays[k])} />
            {k === 'worldcover' ? 'ESA WorldCover 2021 (10 m land cover)' : `Sentinel-2 NDVI, dry season ${s.ndvi.window.replace('/', ' → ')}`}
          </label>
        ))}
        <p className="mt-1 text-[10px] text-slate-500">Brighter inside the pilot, faded in the 300 m buffer.</p>
        <label className="mt-2 flex items-center gap-2 text-[11px] text-slate-300">
          <input type="checkbox" className="accent-sky-400" checked={Boolean(visible.cv_water)} onChange={() => toggle('cv_water')} />
          Surface water polygons — NDWI spectral index (not ML), dry + post-monsoon
          <span className="ml-auto"><ProvenanceBadge status="modelled" small /></span>
        </label>
        <p className="text-[10px] text-slate-500">≥ 99 % of detected water lies inside mapped OSM water (sanity check). 10 m pixels can't see street waterlogging.</p>
      </Card>
      <Card title="Land cover · pilot" right={<ProvenanceBadge status={s.worldcover.data_status} small />}>
        <ul className="space-y-1">
          {Object.entries(s.worldcover.pilot_shares_pct).map(([label, pct]) => (
            <li key={label} className="text-[11px]">
              <div className="flex justify-between text-slate-300">
                <span className="flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: colorOf(label) }} />
                  {label}
                </span>
                <span className="tabular-nums text-slate-100">{pct.toFixed(1)} %</span>
              </div>
              <div className="mt-0.5 h-1.5 rounded bg-slate-800">
                <div className="h-1.5 rounded" style={{ width: `${pct}%`, backgroundColor: colorOf(label) }} />
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-1.5 text-[10px] text-slate-500">© ESA WorldCover 2021 (CC BY 4.0) · 10 m classes, ~75 % accuracy</p>
      </Card>
      <Card title="Vegetation · NDVI" right={<ProvenanceBadge status={s.ndvi.data_status} small />}>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-semibold tabular-nums text-slate-50">{s.ndvi.pilot_mean.toFixed(2)}</span>
          <span className="text-[11px] text-slate-400">pilot mean (−1 … 1; &gt; 0.4 dense green)</span>
        </div>
        <div className="mt-1.5 h-2 rounded" style={{ background: 'linear-gradient(90deg,#a50026,#f46d43,#fee08b,#d9ef8b,#66bd63,#006837)' }} />
        <div className="mt-0.5 flex justify-between text-[10px] text-slate-500"><span>−0.1 bare/built</span><span>0.8 dense vegetation</span></div>
        <p className="mt-1.5 text-[10px] text-slate-500">
          Median of {s.ndvi.scenes.length} low-cloud scenes ({s.ndvi.scenes.map((x) => x.date).join(', ')}); {s.ndvi.note}.
          Contains modified Copernicus Sentinel data 2025–2026.
        </p>
      </Card>
    </div>
  )
}

export default function EnvironmentPanel() {
  const [sub, setSub] = useState<Sub>(LINK_SUB && ['weather', 'air', 'water', 'land'].includes(LINK_SUB) ? LINK_SUB : 'weather')
  const btn = (id: Sub, label: string) => (
    <button key={id} onClick={() => setSub(id)}
      className={`rounded px-2 py-0.5 text-xs ${sub === id ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'text-slate-400 hover:text-slate-200'}`}>
      {label}
    </button>
  )
  return (
    <div className="space-y-3">
      <div className="flex gap-1">{[btn('weather', 'Weather'), btn('air', 'Air'), btn('water', 'Water'), btn('land', 'Land cover')]}</div>
      {sub === 'weather' && (
        <Suspense fallback={<p className="text-xs text-slate-500">Loading…</p>}>
          <WeatherPanel />
        </Suspense>
      )}
      {sub === 'air' && <Air />}
      {sub === 'water' && <Water />}
      {sub === 'land' && <Land />}
    </div>
  )
}
