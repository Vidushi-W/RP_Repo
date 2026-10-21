# LankaSigns · SLSL Avatar Generation
Vidushi's Agentic AI-Based Accessibility Engine foundation. This web component is independent of the root Aware Expo app; do not move or modify the mobile application to run it.

## Frontend (Node 22.12+)
From the repository root, in PowerShell:
```powershell
cd web/avatar-generation/frontend
npm.cmd install
npm.cmd run dev
```
Open http://127.0.0.1:5173. Use npm instead of npm.cmd in shells that do not restrict PowerShell scripts. For reproducible subsequent installs use npm.cmd ci.

```powershell
npm.cmd test
npm.cmd run build
npm.cmd run preview
```
Production hosting needs SPA fallback to index.html for the four routes.

## API scaffold (Python 3.11)
From the repository root:
```powershell
cd web/avatar-generation/backend
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Health: http://127.0.0.1:8000/api/health. Docs: http://127.0.0.1:8000/docs.
Optional offline research dependencies: install requirements-processing.txt in a dedicated compatible environment. Blender is an external desktop tool; install it separately when rigging begins.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests
```

## Implemented
Four responsive, keyboard-accessible pages; local video selection and native playback; additional play/pause/seek/replay controls; overlay visibility and sizes; neutral Three.js placeholder; future GLB clip renderer; pure timestamp synchronization; reviewed-vocabulary lookup; empty real vocabulary; clearly labelled synthetic test markers; persistent display/signing-speed preferences; frontend mapping and boundary tests; FastAPI health scaffold and distinct processing module boundaries.

## Not implemented
Dataset ingestion, real ten-word vocabulary, real educational demo video, validated SLSL motion, speech recognition, agent orchestration, OpenCV/MediaPipe extraction, retargeting, animation validation and accuracy evaluation. No real signs or research metrics are fabricated. Supply licensed dataset references and reviewed assets for PP1; see [architecture and integration guide](docs/architecture.md).

## Layout
See [folder map](docs/architecture.md#folder-map). All code for this component stays here; the repository root and other research components remain independent. Large binaries, downloaded weights, datasets, secrets, build outputs and virtual environments must stay out of commits.
