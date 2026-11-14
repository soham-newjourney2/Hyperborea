import { useEffect, useRef } from 'react'
import {
  Cartesian3,
  Color,
  ColorMaterialProperty,
  ConstantProperty,
  Credit,
  EllipsoidTerrainProvider,
  Entity,
  GeoJsonDataSource,
  HorizontalOrigin,
  ImageryLayer,
  BillboardGraphics,
  Cartographic,
  JulianDate,
  Math as CesiumMath,
  OpenStreetMapImageryProvider,
  PointGraphics,
  PolylineArrowMaterialProperty,
  PolylineDashMaterialProperty,
  PolylineGraphics,
  Rectangle,
  SceneMode,
  SceneTransforms,
  SingleTileImageryProvider,
  ScreenSpaceEventHandler,
  ScreenSpaceEventType,
  ShadowMode,
  UrlTemplateImageryProvider,
  VerticalOrigin,
  Viewer,
  defined,
  type MaterialProperty,
} from 'cesium'
import 'cesium/Build/Cesium/Widgets/widgets.css'
import { getAsset, getLandcover, getLayer, type Asset, type FloodResult, type Region } from '../lib/api'
import { statusStyle } from '../lib/provenance'
import { DRAINAGE_LAYERS, FACILITY, FEEDER_COLOR, POWER_LAYERS, SCENARIO, SCENARIO_POWER, buildingColor, capacityColor, drainWidth,
  loadingColor, pondingColor, probColor, roadStyle, runoffColor } from '../lib/styles'
import { useApp, type Quality } from '../store'
import InfoTag from './InfoTag'

// Fixed sun: 11:00 IST on the data date → consistent, readable facade shading (not a time-of-day sim).
const NOW = JulianDate.fromIso8601('2026-11-06T05:30:00Z')
const css = (c: string, a = 1) => Color.fromCssColorString(c).withAlpha(a)
const HIGHLIGHT = css('#facc15')
// Facilities include the 2 km buffer (hospitals outside the pilot matter); everything else pilot-only.
const FULL_EXTENT = new Set(['facilities', 'boundary', 'drains', 'drain_nodes', 'outfalls', 'catchments', 'sites',
  'substations', 'transformers', 'feeders', 'water_quality', 'cv_water', 'sar_flood'])
const DRAIN_LIFT_M = 1.5 // above road polylines (avoid z-fighting)
const EOX_URL = 'https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2020_3857/default/g/{z}/{y}/{x}.jpg'

function prop(e: Entity, key: string): unknown {
  return e.properties?.[key]?.getValue(NOW)
}

const icons = new Map<string, HTMLCanvasElement>()

// Facility icon: filled circle + white glyph, drawn once per type (no external assets).
function icon(color: string, glyph: string): HTMLCanvasElement {
  const key = color + glyph
  let c = icons.get(key)
  if (c) return c
  c = document.createElement('canvas')
  c.width = c.height = 44
  const g = c.getContext('2d')!
  g.beginPath()
  g.arc(22, 22, 19, 0, Math.PI * 2)
  g.fillStyle = color
  g.fill()
  g.lineWidth = 3
  g.strokeStyle = 'rgba(2,6,23,0.9)'
  g.stroke()
  g.fillStyle = '#fff'
  g.font = 'bold 22px system-ui, sans-serif'
  g.textAlign = 'center'
  g.textBaseline = 'middle'
  g.fillText(glyph, 22, 23)
  icons.set(key, c)
  return c
}

function asPoint(e: Entity, color: string, size: number, glyph?: string) {
  e.billboard = undefined
  if (glyph) {
    e.billboard = new BillboardGraphics({
      image: icon(color, glyph),
      width: size,
      height: size,
      horizontalOrigin: HorizontalOrigin.CENTER,
      verticalOrigin: VerticalOrigin.CENTER,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
    })
    return
  }
  e.point = new PointGraphics({
    pixelSize: size,
    color: css(color),
    outlineColor: Color.BLACK.withAlpha(0.8),
    outlineWidth: 1.5,
    disableDepthTestDistance: Number.POSITIVE_INFINITY,
  })
}

function line(e: Entity, color: string, width: number) {
  if (!e.polyline) return
  e.polyline.width = new ConstantProperty(width)
  e.polyline.material =
    prop(e, 'data_status') === 'simulated'
      ? new PolylineDashMaterialProperty({ color: css(color), dashLength: 12 })
      : new ColorMaterialProperty(css(color))
}

function fill(e: Entity, color: string, alpha: number) {
  if (!e.polygon) return
  e.polygon.material = new ColorMaterialProperty(css(color, alpha))
  e.polygon.outline = new ConstantProperty(false)
}

function lift(positions: Cartesian3[], h: number): Cartesian3[] {
  return positions.map((p) => {
    const c = Cartographic.fromCartesian(p)
    return Cartesian3.fromRadians(c.longitude, c.latitude, h)
  })
}

// Flow arrow: short arrow polyline around the drain midpoint, pointing downstream (geometry is upstream → downstream).
function flowArrow(ds: GeoJsonDataSource, e: Entity, pos: Cartesian3[], color: string) {
  if (pos.length < 2) return
  const seg: number[] = [0]
  for (let i = 1; i < pos.length; i++) seg.push(seg[i - 1] + Cartesian3.distance(pos[i - 1], pos[i]))
  const total = seg[seg.length - 1]
  if (total < 40) return
  const at = (d: number) => {
    const i = Math.max(1, seg.findIndex((s) => s >= d))
    const t = (d - seg[i - 1]) / Math.max(seg[i] - seg[i - 1], 1e-6)
    return Cartesian3.lerp(pos[i - 1], pos[i], t, new Cartesian3())
  }
  const half = Math.min(18, total * 0.2)
  ds.entities.add({
    polyline: {
      positions: lift([at(total / 2 - half), at(total / 2 + half)], DRAIN_LIFT_M + 0.3),
      width: 11,
      material: new PolylineArrowMaterialProperty(css(color)),
    },
    properties: { asset_id: prop(e, 'asset_id'), data_status: 'simulated' },
  })
}

function styleLayer(id: string, ds: GeoJsonDataSource) {
  for (const e of [...ds.entities.values]) {
    const attrs = (prop(e, 'attrs') ?? {}) as Record<string, unknown>
    switch (id) {
      case 'buildings': {
        if (!e.polygon) break
        const assumed = attrs.height_status === 'assumed'
        const h = Number(attrs.height_m) || 9
        // Taller → slightly lighter, so skyline reads at a glance; assumed heights stay translucent.
        const base = Color.fromCssColorString(buildingColor(attrs.use, attrs.amenity))
        const tint = Color.lerp(base, Color.WHITE, Math.min(h / 60, 1) * 0.3, new Color())
        e.polygon.material = new ColorMaterialProperty(tint.withAlpha(assumed ? 0.8 : 1))
        e.polygon.height = new ConstantProperty(0)
        e.polygon.extrudedHeight = new ConstantProperty(h)
        e.polygon.outline = new ConstantProperty(true)
        e.polygon.outlineColor = new ConstantProperty(Color.fromCssColorString('#020617').withAlpha(0.45))
        e.polygon.shadows = new ConstantProperty(ShadowMode.ENABLED)
        break
      }
      case 'roads': {
        const s = roadStyle(attrs.highway)
        line(e, s.color, s.width)
        break
      }
      case 'facilities': {
        const f = FACILITY[String(prop(e, 'asset_type'))]
        asPoint(e, f?.color ?? '#94a3b8', 22, f?.glyph ?? '?')
        break
      }
      case 'boundary': {
        const c = statusStyle('curated').color
        fill(e, c, 0.06)
        const h = e.polygon?.hierarchy?.getValue(NOW) as { positions: Cartesian3[] } | undefined
        if (h)
          e.polyline = new PolylineGraphics({
            positions: [...h.positions, h.positions[0]],
            width: 3,
            material: css(c),
            clampToGround: true,
          })
        break
      }
      case 'drains': {
        if (!e.polyline) break
        const q = Number(attrs.effective_capacity_m3s) || 0
        const color = capacityColor(q)
        line(e, color, drainWidth(Number(attrs.diameter_m) || 0.6)) // dashed: simulated
        const pos = lift(e.polyline.positions?.getValue(NOW) ?? [], DRAIN_LIFT_M)
        e.polyline.positions = new ConstantProperty(pos)
        flowArrow(ds, e, pos, color)
        break
      }
      case 'outfalls':
        asPoint(e, '#22d3ee', 24, 'O')
        break
      case 'drain_nodes':
        if (e.billboard) asPoint(e, attrs.is_outfall ? '#22d3ee' : '#64748b', 5)
        break
      case 'catchments':
        if (e.polygon) {
          e.polygon.material = new ColorMaterialProperty(css(runoffColor(Number(attrs.runoff_c) || 0.4), 0.38))
          e.polygon.outline = new ConstantProperty(true)
          e.polygon.outlineColor = new ConstantProperty(css('#0f172a', 0.6))
          e.polygon.height = new ConstantProperty(0.2)
        }
        break
      case 'cv_water':
        fill(e, '#22d3ee', 0.55)
        if (e.polygon) {
          e.polygon.outline = new ConstantProperty(true)
          e.polygon.outlineColor = new ConstantProperty(css('#67e8f9'))
          e.polygon.height = new ConstantProperty(0.4)
        }
        break
      case 'sar_flood': // P22: radar-observed flood (violet = open water, lighter = urban indicator)
        fill(e, String(attrs.class ?? '').startsWith('open') ? '#7c3aed' : '#a78bfa', 0.5)
        if (e.polygon) e.polygon.height = new ConstantProperty(0.6)
        break
      case 'water_quality':
        asPoint(e, '#38bdf8', 20, 'W')
        break
      case 'transformers':
        asPoint(e, loadingColor(Number(attrs.loading_pct) || 0), attrs.kind === 'distribution' ? 16 : 20, 'T')
        break
      case 'substations':
        asPoint(e, '#e66767', 28, 'S')
        break
      case 'feeders':
        if (e.polyline) {
          e.polyline.width = new ConstantProperty(2)
          e.polyline.material = new PolylineDashMaterialProperty({ color: css(FEEDER_COLOR, 0.85), dashLength: 16 })
          e.polyline.positions = new ConstantProperty(lift(e.polyline.positions?.getValue(NOW) ?? [], 6))
        }
        break
      case 'sites': {
        fill(e, '#a855f7', 0.28)
        const h = e.polygon?.hierarchy?.getValue(NOW) as { positions: Cartesian3[] } | undefined
        if (h)
          e.polyline = new PolylineGraphics({
            positions: [...h.positions, h.positions[0]],
            width: 3,
            material: new PolylineDashMaterialProperty({ color: css('#c084fc'), dashLength: 10 }),
            clampToGround: true,
          })
        break
      }
      case 'waterways':
        fill(e, '#38bdf8', 0.45)
        line(e, '#38bdf8', 2.5)
        if (e.billboard) asPoint(e, '#38bdf8', 6)
        break
      case 'osm_power':
        fill(e, '#facc15', 0.3)
        line(e, '#facc15', 2)
        if (e.billboard) asPoint(e, '#facc15', 7)
        break
      default:
        fill(e, '#a3e635', 0.22)
        line(e, '#a3e635', 1.5)
        if (e.billboard) asPoint(e, '#a3e635', 6)
    }
  }
}

type Mode = 'none' | 'neighbour' | 'selected'
/** Everything the highlight/scenario systems may change on an entity. */
type Look = { polyMat?: MaterialProperty; lineMat?: MaterialProperty; billColor?: unknown; scale?: unknown; outline?: unknown }
type Looks = { originals: Map<Entity, Look>; scenario: Map<Entity, Look>; painted: Map<Entity, Mode> }
const NEIGHBOUR = css('#22d3ee')

function capture(e: Entity, L: Looks) {
  if (!L.originals.has(e))
    L.originals.set(e, {
      polyMat: e.polygon?.material,
      lineMat: e.polyline?.material,
      billColor: e.billboard?.color,
      scale: e.billboard?.scale,
      outline: e.point?.outlineColor,
    })
}

function applyLook(e: Entity, look: Look) {
  if (e.polygon && look.polyMat) e.polygon.material = look.polyMat
  if (e.polyline && look.lineMat) e.polyline.material = look.lineMat
  if (e.billboard) {
    e.billboard.color = (look.billColor ?? new ConstantProperty(Color.WHITE)) as never
    e.billboard.scale = (look.scale ?? new ConstantProperty(1)) as never
  }
  if (e.point && look.outline) e.point.outlineColor = look.outline as never
}

/** Base = original look overridden by the active scenario look; highlights go on top of the base. */
function paint(e: Entity, mode: Mode, L: Looks) {
  capture(e, L)
  const base = { ...L.originals.get(e), ...L.scenario.get(e) }
  if (mode === 'none') return applyLook(e, base)
  const c = mode === 'selected' ? HIGHLIGHT : NEIGHBOUR
  applyLook(e, {
    ...base,
    polyMat: new ColorMaterialProperty(c.withAlpha(0.9)),
    lineMat: new ColorMaterialProperty(c),
    scale: new ConstantProperty(mode === 'selected' ? 1.6 : 1.3),
    outline: new ConstantProperty(c),
  })
}

/** Selected asset → yellow, its relationship neighbourhood → cyan, everything previously painted → base. */
function repaint(index: Map<string, Entity>, L: Looks, selectedId: string | null, neighbourhood: string[], force = false) {
  const want = new Map<Entity, Mode>()
  for (const id of neighbourhood) {
    const e = index.get(id)
    if (e) want.set(e, 'neighbour')
  }
  const sel = selectedId ? index.get(selectedId) : undefined
  if (sel) want.set(sel, 'selected')
  for (const e of L.painted.keys()) if (!want.has(e)) paint(e, 'none', L)
  for (const [e, m] of want) if (force || L.painted.get(e) !== m) paint(e, m, L)
  L.painted.clear()
  want.forEach((m, e) => L.painted.set(e, m))
}

/** Scenario recolouring (P08): drains by load, roads by passability, catchments by ponding, exposed assets. */
function applyScenario(index: Map<string, Entity>, L: Looks, flood: FloodResult | null,
  access: Record<string, string> | null = null, quick: Record<string, number> | null = null) {
  const next = new Map<Entity, Look>()
  if (flood) {
    const dash = (c: string) => new PolylineDashMaterialProperty({ color: css(c), dashLength: 12 })
    const solid = (c: string, a = 1) => new ColorMaterialProperty(css(c, a))
    for (const [id, d] of Object.entries(flood.layers.drains)) {
      const e = index.get(id)
      const c = d.state === 'overloaded' ? (d.load_ratio >= 2 ? SCENARIO.drain_severe : SCENARIO.drain_overloaded)
        : d.state === 'near' ? SCENARIO.drain_near : SCENARIO.drain_ok
      if (e) next.set(e, { lineMat: dash(c) })
    }
    for (const [id, r] of Object.entries(flood.layers.roads)) {
      const e = index.get(id)
      if (e) next.set(e, { lineMat: solid(r.state === 'impassable' ? SCENARIO.road_impassable : SCENARIO.road_impaired) })
    }
    for (const [id, e] of index) {
      if (!id.startsWith('cat_syn_')) continue
      const c = flood.layers.catchments[id]
      next.set(e, { polyMat: c ? solid(pondingColor(c.depth_m), 0.62) : solid('#0f172a', 0.12) })
    }
    for (const id of Object.keys(flood.layers.buildings)) {
      const e = index.get(id)
      if (e) next.set(e, { polyMat: solid(SCENARIO.building_exposed) })
    }
    for (const id of Object.keys(flood.layers.buildings_power ?? {})) {
      const e = index.get(id)
      if (e && !flood.layers.buildings[id]) next.set(e, { polyMat: solid(SCENARIO_POWER.building_no_power, 0.95) })
    }
    for (const id of Object.keys(flood.layers.transformers ?? {})) {
      const e = index.get(id)
      if (e) next.set(e, { billColor: new ConstantProperty(css(SCENARIO_POWER.transformer_shutdown)), scale: new ConstantProperty(1.5) })
    }
    for (const [id, f] of Object.entries(flood.layers.facilities)) {
      const e = index.get(id)
      if (e) next.set(e, { billColor: new ConstantProperty(css(f.state === 'access_cut' ? SCENARIO.facility_cut : SCENARIO.facility_impaired)),
        scale: new ConstantProperty(1.35) })
    }
  }
  if (quick) {  // P13 AI quick-scan: drains by surrogate overload probability (wins on drains)
    for (const [id, p] of Object.entries(quick)) {
      const e = index.get(id)
      if (e) next.set(e, { lineMat: new PolylineDashMaterialProperty({ color: css(probColor(p)), dashLength: 12 }) })
    }
  }
  if (access) {  // P12 accessibility colouring wins on buildings
    for (const [id, col] of Object.entries(access)) {
      const e = index.get(id)
      if (e) next.set(e, { ...next.get(e), polyMat: new ColorMaterialProperty(css(col)) })
    }
  }
  for (const e of [...L.scenario.keys()]) if (!next.has(e)) {
    L.scenario.delete(e)
    if (!L.painted.has(e)) applyLook(e, L.originals.get(e)!)
  }
  for (const [e, look] of next) {
    capture(e, L)
    L.scenario.set(e, look)
    if (!L.painted.has(e)) applyLook(e, { ...L.originals.get(e), ...look })
  }
}

function anchorFor(a: Asset): Cartesian3 {
  const [lon, lat] = a.position
  const top = a.layer === 'buildings' ? Number(a.attrs.height_m) || 9 : 0
  return Cartesian3.fromDegrees(lon, lat, top + 2)
}

function applyQuality(viewer: Viewer, q: Quality) {
  const hq = q === 'high'
  const scene = viewer.scene
  viewer.resolutionScale = hq ? 1 : 0.85
  scene.msaaSamples = hq ? 4 : 1
  scene.postProcessStages.fxaa.enabled = !hq
  viewer.shadows = hq
  const ao = scene.postProcessStages.ambientOcclusion
  ao.enabled = hq
  Object.assign(ao.uniforms, {
    intensity: 2.2, bias: 0.15, lengthCap: 0.12, stepSize: 1.6, frustumLength: 1200, blurStepSize: 0.86,
    ambientOcclusionOnly: false,
  })
  scene.requestRender()
}

function flyHome(viewer: Viewer, region: Region, duration = 2) {
  const mode = viewer.scene.mode
  if (mode === SceneMode.MORPHING) return // camera moves are ignored mid-morph; morphComplete re-homes
  if (mode !== SceneMode.SCENE3D) {
    // 2D is top-down: the oblique 3D vantage point below sits ~2 km south of the pilot, which left the
    // map empty. Frame the pilot's bounding box (plus a margin) instead.
    const [w, s, e, n] = region.bbox
    const px = (e - w) * 0.12
    const py = (n - s) * 0.12
    viewer.camera.flyTo({ destination: Rectangle.fromDegrees(w - px, s - py, e + px, n + py), duration })
    return
  }
  const [lon, lat] = region.centroid
  // P18: 11:00 local solar time at the pilot (UTC = 11 h − lon/15) on the data date, any region
  viewer.clock.currentTime = JulianDate.addHours(JulianDate.fromIso8601('2026-11-06T11:00:00Z'), -lon / 15, new JulianDate())
  viewer.camera.flyTo({
    // ~1.5 km up, looking north at 36° so the pilot fills the frame and facades are visible.
    destination: Cartesian3.fromDegrees(lon + 0.004, lat - 0.0185, 1450),
    orientation: { heading: CesiumMath.toRadians(-10), pitch: CesiumMath.toRadians(-36), roll: 0 },
    duration,
  })
}

export default function MapView() {
  const el = useRef<HTMLDivElement>(null)
  const viewerRef = useRef<Viewer | null>(null)
  const sources = useRef(new Map<string, Promise<GeoJsonDataSource>>())
  const eox = useRef<ImageryLayer | null>(null)
  const entityIndex = useRef(new Map<string, Entity>()) // asset_id → main entity (first per id)
  const looks = useRef<Looks>({ originals: new Map(), scenario: new Map(), painted: new Map() })
  const tagRef = useRef<HTMLDivElement>(null)
  const anchorRef = useRef<Cartesian3 | null>(null)
  const { region, visible, imagery, view, quality, selectedId, selected, neighbourhood, flyTarget, flood, dev, drawing,
    drawPoints, drawn, overlays, accessView, quick, select, setSelected, setLoading } = useApp()
  const overlayLayers = useRef(new Map<string, ImageryLayer>())
  const refreshLooks = () => {
    const st = useApp.getState()
    applyScenario(entityIndex.current, looks.current, st.flood, st.accessView?.colors ?? null, st.quick)
    repaint(entityIndex.current, looks.current, st.selectedId, st.neighbourhood, true)
    viewerRef.current?.scene.requestRender()
  }

  // Create the viewer once.
  useEffect(() => {
    if (!el.current) return
    const base = new ImageryLayer(
      new OpenStreetMapImageryProvider({ url: 'https://tile.openstreetmap.org/', credit: new Credit('© OpenStreetMap contributors') }),
    )
    // Dim + desaturate the street map so data layers read on a dark command-centre canvas.
    base.brightness = 0.42
    base.contrast = 1.25
    base.saturation = 0.15
    const viewer = new Viewer(el.current, {
      baseLayer: base,
      // Start directly in the stored view: morphing to 2D after start-up swallowed the first fly-to.
      sceneMode: useApp.getState().view === '2d' ? SceneMode.SCENE2D : SceneMode.SCENE3D,
      terrainProvider: new EllipsoidTerrainProvider(),
      baseLayerPicker: false,
      geocoder: false,
      timeline: false,
      animation: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      infoBox: false,
      selectionIndicator: false,
      requestRenderMode: true,
      maximumRenderTimeChange: Infinity,
      msaaSamples: 4,
      shouldAnimate: false,
      contextOptions: { webgl: { preserveDrawingBuffer: true } }, // report map capture (P14)
    })
    const scene = viewer.scene
    viewer.clock.currentTime = NOW.clone()
    viewer.useBrowserRecommendedResolution = false // render at device pixels (crisp on HiDPI)
    scene.globe.baseColor = css('#0b0f14')
    scene.globe.maximumScreenSpaceError = 1.5 // sharper basemap tiles (default 2)
    scene.globe.showGroundAtmosphere = false // no haze wash over the dark basemap
    scene.highDynamicRange = false
    viewer.shadowMap.softShadows = true
    viewer.shadowMap.size = 2048
    viewer.shadowMap.darkness = 0.45
    viewer.shadowMap.maximumDistance = 5000
    // Keep the floating info tag glued to its anchor: re-project after every rendered frame.
    scene.postRender.addEventListener(() => {
      const tag = tagRef.current
      const pos = anchorRef.current
      if (!tag) return
      const xy = pos ? SceneTransforms.worldToWindowCoordinates(scene, pos) : undefined
      const w = scene.canvas.clientWidth
      const hgt = scene.canvas.clientHeight
      if (!xy || xy.x < -50 || xy.y < 0 || xy.x > w + 50 || xy.y > hgt + 300) {
        tag.style.visibility = 'hidden'
        return
      }
      tag.style.visibility = 'visible'
      tag.style.transform = `translate(${Math.round(xy.x)}px, ${Math.round(xy.y)}px) translate(-50%, calc(-100% - 14px))`
    })
    // After a 2D ⇄ 3D morph the previous camera no longer frames the pilot: re-home for the new mode.
    scene.morphComplete.addEventListener(() => {
      const r = useApp.getState().region
      if (r) flyHome(viewer, r, 0)
      scene.requestRender()
    })
    viewer.cesiumWidget.screenSpaceEventHandler.removeInputAction(ScreenSpaceEventType.LEFT_DOUBLE_CLICK)
    const click = new ScreenSpaceEventHandler(viewer.scene.canvas)
    click.setInputAction((ev: { position: { x: number; y: number } }) => {
      if (useApp.getState().drawing) {
        const cart = viewer.camera.pickEllipsoid(ev.position as never, viewer.scene.globe.ellipsoid)
        if (cart) {
          const c = Cartographic.fromCartesian(cart)
          useApp.getState().addDrawPoint([CesiumMath.toDegrees(c.longitude), CesiumMath.toDegrees(c.latitude)])
        }
        return
      }
      const picked = viewer.scene.pick(ev.position as never)
      const ent = defined(picked) && picked.id instanceof Entity ? picked.id : null
      useApp.getState().select(ent ? (String(prop(ent, 'asset_id') ?? '') || null) : null)
    }, ScreenSpaceEventType.LEFT_CLICK)
    click.setInputAction(() => {
      if (useApp.getState().drawing) useApp.getState().finishDraw()
    }, ScreenSpaceEventType.LEFT_DOUBLE_CLICK)
    viewerRef.current = viewer
    const overlaysMap = overlayLayers.current
    useApp.getState().setCaptureMap(() => {
      if (viewer.isDestroyed()) return null
      viewer.scene.render()
      try {
        return viewer.scene.canvas.toDataURL('image/jpeg', 0.82)
      } catch {
        return null
      }
    })
    const map = sources.current
    const [idx, lk] = [entityIndex.current, looks.current]
    return () => {
      click.destroy()
      useApp.getState().setCaptureMap(null) // the closure holds the destroyed viewer
      viewer.destroy()
      viewerRef.current = null
      map.clear()
      overlaysMap.clear() // imagery layers of the destroyed viewer: a remount must add them again
      eox.current = null
      idx.clear()
      lk.originals.clear()
      lk.scenario.clear()
      lk.painted.clear()
    }
  }, [])

  // Fly to the region when it arrives.
  useEffect(() => {
    if (viewerRef.current && region) flyHome(viewerRef.current, region, 0)
  }, [region])

  // Lazy-load layers on first toggle; afterwards only flip `show`.
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !region) return
    for (const [id, on] of Object.entries(visible)) {
      let p = sources.current.get(id)
      if (!p && on) {
        setLoading(id, true)
        p = getLayer(id, !FULL_EXTENT.has(id))
          .then((gj) => GeoJsonDataSource.load(gj, { clampToGround: false }))
          .then((ds) => {
            styleLayer(id, ds)
            for (const e of ds.entities.values) {
              const aid = prop(e, 'asset_id')
              if (typeof aid === 'string' && !entityIndex.current.has(aid)) entityIndex.current.set(aid, e)
            }
            if (!viewer.isDestroyed()) viewer.dataSources.add(ds)
            // Selection/neighbourhood made before this layer arrived (deep link, explorer) → paint now.
            refreshLooks()
            const { selectedId: sel, selected: detail } = useApp.getState()
            if (sel && !detail && entityIndex.current.has(sel))
              getAsset(sel).then((a) => useApp.getState().selectedId === sel && setSelected(a)).catch(() => {}) // offline retry
            return ds
          })
          .finally(() => setLoading(id, false))
        sources.current.set(id, p)
      }
      p?.then((ds) => {
        ds.show = Boolean(useApp.getState().visible[id])
        if (!viewer.isDestroyed()) viewer.scene.requestRender()
      }).catch((err: unknown) => {
        console.error(`layer ${id} failed to load`, err)
        sources.current.delete(id)
      })
    }
  }, [visible, region, setLoading, setSelected])

  // Imagery: EOX Sentinel-2 cloudless on top of OSM.
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return
    if (imagery === 'eox' && !eox.current)
      eox.current = viewer.imageryLayers.addImageryProvider(
        new UrlTemplateImageryProvider({
          url: EOX_URL,
          maximumLevel: 15,
          credit: new Credit('Sentinel-2 cloudless by EOX (Contains modified Copernicus Sentinel data 2020)'),
        }),
      )
    if (eox.current) eox.current.show = imagery === 'eox'
    viewer.scene.requestRender()
  }, [imagery])

  // Render quality: High = MSAA + soft shadows + ambient occlusion; Standard = FXAA only.
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return
    applyQuality(viewer, quality)
  }, [quality])

  // Floating info tag anchor: top of a building, else the asset's representative point.
  useEffect(() => {
    anchorRef.current = selected ? anchorFor(selected) : null
    viewerRef.current?.scene.requestRender()
  }, [selected])

  // Esc closes the tag.
  useEffect(() => {
    const onKey = (ev: KeyboardEvent) => ev.key === 'Escape' && useApp.getState().select(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // 2D / 3D morph.
  useEffect(() => {
    const scene = viewerRef.current?.scene
    if (!scene) return
    if (scene.mode === (view === '2d' ? SceneMode.SCENE2D : SceneMode.SCENE3D)) return // already there (initial mount)
    if (view === '2d') scene.morphTo2D(0.8)
    else scene.morphTo3D(0.8)
  }, [view])

  // Selection: fetch asset detail. Highlights (selected + neighbourhood) repaint on any change.
  useEffect(() => {
    if (!selectedId) return
    const ctrl = new AbortController()
    getAsset(selectedId, ctrl.signal).then(setSelected).catch(() => {})
    return () => ctrl.abort()
  }, [selectedId, setSelected])

  useEffect(() => {
    repaint(entityIndex.current, looks.current, selectedId, neighbourhood)
    viewerRef.current?.scene.requestRender()
  }, [selectedId, neighbourhood])

  // P08 scenario recolouring (layers it needs are switched on by the store).
  useEffect(() => {
    applyScenario(entityIndex.current, looks.current, flood, accessView?.colors ?? null, quick)
    repaint(entityIndex.current, looks.current, useApp.getState().selectedId, useApp.getState().neighbourhood, true)
    viewerRef.current?.scene.requestRender()
  }, [flood, accessView, quick])

  // P09 draw tool: live outline while drawing; pending footprint; assessed proposal extruded in purple (simulated).
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return
    for (const id of ['draw-temp', 'proposal']) viewer.entities.removeById(id)
    const purple = css('#a855f7')
    if (drawing && drawPoints.length) {
      const pos = drawPoints.map(([lon, lat]) => Cartesian3.fromDegrees(lon, lat, 1))
      viewer.entities.add({
        id: 'draw-temp',
        polyline: { positions: drawPoints.length > 2 ? [...pos, pos[0]] : pos, width: 3, material: purple },
        polygon: drawPoints.length > 2 ? { hierarchy: pos, material: purple.withAlpha(0.25), height: 0.5 } : undefined,
      })
    } else if (dev || drawn) {
      const ring = dev ? dev.geometry.coordinates[0] : [...drawn!, drawn![0]]
      const pos = ring.map(([lon, lat]) => Cartesian3.fromDegrees(lon, lat))
      const floors = dev ? dev.params.floors : 0
      viewer.entities.add({
        id: 'proposal',
        polygon: {
          hierarchy: pos,
          height: 0,
          extrudedHeight: floors ? floors * 3.2 : 1,
          material: purple.withAlpha(floors ? 0.78 : 0.35),
          outline: true,
          outlineColor: css('#f5d0fe'),
        },
        properties: { asset_id: 'proposal', data_status: 'simulated' },
      })
    }
    viewer.scene.requestRender()
  }, [drawing, drawPoints, drawn, dev])

  // P11 raster overlays (WorldCover / NDVI) as single-tile imagery with the bounds from landcover stats.
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return
    const run = { cancelled: false }
    for (const k of ['worldcover', 'ndvi'] as const) {
      const lyr = overlayLayers.current.get(k)
      if (lyr) lyr.show = overlays[k]
      if (!overlays[k] || lyr) continue
      getLandcover()
        .then(async (s) => {
          const o = s.overlays[k]
          const provider = await SingleTileImageryProvider.fromUrl(`${import.meta.env.BASE_URL ?? '/'}${o.url}`, {
            rectangle: Rectangle.fromDegrees(...o.bounds),
            credit: new Credit(k === 'worldcover' ? '© ESA WorldCover 2021' : 'Contains modified Copernicus Sentinel data'),
          })
          if (run.cancelled || viewer.isDestroyed() || overlayLayers.current.has(k)) return
          const layer = viewer.imageryLayers.addImageryProvider(provider)
          overlayLayers.current.set(k, layer)
          layer.show = useApp.getState().overlays[k]
          viewer.scene.requestRender()
        })
        .catch((e) => console.error(`overlay ${k} failed`, e))
    }
    viewer.scene.requestRender()
    return () => {
      run.cancelled = true
    }
  }, [overlays])

  // Explorer "fly to" requests.
  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer || !flyTarget) return
    if (viewer.scene.mode === SceneMode.MORPHING) return
    if (viewer.scene.mode !== SceneMode.SCENE3D) {
      // top-down: centre on the asset itself (the southward offset is only right for the tilted 3D camera)
      viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(flyTarget.lon, flyTarget.lat, 900), duration: 1.2 })
      return
    }
    viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(flyTarget.lon, flyTarget.lat - 0.0045, 650),
      orientation: { heading: 0, pitch: CesiumMath.toRadians(-48), roll: 0 },
      duration: 1.2,
    })
  }, [flyTarget])

  return (
    <div className="absolute inset-0">
      <div ref={el} className="absolute inset-0" />
      {/* Floating info tag: positioned imperatively in scene.postRender (no React re-render per frame). */}
      <div
        ref={tagRef}
        className="pointer-events-none absolute left-0 top-0 z-10 will-change-transform"
        style={{ visibility: 'hidden' }}
      >
        {selected && selected.asset_id === selectedId && <InfoTag asset={selected} onClose={() => select(null)} />}
      </div>
      {drawing && (
        <div className="absolute left-1/2 top-20 z-[1] w-max max-w-[calc(100%-1.5rem)] -translate-x-1/2 rounded border border-purple-400/70 bg-slate-950/90 px-3 py-1.5 text-[11px] text-purple-100 shadow-lg">
          Drawing footprint · click to add corners ({drawPoints.length}) · double-click to finish ·{' '}
          <button className="underline" onClick={() => useApp.getState().cancelDraw()}>cancel</button>
        </div>
      )}
      {flood && (
        <div className="absolute bottom-10 left-1/2 flex w-max max-w-[calc(100%-1.5rem)] -translate-x-1/2 flex-wrap items-center justify-center gap-x-3 gap-y-0.5 rounded border border-amber-500/60 bg-slate-950/90 px-3 py-1.5 text-[11px] text-amber-200 shadow-lg">
          <span className="font-semibold">
            SCENARIO {flood.params.preset ? flood.params.preset.toUpperCase() : 'CUSTOM'} · {flood.params.rain_mm_h} mm/h × {flood.params.duration_h} h
          </span>
          <span className="text-amber-300/80">Scenario-based estimate — not a prediction</span>
          <button onClick={() => useApp.getState().setFlood(null)} className="rounded border border-amber-500/50 px-1.5 hover:bg-amber-500/20">
            Clear
          </button>
        </div>
      )}
      {POWER_LAYERS.some((l) => visible[l]) && (
        <div className="pointer-events-none absolute left-3 top-11 rounded border border-dashed border-yellow-400/70 bg-slate-950/85 px-2.5 py-1 text-[11px] font-semibold tracking-wider text-yellow-200 shadow">
          SIMULATED NETWORK — not the actual utility grid
        </div>
      )}
      {DRAINAGE_LAYERS.some((l) => visible[l]) && (
        <div className="pointer-events-none absolute left-3 top-3 rounded border border-dashed border-purple-400/70 bg-slate-950/85 px-2.5 py-1 text-[11px] font-semibold tracking-wider text-purple-200 shadow">
          SIMULATED DRAINAGE NETWORK — not municipal records
        </div>
      )}
      <div className="absolute right-3 top-3 flex gap-1.5">
        <MapButton onClick={() => useApp.getState().setQuality(quality === 'high' ? 'standard' : 'high')}>
          Quality: {quality === 'high' ? 'High' : 'Standard'}
        </MapButton>
        <MapButton onClick={() => region && viewerRef.current && flyHome(viewerRef.current, region)}>Home</MapButton>
        {selectedId && <MapButton onClick={() => select(null)}>Clear selection</MapButton>}
      </div>
    </div>
  )
}

function MapButton({ onClick, children }: { onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className="rounded border border-slate-700 bg-slate-950/85 px-2.5 py-1 text-xs font-medium text-slate-200 shadow backdrop-blur hover:border-sky-500 hover:text-sky-300"
    >
      {children}
    </button>
  )
}
