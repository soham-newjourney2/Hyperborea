import { Suspense, lazy, useEffect, useState } from 'react'
import AssetInspector from './components/AssetInspector'
import LayerManager from './components/LayerManager'
import Legend from './components/Legend'
import Login from './components/Login'
import RegionSwitcher from './components/RegionSwitcher'
import { REGION } from './lib/region'
import MapView from './components/MapView'
import { AUTH_EVENT, clearSession, currentToken } from './lib/auth'
import { getHealth, getLayers, getRegion, getWeatherForecast, runFlood, type Health } from './lib/api'
import { useApp } from './store'

// Charts (Recharts) load only when the Weather tab opens — keeps first paint light.
const EnvironmentPanel = lazy(() => import('./components/EnvironmentPanel'))
const RelationshipExplorer = lazy(() => import('./components/RelationshipExplorer'))
const DisasterLab = lazy(() => import('./components/DisasterLab'))
const DevelopmentPanel = lazy(() => import('./components/DevelopmentPanel'))
const AccessPanel = lazy(() => import('./components/AccessPanel'))

type ApiState = { kind: 'checking' } | { kind: 'ok'; health: Health } | { kind: 'offline' }

function useApiHealth(intervalMs = 10000): ApiState {
  const [state, setState] = useState<ApiState>({ kind: 'checking' })
  useEffect(() => {
    let ctrl: AbortController | null = null
    const check = () => {
      ctrl?.abort()
      ctrl = new AbortController()
      getHealth(ctrl.signal)
        .then((health) => setState({ kind: 'ok', health }))
        .catch((e: unknown) => {
          if ((e as Error).name !== 'AbortError') setState({ kind: 'offline' })
        })
    }
    check()
    const id = setInterval(check, intervalMs)
    return () => {
      clearInterval(id)
      ctrl?.abort()
    }
  }, [intervalMs])
  return state
}

function ApiBadge({ state }: { state: ApiState }) {
  const snapshot = state.kind === 'ok' && state.health.status === 'snapshot'
  const style = snapshot
    ? 'bg-amber-500/15 text-amber-300 ring-amber-500/40'
    : state.kind === 'ok'
      ? 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/40'
      : state.kind === 'offline'
        ? 'bg-red-500/15 text-red-300 ring-red-500/40'
        : 'bg-slate-500/15 text-slate-300 ring-slate-500/40'
  const dot = snapshot ? 'bg-amber-400' : state.kind === 'ok' ? 'bg-emerald-400' : state.kind === 'offline' ? 'bg-red-400' : 'bg-slate-400'
  const label = snapshot
    ? `Offline snapshot · ${state.health.snapshot_at?.slice(0, 10) ?? ''}`
    : state.kind === 'ok'
      ? 'API OK'
      : state.kind === 'offline'
        ? 'API offline'
        : 'Checking API…'
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ${style}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

function useBootstrap(ok: boolean) {
  const { region, setRegion, setLayers } = useApp()
  useEffect(() => {
    if (!ok || region) return
    const ctrl = new AbortController()
    Promise.all([getRegion(ctrl.signal), getLayers(ctrl.signal)])
      .then(([r, l]) => {
        setRegion(r)
        setLayers(l)
        const q = new URLSearchParams(window.location.search)
        const deepLink = q.get('asset') // ?asset=<asset_id>
        if (deepLink) useApp.getState().select(deepLink)
        const tabQ = q.get('tab') // ?tab=weather|relations
        if (tabQ === 'weather' || tabQ === 'relations' || tabQ === 'disaster' || tabQ === 'develop' || tabQ === 'access')
          useApp.getState().setRightTab(tabQ)
        const scen = q.get('scenario') // ?scenario=extreme → run preset on load (demo links)
        if (scen) {
          if (!tabQ) useApp.getState().setRightTab('disaster')
          runFlood({ preset: scen }).then((f) => useApp.getState().setFlood(f)).catch(() => {})
        }
        for (const tok of (q.get('layers') ?? '').split(',').filter(Boolean)) { // ?layers=drains,-roads
          const off = tok.startsWith('-')
          const id = off ? tok.slice(1) : tok
          if (Boolean(useApp.getState().visible[id]) === off) useApp.getState().toggle(id)
        }
      })
      .catch(() => {})
    return () => ctrl.abort()
  }, [ok, region, setRegion, setLayers])
}

function useWeatherPoll(ok: boolean, intervalMs = 10 * 60 * 1000) {
  const setWeather = useApp((s) => s.setWeather)
  useEffect(() => {
    if (!ok) return
    const ctrl = new AbortController()
    const load = () => getWeatherForecast(ctrl.signal).then(setWeather).catch(() => {})
    load()
    const id = setInterval(load, intervalMs)
    return () => {
      clearInterval(id)
      ctrl.abort()
    }
  }, [ok, intervalMs, setWeather])
}

function WeatherChip() {
  const w = useApp((s) => s.weather)
  const setRightTab = useApp((s) => s.setRightTab)
  if (!w) return null
  const c = w.current
  return (
    <button onClick={() => setRightTab('weather')} className="hover:text-sky-300" title={`${w.attribution} · fetched ${w.fetched_at}`}>
      {c.temperature_2m.toFixed(0)}°C · {c.condition} · rain {c.rain.toFixed(1)} mm
      {w.stale && <span className="ml-1 text-amber-300">(stale)</span>}
    </button>
  )
}

function Tabs() {
  const { rightTab, setRightTab } = useApp()
  const tab = (id: 'inspector' | 'relations' | 'disaster' | 'develop' | 'access' | 'weather', label: string) => (
    <button
      onClick={() => setRightTab(id)}
      className={`flex-1 border-b-2 px-1 py-2 text-[10px] font-semibold uppercase tracking-wider ${
        rightTab === id ? 'border-sky-400 text-sky-300' : 'border-transparent text-slate-500 hover:text-slate-300'
      }`}
    >
      {label}
    </button>
  )
  return (
    <div className="sticky top-0 z-10 flex border-b border-slate-800 bg-slate-950">
      {tab('inspector', 'Inspect')}
      {tab('relations', 'Graph')}
      {tab('disaster', 'Disaster')}
      {tab('develop', 'Develop')}
      {tab('access', 'Access')}
      {tab('weather', 'Env')}
    </div>
  )
}

function Panel({ title, children, className = '' }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`border-b border-slate-800 p-3 ${className}`}>
      <h2 className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</h2>
      {children}
    </section>
  )
}

export default function App() {
  const api = useApiHealth()
  const [authed, setAuthed] = useState(() => Boolean(currentToken()))
  useEffect(() => {
    const onAuth = () => setAuthed(false)
    window.addEventListener(AUTH_EVENT, onAuth)
    return () => window.removeEventListener(AUTH_EVENT, onAuth)
  }, [])
  // live API → admin login required; unreachable API → offline snapshot without login (P04)
  const live = api.kind === 'ok' && api.health.status !== 'snapshot'
  const ready = api.kind === 'ok' && (authed || !live)
  useBootstrap(ready)
  useWeatherPoll(ready)
  const region = useApp((s) => s.region)
  const rightTab = useApp((s) => s.rightTab)
  if (live && !authed) return <Login onDone={() => setAuthed(true)} />
  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950 px-4 py-2">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-semibold tracking-[0.3em] text-sky-300">HYPERBOREA</h1>
          <span className="text-xs text-slate-500">
            Urban intelligence · {region ? `${region.name} · ${String(region.attrs.area_km2 ?? '')} km²` : 'pilot'}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <RegionSwitcher />
          <ApiBadge state={api} />
          {authed && (
            <button onClick={() => { clearSession(); setAuthed(false) }} className="text-[11px] text-slate-500 hover:text-slate-200">
              Sign out
            </button>
          )}
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="flex w-72 shrink-0 flex-col overflow-y-auto border-r border-slate-800 bg-slate-950/90">
          <Panel title="Layers">
            <LayerManager />
          </Panel>
          <Panel title="Legend" className="border-b-0">
            <Legend />
          </Panel>
        </aside>
        <main className="relative flex-1 bg-[#0b0f14]">
          {api.kind === 'offline' && !region ? (
            <div className="flex h-full items-center justify-center text-sm text-slate-500">
              API offline — start the backend (scripts/dev.ps1).
            </div>
          ) : (
            <MapView />
          )}
        </main>
        <aside
          className={`${rightTab === 'inspector' ? 'w-80' : 'w-96'} shrink-0 overflow-y-auto border-l border-slate-800 bg-slate-950/90`}
        >
          <Tabs />
          <div className="p-3">
            {rightTab === 'inspector' ? (
              <AssetInspector />
            ) : (
              <Suspense fallback={<p className="text-xs text-slate-500">Loading…</p>}>
                {rightTab === 'relations' ? <RelationshipExplorer /> : rightTab === 'disaster' ? <DisasterLab /> : rightTab === 'develop' ? <DevelopmentPanel /> : rightTab === 'access' ? <AccessPanel /> : <EnvironmentPanel />}
              </Suspense>
            )}
          </div>
        </aside>
      </div>

      <footer className="flex items-center gap-4 border-t border-slate-800 bg-slate-950 px-4 py-1.5 text-xs text-slate-500">
        <ApiBadge state={api} />
        {api.kind === 'ok' && (
          <>
            <span>API v{api.health.version}</span>
            <span>Data: {api.health.data_timestamp?.slice(0, 16).replace('T', ' ') ?? 'none loaded'} UTC</span>
          </>
        )}
        <WeatherChip />
        <span className="ml-auto">
          © OpenStreetMap contributors (ODbL) · Sentinel-2 cloudless by EOX · Weather & CAMS air quality via Open-Meteo.com ·
          © ESA WorldCover 2021 · Contains modified Copernicus Sentinel data
          {REGION === 'london_stratford' && ' · Terrain: © Environment Agency copyright and/or database right 2022 (OGL v3)'}
        </span>
      </footer>
    </div>
  )
}
