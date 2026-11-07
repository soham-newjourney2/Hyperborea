// API client. Base URL from VITE_API_URL (planning §8).
// Offline fallback (P04): any request that fails or takes > 5 s is served from public/snapshots/*.json
// (made by scripts/make_snapshots.py) and the app shows an "Offline snapshot" badge.
export const API_URL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api'
const SNAPSHOT_BASE = `${import.meta.env.BASE_URL ?? '/'}snapshots/`
const TIMEOUT_MS = 5000
const LAYER_TIMEOUT_MS = 20000 // big GeoJSON from a cold-started Space can legitimately take > 5 s

export function apiUrl(path: string, base: string = API_URL): string {
  return `${base.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`
}

const SNAPSHOT_PATHS = new Set(['weather/current', 'weather/forecast', 'climate/summary', 'scenarios/presets',
  'environment/air', 'environment/water', 'environment/landcover', 'access/summary'])

/** API path → snapshot file name (must match scripts/make_snapshots.py); null = not snapshotted. */
export function snapshotName(path: string): string | null {
  const [p, q = ''] = path.replace(/^\/+/, '').split('?')
  if (p === 'health' || p === 'region' || p === 'layers') return `${p}.json`
  if (SNAPSHOT_PATHS.has(p)) return `${p.replace('/', '_')}.json`
  const m = /^layers\/([^/]+)$/.exec(p)
  if (m) return `layer_${decodeURIComponent(m[1])}${/(^|&)in_pilot=true(&|$)/.test(q) ? '_pilot' : ''}.json`
  return null
}

export interface Health {
  status: string // "ok" live, "snapshot" when served from the offline fallback
  version: string
  data_timestamp: string | null
  snapshot_at?: string
}

async function fetchWithTimeout(url: string, signal: AbortSignal | undefined, ms: number): Promise<Response> {
  return fetchWithTimeoutInit(url, {}, signal, ms)
}

async function fetchWithTimeoutInit(url: string, init: RequestInit, signal: AbortSignal | undefined, ms: number): Promise<Response> {
  const ctrl = new AbortController()
  const onAbort = () => ctrl.abort()
  signal?.addEventListener('abort', onAbort)
  const timer = setTimeout(() => ctrl.abort(), ms)
  try {
    return await fetch(url, { ...init, signal: ctrl.signal })
  } finally {
    clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
}

async function getJson<T>(path: string, signal?: AbortSignal, timeoutMs = TIMEOUT_MS): Promise<T> {
  try {
    const r = await fetchWithTimeout(apiUrl(path), signal, timeoutMs)
    if (!r.ok) throw new Error(`${path} ${r.status}`)
    return (await r.json()) as T
  } catch (err) {
    if (signal?.aborted) throw err // caller cancelled — not an outage
    const name = snapshotName(path)
    if (!name) throw err
    const r = await fetch(SNAPSHOT_BASE + name, { signal })
    // Missing snapshot: dev servers / SPA hosts answer with index.html — treat as "no snapshot".
    if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) throw err
    return (await r.json()) as T
  }
}

export const getHealth = (signal?: AbortSignal) => getJson<Health>('health', signal)

export interface Region {
  asset_id: string
  name: string
  data_status: string
  source_id: string
  attrs: Record<string, unknown>
  centroid: [number, number]
  bbox: [number, number, number, number]
  boundary: GeoJSON
}

export interface LayerMeta {
  id: string
  title: string
  group: string
  default_visible: boolean
  geometry_type: string[]
  count: number
  count_in_pilot: number
  data_status: Record<string, number>
  source_ids: string[]
}

export interface FeatureProps {
  asset_id: string
  asset_type: string
  name?: string | null
  data_status: string
  source_id: string
  observed_at?: string | null
  ingested_at: string
  confidence?: string | number | null
  assumptions?: string
  attrs: Record<string, unknown>
  in_pilot: boolean
}

export interface GeoJSON {
  type: 'FeatureCollection'
  features: { type: 'Feature'; geometry: unknown; properties: FeatureProps }[]
}

export interface Relationship {
  relationship_id: string
  type: string
  rule: string
  weight: number | null
  unit: string
  data_status: string
  confidence: string
  assumptions: string
  direction: 'out' | 'in'
  label: string
  other_id: string
  other_kind: string
  other_type: string
  other_name: string | null
}

export interface Asset extends FeatureProps {
  layer: string
  position: [number, number]
  relationships: Relationship[]
}

export const getRegion = (signal?: AbortSignal) => getJson<Region>('region', signal)
export const getLayers = (signal?: AbortSignal) => getJson<LayerMeta[]>('layers', signal)
// Layers seen this session — lets asset detail work offline (built from the feature's own props).
const layerCache = new Map<string, GeoJSON>()

export async function getLayer(id: string, inPilot: boolean, signal?: AbortSignal): Promise<GeoJSON> {
  const gj = await getJson<GeoJSON>(`layers/${encodeURIComponent(id)}${inPilot ? '?in_pilot=true' : ''}`, signal, LAYER_TIMEOUT_MS)
  layerCache.set(id, gj)
  return gj
}

function roughCenter(geometry: unknown): [number, number] {
  let sx = 0
  let sy = 0
  let n = 0
  const walk = (c: unknown): void => {
    if (Array.isArray(c) && typeof c[0] === 'number') {
      sx += c[0] as number
      sy += c[1] as number
      n++
    } else if (Array.isArray(c)) c.forEach(walk)
  }
  walk((geometry as { coordinates?: unknown })?.coordinates)
  return n ? [sx / n, sy / n] : [0, 0]
}

export function assetFromCache(id: string): Asset | null {
  for (const [layer, gj] of layerCache) {
    const f = gj.features.find((x) => x.properties.asset_id === id)
    if (f) return { ...f.properties, layer, position: roughCenter(f.geometry), relationships: [] }
  }
  return null
}

export async function getAsset(id: string, signal?: AbortSignal): Promise<Asset> {
  try {
    return await getJson<Asset>(`assets/${encodeURIComponent(id)}`, signal)
  } catch (err) {
    const cached = signal?.aborted ? null : assetFromCache(id)
    if (cached) return cached
    throw err
  }
}

// ---- P05 weather + climate -------------------------------------------------------------------
export interface Weather {
  source_id: string
  data_status: string
  attribution: string
  fetched_at: string
  stale: boolean
  origin: 'live' | 'cache' | 'snapshot'
  stale_reason: string | null
  location: { lat: number; lon: number; elevation_m: number | null; timezone: string }
  units: Record<string, string>
  current: {
    time: string
    temperature_2m: number
    relative_humidity_2m: number
    precipitation: number
    rain: number
    wind_speed_10m: number
    weather_code: number
    condition: string
  }
  hourly?: {
    time: string
    precipitation: number
    rain?: number
    temperature_2m?: number
    precipitation_probability?: number | null
  }[]
}

export interface ClimateYear {
  year: number
  total_mm: number
  jjas_mm: number
  max_1day_mm: number
  heavy_days: number
  very_heavy_days: number
  extremely_heavy_days: number
}

export interface Trend {
  slope_per_decade: number
  p_value: number
  unit: string
  significant_5pct: boolean
}

export interface ClimateSummary {
  source_id: string
  data_status: string
  label: string
  grid: { lat: number; lon: number; resolution: string }
  period: { start: string; end: string; full_years: [number, number]; n_years: number }
  thresholds_mm_day: { heavy: number; very_heavy: number; extremely_heavy: number }
  stats: {
    annual_total_mean_mm: number
    jjas_share_pct: number
    max_1day: { mm: number; date: string }
    annual_max_1day_median_mm: number
    heavy_days_per_year_mean: number
  }
  trends: Record<'annual_total' | 'annual_max_1day' | 'heavy_days', Trend>
  notes: string[]
  years: ClimateYear[]
}

export interface Preset {
  id: string
  title: string
  rain_mm_h: number
  duration_h: number
  total_mm: number
  description: string
  source: string
  data_status: string
  source_id: string
}

export const getWeatherForecast = (signal?: AbortSignal) => getJson<Weather>('weather/forecast', signal)
export const getClimateSummary = (signal?: AbortSignal) => getJson<ClimateSummary>('climate/summary', signal)
export const getPresets = (signal?: AbortSignal) => getJson<Preset[]>('scenarios/presets', signal)

// ---- P07 relationship graph --------------------------------------------------------------------
export interface GraphNode {
  id: string
  kind: string
  layer: string
  asset_type: string
  name: string | null
  data_status: string
  source_id: string
  lon: number
  lat: number
  hop?: number
}
export interface GraphEdge {
  source: string
  target: string
  relationship_id: string
  type: string
  rule: string
  weight: number | null
  unit: string
  data_status: string
  confidence: string
}
export interface Neighbourhood {
  center: string
  depth: number
  truncated: boolean
  nodes: GraphNode[]
  edges: GraphEdge[]
}
export interface EdgeTypeInfo {
  label: string
  description: string
  source: string[]
  target: string[]
  physical: boolean
  active: boolean
}
export interface GraphSummary {
  nodes: number
  edges: number
  node_kinds: Record<string, number>
  edge_types: Record<string, number>
  edge_data_status: Record<string, number>
  components: number
  isolated_nodes: number
  registry: Record<string, EdgeTypeInfo>
}

export const getGraphSummary = (signal?: AbortSignal) => getJson<GraphSummary>('graph/summary', signal)
export const getNeighbours = (id: string, depth: number, types: string[] = [], signal?: AbortSignal) =>
  getJson<Neighbourhood>(
    `graph/neighbors/${encodeURIComponent(id)}?depth=${depth}&max_nodes=200${types.length ? `&types=${types.join(',')}` : ''}`,
    signal,
  )

export interface Trace {
  drain: string
  upstream: string[]
  downstream: string[]
}
export const getTrace = (drainId: string, signal?: AbortSignal) =>
  getJson<Trace>(`graph/trace/${encodeURIComponent(drainId)}`, signal)

// ---- P08 rainfall cascade ------------------------------------------------------------------------
export interface FloodParams {
  preset: string | null
  preset_source_id: string
  rain_mm_h: number
  duration_h: number
  condition_scale: number
}
export interface DrainState {
  q_in: number
  capacity: number
  q_out: number
  overflow_m3s: number
  load_ratio: number
  state: 'ok' | 'near' | 'overloaded'
}
export interface ExplainStep {
  from: string
  edge: string
  to: string
  rule: string
  label: string
  formula: string
  values: Record<string, unknown>
}
export interface Explanation {
  asset_id: string
  kind: string
  state: string
  trigger: string
  path: ExplainStep[]
  risk: { index: number; components: Record<string, number>; weights: Record<string, number>; formula: string; label: string }
  inputs: { name: string; value: unknown; unit: string; source_id: string; data_status: string }[]
  assumptions: string[]
  data_status: string
  confidence: string
  mitigation: string[]
  improve: string[]
  also?: { title: string; path: ExplainStep[] }[]
}
export interface AffectedAsset {
  asset_id: string
  kind: string
  name: string | null
  state: string
  risk: number
  detail: string
}
export interface FloodSummary {
  drains_overloaded: number
  drains_near_capacity: number
  drains_total: number
  catchments_ponded: number
  max_depth_m: number
  total_overflow_m3: number
  roads_impaired: number
  roads_impassable: number
  road_km_impaired: number
  road_km_impassable: number
  buildings_exposed: number
  facilities_access_cut: number
  facilities_access_impaired: number
  facilities_affected: number
  transformers_shutdown?: number
  buildings_power_loss?: number
  facilities_power_loss?: number
  buildings_hospital_slower?: number
  buildings_hospital_isolated?: number
  hospital_mean_delta_min?: number
  hospital_max_delta_min?: number
}
export interface FloodResult {
  result_id: string
  params: FloodParams
  label: string
  data_status: string
  summary: FloodSummary
  layers: {
    drains: Record<string, DrainState>
    roads: Record<string, { depth_m: number; state: 'impaired' | 'impassable'; via: string }>
    catchments: Record<string, { depth_m: number; overflow_m3: number; capped: boolean; drain_id: string }>
    buildings: Record<string, { depth_m: number; via: string }>
    facilities: Record<string, { state: 'access_cut' | 'access_impaired' | 'power_loss'; roads_impassable: string[]; roads_impaired: string[]; power?: string; backup_power?: string }>
    transformers?: Record<string, { depth_m: number; state: 'shutdown'; via: string; buildings: number }>
    buildings_power?: Record<string, string>
  }
  affected: AffectedAsset[]
  explanations: Record<string, Explanation>
  assumptions: string[]
  generated_at: string
  offline?: boolean
}
export interface FloodRequest {
  preset?: string | null
  rain_mm_h?: number
  duration_h?: number
  condition_scale?: number
}

/** POST /scenarios/flood; offline → fixed demo snapshot for plain heavy/extreme presets. */
export async function runFlood(body: FloodRequest, signal?: AbortSignal): Promise<FloodResult> {
  try {
    const r = await fetchWithTimeoutInit(apiUrl('scenarios/flood'), {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }, signal, LAYER_TIMEOUT_MS)
    if (!r.ok) throw new Error(`flood ${r.status}: ${(await r.json().catch(() => ({}))).detail ?? ''}`)
    return (await r.json()) as FloodResult
  } catch (err) {
    if (signal?.aborted) throw err
    const plain = body.rain_mm_h === undefined && body.duration_h === undefined && (body.condition_scale ?? 1) === 1
    if (!plain || !body.preset || !['heavy', 'extreme'].includes(body.preset)) throw err
    const r = await fetch(`${SNAPSHOT_BASE}flood_${body.preset}.json`, { signal })
    if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) throw err
    return { ...((await r.json()) as FloodResult), offline: true }
  }
}

// ---- P09 development assessment ------------------------------------------------------------------
export interface DevCheck {
  dimension: string
  status: 'pass' | 'conditional' | 'fail' | 'insufficient_data'
  value?: number | string
  unit?: string
  detail: string
  threshold?: string
  data_status: string
  source_ids: string[]
  numbers?: Record<string, unknown>
  note?: string
}
export interface DevAssessment {
  assessment_id: string
  label: string
  data_status: string
  params: { site_id: string | null; use: string; floors: number; design_preset: string; upgrades: string[] }
  upgrades_applied: { id: string; label: string }[]
  geometry: { type: 'Polygon'; coordinates: number[][][] }
  derived: Record<string, number>
  checks: DevCheck[]
  verdict: string
  index: { value: number | null; weights: Record<string, number>; scores: Record<string, number | null>; label: string }
  key_dimensions: string[]
  assumptions: string[]
  label_option?: string | null
}
export interface DevRequest {
  site_id?: string | null
  geometry?: { type: 'Polygon'; coordinates: number[][][] } | null
  use: 'residential' | 'commercial'
  floors: number
  upgrades: string[]
  design_preset: string
  label?: string
}
export interface DevCompare {
  options: (DevAssessment & { name: string })[]
  table: Record<string, string>[]
  verdicts: Record<string, string>
  index: Record<string, number | null>
  what_changed: Record<string, string[]>
  label: string
  offline?: boolean
}

async function postJson<T>(path: string, body: unknown, signal?: AbortSignal, timeoutMs = 90000): Promise<T> {
  const r = await fetchWithTimeoutInit(apiUrl(path), {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  }, signal, timeoutMs)
  if (!r.ok) throw new Error(String((await r.json().catch(() => ({}))).detail ?? r.status))
  return (await r.json()) as T
}

export const assessDevelopment = (body: DevRequest, signal?: AbortSignal) =>
  postJson<DevAssessment>('development/assess', body, signal)

/** Compare options; offline → the fixed A/B/C demo snapshot. */
export async function compareDevelopment(options: DevRequest[], signal?: AbortSignal): Promise<DevCompare> {
  try {
    return await postJson<DevCompare>('development/compare', { options }, signal)
  } catch (err) {
    if (signal?.aborted) throw err
    const r = await fetch(`${SNAPSHOT_BASE}dev_compare.json`, { signal })
    if (!r.ok || !(r.headers.get('content-type') ?? '').includes('json')) throw err
    return { ...((await r.json()) as DevCompare), offline: true }
  }
}

// ---- P11 environment ---------------------------------------------------------------------------------
export interface AirQuality {
  source_id: string
  data_status: string
  attribution: string
  fetched_at: string
  stale: boolean
  origin: string
  stale_reason: string | null
  window: { from: string; to: string; hours: number }
  means_ugm3: Record<string, number | null>
  sub_index: Record<string, number | null>
  naqi: number | null
  dominant: string | null
  category: string | null
  color: string | null
  note: string
  hourly: { time: string; pm2_5: number; pm10: number; nitrogen_dioxide: number; ozone: number }[]
}
export interface WaterResponse {
  data_status: string[]
  demo: boolean
  banner: string
  note: string
  points: GeoJSON
}
export interface Landcover {
  worldcover: { source_id: string; data_status: string; year: number; classes: Record<string, { label: string; color: string }>; pilot_shares_pct: Record<string, number> }
  ndvi: { source_id: string; data_status: string; window: string; scenes: { id: string; date: string; cloud_pct: number }[]; pilot_mean: number; note: string }
  per_catchment: Record<string, { built_up_pct: number; green_pct: number; water_pct: number; ndvi_mean?: number }>
  overlays: Record<'worldcover' | 'ndvi', { url: string; bounds: [number, number, number, number] }>
}
export const getAir = (signal?: AbortSignal) => getJson<AirQuality>('environment/air', signal)
export const getWater = (signal?: AbortSignal) => getJson<WaterResponse>('environment/water', signal)
let landcoverPromise: Promise<Landcover> | null = null
/** Cached once per session (overlay bounds + per-catchment shares are static). Shared → never aborted by one caller. */
export function getLandcover(): Promise<Landcover> {
  landcoverPromise ??= getJson<Landcover>('environment/landcover').catch((e) => {
    landcoverPromise = null
    throw e
  })
  return landcoverPromise
}

// ---- P12 accessibility -------------------------------------------------------------------------------
export interface AccessStats { n: number; isolated: number; median_min: number | null; p90_min: number | null; max_min: number | null }
export interface AccessCategory {
  stats?: AccessStats
  baseline?: AccessStats
  scenario?: AccessStats
  newly_isolated?: number
  buildings_slower?: number
  mean_delta_min?: number
  max_delta_min?: number
  minutes: Record<string, number | null>
  delta?: Record<string, number | null>
}
export interface AccessSummary {
  label: string
  data_status: string
  source_id: string
  result_id: string | null
  categories: Record<'hospital' | 'fire' | 'metro', AccessCategory>
  facilities_no_hospital_route?: { asset_id: string; name: string | null; type: string }[]
}
export const getAccessSummary = (resultId?: string, signal?: AbortSignal) =>
  getJson<AccessSummary>(`access/summary${resultId ? `?result_id=${encodeURIComponent(resultId)}` : ''}`, signal, LAYER_TIMEOUT_MS)

// ---- P13 AI quick-scan + model cards -------------------------------------------------------------------
export interface Metrics4 { precision: number; recall: number; f1: number; roc_auc: number }
export interface QuickScan {
  label: string
  data_status: string
  params: { rain_mm_h: number; duration_h: number; condition_scale: number }
  probabilities: Record<string, number>
  expected_overloads: number
  predicted_overloads: number
  drains: number
  inference_ms: number
  held_out: { surrogate: Metrics4; baseline: Metrics4 & { rule: string } }
  vs_engine?: { engine_overloads: number; surrogate_overloads: number; agreement_pct: number; precision: number | null; recall: number | null; f1: number }
}
export interface ModelCard {
  id: string
  title: string
  available: boolean
  card_markdown: string | null
  metrics: Record<string, unknown> | null
}
export const getQuickscan = (rain: number, dur: number, cond: number, compare = false, signal?: AbortSignal) =>
  getJson<QuickScan>(`ml/quickscan?rain_mm_h=${rain}&duration_h=${dur}&condition_scale=${cond}${compare ? '&compare=true' : ''}`, signal)
export const getModels = (signal?: AbortSignal) => getJson<ModelCard[]>('models', signal)

// ---- P14 infrastructure health, explainer, report ------------------------------------------------------
export interface HealthItem {
  asset_id: string
  kind: string
  name: string | null
  health_index: number
  components: Record<string, number>
  weights: Record<string, number>
  simulated_inputs: string[]
  reasons: string[]
  numbers: Record<string, unknown>
}
export interface InfraHealthResponse {
  type: string
  label: string
  formula: string
  weights: Record<string, number>
  simulated_inputs: string[]
  count: number
  items: HealthItem[]
}
export interface ExplainResponse {
  text: string
  mode: 'template' | 'llm'
  grounded: boolean
  model: string | null
  fallback_reason?: string
}
export interface ExplainStatus {
  default_mode: string
  llm: { available: boolean; server: boolean; models: string[]; model: string }
  note: string
}
export interface Report {
  result_id: string
  title: string
  label: string
  data_status: string
  params: FloodParams
  summary: FloodSummary
  narrative: string
  affected: AffectedAsset[]
  affected_total: number
  assumptions: string[]
  simulated_parts: string[]
  limitations: string[]
  attributions: string[]
  generated_at: string
}
export const getInfraHealth = (type: string, top = 10, signal?: AbortSignal) =>
  getJson<InfraHealthResponse>(`infra-health?type=${type}&top=${top}`, signal, LAYER_TIMEOUT_MS)
export const getExplainStatus = (signal?: AbortSignal) => getJson<ExplainStatus>('explain/status', signal)
export const postExplain = (resultId: string, assetId: string | null, mode: 'template' | 'llm') =>
  postJson<ExplainResponse>('explain', { result_id: resultId, asset_id: assetId, mode })
export const getReport = (resultId: string) => getJson<Report>(`report/${encodeURIComponent(resultId)}`)
