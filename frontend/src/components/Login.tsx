import { useState } from 'react'
import { login } from '../lib/api'
import { setSession } from '../lib/auth'

export default function Login({ onDone }: { onDone: (role: string) => void }) {
  const [pw, setPw] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setErr(null)
    try {
      const r = await login(pw)
      setSession(r.access_token, r.role)
      onDone(r.role)
    } catch (x) {
      setErr((x as Error).message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="login-screen flex h-full items-center justify-center bg-[radial-gradient(ellipse_at_center,var(--panel-2)_0%,var(--bg)_70%)]">
      <form onSubmit={submit} className="w-80 space-y-3 rounded-lg border border-slate-800 bg-slate-950/90 p-5 shadow-2xl">
        <div className="flex items-center gap-3">
          <img src="/hyperborea-mark.png" alt="" className="h-11 w-11 rounded-xl border border-pink-500/50 bg-[#0d0a11] object-cover shadow-[0_0_20px_rgba(255,61,154,0.16)]" />
          <div>
            <h1 className="text-lg font-semibold tracking-[0.3em] text-pink-200">HYPERBOREA</h1>
            <p className="text-xs text-slate-500">URBAN INTELLIGENCE PLATFORM</p>
          </div>
        </div>
        <label className="block text-xs text-slate-400">
          Password
          <input type="password" autoFocus value={pw} onChange={(e) => setPw(e.target.value)}
            className="mt-1 w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-100 outline-none focus:border-sky-500" />
        </label>
        {err && <p className="text-xs text-red-300">{err}</p>}
        <button disabled={busy || !pw} className="w-full rounded bg-sky-500 py-1.5 text-sm font-semibold text-slate-950 hover:bg-sky-400 disabled:opacity-50">
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="text-[10px] leading-snug text-slate-500">
          Session lasts 12 h in this browser tab. If the API is unreachable the app opens the offline snapshot without login.
        </p>
      </form>
    </div>
  )
}
