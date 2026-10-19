# SLSL AI Studio

Local-first research application for **Intelligent Continuous Sri Lankan Sign Language Understanding** using two-glove sensor input, CTC sign recognition, and motion-based emotion detection.

## Features

| Section | Purpose |
|---------|---------|
| **Overview** | System health, setup checklist, recent activity |
| **Datasets** | Import, label, split, synthetic generation |
| **Training** | CNN–BiLSTM–CTC training, model registry, workspace reset |
| **Evaluation** | Held-out WER and per-recording analysis |
| **Playground** | CSV recognition, live playback, vocabulary dictionary |

## Prerequisites

- Python 3.11+
- Node.js 20+

## Installation

```powershell
cd slsl-research\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu
copy ..\.env.example .env
alembic upgrade head

cd ..\frontend
npm install
```

## Launch

```powershell
cd slsl-research
.\scripts\start-dev.ps1
```

Opens http://localhost:5173 (checks venv and node_modules; does not reinstall packages).

Manual start:

```powershell
# Terminal 1 — backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev
```

## Typical workflow

1. **Datasets** → Generate Synthetic or import CSV recordings with manifest.
2. Assign **train / val / test** splits on the dataset detail page.
3. **Training** → Review settings → Start Fresh Training → monitor job → Activate model.
4. **Evaluation** → Select model + dataset → Run on **test** split.
5. **Playground** → Upload unknown CSV → view English + gloss + emotion.

### Synthetic → real transition

1. Import real glove recordings as a new dataset (`provenance: real`).
2. **Start Fresh Training** on the real dataset (do not fine-tune from synthetic unless intentional).
3. Activate the new model — no code changes required.
4. Optionally **Reset Workspace** to archive synthetic models (type `RESET`; real data preserved).

## Settings

Open **Settings** in the sidebar footer:

- Storage paths (read-only, from `.env`)
- CPU thread preference
- Uncertainty threshold
- Export research metadata JSON

## Sensor schema

23-column CSV: `timestamp_ms` + 22 features (flex, acc, gyro per hand). Labels live in the database/manifest only — never in sensor files. See `docs/DATASETS.md`.

## Model bundles

See `docs/MODEL_BUNDLE.md`. Checkpoints live in `artifacts/models/`.

## Hardware gloves (future)

Not connected in this release. See `docs/HARDWARE_CONTRACT.md` for the adapter contract.

## Tests

```powershell
cd backend
pytest tests/ -q

cd ..\frontend
npm run test
npm run typecheck
npm run build
```

End-to-end lifecycle: `pytest tests/test_lifecycle_e2e.py -q`

## Limitations

- Prototype trained on **synthetic** motion patterns; real SLSL accuracy requires real collected data.
- Decoder scores are **uncalibrated** — not correctness probabilities.
- Live streaming uses provisional predictions; BiLSTM requires bidirectional context.
- Emotion model uses motion features only — not text content.
- Single-user local deployment; no authentication.

## Documentation

- `docs/ARCHITECTURE.md` — module map and adapter guide
- `docs/DATASETS.md` — import schema
- `docs/TRAINING.md` — training engine
- `docs/EVALUATION.md` — metrics
- `docs/PLAYGROUND.md` — inference UI
- `docs/HARDWARE_CONTRACT.md` — future ESP32 integration
