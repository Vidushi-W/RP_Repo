# Start SLSL AI Studio (backend + frontend)
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

Write-Host "Starting backend on http://127.0.0.1:8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backend'; if (Test-Path .\.venv\Scripts\Activate.ps1) { .\.venv\Scripts\Activate.ps1 }; alembic upgrade head; uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

Start-Sleep -Seconds 2
Write-Host "Starting frontend on http://localhost:5173"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontend'; npm run dev"
