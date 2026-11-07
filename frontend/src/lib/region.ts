// P16 multi-region: the active pilot comes from the URL (?region=<id>, default sector_v). Switching reloads the
// app so layers, scenarios and caches never mix regions.
export const DEFAULT_REGION = 'sector_v'

function fromUrl(): string {
  try {
    return new URLSearchParams(window.location.search).get('region') || DEFAULT_REGION
  } catch {
    return DEFAULT_REGION
  }
}

export const REGION: string = fromUrl()
export const isDefaultRegion = (id: string = REGION) => id === DEFAULT_REGION

/** `region=<id>` for non-default regions (default keeps the pre-P16 URLs and snapshot names). */
export const regionQuery = (id: string = REGION) => (isDefaultRegion(id) ? '' : `region=${encodeURIComponent(id)}`)

export function withRegion(url: string, id: string = REGION): string {
  const q = regionQuery(id)
  return q ? `${url}${url.includes('?') ? '&' : '?'}${q}` : url
}

export function switchRegion(id: string) {
  const u = new URL(window.location.href)
  u.search = regionQuery(id) ? `?${regionQuery(id)}` : '' // drop asset/scenario deep links of the old region
  window.location.assign(u.toString())
}
