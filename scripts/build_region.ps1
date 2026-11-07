# P17: build every data layer for one pilot region (D-22). Same pipelines as Sector V, region from HYPERBOREA_REGION.
#   . .\scripts\env.ps1; .\scripts\build_region.ps1 -Region chennai_velachery [-From normalize_osm]
# Snapshots need the API: start it, then  $env:HYPERBOREA_REGION='<id>'; python scripts/make_snapshots.py
param(
  [Parameter(Mandatory = $true)][string]$Region,
  [string]$From = 'make_region_boundary'
)
# No ErrorActionPreference=Stop: PS 5.1 turns native stderr (Python warnings) into errors; exit codes are checked.
$steps = @('make_region_boundary', 'fetch_osm', 'normalize_osm', 'fetch_dem', 'build_drainage', 'build_power',
           'make_water_demo', 'landcover', 'cv_water', 'build_access', 'climate', 'make_sites', 'train_surrogate')
$start = [array]::IndexOf($steps, $From)
if ($start -lt 0) { throw "Unknown step $From. Steps: $($steps -join ', ')" }
$env:HYPERBOREA_REGION = $Region
try {
  foreach ($s in $steps[$start..($steps.Length - 1)]) {
    $t = Get-Date
    Write-Host "== $Region | $s" -ForegroundColor Cyan
    python -m "pipelines.$s"
    if ($LASTEXITCODE -ne 0) { throw "$s failed (exit $LASTEXITCODE) - rerun with -From $s" }
    Write-Host ("   {0:n0} s" -f ((Get-Date) - $t).TotalSeconds)
  }
} finally {
  Remove-Item Env:HYPERBOREA_REGION -ErrorAction SilentlyContinue
}
