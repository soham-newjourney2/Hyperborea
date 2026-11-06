// Provenance status → colour (planning §6, P03 step 6). Used by badges, legend and map styling.
export type DataStatus = 'observed' | 'curated' | 'modelled' | 'simulated' | 'unknown'

export interface StatusStyle {
  label: string
  color: string // hex, for Cesium + inline styles
  dashed: boolean // simulated layers get a dashed outline on the map
}

export const STATUS_STYLES: Record<DataStatus, StatusStyle> = {
  observed: { label: 'Observed', color: '#3b82f6', dashed: false },
  curated: { label: 'Curated', color: '#14b8a6', dashed: false },
  modelled: { label: 'Modelled', color: '#f59e0b', dashed: false },
  simulated: { label: 'Simulated', color: '#a855f7', dashed: true },
  unknown: { label: 'Unknown', color: '#64748b', dashed: false },
}

export function statusStyle(status: string | null | undefined): StatusStyle {
  return STATUS_STYLES[(status ?? 'unknown') as DataStatus] ?? STATUS_STYLES.unknown
}

// Building height provenance (attrs.height_status) — not a DataStatus, shown as its own chip.
export const HEIGHT_STATUS: Record<string, StatusStyle> = {
  observed: { label: 'Height observed', color: '#3b82f6', dashed: false },
  modelled: { label: 'Height modelled (levels × 3.2 m)', color: '#f59e0b', dashed: false },
  assumed: { label: 'Height assumed (9 m default)', color: '#64748b', dashed: false },
}
