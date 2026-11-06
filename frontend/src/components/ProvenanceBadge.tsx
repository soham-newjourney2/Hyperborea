import { statusStyle, type StatusStyle } from '../lib/provenance'

export function Chip({ style, count, small }: { style: StatusStyle; count?: number; small?: boolean }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ring-1 ${small ? 'px-1.5 py-px text-[10px]' : 'px-2 py-0.5 text-xs'}`}
      style={{
        color: style.color,
        backgroundColor: `${style.color}1f`,
        boxShadow: `inset 0 0 0 1px ${style.color}66`,
        borderStyle: style.dashed ? 'dashed' : undefined,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: style.color }} />
      {style.label}
      {count !== undefined && <span className="opacity-70">{count.toLocaleString()}</span>}
    </span>
  )
}

export default function ProvenanceBadge({ status, count, small }: { status: string; count?: number; small?: boolean }) {
  return <Chip style={statusStyle(status)} count={count} small={small} />
}
