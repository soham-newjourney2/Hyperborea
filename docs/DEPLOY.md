# Deploy

- **Web (Vercel):** `<set after first deploy>` · project `hyperborea` · static Vite build, `VITE_API_URL` → Space.
- **API (HF Space, Docker, CPU):** `https://huggingface.co/spaces/<HF_SPACE>` · API `https://<user>-<space>.hf.space/api/health`.
- **Redeploy:** `. .\scripts\env.ps1; .\scripts\deploy.ps1 -Target api|web|all -WebOrigin https://<app>.vercel.app` (needs `.env` HF_TOKEN/HF_SPACE + `npx vercel login`). Only with the user's go-ahead.
- **Space secrets (set in the HF UI after the first upload):** open access by default (P20, D-24); for a login set `AUTH_REQUIRED=true` + `ADMIN_PASSWORD` (the judges' password), `JWT_SECRET` (≥ 32 random characters — PyJWT warns on shorter keys), `CORS_ORIGINS` (set by the deploy script). The hosted explainer is the template (no LLM on CPU). The Space **refuses login** (503) while `ADMIN_PASSWORD` is the default; a missing/short `JWT_SECRET` falls back to a random per-process key (sessions end on restart).
- **Offline fallback:** API up locally → `python scripts/make_snapshots.py` (logs in only if `AUTH_REQUIRED=true`) → commit `frontend/public/snapshots/regions/<id>/` (one run per region: `$env:HYPERBOREA_REGION='<id>'`). Offline mode opens without login.
- **Before a demo:** open the Space URL ~3 min early — free Spaces sleep after inactivity (cold start + data load). See [DEMO_SCRIPT.md](DEMO_SCRIPT.md).
- **Checks:** `pytest -q` · `cd frontend; npm test; npm run build` · `python scripts/audit_data.py`.
