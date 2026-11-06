import { create } from 'zustand'
import type { Asset, DevAssessment, FloodResult, LayerMeta, Region, Weather } from './lib/api'

export type Imagery = 'osm' | 'eox'
export type ViewMode = '3d' | '2d'
export type Quality = 'high' | 'standard'
export type RightTab = 'inspector' | 'relations' | 'disaster' | 'develop' | 'weather'
export type LonLat = [number, number]
export type FlyTarget = { lon: number; lat: number; ts: number }

const QUALITY_KEY = 'hyperborea.quality'
function savedQuality(): Quality {
  const q = new URLSearchParams(window.location.search).get('quality') // ?quality=standard|high
  if (q === 'standard' || q === 'high') return q
  try {
    return localStorage.getItem(QUALITY_KEY) === 'standard' ? 'standard' : 'high'
  } catch {
    return 'high'
  }
}

interface AppState {
  region: Region | null
  layers: LayerMeta[]
  visible: Record<string, boolean>
  loading: Record<string, boolean>
  selectedId: string | null
  selected: Asset | null
  imagery: Imagery
  view: ViewMode
  quality: Quality
  rightTab: RightTab
  weather: Weather | null
  neighbourhood: string[]
  flyTarget: FlyTarget | null
  flood: FloodResult | null
  dev: DevAssessment | null
  drawing: boolean
  drawPoints: LonLat[]
  drawn: LonLat[] | null
  setRegion: (r: Region) => void
  setLayers: (l: LayerMeta[]) => void
  toggle: (id: string) => void
  setLoading: (id: string, v: boolean) => void
  select: (id: string | null) => void
  setSelected: (a: Asset | null) => void
  setImagery: (i: Imagery) => void
  setView: (v: ViewMode) => void
  setQuality: (q: Quality) => void
  setRightTab: (t: RightTab) => void
  setWeather: (w: Weather | null) => void
  setNeighbourhood: (ids: string[]) => void
  flyTo: (lon: number, lat: number) => void
  setFlood: (f: FloodResult | null) => void
  setDev: (d: DevAssessment | null) => void
  startDraw: () => void
  addDrawPoint: (p: LonLat) => void
  finishDraw: () => void
  cancelDraw: () => void
}

export const useApp = create<AppState>((set) => ({
  region: null,
  layers: [],
  visible: {},
  loading: {},
  selectedId: null,
  selected: null,
  imagery: 'osm',
  view: '3d',
  quality: savedQuality(),
  rightTab: 'inspector',
  weather: null,
  neighbourhood: [],
  flyTarget: null,
  flood: null,
  dev: null,
  drawing: false,
  drawPoints: [],
  drawn: null,
  setRegion: (region) => set({ region }),
  setLayers: (layers) =>
    set((s) => ({
      layers,
      visible: Object.fromEntries(layers.map((l) => [l.id, s.visible[l.id] ?? l.default_visible])),
    })),
  toggle: (id) => set((s) => ({ visible: { ...s.visible, [id]: !s.visible[id] } })),
  setLoading: (id, v) => set((s) => ({ loading: { ...s.loading, [id]: v } })),
  select: (selectedId) =>
    set((s) => ({
      selectedId,
      selected: null,
      neighbourhood: selectedId ? s.neighbourhood : [],
      rightTab: selectedId && s.rightTab === 'weather' ? 'inspector' : s.rightTab, // keep Relations open while exploring
    })),
  setSelected: (selected) => set({ selected }),
  setImagery: (imagery) => set({ imagery }),
  setView: (view) => set({ view }),
  setQuality: (quality) => {
    try {
      localStorage.setItem(QUALITY_KEY, quality)
    } catch {
      /* private mode: keep in memory only */
    }
    set({ quality })
  },
  setRightTab: (rightTab) => set({ rightTab }),
  setWeather: (weather) => set({ weather }),
  setNeighbourhood: (neighbourhood) => set({ neighbourhood }),
  flyTo: (lon, lat) => set({ flyTarget: { lon, lat, ts: Date.now() } }),
  setDev: (dev) => set({ dev }),
  startDraw: () => set({ drawing: true, drawPoints: [], drawn: null, dev: null }),
  addDrawPoint: (p) => set((s) => ({ drawPoints: [...s.drawPoints, p] })),
  finishDraw: () =>
    set((s) => {
      // a double-click also fires two single clicks: drop near-duplicate consecutive points
      const pts = s.drawPoints.filter((p, i, a) => i === 0 || Math.hypot(p[0] - a[i - 1][0], p[1] - a[i - 1][1]) > 2e-6)
      return pts.length >= 3 ? { drawing: false, drawn: pts, drawPoints: [] } : { drawing: false, drawPoints: [] }
    }),
  cancelDraw: () => set({ drawing: false, drawPoints: [] }),
  setFlood: (flood) =>
    set((s) => ({
      flood,
      // a scenario needs its layers on: drains + catchments (ponding) + roads + buildings
      visible: flood ? { ...s.visible, drains: true, catchments: true, roads: true, buildings: true, transformers: true } : s.visible,
    })),
}))
