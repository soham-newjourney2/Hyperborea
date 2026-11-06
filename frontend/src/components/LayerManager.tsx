import { useApp } from '../store'
import ProvenanceBadge from './ProvenanceBadge'

const EXTENT_NOTE: Record<string, string> = {
  facilities: 'pilot + 2 km buffer',
}

export default function LayerManager() {
  const { layers, visible, loading, toggle } = useApp()
  const groups = [...new Set(layers.map((l) => l.group))]
  if (!layers.length) return <p className="text-sm text-slate-500">No layers loaded.</p>
  return (
    <div className="space-y-4">
      {groups.map((g) => (
        <section key={g}>
          <h3 className="mb-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">{g}</h3>
          <ul className="space-y-1">
            {layers
              .filter((l) => l.group === g)
              .map((l) => (
                <li key={l.id}>
                  <label className="flex cursor-pointer items-start gap-2 rounded px-1.5 py-1 hover:bg-slate-800/60">
                    <input
                      type="checkbox"
                      className="mt-0.5 accent-sky-400"
                      checked={Boolean(visible[l.id])}
                      onChange={() => toggle(l.id)}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center justify-between gap-2 text-sm text-slate-200">
                        {l.title}
                        <span className="text-xs tabular-nums text-slate-500">
                          {loading[l.id] ? 'loading…' : (EXTENT_NOTE[l.id] ? l.count : l.count_in_pilot).toLocaleString()}
                        </span>
                      </span>
                      <span className="mt-0.5 flex flex-wrap gap-1">
                        {Object.keys(l.data_status).map((s) => (
                          <ProvenanceBadge key={s} status={s} small />
                        ))}
                        <span className="text-[10px] text-slate-500">{EXTENT_NOTE[l.id] ?? 'pilot'}</span>
                      </span>
                    </span>
                  </label>
                </li>
              ))}
          </ul>
        </section>
      ))}
    </div>
  )
}
