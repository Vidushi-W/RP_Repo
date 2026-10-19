# SLSL AI Studio

Local-first research application for **Intelligent Continuous Sri Lankan Sign Language Understanding Using Multimodal AI**.

## Step 3 status (complete)

- CPU PyTorch CNN–BiLSTM–CTC continuous sign recognizer
- Separate sklearn motion-based emotion classifier (neutral/angry)
- Subprocess training jobs with persistent metrics, cancellation, and model bundles
- Training page: New Training, Training Runs, Models registry, workspace reset
- Evaluation and playground inference are planned for Step 4

## Requirements

- Python 3.11+
- Node.js 20+

## Setup

### Backend

```powershell
cd slsl-research\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd slsl-research\frontend
npm install
npm run dev
```

Open http://localhost:5173

### Convenient launcher (Windows)

```powershell
cd slsl-research
.\scripts\start-dev.ps1
```

## Dataset workflow

1. Open **Datasets** → **Generate Synthetic** (≈400 recordings) or **Import Dataset**.
2. Open a dataset → review recordings table and splits.
3. Click a recording → inspect sensor charts and edit annotations.
4. Run **Validation** from the dataset detail page.

See `docs/DATASETS.md` for CSV/manifest schema details.

## Training workflow

1. Open **Datasets** → generate or import a dataset with train/val/test splits.
2. Open **Training** → **New Training** → select dataset → **Review Settings**.
3. Confirm train/val counts, vocabulary, and warnings (test split is never used).
4. **Start Training** — job runs in a background subprocess; monitor under **Training Runs**.
5. When complete, activate the model under **Models**. Use **Reset Workspace** only when moving from synthetic to real data.

See `docs/TRAINING.md` for architecture and bundle format.

## Tests

```powershell
cd backend
pytest tests/ -q

cd ..\frontend
npm run test
npm run typecheck
npm run build
```

## Navigation

1. Overview
2. Datasets
3. Training
4. Evaluation
5. Playground
