# SLSL AI Studio — Architecture

## Overview

Local-first research application for continuous Sri Lankan Sign Language recognition from two-glove sensor data.

```
CSV / Live frames → Preprocessing → CNN–BiLSTM–CTC → Gloss sequence → English sentence
                                  ↘ Motion features → Emotion classifier
```

## Module responsibilities

| Area | Path | Role |
|------|------|------|
| API | `backend/app/api/routes/` | REST endpoints per feature |
| Datasets | `backend/app/services/dataset_service.py` | Import, label, split, synthetic generation |
| Training | `backend/app/ml/trainer.py`, `scripts/train_worker.py` | CTC training subprocess |
| Evaluation | `backend/app/ml/evaluator.py` | Held-out metrics, no label leakage |
| Inference | `backend/app/ml/inference.py` | Bundle load, sensor-only decode |
| Playground | `backend/app/services/playground_service.py` | Upload recognition + history |
| Registry | `backend/app/services/model_registry.py` | Activate, archive, import/export bundles |
| Sensors | `backend/app/sensors/` | `SensorFrame` adapters (CSV, playback, hardware stub) |

## Adding a new input adapter

1. Implement `SensorSource` in `backend/app/sensors/`.
2. Emit `SensorFrame(timestamp_ms, features×22)` — see `docs/DATASETS.md`.
3. Wire into Playground live session or import flow.
4. Do not change preprocessing dimensions without updating `feature_schema.json`.

## Data stores

- **SQLite** — datasets, models, jobs, evaluations, recognition history, activity log
- **Filesystem** — `data/datasets/`, `artifacts/models/`, `artifacts/evaluations/`

## Frontend

React + TypeScript + TanStack Query. Five nav sections; settings via sidebar dialog.
