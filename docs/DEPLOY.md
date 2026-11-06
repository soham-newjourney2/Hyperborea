# Deploy (P04)

- **Web (Vercel):** `<set after first deploy>` · project `hyperborea` · static Vite build, `VITE_API_URL` → Space.
- **API (HF Space, Docker, CPU):** `https://huggingface.co/spaces/<HF_SPACE>` · API `https://<user>-<space>.hf.space/api/health`.
- **Redeploy:** `. .\scripts\env.ps1; .\scripts\deploy.ps1 -Target api|web|all -WebOrigin https://<app>.vercel.app` (needs `.env` HF_TOKEN/HF_SPACE + `npx vercel login`). Only with the user's go-ahead.
- **Offline fallback:** API up locally → `python scripts/make_snapshots.py` → commit `frontend/public/snapshots/`. Regenerate at the end of every phase.
- **Before a demo:** open the Space URL ~3 min early — free Spaces sleep after inactivity (cold start). If it is down, the web app falls back to snapshots (amber *Offline snapshot* badge).
- **CORS:** Space variable `CORS_ORIGINS` = Vercel origin + `http://localhost:5173` (set by deploy script).
