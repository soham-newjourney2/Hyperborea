import { STATUS_STYLES } from '../lib/provenance'
import { BUILDING_USE, CAPACITY_STOPS, FACILITY, PONDING_STOPS, ROAD_CLASS, RUNOFF_STOPS, SCENARIO } from '../lib/styles'
import { useApp } from '../store'
import { Chip } from './ProvenanceBadge'

function Swatch({ color, label, shape = 'box' }: { color: string; label: string; shape?: 'box' | 'line' | 'dot' }) {
  const cls = shape === 'line' ? 'h-1 w-4 rounded' : shape === 'dot' ? 'h-2.5 w-2.5 rounded-full' : 'h-2.5 w-2.5 rounded-sm'
  return (
    <li className="flex items-center gap-1.5 text-[11px] text-slate-300">
      <span className={cls} style={{ backgroundColor: color }} />
      {label}
    </li>
  )
}

export default function Legend() {
  const { visible, flood } = useApp()
  return (
    <div className="space-y-2.5">
      {flood && (
        <div className="rounded border border-amber-500/40 p-1.5">
          <h4 className="mb-1 text-[10px] uppercase tracking-wider text-amber-300">Scenario (estimate, not a prediction)</h4>
          <ul className="grid grid-cols-2 gap-x-2 gap-y-0.5">
            <Swatch color={SCENARIO.drain_ok} label="Drain OK" shape="line" />
            <Swatch color={SCENARIO.drain_near} label="Drain ≥ 80 % load" shape="line" />
            <Swatch color={SCENARIO.drain_overloaded} label="Drain overloaded" shape="line" />
            <Swatch color={SCENARIO.drain_severe} label="Drain ≥ 2× capacity" shape="line" />
            <Swatch color={SCENARIO.road_impaired} label="Road impaired ≥ 0.15 m" shape="line" />
            <Swatch color={SCENARIO.road_impassable} label="Road impassable ≥ 0.30 m" shape="line" />
            <Swatch color={SCENARIO.building_exposed} label="Building above plinth" />
            <Swatch color={SCENARIO.facility_impaired} label="Facility access hit" shape="dot" />
          </ul>
          <div className="mt-1 h-2 rounded" style={{ background: `linear-gradient(90deg, ${PONDING_STOPS.join(',')})` }} />
          <div className="mt-0.5 flex justify-between text-[10px] text-slate-500">
            <span>ponding 0.15 m</span><span>≥ 1.0 m (cap)</span>
          </div>
        </div>
      )}
      {visible.buildings && (
        <div>
          <h4 className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Buildings (height = extrusion)</h4>
          <ul className="grid grid-cols-2 gap-x-2 gap-y-0.5">
            {BUILDING_USE.map((u) => <Swatch key={u.key} color={u.color} label={u.label} />)}
          </ul>
          <p className="mt-0.5 text-[10px] text-slate-500">Faded = height assumed (no OSM tag)</p>
        </div>
      )}
      {visible.roads && (
        <div>
          <h4 className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Roads</h4>
          <ul className="space-y-0.5">{ROAD_CLASS.map((r) => <Swatch key={r.label} color={r.color} label={r.label} shape="line" />)}</ul>
        </div>
      )}
      {visible.facilities && (
        <div>
          <h4 className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Facilities</h4>
          <ul className="grid grid-cols-2 gap-x-2 gap-y-0.5">
            {Object.entries(FACILITY).map(([k, f]) => <Swatch key={k} color={f.color} label={`${f.glyph} ${f.label}`} shape="dot" />)}
          </ul>
        </div>
      )}
      {visible.drains && (
        <div>
          <h4 className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Drains · effective capacity (simulated)</h4>
          <div className="h-2 rounded" style={{ background: `linear-gradient(90deg, ${CAPACITY_STOPS.join(',')})` }} />
          <div className="mt-0.5 flex justify-between text-[10px] text-slate-500">
            <span>≤ 0.1</span><span>0.5</span><span>≥ 5 m³/s</span>
          </div>
          <p className="mt-0.5 text-[10px] text-slate-500">Width = diameter (0.6 / 0.9 / 1.2 m) · arrows = flow · dashed = simulated</p>
        </div>
      )}
      {visible.catchments && (
        <div>
          <h4 className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Catchments · runoff coefficient C</h4>
          <div className="h-2 rounded" style={{ background: `linear-gradient(90deg, ${RUNOFF_STOPS.join(',')})` }} />
          <div className="mt-0.5 flex justify-between text-[10px] text-slate-500">
            <span>0.40 green/open</span><span>0.90 roofs/roads</span>
          </div>
        </div>
      )}
      <div>
        <h4 className="mb-1 text-[10px] uppercase tracking-wider text-slate-500">Data status</h4>
        <div className="flex flex-wrap gap-1">
          {Object.entries(STATUS_STYLES).map(([k, s]) => <Chip key={k} style={s} small />)}
        </div>
      </div>
    </div>
  )
}
