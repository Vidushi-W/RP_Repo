# LankaSigns · Local Audio and 2D Sign Avatar

This component captures shared-tab audio after a user click, runs local speech recognition and Qwen selection, and replays stored hand/body/face motion. It does not generate sign movements, establish SLSL grammar or capture a live camera. All implementation changes stay in `web/avatar-generation`.

## Listen and watch

`/translation` now presents only Listen/Stop and the avatar as primary controls.
See [complete audio setup, measured results and limitations](docs/live-audio.md).
59 source videos have been processed. Ten concepts are eligible after
owner-authorized assistant research review: CRY, WALK, LOOK, DRINK, RUN, GIVE,
TAKE, SEE, DRAW and EAT. The other 49 sources remain pending. ASK was withheld
because the ahanawa clip conflicts with the question-asking meaning; EAT is the
reviewed replacement. See the [candidate review package](research/evaluation/vocabulary-expansion/review-report.md).
NURSE remains pending. Sinhala speech quality and visible
browser capture/playback are not yet verified.

## Semantic AI selection

The `/research` page preserves the local Qwen3 1.7B text agent through Ollama,
manual transcript input and automatic playback through the existing renderer.
See [agent setup, registry, STT interface and evaluation](docs/semantic-agent.md).
NURSE remains pending expert review and requires explicit research-preview
opt-in; no PHONE animation is present. No paid API or API key is used.
Start Ollama, run `ollama pull qwen3:1.7b`, and configure the backend using
`backend/.env.example`. The guide includes exact Windows commands, tests,
CPU settings and real-inference verification.

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
1. Open `/research` for the preserved developer playback studio.
2. Enable **Use coordinate test fixtures (not SLSL)**.
3. Process **test-a test-b**, then select Play.
4. Pause, Resume, Restart, Replay, and change playback speed.
5. For video testing, choose **Load timestamped coordinate test**, select a local MP4/WebM and enable synchronization. Seek across the prepared segments or replay using the video controls.

Both coordinate fixtures are explicitly synthetic diagnostics, not human recordings, ASL, SLSL signs or linguistic demonstrations. One fixture includes a missing-hand frame. This diagnostics studio retains its original empty manifest. Live translation uses the separate server registry, which now has ten concepts eligible for research playback.

## Extract a dataset recording
Python 3.11 is recommended. This checkout now has a component-local Python 3.11.9 runtime in .tools and a working .venv with MediaPipe/OpenCV. NURSE has been extracted from the supplied Kaggle recording; see [NURSE preview](docs/nurse-preview.md). The system-wide py launcher remains unconfigured.

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
See [engine design and schema](docs/hand-animation-engine.md). Agent payloads contain explicit sign IDs; the player preserves mention order without claiming SLSL grammar. Use the local semantic panel, paste external agent JSON in the studio, or inject an AgentClient through requestAgent. Unavailable Ollama/model errors are reported explicitly.

New processed recordings include detected body and face points in addition to hands. Missing detections remain missing. Extraction alone does not prove sign correctness, and isolated vocabulary playback is not complete grammatical SLSL translation. The live service uses offline speech recognition and local Qwen; the original research/manual playback features remain available separately.

The retained FastAPI health scaffold can be started after installing backend/requirements.txt with `python -m uvicorn app.main:app --reload` from backend. It is separate from this offline 2D engine.
