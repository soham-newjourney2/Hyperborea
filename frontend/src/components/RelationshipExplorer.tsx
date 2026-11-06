import cytoscape from 'cytoscape'
import { useEffect, useMemo, useRef, useState } from 'react'
import { getGraphSummary, getNeighbours, getTrace, type GraphSummary, type Neighbourhood, type Relationship, type Trace } from '../lib/api'
import { KIND } from '../lib/styles'
import { useApp } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

// Quick views: the flood dependency chain hides building/catchment leaves (facility → roads → drains → network).
const FLOOD_CHAIN = ['DEPENDS_ON', 'ADJACENT_TO', 'DRAINS_TO']
const FLOOD_LINK = new URLSearchParams(window.location.search).get('view') === 'flood' // ?view=flood

function DrainTrace({ id }: { id: string }) {
  const setNeighbourhood = useApp((s) => s.setNeighbourhood)
  const [t, setT] = useState<Trace | null>(null)
  useEffect(() => {
    const ctrl = new AbortController()
    getTrace(id, ctrl.signal).then(setT).catch(() => {})
    return () => ctrl.abort()
  }, [id])
  if (!t || t.drain !== id) return null
  const btn = 'flex-1 rounded border border-slate-700 bg-slate-900/60 px-2 py-1 text-[11px] text-slate-200 hover:border-cyan-500'
  return (
    <div className="flex gap-1.5">
      <button className={btn} onClick={() => setNeighbourhood(t.upstream)}>
        Light up upstream · <span className="tabular-nums text-cyan-300">{t.upstream.length}</span> drains
      </button>
      <button className={btn} onClick={() => setNeighbourhood(t.downstream)}>
        Flow path to outfall · <span className="tabular-nums text-cyan-300">{t.downstream.length}</span> hops
      </button>
    </div>
  )
}

const short = (s: string | null | undefined, n = 18) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : (s ?? ''))

function KindLegend() {
  return (
    <ul className="grid grid-cols-4 gap-x-2 gap-y-0.5">
      {Object.entries(KIND).map(([k, v]) => (
        <li key={k} className="flex items-center gap-1 text-[10px] text-slate-300">
          <span className="h-2 w-2 rounded-sm" style={{ backgroundColor: v.color }} />
          {v.label}
        </li>
      ))}
    </ul>
  )
}

function EdgeLegend({ summary, active, toggle }: { summary: GraphSummary; active: Set<string>; toggle: (t: string) => void }) {
  const types = Object.entries(summary.registry).filter(([, v]) => v.active)
  return (
    <div className="space-y-1">
      {types.map(([t, v]) => {
        const on = active.size === 0 || active.has(t)
        return (
          <button
            key={t}
            onClick={() => toggle(t)}
            title={v.description}
            className={`flex w-full items-start gap-2 rounded px-1.5 py-1 text-left text-[11px] ${on ? 'bg-slate-800/60' : 'opacity-40'}`}
          >
            <code className="shrink-0 text-[10px] font-semibold text-sky-300">{t}</code>
            <span className="text-slate-400">{v.description}</span>
            <span className="ml-auto shrink-0 tabular-nums text-slate-500">{summary.edge_types[t]?.toLocaleString() ?? 0}</span>
          </button>
        )
      })}
      <p className="text-[10px] text-slate-500">Tap a type to filter · dashed = simulated edge, solid = modelled from observed data</p>
    </div>
  )
}

function GraphView({ nb, onPick }: { nb: Neighbourhood; onPick: (id: string) => void }) {
  const el = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!el.current) return
    const cy = cytoscape({
      container: el.current,
      elements: [
        ...nb.nodes.map((n) => ({
          data: { id: n.id, label: short(n.name ?? n.asset_type.replace(/_/g, ' ')), kind: n.kind, hop: n.hop ?? 0 },
          classes: n.id === nb.center ? 'center' : '',
        })),
        ...nb.edges.map((e) => ({
          data: { id: e.relationship_id, source: e.source, target: e.target, label: e.type, status: e.data_status },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (n: cytoscape.NodeSingular) => KIND[n.data('kind')]?.color ?? '#64748b',
            shape: ((n: cytoscape.NodeSingular) => KIND[n.data('kind')]?.shape ?? 'ellipse') as never,
            width: 16,
            height: 16,
            label: 'data(label)',
            color: '#cbd5e1',
            'font-size': 8,
            'text-valign': 'bottom',
            'text-margin-y': 3,
            'border-width': 1.5,
            'border-color': '#0b1220',
          },
        },
        { selector: 'node.center', style: { width: 26, height: 26, 'border-color': '#facc15', 'border-width': 3, 'font-size': 10, color: '#f8fafc' } },
        {
          selector: 'edge',
          style: {
            width: 1.2,
            'line-color': '#475569',
            'target-arrow-color': '#475569',
            'target-arrow-shape': 'triangle',
            'arrow-scale': 0.7,
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': 6,
            color: '#64748b',
            'text-rotation': 'autorotate',
            'text-background-color': '#0b1220',
            'text-background-opacity': 1,
            'text-background-padding': '1px',
          },
        },
        { selector: 'edge[status = "simulated"]', style: { 'line-style': 'dashed' } },
        { selector: 'node:active, node:selected', style: { 'overlay-opacity': 0.15 } },
      ],
      layout: {
        name: 'concentric',
        concentric: (n: cytoscape.NodeSingular) => 10 - Number(n.data('hop')),
        levelWidth: () => 1,
        minNodeSpacing: 14,
        animate: false,
      } as cytoscape.LayoutOptions,
      wheelSensitivity: 0.3,
    })
    cy.on('tap', 'node', (ev) => onPick(ev.target.id()))
    return () => cy.destroy()
  }, [nb, onPick])
  return <div ref={el} className="h-80 w-full rounded border border-slate-800 bg-[#0b1220]" role="img" aria-label="Relationship graph" />
}

function GroupedList({ rels, onPick }: { rels: Relationship[]; onPick: (id: string) => void }) {
  const groups = useMemo(() => {
    const m = new Map<string, Relationship[]>()
    for (const r of rels) m.set(r.label, [...(m.get(r.label) ?? []), r])
    return [...m.entries()]
  }, [rels])
  if (!rels.length) return <p className="text-xs text-slate-500">No relationships — this asset is not connected by any rule (shown honestly, not inferred).</p>
  return (
    <div className="space-y-2">
      {groups.map(([label, rs]) => (
        <section key={label}>
          <h4 className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            {label} · {rs[0].type} ({rs.length})
          </h4>
          <ul className="space-y-1">
            {rs.slice(0, 25).map((r) => (
              <li key={r.relationship_id}>
                <button onClick={() => onPick(r.other_id)} className="w-full rounded border border-slate-800 bg-slate-900/50 px-2 py-1 text-left hover:border-sky-600">
                  <div className="flex items-center gap-1.5 text-xs text-slate-100">
                    <span className="h-2 w-2 shrink-0 rounded-sm" style={{ backgroundColor: KIND[r.other_kind]?.color ?? '#64748b' }} />
                    <span className="truncate">{r.other_name || r.other_type.replace(/_/g, ' ')}</span>
                    <span className="ml-auto shrink-0">
                      <ProvenanceBadge status={r.data_status} small />
                    </span>
                  </div>
                  <div className="mt-0.5 text-[10px] leading-snug text-slate-500">
                    {r.rule}
                    {r.weight !== null && r.unit ? ` · ${r.weight} ${r.unit}` : ''} · conf {r.confidence}
                  </div>
                </button>
              </li>
            ))}
            {rs.length > 25 && <li className="text-[10px] text-slate-500">+ {rs.length - 25} more</li>}
          </ul>
        </section>
      ))}
    </div>
  )
}

export default function RelationshipExplorer() {
  const { selectedId, selected, select, setNeighbourhood, flyTo } = useApp()
  const [summary, setSummary] = useState<GraphSummary | null>(null)
  const [depth, setDepth] = useState(FLOOD_LINK ? 3 : 2)
  const [types, setTypes] = useState<Set<string>>(new Set(FLOOD_LINK ? FLOOD_CHAIN : []))
  const [nb, setNb] = useState<Neighbourhood | null>(null)
  const [err, setErr] = useState<{ id: string; msg: string } | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    getGraphSummary(ctrl.signal).then(setSummary).catch(() => {})
    return () => ctrl.abort()
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setNeighbourhood([])
      return
    }
    const ctrl = new AbortController()
    getNeighbours(selectedId, depth, [...types], ctrl.signal)
      .then((n) => {
        setNb(n)
        setNeighbourhood(n.nodes.map((x) => x.id).filter((id) => id !== n.center))
      })
      .catch((e: Error) => e.name !== 'AbortError' && setErr({ id: selectedId, msg: 'Graph unavailable (offline snapshot has no graph).' }))
    return () => ctrl.abort()
  }, [selectedId, depth, types, setNeighbourhood])

  // Leaving the tab clears the map neighbourhood highlight.
  useEffect(() => () => setNeighbourhood([]), [setNeighbourhood])

  // Only show results that belong to the current selection (derived, no reset-in-effect).
  const view = nb && nb.center === selectedId ? nb : null
  const error = err && err.id === selectedId ? err.msg : null

  const pick = useMemo(
    () => (id: string) => {
      const n = nb?.nodes.find((x) => x.id === id)
      select(id)
      if (n) flyTo(n.lon, n.lat)
    },
    [nb, select, flyTo],
  )
  const toggle = (t: string) =>
    setTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })

  return (
    <div className="space-y-3">
      {!selectedId && summary && (
        <section className="rounded border border-slate-800 bg-slate-900/50 p-2.5 text-xs">
          <h3 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Dependency graph</h3>
          <p className="text-slate-300">
            {summary.nodes.toLocaleString()} assets · {summary.edges.toLocaleString()} typed relationships ·{' '}
            {Object.keys(summary.node_kinds).length} asset kinds
          </p>
          <p className="mt-1 text-[11px] text-slate-500">Click any asset on the map to explore what it connects to and depends on.</p>
        </section>
      )}

      {selectedId && (
        <>
          <div className="flex items-center gap-2">
            <span className="text-[11px] text-slate-400">Hops</span>
            {[1, 2, 3].map((d) => (
              <button
                key={d}
                onClick={() => setDepth(d)}
                className={`rounded px-2 py-0.5 text-xs ${depth === d ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'text-slate-400 hover:text-slate-200'}`}
              >
                {d}
              </button>
            ))}
            <span className="ml-2 text-[11px] text-slate-400">View</span>
            {(
              [
                ['All', [] as string[], depth],
                ['Flood chain', FLOOD_CHAIN, 3],
              ] as const
            ).map(([label, ts, d]) => {
              const on = ts.length === types.size && ts.every((t) => types.has(t))
              return (
                <button
                  key={label}
                  onClick={() => {
                    setTypes(new Set(ts))
                    setDepth(d)
                  }}
                  className={`whitespace-nowrap rounded px-2 py-0.5 text-xs ${on ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  {label}
                </button>
              )
            })}
            {view && (
              <span className="ml-auto text-[10px] tabular-nums text-slate-500">
                {view.nodes.length} nodes · {view.edges.length} edges{view.truncated ? ' · capped at 200' : ''}
              </span>
            )}
          </div>
          {error && <p className="text-xs text-amber-300">{error}</p>}
          {view && <GraphView nb={view} onPick={pick} />}
          {selected?.layer === 'drains' && <DrainTrace id={selected.asset_id} />}
          <KindLegend />
        </>
      )}

      {summary && <EdgeLegend summary={summary} active={types} toggle={toggle} />}

      {selected && (
        <section>
          <h3 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
            Relationships of {short(selected.name || selected.asset_type, 28)}
          </h3>
          <GroupedList rels={selected.relationships ?? []} onPick={pick} />
        </section>
      )}
    </div>
  )
}
