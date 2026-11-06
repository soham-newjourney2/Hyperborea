// Map styling shared by MapView + Legend.
export const BUILDING_USE: { key: string; label: string; color: string; match: string[] }[] = [
  { key: 'residential', label: 'Residential', color: '#7c8da6', match: ['residential', 'apartments', 'house', 'detached', 'terrace', 'dormitory', 'hostel'] },
  { key: 'commercial', label: 'Commercial / office', color: '#38bdf8', match: ['commercial', 'office', 'retail', 'hotel', 'supermarket', 'mall'] },
  { key: 'institutional', label: 'Institutional', color: '#2dd4bf', match: ['school', 'college', 'university', 'hospital', 'government', 'public', 'civic', 'clinic', 'fire_station', 'police'] },
  { key: 'industrial', label: 'Industrial / utility', color: '#c084fc', match: ['industrial', 'warehouse', 'service', 'transformer_tower', 'utility'] },
  { key: 'other', label: 'Other / untagged', color: '#94a3b8', match: [] },
]

export function buildingColor(use: unknown, amenity: unknown): string {
  for (const v of [amenity, use]) {
    const hit = BUILDING_USE.find((u) => u.match.includes(String(v)))
    if (hit) return hit.color
  }
  return BUILDING_USE[BUILDING_USE.length - 1].color
}

export const ROAD_CLASS: { label: string; color: string; width: number; match: string[] }[] = [
  { label: 'Arterial (trunk / primary)', color: '#fbbf24', width: 4, match: ['motorway', 'trunk', 'primary', 'motorway_link', 'trunk_link', 'primary_link'] },
  { label: 'Secondary / tertiary', color: '#e2e8f0', width: 2.5, match: ['secondary', 'tertiary', 'secondary_link', 'tertiary_link'] },
  { label: 'Local / service', color: '#64748b', width: 1.5, match: [] },
]

export function roadStyle(highway: unknown) {
  // osmnx may merge edges with several classes: "['primary', 'secondary']"
  const h = String(highway ?? '')
  return ROAD_CLASS.find((c) => c.match.some((m) => h === m || h.includes(`'${m}'`))) ?? ROAD_CLASS[ROAD_CLASS.length - 1]
}

export const FACILITY: Record<string, { label: string; color: string; glyph: string }> = {
  hospital: { label: 'Hospital', color: '#ef4444', glyph: 'H' },
  clinic: { label: 'Clinic', color: '#f87171', glyph: '+' },
  school: { label: 'School', color: '#22c55e', glyph: 'S' },
  college: { label: 'College', color: '#16a34a', glyph: 'C' },
  university: { label: 'University', color: '#15803d', glyph: 'U' },
  fire_station: { label: 'Fire station', color: '#f97316', glyph: 'F' },
  police: { label: 'Police', color: '#6366f1', glyph: 'P' },
  metro_station: { label: 'Metro station', color: '#0ea5e9', glyph: 'M' },
  rail_station: { label: 'Rail station', color: '#0284c7', glyph: 'R' },
}

export const UNITS: Record<string, string> = {
  height_m: 'm', area_m2: 'm²', length_m: 'm', footprint_m2: 'm²', area_km2: 'km²', width: 'm',
  diameter_m: 'm', slope: 'm/m', capacity_m3s: 'm³/s', effective_capacity_m3s: 'm³/s', catchment_m2: 'm²',
  upstream_area_m2: 'm²', elev_up_m: 'm', elev_down_m: 'm', ground_elev_m: 'm', dist_to_outfall_m: 'm',
  distance_to_water_m: 'm', roof_m2: 'm²', road_m2: 'm²', other_m2: 'm²',
  rating_kva: 'kVA', unit_kva: 'kVA', load_kva: 'kVA', loading_pct: '%', plinth_m: 'm', rating_mva: 'MVA',
}

// ---- P06 drainage (sequential, one hue family; dark canvas → brighter = more) --------------------------
function lerpHex(a: string, b: string, t: number): string {
  const p = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16))
  const [x, y] = [p(a), p(b)]
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0')).join('')
}
const ramp = (stops: string[], t: number) => {
  const c = Math.min(Math.max(t, 0), 1) * (stops.length - 1)
  const i = Math.min(Math.floor(c), stops.length - 2)
  return lerpHex(stops[i], stops[i + 1], c - i)
}

export const CAPACITY_STOPS = ['#1e3a8a', '#2563eb', '#38bdf8', '#a5f3fc']
export const CAPACITY_RANGE: [number, number] = [0.1, 5] // m³/s, log scale
/** Effective drain capacity (m³/s) → colour on a log scale. */
export function capacityColor(q: number): string {
  const [lo, hi] = CAPACITY_RANGE
  return ramp(CAPACITY_STOPS, Math.log(Math.max(q, lo) / lo) / Math.log(hi / lo))
}
export const drainWidth = (d: number) => (d >= 1.2 ? 5 : d >= 0.9 ? 3.5 : 2.2)

export const RUNOFF_STOPS = ['#422006', '#a16207', '#fbbf24']
/** Runoff coefficient C (0.40–0.90) → colour. */
export const runoffColor = (c: number) => ramp(RUNOFF_STOPS, (c - 0.4) / 0.5)

export const DRAINAGE_LAYERS = ['drains', 'drain_nodes', 'outfalls', 'catchments']

// ---- P07 graph node kinds: validated dark categorical palette (dataviz slots 1–7, fixed order) + shape -------
export const KIND: Record<string, { label: string; color: string; shape: string }> = {
  building: { label: 'Building', color: '#3987e5', shape: 'round-rectangle' },
  road: { label: 'Road', color: '#d95926', shape: 'rectangle' },
  drain: { label: 'Drain', color: '#199e70', shape: 'diamond' },
  catchment: { label: 'Catchment', color: '#c98500', shape: 'hexagon' },
  facility: { label: 'Facility', color: '#d55181', shape: 'star' },
  outfall: { label: 'Outfall', color: '#008300', shape: 'triangle' },
  manhole: { label: 'Manhole', color: '#9085e9', shape: 'ellipse' },
  // slot 8 (red) shared by the two power kinds; shape tells them apart
  transformer: { label: 'Transformer', color: '#e66767', shape: 'vee' },
  substation: { label: 'Substation', color: '#e66767', shape: 'octagon' },
}

// ---- P08 scenario styling (status colours carry state; legend always pairs them with labels) -----------
export const SCENARIO = {
  drain_ok: '#1e40af',
  drain_near: '#f59e0b',
  drain_overloaded: '#ef4444',
  drain_severe: '#991b1b', // ≥ 2× capacity
  road_impaired: '#f59e0b',
  road_impassable: '#ef4444',
  building_exposed: '#f43f5e',
  facility_impaired: '#f59e0b',
  facility_cut: '#ef4444',
}
export const PONDING_STOPS = ['#1e3a8a', '#2563eb', '#60a5fa']
/** Ponding depth 0.15–1.0 m → blue. */
export const pondingColor = (d: number) => ramp(PONDING_STOPS, (d - 0.15) / 0.85)

// ---- P10 electrical (simulated) --------------------------------------------------------------------
export const POWER_LAYERS = ['substations', 'transformers', 'feeders']
export const LOADING_STOPS: [number, string, string][] = [
  [60, '#22c55e', '< 60 % loading'],
  [80, '#f59e0b', '60–80 %'],
  [Infinity, '#ef4444', '> 80 %'],
]
export const loadingColor = (pct: number) => LOADING_STOPS.find(([lim]) => pct < lim)![1]
export const FEEDER_COLOR = '#facc15'
export const SCENARIO_POWER = { transformer_shutdown: '#ef4444', building_no_power: '#1e293b' }
