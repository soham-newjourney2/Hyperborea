# Setup guide (Windows / PowerShell)

Everything runs **inside the project folder**: Python packages in `.venv`, npm packages in `frontend/node_modules`,
models, caches and (optionally) portable Python / Node in `local/`. Nothing is installed globally except the
prerequisites below. Run every command in **PowerShell from the repo root** unless a step says otherwise.

| You want to… | Do steps |
|---|---|
| run the app | 1 → 2 → 3 → 5 |
| also use the local LLM (Ask Hyperborea, explanations) | + 4 |
| change pipelines or add a city | + 7 (full data download) |

---

## 1. Prerequisites (once per machine)

| Tool | Version | Get it |
|---|---|---|
| Git + **Git LFS** | Git for Windows (includes Git LFS 3.x) | <https://git-scm.com/download/win> |
| Python | **3.12** | system install (<https://www.python.org/downloads/>, tick "Add python.exe to PATH") **or** portable, below |
| Node.js | **24 LTS** or newer (tested: 24.22, 26.12) | system install (<https://nodejs.org/>) **or** portable, below |
| NVIDIA GPU + driver | only for the optional local LLM (6 GB VRAM is enough) | <https://www.nvidia.com/Download/index.aspx> |

```powershell
git lfs version        # git-lfs/3.x — the larger data files come through Git LFS
py -3.12 --version     # system Python: the launcher must find 3.12
node --version         # system Node: v24 or newer
```
If PowerShell refuses to run scripts (`running scripts is disabled`): `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

### Optional — keep Python and Node inside the project
`local/tools/` is git-ignored. When these folders exist, the scripts use them instead of the system installs:

| Folder | Used by | Contents |
|---|---|---|
| `local/tools/python/` | `setup.ps1` builds `.venv` from it | a standalone CPython 3.12 (`python.exe` directly inside), e.g. the `install_only` build from [python-build-standalone](https://github.com/astral-sh/python-build-standalone/releases) |
| `local/tools/node/` | `env.ps1` puts it first on `PATH` | the Node.js Windows zip, unpacked (`node.exe` directly inside) |

```powershell
# Node 24 LTS, portable (after step 2, from the repo root)
$v = 'v24.22.3'; New-Item -ItemType Directory -Force local\cache, local\tools | Out-Null
Invoke-WebRequest -UseBasicParsing "https://nodejs.org/dist/$v/node-$v-win-x64.zip" -OutFile local\cache\node.zip
Expand-Archive local\cache\node.zip local\cache\node-x; Move-Item "local\cache\node-x\node-$v-win-x64" local\tools\node
Remove-Item -Recurse local\cache\node.zip, local\cache\node-x
```
Check the zip against `https://nodejs.org/dist/<version>/SHASUMS256.txt` before unpacking if you want to be strict.

---

## 2. Clone (private repo — ask the owner for access)

A normal clone downloads **all ~1.7 GB** of LFS files. To run the app you need only **~12 MB** of them, so clone without
LFS downloads and let the setup script fetch what is needed:

```powershell
git lfs install                                   # once per machine
$env:GIT_LFS_SKIP_SMUDGE = "1"                    # clone without downloading LFS files
git clone https://github.com/soham-newjourney2/z-Hyperborea.git hyperborea
Remove-Item Env:GIT_LFS_SKIP_SMUDGE
cd hyperborea
```

| LFS content | Size | Needed for |
|---|---|---|
| `data/regions/*/processed/` (large GeoPackages) | ~12 MB | **running the app** |
| `data/regions/*/raw/` (OSM clips as fetched) | ~450 MB | rebuilding processed data |
| `local/regions/*/osm/` (Geofabrik / BBBike extracts) | ~1.2 GB | re-fetching OSM |
| `local/regions/*/rasters/` (DEMs) | ~7 MB | rebuilding drainage |

---

## 3. One-command setup

```powershell
.\scripts\setup.ps1          # run-only data (~12 MB) + .venv + Python packages + npm packages + .env
.\scripts\setup.ps1 -Full    # same, with every LFS file (~1.7 GB) — only if you will rebuild data
```

What it does, step by step (if you prefer to run it by hand):

```powershell
git lfs pull --include "data/regions/*/processed/**"   # run-only data (or: git lfs pull  for everything)
py -3.12 -m venv .venv                                  # or: local\tools\python\python.exe -m venv .venv
. .\scripts\env.ps1                                     # activate .venv, portable Node on PATH, caches in local/ (every new shell)
python -m pip install --upgrade pip
pip install -r requirements-pipelines.txt               # API + pipelines (includes backend/requirements.txt)
cd frontend; npm ci; cd ..                              # frontend packages from package-lock.json
copy .env.example .env                                  # the defaults work as-is
```

### `.env` (never committed)
| Variable | Default | Meaning |
|---|---|---|
| `AUTH_REQUIRED` | `false` | `false`: open access, no login · `true`: admin login (set the two below) |
| `ADMIN_PASSWORD` | `change-me` | login password when `AUTH_REQUIRED=true` |
| `JWT_SECRET` | empty | ≥ 32 random characters when `AUTH_REQUIRED=true`: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | `http://localhost:5173` | browser origins allowed to call the API |
| `EXPLAINER` | `template` | `template` or `ollama` (default answer mode) |
| `OLLAMA_URL` / `OLLAMA_MODEL` | `http://localhost:11434` / `qwen3:4b-instruct-2507-q4_K_M` | local LLM |
| `VITE_API_URL` | `http://localhost:8000/api` | where the frontend finds the API |

---

## 4. Optional — local LLM (Ollama + Qwen3-4B-Instruct, ~4.7 GB, not in the repo)

Used by **Ask Hyperborea** and the plain-language explanations in Flood Simulation. Without it, both use deterministic
templates. The LLM only rephrases engine facts; any answer containing a number that is not in the facts is rejected.

```powershell
. .\scripts\env.ps1
python scripts/install_ollama.py                      # portable Ollama (MIT) → local/tools/ollama
ollama serve                                          # keep this window open (dev.ps1 also starts it)
# second window:
. .\scripts\env.ps1
ollama pull qwen3:4b-instruct-2507-q4_K_M             # Apache-2.0, 4-bit, ~2.5 GB → local/ollama/models
```
Use the **instruct-2507** build; the plain `qwen3:4b` is a "thinking" model that leaks its reasoning into answers.

---

## 5. Run

```powershell
. .\scripts\env.ps1
.\scripts\dev.ps1            # opens windows: API :8000 (auto-reload), web :5173, Ollama :11434 if installed
```

Open <http://localhost:5173>. No login by default. Close the windows to stop the servers.

**The screen:** module sidebar on the left (16 modules), the map in the middle (Satellite / Street, 2D / 3D buttons
above it), the active module's panel on the right. The header has the **Pilot** switcher and the theme button
(dark ↔ light, remembered in this browser).

| Module | Try |
|---|---|
| **Command Centre** | click a building, road or facility → inspector; layer switches and provenance badges |
| **3D Digital Twin** | 3D view with extruded buildings; **Home** re-frames the pilot |
| **Flood Simulation** | run *Extreme 80×2h*, click an affected asset → **Why?**; the upgrade optimiser at the bottom |
| **Early Warning** | 72 h outlook (or "try a demo burst" when the forecast is dry) |
| **Data Validation** | switch Pilot to **Chennai** → Sentinel-1 scorecard + "radar flood map" layer |
| **Development Screening** | pick site S1–S3 → Assess → Compare A/B/C |
| **Accessibility** | drive times to hospitals / fire stations / metro; run a flood first for the Δ view |
| **Ask Hyperborea** | "Which hospitals lose access at 60 mm/h for 2 hours?" |
| **Reports** | what a report contains; after a flood run, **Open report** in Flood Simulation gives the printable report (PDF / JSON / CSV) |

### Deep links
| Link | Opens |
|---|---|
| `?region=london_stratford` | another pilot (`sector_v` default, `chennai_velachery`, `pune_kharadi`, `london_stratford`, `sydney_green_square`) |
| `?module=<id>` | a module: `command` `twin` `infrastructure` `graph` `flood` `warning` `validation` `development` `upgrade` `access` `weather` `air` `water` `land` `ask` `reports` |
| `?scenario=extreme` | Flood Simulation with that preset already run (`moderate`, `design`, `heavy`, `extreme`) |
| `?env=air` · `?tab=relations` | older link forms, still supported |
| `?layers=sar_flood,-buildings` | switch layers on / off on load |
| `?asset=<asset_id>` | select an asset on load |

API health: <http://localhost:8000/api/health> (add `?region=london_stratford` for another city).
If the API is not running, the web app opens **offline snapshots** (amber "Offline snapshot" badge) for every city.

---

## 6. Tests and checks

```powershell
. .\scripts\env.ps1
pytest backend/tests -q                                    # 138 tests: engines, endpoints, regions, add-ons
cd frontend; npm run lint; npm test; npm run build; cd ..   # oxlint, vitest (9 tests), type-check + production build
python scripts/audit_data.py                               # provenance audit of all five cities — must say PASS
```

---

## 7. Rebuilding data (pipelines changed, or a new city)

Run `.\scripts\setup.ps1 -Full` (or `git lfs pull`) first. Cities are defined in `config/regions.yaml`; the pipelines pick
the city from `HYPERBOREA_REGION`.

```powershell
. .\scripts\env.ps1
.\scripts\build_region.ps1 -Region chennai_velachery              # all 13 steps: boundary → OSM → DEM → drainage → power →
                                                                  # water demo → land cover → NDWI → access → climate → sites → surrogate
.\scripts\build_region.ps1 -Region pune_kharadi -From build_power  # resume from a step
$env:HYPERBOREA_REGION = 'chennai_velachery'; python -m pipelines.validate_flood; Remove-Item Env:HYPERBOREA_REGION  # Sentinel-1 validation
```
Sector V (`sector_v`) keeps its own boundary tools: `python -m pipelines.scan_candidates` → `python -m pipelines.make_boundary`,
then `build_region.ps1 -Region sector_v -From fetch_osm`.

**New city:** add an entry to `config/regions.yaml` (id, name, bbox, timezone, `metric_crs` = UTM zone, `aq_index`,
`design_storm_mm_h`, `osm_pbf` URL), register any new data source in `docs/DATA.md`, then
`.\scripts\build_region.ps1 -Region <id>`.

**Offline snapshots** (API running), once per city:
```powershell
foreach ($r in 'sector_v','chennai_velachery','pune_kharadi','london_stratford','sydney_green_square') {
  $env:HYPERBOREA_REGION = $r; python scripts/make_snapshots.py }
Remove-Item Env:HYPERBOREA_REGION
```

Downloads during rebuilds: OSM extracts (Geofabrik, BBBike), Copernicus DEM, ESA WorldCover, Sentinel-1/2 (Microsoft
Planetary Computer — no account), EA LiDAR (London, no account), ERA5 / forecast / CAMS (Open-Meteo — no key).
Sources and licences: [DATA.md](DATA.md). Rebuilds are CPU-heavy (minutes per step on a laptop).

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `running scripts is disabled` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| A city shows no buildings / API error "No data loaded" | its processed LFS files are pointers: `git lfs pull --include "data/regions/*/processed/**"` |
| Pipeline says an OSM extract is missing or tiny | full LFS not pulled: `git lfs pull` (or `.\scripts\setup.ps1 -Full`) |
| `No .venv yet` from env.ps1 | `py -3.12 -m venv .venv` (or the portable Python), then re-run setup |
| `node` not found / wrong version | install Node 24+, or unpack it to `local/tools/node` (step 1) and open a new shell with `. .\scripts\env.ps1` |
| A login screen appears | `AUTH_REQUIRED=true` in `.env` — set it to `false` and restart the API |
| Map is grey / no basemap | Satellite (EOX) and Street (OSM) tiles need internet; layers still draw without them |
| Header says "Offline snapshot" | the API is not reachable — start it with `.\scripts\dev.ps1`; the app shows frozen results meanwhile |
| "Error in sys.excepthook" after a pipeline step | harmless GDAL shutdown noise in PowerShell 5.1 (exit code is 0) |
| "Local LLM" greyed out | Ollama not running or model not pulled (step 4); templates still work |
| Port 8000 / 5173 busy | close old dev windows, or `Get-NetTCPConnection -LocalPort 8000` to find the process |

More: [../README.md](../README.md) (overview) · [ARCHITECTURE.md](ARCHITECTURE.md) (design, API) · [DATA.md](DATA.md) (data, provenance, sources).
