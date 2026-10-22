param([int]$Port = 8010)
$ErrorActionPreference = 'Stop'
$appRoot = Split-Path $PSScriptRoot -Parent
$repoRoot = Split-Path $appRoot -Parent
$python = Join-Path $repoRoot 'slsl-research\backend\.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Create the backend Python environment and install app/server/requirements.txt first.' }
Push-Location (Join-Path $appRoot 'server')
try { & $python -m uvicorn client_api.main:create_app --factory --host 127.0.0.1 --port $Port }
finally { Pop-Location }
