# Assemble deploy/hf-space/ (Docker Space bundle) from the repo. No network access; safe to run anytime.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root 'deploy\hf-space'
if (Test-Path $out) { Remove-Item -Recurse -Force $out -Confirm:$false }
New-Item -ItemType Directory -Force $out | Out-Null

Copy-Item (Join-Path $root 'backend\Dockerfile') $out
# backend code (no tests, no caches)
robocopy (Join-Path $root 'backend') (Join-Path $out 'backend') /E /XD tests __pycache__ .pytest_cache /XF Dockerfile *.pyc /NFL /NDL /NJH /NJS /NP | Out-Null
# small data the API serves, per region (raw/ never ships): data/regions/<id>/{processed,curated,synthetic,snapshots}
Get-ChildItem (Join-Path $root 'data\regions') -Directory | ForEach-Object {
  foreach ($d in 'processed', 'curated', 'synthetic', 'snapshots') {
    $src = Join-Path $_.FullName $d
    if (Test-Path $src) { robocopy $src (Join-Path $out "data\regions\$($_.Name)\$d") /E /NFL /NDL /NJH /NJS /NP | Out-Null }
  }
}
$cfg = Join-Path $root 'config'
if (Test-Path $cfg) { robocopy $cfg (Join-Path $out 'config') /E /NFL /NDL /NJH /NJS /NP | Out-Null }
else { New-Item -ItemType Directory -Force (Join-Path $out 'config') | Out-Null }
New-Item -ItemType File -Force (Join-Path $out 'config\.keep') | Out-Null

@'
---
title: Hyperborea API
emoji: 🛰️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
license: mit
short_description: Urban intelligence API — Salt Lake Sector V pilot (OSM, ODbL)
---

FastAPI backend for the Hyperborea prototype. Data © OpenStreetMap contributors (ODbL).
Health check: `/api/health`.
'@ | Set-Content -Encoding utf8 (Join-Path $out 'README.md')

$size = (Get-ChildItem $out -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("deploy/hf-space ready: {0:N1} MB" -f $size)
exit 0  # robocopy returns 1 when files were copied; that is success
