import { useEffect, useState } from 'react'
import { getWarning, type WarningOutlook } from '../lib/api'
import { useApp } from '../store'
import { LEVEL_STYLE } from '../lib/styles'

// P21: slim strip under the header when the 72 h outlook reaches "watch" or "warning". Click → Disaster tab.
export default function WarningBanner() {
  const setRightTab = useApp((s) => s.setRightTab)
  const [w, setW] = useState<WarningOutlook | null>(null)
  useEffect(() => {
    const c = new AbortController()
    getWarning(c.signal).then(setW).catch(() => {})
    return () => c.abort()
  }, [])
  if (!w || w.level === 'none') return null
  const st = LEVEL_STYLE[w.level]
  return (
    <button onClick={() => setRightTab('disaster')}
      className={`flex w-full items-center gap-2 border-b px-4 py-1 text-left text-xs ${st.box} ${st.text}`}>
      <span className="font-semibold uppercase tracking-wider">{st.label}</span>
      <span className="truncate">{w.headline}</span>
      <span className="ml-auto shrink-0 text-[10px] text-slate-400">estimate · not an official warning · open Disaster tab →</span>
    </button>
  )
}
