# Starts backend (:8000, reload) and frontend (:5173) in two PowerShell windows.
$root = Split-Path -Parent $PSScriptRoot
$env_ = Join-Path $root 'scripts\env.ps1'
Start-Process powershell -WorkingDirectory $root -ArgumentList '-NoExit', '-Command',
  ". '$env_'; uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir backend"
Start-Process powershell -WorkingDirectory (Join-Path $root 'frontend') -ArgumentList '-NoExit', '-Command',
  ". '$env_'; npm run dev"
# P14: local LLM explainer (optional) — only if Ollama portable is installed (scripts/install_ollama.py)
if (Test-Path (Join-Path $root 'local\tools\ollama\ollama.exe')) {
  Start-Process powershell -WorkingDirectory $root -ArgumentList '-NoExit', '-Command',
    ". '$env_'; `$env:OLLAMA_HOST = '127.0.0.1:11434'; ollama serve"
  Write-Host 'Ollama   http://127.0.0.1:11434 (local LLM explainer)'
}
Write-Host 'Backend  http://localhost:8000/api/health'
Write-Host 'Frontend http://localhost:5173'
