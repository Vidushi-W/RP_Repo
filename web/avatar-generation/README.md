# LankaSigns · 2D SLSL Hand Animation Engine

This component replays saved 21-landmark hand recordings. It does not generate signs, determine SLSL grammar, translate Sinhala, or capture a live camera. All changes are confined to the existing `web/avatar-generation/` directory. The root Aware app and global routing are unchanged.

## Run the player

From the repository root:
```powershell
cd web/avatar-generation/frontend
npm.cmd ci
npm.cmd run dev
```
Open http://127.0.0.1:5173/translation. Node 22.12+ is required. Use npm instead of npm.cmd in other shells.

```powershell
npm.cmd test
npm.cmd run build
```

## Demonstrate without a dataset
1. Open Video Translation.
2. Enable **Use coordinate test fixtures (not SLSL)**.
3. Process **test-a test-b**, then select Play.
4. Pause, Resume, Restart, Replay, and change playback speed.
5. For video testing, choose **Load timestamped coordinate test**, select a local MP4/WebM and enable synchronization. Seek across the prepared segments or replay using the video controls.

Both coordinate fixtures are explicitly synthetic diagnostics, not human recordings, ASL, SLSL signs or linguistic demonstrations. One fixture includes a missing-hand frame. Real SLSL playback is available only after reviewed recordings are registered; the real manifest is currently empty.

## Extract a dataset recording
Python 3.11 is recommended. It is not installed on the current development machine, so actual MediaPipe extraction has not been executed here.

From the component directory:
```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r preprocessing/requirements.txt
```
Put licensed SLSL MP4s in preprocessing/dataset and an official Hand Landmarker .task model in preprocessing/models. Model and dataset binaries are ignored by Git. No models or recordings are downloaded automatically.

```powershell
.venv\Scripts\python.exe preprocessing/extract_hand_landmarks.py --input preprocessing/dataset/laptop.mp4 --model preprocessing/models/hand_landmarker.task --sign-id LAPTOP --dataset-reference "EXACT_DATASET_URL_AND_VERSION" --output frontend/public/hand-animations/recorded/laptop.json
```
LAPTOP is only an illustrative identifier, not a claim that a recording is bundled or reviewed. The script reads an MP4 file, detects up to two hands, preserves full-frame normalized coordinates and source timestamps (with a documented monotonic FPS fallback), writes missing hands as null, and refuses existing output paths. All supplied input/model/output paths must remain within this component.

Review handshape, ordering, handedness, clipping and landmark failures against the original recording with an SLSL reviewer. Verify the source's mirroring convention; use --swap-handedness only when warranted. No mirror transform is applied to coordinates. After review add an entry to frontend/public/hand-animations/manifest.json:
```json
{
  "schemaVersion": 1,
  "fixture": false,
  "signs": [{
    "signId": "LAPTOP",
    "label": "Laptop",
    "aliases": ["laptop"],
    "animationUrl": "hand-animations/recorded/laptop.json",
    "datasetReference": "EXACT_DATASET_URL_AND_VERSION",
    "reviewed": true
  }]
}
```
Refresh the page after updating the manifest. Generated recordings are ignored to avoid accidental dataset commits; provide them locally in public/hand-animations/recorded. Public-relative asset paths are validated and work in Vite dev/production output without an external server change.

## Folder map
- frontend/src/components/avatar: SVG renderer, single-sign player, sequence player, input/translation panels and component tests.
- frontend/src/services: schema/manifest validation, local asset loading, exact-match development resolver and injected agent boundary.
- frontend/src/utils: standard hand connections, playback scheduler, sequence timing and video synchronization.
- frontend/src/hooks: cancellable animation clock and library loading.
- frontend/public/hand-animations: empty real manifest, separate coordinate fixtures and ignored recorded JSON files.
- preprocessing: offline MediaPipe/OpenCV utility, optional requirements, local model/dataset locations.
- docs: schema, integration details, limitations and verification notes.
- backend, datasets and research: retained research scaffolding; the 2D player does not require an API or retargeting.

## Integration and limitations
See [engine design and schema](docs/hand-animation-engine.md). Agent payloads contain explicit sign IDs; the player never invents SLSL ordering. Paste actual agent JSON in the studio, or inject an AgentClient through requestAgent. A missing agent is explicitly reported as pending.

Hand-only playback omits face, body, orientation depth and other linguistically important features. Extracted landmarks require validation; extraction alone does not prove sign correctness. No speech recognition, dataset, real signs, translation service, accuracy results or live camera capture is supplied. No modifications outside this component are needed. Any future connection to an external/shared agent should be configured by its owning component.

The retained FastAPI health scaffold can be started after installing backend/requirements.txt with `python -m uvicorn app.main:app --reload` from backend. It is separate from this offline 2D engine.
