# Hyperborea — setup guide (Windows)

Everything runs **inside the project folder**: Python packages go to `.venv`, npm packages to `frontend/node_modules`,
and models, tools and caches to `local/`. Nothing is installed globally except the four prerequisites below.
Every command runs in **PowerShell** from the repo root unless a step says otherwise.

---

## 1. Prerequisites (install once per machine)

| Tool | Version we use | Get it |
|---|---|---|
| Git + **Git LFS** | Git for Windows (includes Git LFS 3.7) | <https://git-scm.com/download/win> |
| Python | **3.12** (3.12.10) | <https://www.python.org/downloads/> — tick "Add python.exe to PATH" |
| Node.js | 26.x (26.12.1) | <https://nodejs.org/> |
| NVIDIA driver | only for the optional local LLM (6 GB VRAM is enough) | <https://www.nvidia.com/Download/index.aspx> |

```powershell
git --version          # any recent Git for Windows
git lfs version        # must print git-lfs/3.x — large files (OSM extracts, rasters) come through LFS
py -3.12 --version     # Python launcher must find 3.12
node --version         # v26.x
```

---

## 2. Clone (the repo is private — ask the repo owner for access)

```powershell
git lfs install                        # once per machine: enables Git LFS hooks for your user
git clone https://github.com/soham-newjourney2/hyperborea.git
cd hyperborea
git lfs pull                           # downloads ~1.2 GB of LFS files (OSM extracts, rasters, raw OSM)
```

> If PowerShell blocks scripts (`running scripts is disabled`), allow them for your user once:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

---

## 3. One-command setup

```powershell
.\scripts\setup.ps1                    # = steps 3a–3d below (safe to re-run)
```

What it does, if you prefer to run it by hand:

```powershell
# 3a. Python virtual environment inside the project
py -3.12 -m venv .venv

# 3b. Activate it + point every cache (pip, npm, osmnx, HF, Ollama models) into local/
. .\scripts\env.ps1                    # dot-source it in EVERY new PowerShell window

# 3c. Python packages: API (FastAPI, GeoPandas, NetworkX, scikit-learn, PyJWT …) + offline pipelines (osmnx, rasterio …)
python -m pip install --upgrade pip
pip install -r requirements-pipelines.txt   # includes backend/requirements.txt

# 3d. Frontend packages (React, CesiumJS, Vite, Tailwind, Recharts, Cytoscape …) from the lockfile
cd frontend; npm ci; cd ..
```

---

## 4. Secrets — `.env` (never committed)

```powershell
copy .env.example .env                 # then edit .env
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste the output as JWT_SECRET
```

| Variable | What to set |
|---|---|
| `ADMIN_PASSWORD` | the team password for the login screen (ask the repo owner; don't keep `change-me`) |
| `JWT_SECRET` | 32+ random characters (command above) |
| `CORS_ORIGINS` | `http://localhost:5173` for local work |
| `EXPLAINER` | `template` (default) or `ollama` if you install the local LLM |
| `OLLAMA_URL` / `OLLAMA_MODEL` | `http://localhost:11434` / `qwen3:4b-instruct-2507-q4_K_M` |
| `VITE_API_URL` | `http://localhost:8000/api` |
| `HF_TOKEN`, `HF_SPACE` | only for deploying (step 9) |

---

## 5. Optional: local LLM explainer (Ollama + Qwen3-4B, ~4.7 GB, not in the repo)

The deterministic template explainer works without this. The LLM only rephrases engine facts; a grounding check
rejects invented numbers (model card: `models/model_cards/llm_explainer.md`).

```powershell
. .\scripts\env.ps1
python scripts/install_ollama.py                      # portable Ollama (MIT) → local/tools/ollama (latest release; we used v0.40.15)
ollama serve                                          # leave this window open (or let dev.ps1 start it)
# in a second window:
. .\scripts\env.ps1
ollama pull qwen3:4b-instruct-2507-q4_K_M             # Qwen3-4B-Instruct-2507, Apache-2.0, 4-bit, ~2.5 GB → local/ollama/models
ollama run qwen3:4b-instruct-2507-q4_K_M "Say hi"     # quick check (Ctrl+D to exit)
```

Use the **instruct-2507** build — the plain `qwen3:4b` is a "thinking" model and leaks its reasoning into answers.

---

## 6. Run the app

```powershell
. .\scripts\env.ps1
.\scripts\dev.ps1                      # opens windows: API :8000 (auto-reload), web :5173, + Ollama if installed
```

- Open <http://localhost:5173> and sign in with `ADMIN_PASSWORD`.
- Use the **Pilot** switcher in the header to change region: Kolkata Sector V, Chennai Velachery, Pune Kharadi
  (London and Sydney show "data pending" until P18/P19).
- Health check: <http://localhost:8000/api/health> (add `?region=pune_kharadi` for another pilot).
- If the API is down, the app opens the **offline snapshot** (amber badge) without login.

---

## 7. Tests and checks

```powershell
. .\scripts\env.ps1
pytest backend/tests -q                # backend: data integrity, engines, endpoints, auth, regions (93 tests)
cd frontend; npm run lint; npm test; npm run build; cd ..   # frontend: oxlint, vitest, type-check + production build
python scripts/audit_data.py           # provenance audit of every region → docs/DATA_AUDIT.md (must say PASS)
```

---

## 8. Rebuilding data (only if you change pipelines or add a region)

Processed data is already in the repo. Each region is built by the same pipelines; the region comes from
`HYPERBOREA_REGION` (ids in `config/regions.yaml`).

```powershell
. .\scripts\env.ps1

# New regions (Chennai, Pune, London, Sydney): all 13 steps in order
.\scripts\build_region.ps1 -Region chennai_velachery               # boundary → OSM → DEM → drainage → power → … → surrogate
.\scripts\build_region.ps1 -Region pune_kharadi -From build_power  # resume from a step after a failure

# Sector V (default region) step by step
python -m pipelines.fetch_osm          # OSM from the Geofabrik extract in local/osm (downloads it if missing)
python -m pipelines.normalize_osm      # → data/processed/hyperborea.gpkg
python -m pipelines.fetch_dem          # Copernicus DEM 30 m (Planetary Computer) → local/rasters/dem.tif
python -m pipelines.build_drainage     # simulated drains, manholes, outfalls, catchments
python -m pipelines.build_power        # simulated transformers + feeders
python -m pipelines.make_water_demo    # DEMO water-quality points (labelled simulated)
python -m pipelines.landcover          # ESA WorldCover + Sentinel-2 NDVI
python -m pipelines.cv_water           # Sentinel-2 NDWI surface water (index, not ML)
python -m pipelines.build_access       # drive graph for travel times
python -m pipelines.climate            # ERA5 1981–today via Open-Meteo
python -m pipelines.make_sites         # candidate development sites S1–S3
python -m pipelines.train_surrogate    # ML flood surrogate (scikit-learn) → models/

# Offline snapshots (API must be running; logs in with ADMIN_PASSWORD from .env)
python scripts/make_snapshots.py                                        # Sector V
$env:HYPERBOREA_REGION='chennai_velachery'; python scripts/make_snapshots.py; Remove-Item Env:HYPERBOREA_REGION
```

Downloads during rebuilds: Geofabrik OSM extracts (eastern 248 MB, southern 559 MB, western 222 MB — already in
`local/osm` via LFS), Copernicus DEM, ESA WorldCover and Sentinel-2 tiles (Microsoft Planetary Computer, no account
needed), ERA5/forecast/CAMS air quality (Open-Meteo, no key). Licences: `docs/DATA_SOURCES.md`.

---

## 9. Deploy (only when the team agrees)

```powershell
npx vercel login                                                     # once, for the web app
.\scripts\deploy.ps1 -Target all -WebOrigin https://<app>.vercel.app # needs HF_TOKEN + HF_SPACE in .env
```

Then set the Hugging Face Space secrets `ADMIN_PASSWORD`, `JWT_SECRET` (32+ chars) and `CORS_ORIGINS`.
Details: `docs/DEPLOY.md`.

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Files in `local/osm` are tiny text files | LFS not pulled: `git lfs install; git lfs pull` |
| `No .venv yet` from env.ps1 | run step 3a |
| Login says "Wrong password" | `ADMIN_PASSWORD` in `.env` differs from the one you typed; restart the API after editing `.env` |
| "Error in sys.excepthook" lines after a pipeline | harmless GDAL shutdown noise in PowerShell 5.1 (exit code is 0) |
| LLM option greyed out | Ollama not running or model not pulled (step 5); the template explainer still works |
| Port 8000/5173 busy | close old dev windows, or `Get-NetTCPConnection -LocalPort 8000` to find the process |

More: `README.md` (overview), `docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`, `CLAUDE.md` + `planning.md` (how we work).
