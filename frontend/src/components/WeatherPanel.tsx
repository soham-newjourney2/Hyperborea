import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getClimateSummary, getPresets, type ClimateSummary, type Preset, type Trend } from '../lib/api'
import { CHART_AXIS, CHART_GRID, CHART_MUTED } from '../lib/styles'
import { useApp } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

// Single-series charts: one hue (magnitude), recessive grid/axes, labelled reference lines in muted ink.
const RAIN = '#38bdf8'
const INK_MUTED = CHART_MUTED
const GRID = CHART_GRID
const AXIS = CHART_AXIS

const timeFmt = new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', day: '2-digit', month: 'short' })
const fmtTime = (iso: string) => timeFmt.format(new Date(iso))

function Card({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
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

function TipBox({ lines }: { lines: string[] }) {
  return (
    <div className="rounded border border-slate-700 bg-slate-950/95 px-2 py-1 text-[11px] text-slate-200 shadow-lg">
      {lines.map((l, i) => (
        <div key={i} className={i === 0 ? 'font-semibold' : 'text-slate-400'}>
          {l}
        </div>
      ))}
    </div>
  )
}

function TrendLine({ label, t }: { label: string; t: Trend }) {
  const sign = t.slope_per_decade > 0 ? '+' : ''
  return (
    <div className="flex justify-between gap-2 text-[11px]">
      <span className="text-slate-400">{label}</span>
      <span className="tabular-nums text-slate-200">
        {sign}
        {t.slope_per_decade} {t.unit}{' '}
        <span className={t.significant_5pct ? 'text-slate-200' : 'text-slate-500'}>
          (p={t.p_value}{t.significant_5pct ? '' : ', not significant'})
        </span>
      </span>
    </div>
  )
}

function CurrentCard() {
  const w = useApp((s) => s.weather)
  const offline = useApp((s) => s.weather?.origin === 'snapshot')
  if (!w) return <Card title="Now · pilot centroid"><p className="text-xs text-slate-500">Loading weather…</p></Card>
  const c = w.current
  return (
    <Card
      title="Now · pilot centroid"
      right={
        w.stale ? (
          <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-300 ring-1 ring-amber-500/40">
            Stale{offline ? ' snapshot' : ''}
          </span>
        ) : (
          <ProvenanceBadge status={w.data_status} small />
        )
      }
    >
      <div className="flex items-end gap-3">
        <div className="text-3xl font-semibold tabular-nums text-slate-50">
          {c.temperature_2m.toFixed(1)}
          <span className="text-base font-normal text-slate-400">°C</span>
        </div>
        <div className="pb-1 text-sm text-slate-300">{c.condition}</div>
      </div>
      <dl className="mt-2 grid grid-cols-3 gap-2 text-xs">
        {[
          ['Rain', `${c.rain.toFixed(1)} mm`],
          ['Humidity', `${c.relative_humidity_2m}%`],
          ['Wind', `${c.wind_speed_10m.toFixed(0)} km/h`],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="text-[9px] uppercase tracking-wider text-slate-500">{k}</dt>
            <dd className="tabular-nums text-slate-100">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-2 text-[10px] text-slate-500">
        Model forecast for {fmtTime(c.time)} {tzLabel(w.location.timezone)} · fetched {fmtTime(w.fetched_at)}
        {w.stale && w.stale_reason ? ` · ${w.stale_reason}` : ''}
      </p>
    </Card>
  )
}

function RainForecast() {
  const w = useApp((s) => s.weather)
  const hourly = w?.hourly ?? []
  const total = hourly.reduce((a, h) => a + (h.precipitation ?? 0), 0)
  return (
    <Card title="Rain · next 72 h (mm/h)" right={<span className="text-[11px] tabular-nums text-slate-400">{total.toFixed(1)} mm total</span>}>
      {hourly.length === 0 ? (
        <p className="text-xs text-slate-500">No forecast.</p>
      ) : (
        <div className="h-28" role="img" aria-label={`Hourly precipitation forecast, ${total.toFixed(1)} mm over 72 hours`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hourly} margin={{ top: 4, right: 4, bottom: 0, left: -8 }} barCategoryGap={1}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="time" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval={23}
                tickFormatter={(t: string) => t.slice(5, 10)} />
              <YAxis tick={AXIS} tickLine={false} axisLine={false} width={40} allowDecimals
                domain={[0, (max: number) => Math.max(1, Math.ceil(max))]} />
              <Tooltip
                cursor={{ fill: 'rgba(148,163,184,0.12)' }}
                content={({ active, payload }) => {
                  const h = active && payload?.[0]?.payload
                  if (!h) return null
                  return (
                    <TipBox
                      lines={[
                        `${h.precipitation.toFixed(1)} mm/h`,
                        `${h.time.replace('T', ' ')} ${tzLabel(w?.location.timezone)}`,
                        h.precipitation_probability != null ? `probability ${h.precipitation_probability}%` : '',
                      ].filter(Boolean)}
                    />
                  )
                }}
              />
              <Bar dataKey="precipitation" fill={RAIN} radius={[2, 2, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <p className="mt-1 text-[10px] text-slate-500">{w?.attribution ?? 'Weather data by Open-Meteo.com'}</p>
    </Card>
  )
}

function ClimateCharts({ c }: { c: ClimateSummary }) {
  const t = c.thresholds_mm_day
  const [a, b] = c.period.full_years
  return (
    <>
      <Card title={`Wettest day each year (mm) · ${a}–${b}`} right={<ProvenanceBadge status={c.data_status} small />}>
        <div className="h-36" role="img" aria-label={`Annual maximum one-day rainfall with ${t.label ?? 'IMD thresholds'} (heavy, very heavy)`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={c.years} margin={{ top: 8, right: 34, bottom: 0, left: -8 }} barCategoryGap={1}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="year" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval={9} />
              <YAxis tick={AXIS} tickLine={false} axisLine={false} width={40} domain={[0, 200]} ticks={[0, 50, 100, 150, 200]} />
              <Tooltip
                cursor={{ fill: 'rgba(148,163,184,0.12)' }}
                content={({ active, payload }) => {
                  const y = active && payload?.[0]?.payload
                  return y ? <TipBox lines={[`${y.year}: ${y.max_1day_mm} mm`, `${y.heavy_days} heavy-rain day(s)`]} /> : null
                }}
              />
              <ReferenceLine y={t.heavy} stroke={INK_MUTED} strokeDasharray="4 3"
                label={{ value: `${t.heavy}`, position: 'right', fontSize: 9, fill: CHART_AXIS.fill }} />
              <ReferenceLine y={t.very_heavy} stroke={INK_MUTED} strokeDasharray="4 3"
                label={{ value: `${t.very_heavy}`, position: 'right', fontSize: 9, fill: CHART_AXIS.fill }} />
              <Bar dataKey="max_1day_mm" fill={RAIN} radius={[2, 2, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-1 flex items-center gap-1.5 text-[10px] text-slate-500">
          <span className="inline-block w-4 border-t border-dashed border-slate-500" />
          {t.label ?? 'IMD thresholds'}: heavy {t.heavy} · very heavy {t.very_heavy} mm/day (extremely heavy ≥ {t.extremely_heavy})
        </p>
      </Card>

      <Card title={`Heavy-rain days (≥ ${t.heavy} mm) per year`}>
        <div className="h-24" role="img" aria-label={`Heavy rain days per year (${t.label ?? 'IMD thresholds'})`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={c.years} margin={{ top: 4, right: 4, bottom: 0, left: -8 }} barCategoryGap={1}>
              <CartesianGrid vertical={false} stroke={GRID} />
              <XAxis dataKey="year" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} interval={9} />
              <YAxis tick={AXIS} tickLine={false} axisLine={false} width={40} allowDecimals={false} />
              <Tooltip
                cursor={{ fill: 'rgba(148,163,184,0.12)' }}
                content={({ active, payload }) => {
                  const y = active && payload?.[0]?.payload
                  return y ? <TipBox lines={[`${y.year}: ${y.heavy_days} day(s)`, `annual total ${y.total_mm} mm`]} /> : null
                }}
              />
              <Bar dataKey="heavy_days" fill={RAIN} radius={[2, 2, 0, 0]} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Climate context">
        <dl className="mb-2 grid grid-cols-2 gap-2 text-xs">
          {[
            ['Mean annual rain', `${c.stats.annual_total_mean_mm.toLocaleString()} mm`],
            ['Monsoon (JJAS) share', `${c.stats.jjas_share_pct}%`],
            ['Record day', `${c.stats.max_1day.mm} mm · ${c.stats.max_1day.date}`],
            ['Heavy days / yr', `${c.stats.heavy_days_per_year_mean}`],
          ].map(([k, v]) => (
            <div key={k}>
              <dt className="text-[9px] uppercase tracking-wider text-slate-500">{k}</dt>
              <dd className="tabular-nums text-slate-100">{v}</dd>
            </div>
          ))}
        </dl>
        <div className="space-y-0.5">
          <TrendLine label="Annual total" t={c.trends.annual_total} />
          <TrendLine label="Wettest day" t={c.trends.annual_max_1day} />
          <TrendLine label="Heavy days" t={c.trends.heavy_days} />
        </div>
        <p className="mt-2 text-[10px] leading-snug text-slate-500">
          {c.label}. Grid cell {c.grid.lat}°N {c.grid.lon}°E, {c.period.start} → {c.period.end}. {c.notes[0]}
        </p>
      </Card>
    </>
  )
}

function Presets({ presets }: { presets: Preset[] }) {
  return (
    <Card title="Rainfall scenario presets" right={<ProvenanceBadge status="simulated" small />}>
      <ul className="space-y-1.5">
        {presets.map((p) => (
          <li key={p.id} className="rounded border border-dashed border-purple-500/30 bg-slate-950/40 px-2 py-1.5">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-xs font-medium text-slate-100">{p.title}</span>
              <span className="text-[11px] tabular-nums text-slate-300">
                {p.rain_mm_h} mm/h × {p.duration_h} h = {p.total_mm} mm
              </span>
            </div>
            <p className="mt-0.5 text-[10px] leading-snug text-slate-500">{p.description}</p>
          </li>
        ))}
      </ul>
      <p className="mt-1.5 text-[10px] text-slate-500">Uniform design storms for the disaster lab (P08). Edit in config/scenarios.yaml.</p>
    </Card>
  )
}

// P18: forecast times come in the pilot's timezone (Open-Meteo `timezone`)
const tzLabel = (tz?: string) => (!tz || tz === 'Asia/Kolkata' ? 'IST' : tz)

export default function WeatherPanel() {
  const [climate, setClimate] = useState<ClimateSummary | null>(null)
  const [presets, setPresets] = useState<Preset[]>([])
  useEffect(() => {
    const ctrl = new AbortController()
    getClimateSummary(ctrl.signal).then(setClimate).catch(() => {})
    getPresets(ctrl.signal).then(setPresets).catch(() => {})
    return () => ctrl.abort()
  }, [])
  return (
    <div className="space-y-2.5">
      <CurrentCard />
      <RainForecast />
      {climate ? <ClimateCharts c={climate} /> : <p className="text-xs text-slate-500">Loading climate record…</p>}
      {presets.length > 0 && <Presets presets={presets} />}
    </div>
  )
}
