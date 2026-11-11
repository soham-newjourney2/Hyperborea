import { useEffect, useRef, useState } from 'react'
import { getExplainStatus, postAsk, runFlood, type AskAnswer } from '../lib/api'
import { useApp } from '../store'

// P24 ask-the-twin: question → engine run → answer grounded in the result. Template answers by default; the local LLM
// only rephrases facts and is rejected (→ template) if it invents a number.
const EXAMPLES = [
  'Which hospitals lose access if 60 mm/h hits for 2 hours?',
  'What happens to power in an extreme storm?',
  'How many km of road flood with 120 mm in 3 hours?',
  'Are schools affected during heavy rain?',
]

export default function AskPanel() {
  const setFlood = useApp((s) => s.setFlood)
  const [q, setQ] = useState('')
  const [mode, setMode] = useState<'template' | 'llm'>('template')
  const [llm, setLlm] = useState(false)
  const [busy, setBusy] = useState(false)
  const [history, setHistory] = useState<AskAnswer[]>([])
  const [err, setErr] = useState<string | null>(null)
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const c = new AbortController()
    getExplainStatus(c.signal).then((s) => setLlm(s.llm.available)).catch(() => {})
    return () => c.abort()
  }, [])
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth' }) // block body: newer Chromium returns a Promise here
  }, [history])
  const ask = async (text: string) => {
    if (!text.trim()) return
    setBusy(true)
    setErr(null)
    try {
      const a = await postAsk(text.trim(), mode)
      setHistory((h) => [...h, a])
      setQ('')
    } catch (e) {
      setErr(`Ask failed: ${(e as Error).message} (needs the live API)`)
    } finally {
      setBusy(false)
    }
  }
  const showOnMap = async (a: AskAnswer) => {
    const p = a.intent
    setFlood(await runFlood(p.preset ? { preset: p.preset, condition_scale: 1 } : { rain_mm_h: p.rain_mm_h, duration_h: p.duration_h, condition_scale: 1 }))
  }
  return (
    <div className="flex h-full flex-col gap-2">
      <div className="rounded border border-sky-500/40 bg-sky-500/10 px-2.5 py-1.5 text-[11px] text-sky-200">
        Ask the twin — answers come only from the rule engine's scenario result (simulated networks, modelled rain).
      </div>
      <div className="flex items-center gap-2 text-[11px] text-slate-400">
        Answer:
        {(['template', 'llm'] as const).map((m) => (
          <button key={m} onClick={() => setMode(m)} disabled={m === 'llm' && !llm}
            className={`rounded px-1.5 py-0.5 ${mode === m ? 'bg-sky-500/20 text-sky-300 ring-1 ring-sky-500/50' : 'hover:text-slate-200'} disabled:opacity-40`}>
            {m === 'template' ? 'Template' : 'Local LLM'}
          </button>
        ))}
        {!llm && <span className="text-[10px] text-slate-500">(LLM offline)</span>}
      </div>
      <div className="min-h-0 flex-1 space-y-2 overflow-y-auto">
        {history.length === 0 && (
          <div className="space-y-1">
            <p className="text-[11px] text-slate-500">Try:</p>
            {EXAMPLES.map((e) => (
              <button key={e} onClick={() => ask(e)} disabled={busy}
                className="block w-full rounded border border-slate-800 px-2 py-1 text-left text-xs text-slate-300 hover:border-slate-600">{e}</button>
            ))}
          </div>
        )}
        {history.map((a, i) => (
          <div key={i} className="space-y-1">
            <p className="ml-6 rounded bg-slate-800 px-2 py-1 text-xs text-slate-100">{a.question}</p>
            <div className="mr-4 rounded border border-slate-700 bg-slate-900/70 px-2 py-1.5">
              <p className="text-xs leading-snug text-slate-100">{a.answer}</p>
              <p className="mt-1 text-[10px] text-slate-500">
                parsed by {a.parser} · answer {a.answer_mode}{a.grounding_rejected.length ? ` (LLM rejected: ${a.grounding_rejected.join(', ')})` : ''}
                {' '}· scenario {a.intent.rain_mm_h} mm/h × {a.intent.duration_h} h{a.notes.length ? ` · ${a.notes.join('; ')}` : ''}
              </p>
              <button onClick={() => showOnMap(a)} className="mt-1 text-[11px] text-sky-300 hover:underline">Show this scenario on the map →</button>
            </div>
          </div>
        ))}
        <div ref={end} />
      </div>
      {err && <p className="text-[11px] text-red-300">{err}</p>}
      <form onSubmit={(e) => { e.preventDefault(); ask(q) }} className="flex gap-1.5">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Which roads close at 70 mm/h for 1 hour?"
          aria-label="Question for the twin"
          className="min-w-0 flex-1 rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-xs text-slate-100 outline-none focus:border-sky-500" />
        <button disabled={busy || !q.trim()} className="rounded bg-sky-500 px-3 text-xs font-semibold text-slate-950 hover:bg-sky-400 disabled:opacity-50">
          {busy ? '…' : 'Ask'}
        </button>
      </form>
    </div>
  )
}
