# Dot-source in every shell:  . .\scripts\env.ps1
# Keeps every download/cache inside the project (planning D-05, §9).
$root = Split-Path -Parent $PSScriptRoot
$local = Join-Path $root 'local'
$dirs = 'cache\pip','cache\npm','cache\osmnx','cache\mpl','hf','torch','ollama\models','tools','tiles','rasters'
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path (Join-Path $local $d) | Out-Null }

$env:HYPERBOREA_ROOT = $root
$env:PIP_CACHE_DIR   = Join-Path $local 'cache\pip'
$env:npm_config_cache = Join-Path $local 'cache\npm'
$env:HF_HOME         = Join-Path $local 'hf'
$env:TORCH_HOME      = Join-Path $local 'torch'
$env:MPLCONFIGDIR    = Join-Path $local 'cache\mpl'
$env:OLLAMA_MODELS   = Join-Path $local 'ollama\models'
$env:OSMNX_CACHE     = Join-Path $local 'cache\osmnx'
$ollama = Join-Path $local 'tools\ollama'
if (Test-Path $ollama) { $env:PATH = "$ollama;$env:PATH" }

$venv = Join-Path $root '.venv\Scripts\Activate.ps1'
if (Test-Path $venv) { . $venv } else { Write-Host 'No .venv yet - create it in P01: python -m venv .venv' }
Write-Host "Hyperborea env ready ($root)"
