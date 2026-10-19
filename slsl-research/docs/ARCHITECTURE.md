# SLSL AI Studio — Step 1 Architecture

## Monorepo layout

- `frontend/` — React + TypeScript research UI
- `backend/` — FastAPI API, SQLite persistence, sensor interfaces
- `data/` — recordings and imports (filesystem)
- `artifacts/` — model checkpoints and evaluation outputs
- `docs/` — project documentation

## API

- `GET /api/health` — backend liveness
- `GET /api/system/status` — real counts and setup state from SQLite

## Sensor adapters (interfaces only)

All sources must emit `SensorFrame` with 22 synchronized features. Implementations for CSV import, playback, and hardware are deferred to later milestones.

## Database tables

- `datasets`
- `ml_models`
- `training_jobs`
- `evaluation_runs`
- `activity_logs`
