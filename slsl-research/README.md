# SLSL AI Studio

Local-first research application for **Intelligent Continuous Sri Lankan Sign Language Understanding Using Multimodal AI**.

## Step 2 status

Dataset management is implemented: import wizard, synthetic generator, annotations, sensor visualization, split management, and validation. Training, evaluation, and playground inference are planned for later steps.

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
