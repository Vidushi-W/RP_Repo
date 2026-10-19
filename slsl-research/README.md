# SLSL AI Studio

Local-first research application for **Intelligent Continuous Sri Lankan Sign Language Understanding Using Multimodal AI**.

## Step 4 status (complete)

- Model evaluation on held-out test recordings with real WER and exact-sequence accuracy
- Sensor-only inference; labels compared after decoding (data-leakage tests included)
- Evaluation page: 5-stage workflow, prediction table, alignment detail, experiment history
- Playground live recognition is planned for Step 5

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

## Evaluation workflow

1. Train or register a model under **Training** → **Models**.
2. Open **Evaluation** → choose model and dataset with a held-out **test** split.
3. Review compatibility warnings (vocabulary, signer overlap, split isolation).
4. **Run Evaluation** and inspect WER, per-recording predictions, and token alignments.

See `docs/EVALUATION.md` for metrics definitions and limitations.

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
