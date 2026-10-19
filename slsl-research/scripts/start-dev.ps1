# SLSL AI Studio — local launcher (does not reinstall packages)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$venv = Join-Path $backend ".venv\Scripts\Activate.ps1"
$nodeModules = Join-Path $frontend "node_modules"

if (-not (Test-Path $venv)) {
    Write-Host "ERROR: Backend virtual environment not found." -ForegroundColor Red
    Write-Host "Run: cd backend; py -3.11 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt"
    exit 1
}

if (-not (Test-Path $nodeModules)) {
    Write-Host "ERROR: Frontend dependencies not installed." -ForegroundColor Red
    Write-Host "Run: cd frontend; npm install"
    exit 1
}

Write-Host "Starting SLSL AI Studio..."
Write-Host "  Backend:  http://127.0.0.1:8000"
Write-Host "  Frontend: http://localhost:5173"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; .\.venv\Scripts\Activate.ps1; alembic upgrade head; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

Start-Sleep -Seconds 3

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontend'; npm run dev"

Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"

Write-Host "Launcher complete. Close the terminal windows to stop servers."
