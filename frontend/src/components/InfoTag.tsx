import type { Asset } from '../lib/api'
import { HEIGHT_STATUS, statusStyle } from '../lib/provenance'
import { FACILITY, buildingColor, roadStyle } from '../lib/styles'
import ProvenanceBadge, { Chip } from './ProvenanceBadge'

type Stat = { label: string; value: string }

const num = (v: unknown, digits = 0) =>
  typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: digits }) : null
const txt = (v: unknown) => (v === null || v === undefined || v === '' ? null : String(v).replace(/[[\]']/g, ''))
const title = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

function stats(a: Asset): Stat[] {
  const t = a.attrs
  const rows: [string, string | null][] =
    a.layer === 'buildings'
      ? [
          ['Height', num(t.height_m, 1) && `${num(t.height_m, 1)} m`],
          ['Levels', num(t.levels)],
          ['Use', txt(t.use) === 'yes' ? 'untagged' : txt(t.use)],
          ['Footprint', num(t.area_m2) && `${num(t.area_m2)} m²`],
        ]
      : a.layer === 'roads'
        ? [
            ['Class', txt(t.highway)],
            ['Length', num(t.length_m) && `${num(t.length_m)} m`],
            ['Lanes', txt(t.lanes)],
            ['Max speed', txt(t.maxspeed)],
          ]
        : a.layer === 'drains'
          ? [
              ['Capacity', num(t.effective_capacity_m3s, 2) && `${num(t.effective_capacity_m3s, 2)} m³/s`],
              ['Diameter', num(t.diameter_m, 1) && `${num(t.diameter_m, 1)} m`],
              ['Slope', txt(t.slope)],
              ['Condition', num(t.condition_factor, 2) && `× ${num(t.condition_factor, 2)}`],
            ]
        : a.layer === 'outfalls'
          ? [
              ['Receives', txt(t.receiving_water) ?? `unnamed ${txt(t.receiving_kind) ?? 'canal'}`],
              ['To water', num(t.distance_to_water_m) && `${num(t.distance_to_water_m)} m`],
              ['Drains in', num(t.n_upstream_segments)],
            ]
        : a.layer === 'catchments'
          ? [
              ['Area', num(t.area_m2) && `${num(t.area_m2)} m²`],
              ['Runoff C', num(t.runoff_c, 2)],
              ['Roof', num(t.roof_m2) && `${num(t.roof_m2)} m²`],
              ['Drain', txt(t.drain_id)?.replace('drn_syn_', '…') ?? null],
            ]
        : a.layer === 'drain_nodes'
          ? [
              ['Ground', num(t.ground_elev_m, 1) && `${num(t.ground_elev_m, 1)} m`],
              ['To outfall', num(t.dist_to_outfall_m) && `${num(t.dist_to_outfall_m)} m`],
            ]
        : a.layer === 'facilities'
          ? [
              ['Operator', txt(t.operator)],
              ['Beds', txt(t.beds)],
              ['Emergency', txt(t.emergency)],
              ['Footprint', num(t.footprint_m2) && `${num(t.footprint_m2)} m²`],
            ]
          : Object.entries(t)
              .filter(([k]) => k !== 'osm_id')
              .slice(0, 4)
              .map(([k, v]) => [title(k), txt(v)])
  return rows.filter((r): r is [string, string] => Boolean(r[1])).map(([label, value]) => ({ label, value }))
}

function accent(a: Asset): string {
  if (a.layer === 'buildings') return buildingColor(a.attrs.use, a.attrs.amenity)
  if (a.layer === 'roads') return roadStyle(a.attrs.highway).color
  if (a.layer === 'facilities') return FACILITY[a.asset_type]?.color ?? '#94a3b8'
  return statusStyle(a.data_status).color
}

export default function InfoTag({ asset: a, onClose }: { asset: Asset; onClose: () => void }) {
  const hs = a.layer === 'buildings' ? HEIGHT_STATUS[String(a.attrs.height_status)] : undefined
  const color = accent(a)
  const s = stats(a)
  return (
    <div className="pointer-events-auto relative w-64 animate-[tagIn_160ms_ease-out] select-none">
      <div
        className="overflow-hidden rounded-lg border border-slate-700/80 bg-slate-950/90 text-slate-200 shadow-[0_10px_30px_rgba(0,0,0,0.55)] backdrop-blur-md"
        style={{ borderTopColor: color, borderTopWidth: 2 }}
      >
        <div className="flex items-start gap-2 px-3 pb-1.5 pt-2">
          <div className="min-w-0 flex-1">
            <div className="truncate text-[13px] font-semibold leading-tight text-slate-50">
              {a.name || <span className="italic text-slate-400">Unnamed {a.asset_type.replace(/_/g, ' ')}</span>}
            </div>
            <div className="mt-0.5 text-[10px] uppercase tracking-wider text-slate-400">
              {title(a.asset_type)} · {a.in_pilot ? 'pilot' : 'buffer'}
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="-mr-1 rounded px-1 text-base leading-none text-slate-500 hover:bg-slate-800 hover:text-slate-200"
          >
            ×
          </button>
        </div>

        {s.length > 0 && (
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 border-t border-slate-800/80 px-3 py-2">
            {s.map((r) => (
              <div key={r.label} className="min-w-0">
                <dt className="text-[9px] uppercase tracking-wider text-slate-500">{r.label}</dt>
                <dd className="truncate text-xs font-medium tabular-nums text-slate-100">{r.value}</dd>
              </div>
            ))}
          </dl>
        )}

        <div className="flex flex-wrap items-center gap-1 border-t border-slate-800/80 bg-slate-900/50 px-3 py-1.5">
          <ProvenanceBadge status={a.data_status} small />
          {hs && <Chip style={hs} small />}
          <span className="ml-auto text-[10px] text-slate-500">
            {a.source_id}
            {a.confidence ? ` · conf ${a.confidence}` : ''}
          </span>
        </div>
      </div>
      {/* caret pointing at the anchor */}
      <div
        className="absolute left-1/2 top-full h-3 w-3 -translate-x-1/2 -translate-y-1.5 rotate-45 border-b border-r border-slate-700/80 bg-slate-950/90"
      />
    </div>
  )
}
