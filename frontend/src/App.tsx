import { Suspense, lazy, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import AssetInspector from './components/AssetInspector'
import LayerManager from './components/LayerManager'
import Legend from './components/Legend'
import Login from './components/Login'
import RegionSwitcher from './components/RegionSwitcher'
import WarningBanner from './components/WarningBanner'
import { REGION } from './lib/region'
import MapView from './components/MapView'
import InfraHealth from './components/InfraHealth'
import ForecastOutlook from './components/ForecastOutlook'
import ValidationCard from './components/ValidationCard'
import OptimiserCard from './components/OptimiserCard'
import { AUTH_EVENT, clearSession, currentToken } from './lib/auth'
import { getHealth, getLayers, getRegion, getWeatherForecast, runFlood, type Health } from './lib/api'
import { useApp, type RightTab } from './store'

const EnvironmentPanel = lazy(() => import('./components/EnvironmentPanel'))
const RelationshipExplorer = lazy(() => import('./components/RelationshipExplorer'))
const DisasterLab = lazy(() => import('./components/DisasterLab'))
const DevelopmentPanel = lazy(() => import('./components/DevelopmentPanel'))
const AskPanel = lazy(() => import('./components/AskPanel'))
const AccessPanel = lazy(() => import('./components/AccessPanel'))
const WeatherPanel = lazy(() => import('./components/WeatherPanel'))

type ApiState = { kind: 'checking' } | { kind: 'ok'; health: Health } | { kind: 'offline' }
type ModuleId = 'command'|'twin'|'infrastructure'|'graph'|'flood'|'warning'|'validation'|'development'|'upgrade'|'access'|'weather'|'air'|'water'|'land'|'ask'|'reports'
type Theme = 'dark'|'light'

const MODULES: { id: ModuleId; label: string; short: string; group: string; description: string }[] = [
  {id:'command',label:'Command Centre',short:'Overview',group:'WORKSPACE',description:'A consolidated view of the selected pilot area, its mapped assets and current analytical context.'},
  {id:'twin',label:'3D Digital Twin',short:'Digital Twin',group:'WORKSPACE',description:'Explore the pilot area in 2D or 3D, inspect mapped buildings and switch geographic basemaps.'},
  {id:'infrastructure',label:'Infrastructure Intelligence',short:'Infrastructure',group:'ANALYSIS',description:'Inspect mapped infrastructure and review modelled asset-health indicators.'},
  {id:'graph',label:'Dependency Graph',short:'Dependencies',group:'ANALYSIS',description:'Explore typed relationships between infrastructure assets and understand connected systems.'},
  {id:'flood',label:'Flood Simulation',short:'Flood',group:'RISK & RESILIENCE',description:'Run scenario-based flood analysis using the configured rainfall and drainage assumptions.'},
  {id:'warning',label:'Early Warning',short:'Early Warning',group:'RISK & RESILIENCE',description:'72 h forecast → hourly ML quick-scan → worst burst run through the full flood engine. Modelled risks are labelled separately from observations.'},
  {id:'validation',label:'Data Validation',short:'Validation',group:'DATA & PLANNING',description:'Review data provenance, source status and coverage for the selected pilot, and how the flood engine scores against an observed flood where one was scored.'},
  {id:'development',label:'Development Screening',short:'Development',group:'DATA & PLANNING',description:'Screen a drawn or selected site against the available planning and environmental context.'},
  {id:'upgrade',label:'Upgrade Optimiser',short:'Upgrade Optimiser',group:'DATA & PLANNING',description:'Best drain upsizes, plinth raises and detention tanks for a budget (assumed unit costs), alongside modelled asset-condition rankings.'},
  {id:'access',label:'Accessibility',short:'Accessibility',group:'DATA & PLANNING',description:'Explore accessibility analysis for configured essential-service categories and network assumptions.'},
  {id:'weather',label:'Weather & Climate',short:'Weather',group:'ENVIRONMENT',description:'Review current conditions, forecasts and the available climate summary.'},
  {id:'air',label:'Air Quality',short:'Air Quality',group:'ENVIRONMENT',description:'Review available air-quality indicators, pollutant series and source provenance.'},
  {id:'water',label:'Water Quality',short:'Water Quality',group:'ENVIRONMENT',description:'Explore mapped water-quality sampling points and available measurements.'},
  {id:'land',label:'Land Cover',short:'Land Cover',group:'ENVIRONMENT',description:'Explore land-cover classifications and vegetation indices where raster coverage is available.'},
  {id:'ask',label:'Ask Hyperborea',short:'Ask Hyperborea',group:'TOOLS',description:'Ask plain-language questions about the selected pilot. Answers come only from engine results (rule parser, or a local LLM with a numeric grounding check); the layer catalogue is searchable below.'},
  {id:'reports',label:'Reports',short:'Reports',group:'TOOLS',description:'Access report workflows and exportable outputs produced by the analytical modules.'},
]

// The reused panels still talk to the store's `rightTab` (deep links, "explore relationships", scenario runs).
// These two maps keep the module navigation and that tab state in step.
const MODULE_TAB: Partial<Record<ModuleId, RightTab>> = { graph: 'relations', flood: 'disaster', development: 'develop', access: 'access', weather: 'weather', air: 'weather', water: 'weather', land: 'weather', ask: 'ask' }
const TAB_MODULE: Partial<Record<RightTab, ModuleId>> = { relations: 'graph', disaster: 'flood', develop: 'development', access: 'access', weather: 'weather', ask: 'ask' }
const ENV_MODULES: ModuleId[] = ['weather', 'air', 'water', 'land']
const isModuleId = (v: string | null): v is ModuleId => MODULES.some((m) => m.id === v)

/** Module to open on load: ?module=<id>, else ?env=air|water|land, else the legacy ?tab= / ?scenario= links. */
function initialModule(): ModuleId {
  try {
    const q = new URLSearchParams(window.location.search)
    const m = q.get('module')
    if (isModuleId(m)) return m
    const env = q.get('env')
    if (env === 'air' || env === 'water' || env === 'land') return env
    const tab = q.get('tab')
    if (tab === 'weather' || tab === 'relations' || tab === 'disaster' || tab === 'develop' || tab === 'access' || tab === 'ask') return TAB_MODULE[tab]!
    if (q.get('scenario')) return 'flood'
  } catch { /* malformed URL: fall through */ }
  return 'command'
}

function useApiHealth(intervalMs = 10000): ApiState {
  const [state, setState] = useState<ApiState>({ kind: 'checking' })
  useEffect(() => {
    let ctrl: AbortController | null = null
    const check = () => {
      ctrl?.abort(); ctrl = new AbortController()
      getHealth(ctrl.signal).then((health) => setState({kind:'ok',health})).catch((e:unknown) => {
        if ((e as Error).name !== 'AbortError') setState({kind:'offline'})
      })
    }
    check(); const id = setInterval(check, intervalMs)
    return () => { clearInterval(id); ctrl?.abort() }
  }, [intervalMs])
  return state
}

function ApiBadge({state}:{state:ApiState}) {
  const snapshot = state.kind === 'ok' && state.health.status === 'snapshot'
  const cls = state.kind === 'offline' ? 'status-bad' : snapshot ? 'status-warn' : state.kind === 'ok' ? 'status-good' : 'status-pending'
  const label = state.kind === 'offline' ? 'API offline' : snapshot ? 'Offline snapshot' : state.kind === 'ok' ? 'API connected' : 'Checking API'
  return <span className={`status-pill ${cls}`}><i />{label}</span>
}

function useBootstrap(ok:boolean) {
  const region=useApp(s=>s.region);const setRegion=useApp(s=>s.setRegion);const setLayers=useApp(s=>s.setLayers)
  useEffect(()=>{
    if(!ok||region)return
    const ctrl=new AbortController()
    Promise.all([getRegion(ctrl.signal),getLayers(ctrl.signal)]).then(([r,l])=>{
      setRegion(r);setLayers(l)
      const q=new URLSearchParams(window.location.search)
      const deep=q.get('asset');if(deep)useApp.getState().select(deep)
      const tab=q.get('tab')
      if(tab==='weather'||tab==='relations'||tab==='disaster'||tab==='develop'||tab==='access'||tab==='ask')useApp.getState().setRightTab(tab)
      const scen=q.get('scenario');if(scen){if(!tab&&!q.get('module')&&!q.get('env'))useApp.getState().setRightTab('disaster');runFlood({preset:scen}).then(f=>useApp.getState().setFlood(f)).catch((e:unknown)=>console.error(`scenario ${scen} failed to load`,e))}
      for(const tok of(q.get('layers')??'').split(',').filter(Boolean)){const off=tok.startsWith('-');const id=off?tok.slice(1):tok;if(Boolean(useApp.getState().visible[id])===off)useApp.getState().toggle(id)}
    }).catch((e:unknown)=>{if((e as Error).name!=='AbortError')console.error('pilot bootstrap failed',e)})
    return()=>ctrl.abort()
  },[ok,region,setRegion,setLayers])
}
function useWeatherPoll(ok:boolean){
  const setWeather=useApp(s=>s.setWeather)
  useEffect(()=>{if(!ok)return;const c=new AbortController();const load=()=>getWeatherForecast(c.signal).then(setWeather).catch(()=>{});load();const id=setInterval(load,600000);return()=>{clearInterval(id);c.abort()}},[ok,setWeather])
}

const ICON_PATHS: Record<ModuleId, ReactNode> = {
  command: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
  twin: <><path d="M12 2.5 21 7.5v9l-9 5-9-5v-9z"/><path d="M3 7.5l9 5 9-5M12 12.5v9"/></>,
  infrastructure: <><path d="M4 21V9l8-6 8 6v12"/><path d="M9 21v-6h6v6M3 21h18"/></>,
  graph: <><circle cx="5" cy="6" r="2.2"/><circle cx="19" cy="6" r="2.2"/><circle cx="12" cy="18" r="2.2"/><path d="M7.2 6h9.6M6.2 7.9l4.7 8.2M17.8 7.9l-4.7 8.2"/></>,
  flood: <><path d="M3 9c2 0 2-1.6 4.5-1.6S10 9 12 9s2-1.6 4.5-1.6S19 9 21 9"/><path d="M3 14c2 0 2-1.6 4.5-1.6S10 14 12 14s2-1.6 4.5-1.6S19 14 21 14"/><path d="M3 19c2 0 2-1.6 4.5-1.6S10 19 12 19s2-1.6 4.5-1.6S19 19 21 19"/></>,
  warning: <><path d="M12 3.5 22 20H2z"/><path d="M12 10v4.5M12 17.2v.3"/></>,
  validation: <><path d="M12 3l8 3v6c0 4.6-3.2 7.8-8 9-4.8-1.2-8-4.4-8-9V6z"/><path d="M8.5 12.2l2.5 2.5 4.5-5"/></>,
  development: <><circle cx="12" cy="12" r="7"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/><circle cx="12" cy="12" r="1.2"/></>,
  upgrade: <><path d="M4 19 10 13l4 3 6-8"/><path d="M15 8h5v5"/></>,
  access: <><circle cx="12" cy="4.5" r="1.8"/><path d="M5 8.500h14M12 8.500v6M12 14.500l-3.5 6M12 14.500l3.5 6"/></>,
  weather: <><circle cx="12" cy="12" r="4"/><path d="M12 2.500v2.500M12 19v2.500M2.5 12H5M19 12h2.500M5.3 5.3 7 7M17 17l1.7 1.700M5.3 18.7 7 17M17 7l1.7-1.7"/></>,
  air: <><path d="M3 8h10.500a2.5 2.5 0 1 0-2.4-3.2"/><path d="M3 12h15a2.5 2.5 0 1 1-2.4 3.2"/><path d="M3 16h7.500a2.2 2.2 0 1 1-2.1 2.9"/></>,
  water: <><path d="M12 3s6.5 6.8 6.5 11.300a6.5 6.5 0 0 1-13 0C5.5 9.8 12 3 12 3z"/></>,
  land: <><path d="M3 20h18"/><path d="M12 20v-7"/><path d="M12 13c0-3.5 2.5-5.5 6-5.5 0 3.5-2.5 5.5-6 5.500z"/><path d="M12 15.500c0-2.8-2-4.5-5-4.5 0 2.8 2 4.5 5 4.500z"/></>,
  ask: <><circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/></>,
  reports: <><path d="M6 2.500h8l4 4V21.500H6z"/><path d="M14 2.500v4h4M9 12h6M9 16h6"/></>,
}
function Svg({children,size=17}:{children:ReactNode;size?:number}) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{children}</svg>
}
function ModuleIcon({id}:{id:ModuleId}) {
  return <span className="nav-icon" aria-hidden="true"><Svg>{ICON_PATHS[id]}</Svg></span>
}

function DataSummary({module,onNavigate}:{module:ModuleId;onNavigate:(id:ModuleId)=>void}) {
  const layers=useApp(s=>s.layers)
  const region=useApp(s=>s.region)
  const visible=useApp(s=>s.visible)
  const selectedId=useApp(s=>s.selectedId)
  const [query,setQuery]=useState('')
  // Picking an asset (ranked list or map) had no visible result in these modules: show its detail in place.
  const selectedCard=selectedId?<div className="module-card"><div className="eyebrow">SELECTED ASSET</div><AssetInspector/></div>:null
  const filtered=useMemo(()=>layers.filter(l=>`${l.title} ${l.group} ${l.id}`.toLowerCase().includes(query.toLowerCase())),[layers,query])
  const statusCounts=layers.reduce((acc,l)=>{for(const [k,v] of Object.entries(l.data_status??{}))acc[k]=(acc[k]??0)+v;return acc},{} as Record<string,number>)
  if(module==='ask') return <div className="module-card-stack"><div className="module-card"><Suspense fallback={<p className="muted">Loading…</p>}><AskPanel/></Suspense></div><div className="module-card"><div className="eyebrow">DATA CATALOGUE SEARCH</div><h3>Explore pilot data</h3><p>Search layer names and inspect their available coverage. This is a catalogue search, not an AI-generated answer.</p><input className="field" type="search" aria-label="Search the layer catalogue" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search buildings, drains, roads…"/><div className="catalogue-list">{filtered.length===0&&<p className="muted">{layers.length?`No layers match “${query}”.`:'No layers loaded yet.'}</p>}{filtered.map(l=><div className="catalogue-row" key={l.id}><span><b>{l.title}</b><small>{l.group} · {l.id}</small></span><strong>{(l.count_in_pilot??l.count??0).toLocaleString()}</strong></div>)}</div></div></div>
  if(module==='validation') return <div className="module-card-stack"><ValidationCard/><div className="metric-grid"><div className="metric-card"><small>Mapped layers</small><b>{layers.length}</b></div><div className="metric-card"><small>Observed records</small><b>{(statusCounts.observed??0).toLocaleString()}</b></div><div className="metric-card"><small>Curated records</small><b>{(statusCounts.curated??0).toLocaleString()}</b></div><div className="metric-card"><small>Modelled / simulated</small><b>{((statusCounts.modelled??0)+(statusCounts.simulated??0)).toLocaleString()}</b></div></div><div className="module-card"><div className="eyebrow">PROVENANCE REGISTER</div><h3>Layer coverage and source status</h3>{layers.map(l=><div className="catalogue-row" key={l.id}><span><b>{l.title}</b><small>{Object.entries(l.data_status??{}).map(([k,v])=>`${k}: ${v.toLocaleString()}`).join(' · ')||'No status breakdown returned'}{l.count_in_pilot!=null&&l.count_in_pilot!==l.count?` · ${l.count_in_pilot.toLocaleString()} inside pilot`:''}</small></span><strong>{(l.count??l.count_in_pilot??0).toLocaleString()}</strong></div>)}</div></div>
  if(module==='reports') return <div className="module-card-stack"><div className="module-card"><div className="eyebrow">REPORT WORKSPACE</div><h3>Analytical outputs</h3><p>Run an analysis in Flood Simulation or Development Screening to produce its corresponding result. Reports should retain assumptions, simulated inputs, provenance and limitations.</p><div className="report-actions"><button className="action-button" onClick={()=>onNavigate('flood')}>Open flood simulation</button><button className="action-button secondary" onClick={()=>onNavigate('development')}>Open development screening</button></div></div><div className="module-card"><div className="eyebrow">REPORTING STANDARD</div><h3>Every report should include</h3><ul className="clean-list"><li>Selected pilot area and analysis date</li><li>Input datasets and provenance status</li><li>Scenario assumptions and modelled components</li><li>Results, limitations and attribution</li></ul></div></div>
  if(module==='upgrade') return <div className="module-card-stack">{selectedCard}<div className="module-card"><OptimiserCard/></div><div className="module-card"><div className="eyebrow">INFRASTRUCTURE PRIORITISATION</div><h3>Assets needing attention</h3><p>Ranked condition indicators are available for supported asset classes. Review the health model and its assumptions before making investment decisions.</p><InfraHealth/></div></div>
  if(module==='infrastructure') return <div className="module-card-stack">{selectedCard}<div className="module-card"><div className="eyebrow">ASSET CONDITION</div><h3>Infrastructure health</h3><p>Modelled condition indicators for mapped drains, roads and transformers. These scores are not direct field inspections.</p><InfraHealth/></div><div className="module-card"><div className="eyebrow">LAYER INVENTORY</div><h3>Mapped infrastructure</h3>{layers.filter(l=>['buildings','roads','drains','transformers','substations','facilities','waterways'].includes(l.id)).map(l=><div className="catalogue-row" key={l.id}><span><b>{l.title}</b><small>{visible[l.id]?'Visible on map':'Hidden on map'}</small></span><strong>{(l.count_in_pilot??l.count??0).toLocaleString()}</strong></div>)}</div></div>
  if(module==='warning') return <div className="module-card-stack"><div className="module-card"><ForecastOutlook/></div><div className="module-card"><div className="eyebrow">EARLY WARNING CONTEXT</div><h3>Weather and risk indicators</h3><p>Review forecast conditions alongside scenario-based infrastructure analysis. Alerts are only as reliable as their underlying data and configured thresholds.</p><Suspense fallback={<p className="muted">Loading forecast…</p>}><WeatherPanel/></Suspense></div><div className="module-card"><div className="eyebrow">SCENARIO ANALYSIS</div><h3>Test rainfall and drainage stress</h3><p>Use the flood simulation workspace to test defined rainfall presets. Scenario outputs are estimates, not forecasts.</p><button className="action-button" onClick={()=>onNavigate('flood')}>Open flood simulation</button></div></div>
  return <div className="module-card-stack"><div className="module-card"><div className="eyebrow">{MODULES.find(m=>m.id===module)?.group}</div><h3>{MODULES.find(m=>m.id===module)?.label}</h3><p>{MODULES.find(m=>m.id===module)?.description}</p><div className="metric-grid"><div className="metric-card"><small>Selected area</small><b>{region?`${Number(region.attrs.area_km2??0).toFixed(2)} km²`:'—'}</b></div><div className="metric-card"><small>Available layers</small><b>{layers.length}</b></div><div className="metric-card"><small>Mapped features</small><b>{layers.reduce((n,l)=>n+(l.count_in_pilot??l.count??0),0).toLocaleString()}</b></div><div className="metric-card"><small>Visible layers</small><b>{layers.filter(l=>visible[l.id]).length}</b></div></div><p className="muted">Use the map and layer controls to explore the currently loaded pilot data. Values are drawn from the project API and snapshots.</p></div><div className="module-card"><div className="eyebrow">DATA COVERAGE</div><h3>Available layers</h3>{layers.map(l=><div className="catalogue-row" key={l.id}><span><b>{l.title}</b><small>{l.group} · {Object.keys(l.data_status??{}).join(', ')||'status not supplied'}</small></span><strong>{(l.count_in_pilot??l.count??0).toLocaleString()}</strong></div>)}</div></div>
}

function ModuleContent({module,onNavigate}:{module:ModuleId;onNavigate:(id:ModuleId)=>void}) {
  if(module==='command'||module==='twin') return <div className="right-content"><div className="panel-heading"><span className="eyebrow">{module==='command'?'AREA OVERVIEW':'DIGITAL TWIN'}</span><h2>{module==='command'?'Contextual intelligence':'Map inspection'}</h2></div><AssetInspector/><div className="module-card"><div className="eyebrow">MAP LAYERS</div><LayerManager/><div className="legend-wrap"><Legend/></div></div></div>
  if(module==='graph') return <div className="right-content"><RelationshipExplorer/></div>
  if(module==='flood') return <div className="right-content"><DisasterLab/></div>
  if(module==='development') return <div className="right-content"><DevelopmentPanel/></div>
  if(module==='access') return <div className="right-content"><AccessPanel/></div>
  if(module==='weather'||module==='air'||module==='water'||module==='land') return <div className="right-content"><EnvironmentPanel sub={module} onSub={onNavigate}/></div>
  return <DataSummary module={module} onNavigate={onNavigate}/>
}

export default function App() {
  const api=useApiHealth()
  const [authed,setAuthed]=useState(()=>Boolean(currentToken()))
  const [active,setActive]=useState<ModuleId>(initialModule)
  const [theme,setTheme]=useState<Theme>(()=>{try{return localStorage.getItem('hyperborea.theme')==='light'?'light':'dark'}catch{return'dark'}})
  useEffect(()=>{const onAuth=()=>setAuthed(false);window.addEventListener(AUTH_EVENT,onAuth);return()=>window.removeEventListener(AUTH_EVENT,onAuth)},[])
  // Native controls, scrollbars and the page background behind the shell follow the theme too.
  useEffect(()=>{document.documentElement.dataset.theme=theme;document.documentElement.style.colorScheme=theme},[theme])
  // Panels and deep links change the store's tab (e.g. "explore relationships", ?tab=, ?scenario=): follow it.
  useEffect(()=>useApp.subscribe((s,prev)=>{
    if(s.rightTab===prev.rightTab)return
    const target=TAB_MODULE[s.rightTab]
    if(target)setActive(cur=>MODULE_TAB[cur]===s.rightTab?cur:target)
    else setActive(cur=>ENV_MODULES.includes(cur)?'command':cur) // asset picked while in an environment view → inspector
  }),[])
  const panelBody=useRef<HTMLDivElement>(null)
  useEffect(()=>{panelBody.current?.scrollTo(0,0)},[active]) // each module starts at the top of its panel
  const live=api.kind==='ok'&&api.health.status!=='snapshot'
  const snapshot=api.kind==='ok'&&!live
  // P20: login only when the API says auth is required (default off); offline snapshot never needs it (P04)
  const needsLogin=live&&api.kind==='ok'&&api.health.auth_required===true
  const ready=api.kind==='ok'&&(authed||!needsLogin)
  useBootstrap(ready);useWeatherPoll(ready)
  // All hooks stay above the login early-return: calling them after it changed the hook order on sign-in/out.
  const region=useApp(s=>s.region)
  const layers=useApp(s=>s.layers)
  const visibleLayers=useApp(s=>s.visible)
  const weather=useApp(s=>s.weather)
  const imagery=useApp(s=>s.imagery)
  const view=useApp(s=>s.view)
  const setThemeMode=(next:Theme)=>{setTheme(next);try{localStorage.setItem('hyperborea.theme',next)}catch{/* storage unavailable */}}
  const selectModule=(id:ModuleId)=>{
    setActive(id)
    useApp.getState().setRightTab(MODULE_TAB[id]??'inspector')
    if(id==='twin')useApp.getState().setView('3d')
    if(id==='command')useApp.getState().setView('2d')
  }
  const grouped=MODULES.reduce((acc,m)=>{(acc[m.group]??=[]).push(m);return acc},{} as Record<string,typeof MODULES>)
  if(needsLogin&&!authed)return <div className="app-shell" data-theme={theme}><Login onDone={()=>setAuthed(true)}/></div>
  const module=MODULES.find(m=>m.id===active)!
  const count=layers.reduce((n,l)=>n+(l.count_in_pilot??l.count??0),0)
  const conn=api.kind==='offline'?{cls:'bad',label:'API offline'}:snapshot?{cls:'warn',label:'Offline snapshot'}:live?{cls:'good',label:'Connected'}:{cls:'pending',label:'Connecting…'}
  return <div className="app-shell" data-theme={theme}>
    <header className="topbar">
      <div className="brand-lockup"><div className="brand-mark"><img src="/hyperborea-mark.png" alt="" /></div><div><div className="brand-name">HYPERBOREA</div><div className="brand-subtitle">URBAN INTELLIGENCE PLATFORM</div></div></div>
      <div className="topbar-status"><ApiBadge state={api}/><span className="topbar-area">{region?`${region.name} · ${Number(region.attrs.area_km2??0).toFixed(2)} km²`:'Pilot area'}</span></div>
      <div className="topbar-actions"><RegionSwitcher/><button className="icon-button" title={theme==='dark'?'Switch to light theme':'Switch to dark theme'} aria-label={theme==='dark'?'Switch to light theme':'Switch to dark theme'} onClick={()=>setThemeMode(theme==='dark'?'light':'dark')}><Svg size={15}>{theme==='dark'?ICON_PATHS.weather:<path d="M20 14.500A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.500z"/>}</Svg></button>{needsLogin&&authed&&<button className="signout" onClick={()=>{clearSession();setAuthed(false)}}>Sign out</button>}</div>
    </header>
    {ready&&<WarningBanner/>}
    <div className="app-body">
      <aside className="sidebar">
        <div className="sidebar-label">PLATFORM</div>
        {Object.entries(grouped).map(([group,items])=><div className="nav-group" key={group}><div className="nav-group-label">{group}</div>{items.map(m=><button key={m.id} title={m.label} aria-current={active===m.id?'page':undefined} className={`nav-item ${active===m.id?'active':''}`} onClick={()=>selectModule(m.id)}><ModuleIcon id={m.id}/><span>{m.label}</span></button>)}</div>)}
        <div className="sidebar-bottom"><div className="sidebar-note">PILOT WORKSPACE</div><strong>{region?.name??'Loading region…'}</strong><small>{count.toLocaleString()} mapped features</small></div>
      </aside>
      <main className="main-workspace">
        <div className="workspace-heading"><div><div className="breadcrumb">HYPERBOREA <span>/</span> {module.group}</div><h1>{module.label}</h1><p>{module.description}</p></div><div className="workspace-meta"><span className={`live-dot live-${conn.cls}`}/> {conn.label}<span className="meta-divider"/>{weather?.current?`${Math.round(weather.current.temperature_2m)}°C · ${weather.current.condition}`:'Weather unavailable'}</div></div>
        <div className="kpi-strip"><div className="kpi-card"><span>AREA</span><b>{region?`${Number(region.attrs.area_km2??0).toFixed(2)} km²`:'—'}</b><small>Selected pilot</small></div><div className="kpi-card"><span>MAPPED FEATURES</span><b>{count.toLocaleString()}</b><small>Current pilot coverage</small></div><div className="kpi-card"><span>DATA LAYERS</span><b>{layers.length}</b><small>Available in workspace</small></div><div className="kpi-card"><span>VISIBLE LAYERS</span><b>{layers.filter(l=>visibleLayers[l.id]).length}</b><small>Currently on map</small></div></div>
        <div className={`workspace-grid ${active==='command'?'command-grid':''}`}>
          <section className="map-panel"><div className="map-panel-head"><div><span className="eyebrow">GEOSPATIAL WORKSPACE</span><strong>{region?.name??'Pilot map'}</strong></div><div className="map-controls"><button onClick={()=>useApp.getState().setImagery('eox')} aria-pressed={imagery==='eox'} className={imagery==='eox'?'selected':''}>Satellite</button><button onClick={()=>useApp.getState().setImagery('osm')} aria-pressed={imagery==='osm'} className={imagery==='osm'?'selected':''}>Street</button><span className="map-controls-gap"/><button onClick={()=>useApp.getState().setView('2d')} aria-pressed={view==='2d'} className={view==='2d'?'selected':''}>2D</button><button onClick={()=>useApp.getState().setView('3d')} aria-pressed={view==='3d'} className={view==='3d'?'selected':''}>3D</button></div></div><div className="map-canvas">{api.kind==='offline'&&!region?<div className="map-empty">API offline — start the backend to load the pilot map.</div>:<MapView/>}</div><div className="map-attribution">© OpenStreetMap contributors · Sentinel-2 cloudless by EOX · Geographic data and model assumptions are shown in layer provenance.</div></section>
          <aside className="insight-panel"><div className="insight-panel-head"><div><span className="eyebrow">MODULE WORKSPACE</span><h2>{module.short}</h2></div><span className="module-index">{String(MODULES.findIndex(m=>m.id===active)+1).padStart(2,'0')} / {MODULES.length}</span></div><div className="insight-panel-body" ref={panelBody}><Suspense fallback={<p className="muted">Loading module…</p>}><ModuleContent module={active} onNavigate={selectModule}/></Suspense></div></aside>
        </div>
      </main>
    </div>
    <footer className="app-footer"><span><ApiBadge state={api}/></span><span>{api.kind==='ok'?`API v${api.health.version}`:'Local workspace'}</span><span>{api.kind==='ok'?`Data ${api.health.data_timestamp?.slice(0,16).replace('T',' ')??'timestamp unavailable'} UTC`:'Waiting for data'}</span><span className="footer-right">© OpenStreetMap contributors · EOX Sentinel-2 · Open-Meteo · ESA WorldCover{REGION==='london_stratford'&&' · Terrain © Environment Agency 2022 (OGL v3)'}</span></footer>
  </div>
}
