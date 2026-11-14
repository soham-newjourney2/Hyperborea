# One-command setup for a fresh clone (Windows / PowerShell). Run from the repo root. Guide: docs/SETUP.md
#   .\scripts\setup.ps1          run-only: LFS files the app needs (~12 MB of processed data)
#   .\scripts\setup.ps1 -Full    everything in LFS (~1.7 GB: OSM extracts + raw OSM, needed only to rebuild data)
# Creates .venv (Python 3.12), installs Python + npm packages, creates .env from the template. Safe to re-run.
param([switch]$Full)
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if ($Full) { git lfs pull } else { git lfs pull --include "data/regions/*/processed/**" }
$py = Join-Path $root 'local\tools\python\python.exe'   # portable Python 3.12 (optional; else py launcher)
if (-not (Test-Path .venv)) { if (Test-Path $py) { & $py -m venv .venv } else { py -3.12 -m venv .venv } }
. .\scripts\env.ps1
python -m pip install --upgrade pip
pip install -r requirements-pipelines.txt
Push-Location frontend; npm ci; Pop-Location
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "Created .env from .env.example - the defaults work (open access, no login)." -ForegroundColor Yellow
}
Write-Host "Optional local LLM (not in the repo, ~4.7 GB): python scripts/install_ollama.py; ollama pull qwen3:4b-instruct-2507-q4_K_M" -ForegroundColor Cyan
Write-Host "Done. Start with: . .\scripts\env.ps1; .\scripts\dev.ps1  ->  http://localhost:5173" -ForegroundColor Green
