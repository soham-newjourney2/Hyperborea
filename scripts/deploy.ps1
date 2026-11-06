# P04 deploy. Run ONLY with the user's go-ahead. Needs .env: HF_TOKEN, HF_SPACE; Vercel: `npx vercel login` done once.
#   .\scripts\deploy.ps1 -Target api  -WebOrigin https://hyperborea.vercel.app
#   .\scripts\deploy.ps1 -Target web
#   .\scripts\deploy.ps1 -Target all  -WebOrigin https://hyperborea.vercel.app
param(
  [ValidateSet('api', 'web', 'all')][string]$Target = 'all',
  [string]$WebOrigin = '',
  [string]$Project = 'hyperborea'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
. (Join-Path $root 'scripts\env.ps1') | Out-Null

function Get-DotEnv([string]$key) {
  $line = Get-Content (Join-Path $root '.env') | Where-Object { $_ -match "^\s*$key\s*=" } | Select-Object -First 1
  if (-not $line) { throw "$key missing in .env" }
  return (($line -split '=', 2)[1] -split '#')[0].Trim()
}
$space = Get-DotEnv 'HF_SPACE'
$spaceUrl = 'https://' + ($space.ToLower() -replace '[/_.]', '-') + '.hf.space'

if ($Target -in 'api', 'all') {
  & (Join-Path $root 'scripts\build_space.ps1')
  $cors = (@($WebOrigin, 'http://localhost:5173') | Where-Object { $_ }) -join ','
  python (Join-Path $root 'scripts\deploy_space.py') --cors $cors
  if ($LASTEXITCODE) { throw 'Space upload failed' }
}

if ($Target -in 'web', 'all') {
  Push-Location (Join-Path $root 'frontend')
  try {
    npx vercel link --yes --project $Project
    npx vercel pull --yes --environment=production
    $env:VITE_API_URL = "$spaceUrl/api"
    npx vercel build --prod
    if ($LASTEXITCODE) { throw 'vercel build failed' }
    npx vercel deploy --prebuilt --prod
  } finally { Pop-Location }
}
Write-Host "API: $spaceUrl/api/health  (first boot of the Space takes a few minutes)"
