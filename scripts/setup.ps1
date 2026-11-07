# One-command setup for a fresh clone (Windows / PowerShell). Run from the repo root:
#   git lfs install; git clone <repo>; cd hyperborea; .\scripts\setup.ps1
# Creates .venv (Python 3.12), installs Python + npm packages, pulls LFS files, creates .env from the template.
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
git lfs pull
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
. .\scripts\env.ps1
python -m pip install --upgrade pip
pip install -r requirements-pipelines.txt
Push-Location frontend; npm ci; Pop-Location
if (-not (Test-Path .env)) {
  Copy-Item .env.example .env
  Write-Host "Created .env from .env.example - set ADMIN_PASSWORD and a 32+ char JWT_SECRET (ask the team)." -ForegroundColor Yellow
}
Write-Host "Optional local LLM (not in the repo, 4.7 GB): python scripts/install_ollama.py; ollama pull qwen3:4b-instruct-2507-q4_K_M" -ForegroundColor Cyan
Write-Host "Done. Start with: . .\scripts\env.ps1; .\scripts\dev.ps1" -ForegroundColor Green
