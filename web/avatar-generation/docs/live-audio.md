# Local audio-to-avatar prototype

`/translation` is now the minimal Listen/Stop interface with a large 2D avatar.
The original text, fixtures, manual JSON preview and research tools remain at
`/research`. They are not displayed in normal listening mode.

## Current verified scope

- 59 MP4 sources discovered recursively; all 59 converted and structurally
  validated. Source SHA-256 checks confirm all 59 originals unchanged.
- Ten concepts eligible for normal research playback: **CRY, WALK, LOOK, DRINK,
  RUN, GIVE, TAKE, SEE, DRAW, EAT**. The original three retain their assets.
- See the [eight-candidate expansion review](../research/evaluation/vocabulary-expansion/review-report.md)
  for actual filenames, dictionary/source-frame evidence, tracking limitations,
  checksums and playback results. ASK remains pending because the ahanawa clip
  cups a hand behind the ear; EAT was separately reviewed as its replacement.
- The other 49 source entries are processed but unavailable for normal playback.
  The existing NURSE restriction remains enforced.
- The repository owner explicitly authorized Codex to review. The mapping
  approvals record lexical dictionary evidence and actual source-frame inspection.
  They are research eligibility decisions, **not independent SLSL certification**.
  Every batch entry records `linguisticallyCertified: false`.
- Real generated English audio was processed by local Whisper and Qwen and
  selected CRY, WALK and LOOK. Real-paced PCM injection at the capture boundary
  also exercised the real WebSocket, ASR, Qwen, asset checks and continuous SVG
  player. The capture boundary was simulated in that DOM test.
- No visible browser was connected. Actual tab-sharing permission, shared audio
  acquisition and visible Windows-browser playback remain unverified.
- Sinhala text-to-concept was exercised separately. Sinhala **speech** accuracy
  remains unverified; the supplied CRY video's audio track was silent.

The two reviewed-label registries are `datasets/metadata/vocabulary-reviews.json`
and `sign-registry.json`. The complete 59-source inventory, including original
names, romanization, nullable Sinhala/English labels, processing status, hashes,
availability and detection counts, is `dataset-vocabulary.json`. Do not infer
meanings for its pending entries from spelling alone.

## Run on the current Windows checkout

The component's `.venv`, landmark models and multilingual Whisper base weights
were installed during implementation. Keep Ollama serving locally and the model
installed. In a PowerShell terminal:

```powershell
ollama list
# Only if Ollama's tray app/server is not already running:
ollama serve
```

In another terminal, from the repository root:

```powershell
Set-Location web/avatar-generation/backend
$env:AI_PROVIDER = 'ollama'
$env:OLLAMA_BASE_URL = 'http://localhost:11434'
$env:OLLAMA_MODEL = 'qwen3:1.7b'
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --ws-max-size 400000
```

In a third terminal, from the repository root:

```powershell
Set-Location web/avatar-generation/frontend
npm.cmd run dev
```

Open http://127.0.0.1:5173/translation. Click **Listen**, choose a browser tab
containing the speech, and enable **Share tab audio** in the browser picker.
Try “Someone is crying” or “The child is walking and looking”. Pause between
phrases on this CPU. Stop Listening immediately ends all capture tracks,
closes the connection, drops pending speech/playback and returns the avatar to
rest. Native work already running may finish locally; it cannot enqueue after
the session stops, and cancellation prevents starting a subsequent stage.

Use desktop Chrome or Edge on localhost. Display capture requires a secure
context and a user gesture. Sharing a tab/screen does **not** guarantee an audio
track: availability depends on browser, OS and chosen surface. The app checks
the audio track and stops all tracks with an accessible error if none is shared.
It never falls back to capturing the microphone and never requests capture on
page load. The video track required by the screen-capture API is not displayed
as a substitute for the avatar.

## Reproduce installation and preprocessing

From `web/avatar-generation`, using the existing local Python environment:

```powershell
.venv\Scripts\python.exe -m pip install -r backend/requirements-speech.txt -r preprocessing/requirements.txt
```

On a fresh machine create `.venv` with Python 3.11 first. Source recordings and
large generated assets/models are ignored by Git; supply the same MP4 dataset.
Download models once from their official locations:

```powershell
Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task' -OutFile 'preprocessing/models/hand_landmarker.task'
Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task' -OutFile 'preprocessing/models/pose_landmarker_lite.task'
Invoke-WebRequest -Uri 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task' -OutFile 'preprocessing/models/face_landmarker.task'
.venv\Scripts\python.exe backend/scripts/setup_speech.py
.venv\Scripts\python.exe preprocessing/process_vocabulary.py
```

Processing is offline and separate from playback. It samples the stored source
timestamps at up to 15 fps, tracks at most one pose/face and two hands, and keeps
full-frame normalized coordinates. Hands have 21 points, pose 33, and face 478.
Low-visibility/nonfinite pose/face points remain null. No body/face detector
output is invented when detection fails. Pose and face models run only during
preprocessing. The renderer draws stored upper-body, face and hand points;
the static neutral illustration is a resting UI state, not a generated sign.

Existing generated files are immutable: processing reuses them after validation,
or reports an error if the original source changed. Choose separately reviewed,
versioned outputs for changed data. Failures are recorded as unavailable. The
batch checkpoints the inventory and registry and produces
`research/evaluation/dataset-processing-results.json`.

## Data review and expansion

`vocabulary-reviews.json` contains explicit source-relative filenames, canonical
concept IDs, Sinhala/English labels, sense definitions, synonyms, provenance,
review scope and reviewer. Edit it only after reviewing actual clips and lexical
meaning. Uncertain filenames stay pending. Multiple variants need an explicit
selection, not automatic synonym approval. Running the processor then registers
validated assets. The legacy NURSE entry is separately managed and remains
pending; changing a filename does not bypass that restriction.

The initial three lexical mappings were checked against the author's
[English–Sinhala dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf)
(cry p.68, look p.151, walk p.260). Source clips were also inspected at multiple
timestamps. This establishes documented research provenance, not a guarantee of
linguistic accuracy or grammatical SLSL. Independent review is still valuable.

## Audio and inference architecture

1. A user click invokes `getDisplayMedia({video:true,audio:true})` immediately.
2. Web Audio produces mono 16 kHz samples through a silent AudioWorklet. A
   supported sample rate is checked; there is no loopback to speakers.
3. An RMS gate creates non-overlapping utterances with 200 ms pre-roll, at least
   400 ms of voiced samples, 600 ms trailing silence and a six-second cap.
4. A bounded client sends PCM16 windows with sequence IDs and source offsets to
   `/api/audio/live`. There is one request in flight and at most three pending.
5. The backend checks origins, sizes, order, non-overlap and duplicate IDs. It
   allows two sessions and serializes processing. No raw audio is stored.
6. **faster-whisper 1.2.1**, multilingual **base**, runs locally on CPU with int8
   and two threads, beam size 1, built-in Silero VAD and no previous-text carry.
   It translates supported English/Sinhala speech into English text for Qwen.
   Language probability, average log probability and no-speech probability are
   logged as uncertainty signals, not calibrated accuracy guarantees. Sinhala
   coverage in the model does not establish reliable local Sinhala recognition.
7. Local Qwen3:1.7b uses a compact structured schema for eligible sign IDs and
   exact evidence. Registered sense descriptions guide semantics. A model entry
   with absent/overlapping/out-of-order evidence is discarded individually and
   logged; remaining entries still pass the existing complete sign/sense/file/
   checksum validation. This does not replace semantic inference with keywords.
   The fuller text/research agent remains intact on `/research`.
   The expanded live schema permits null sign IDs for explicit abstention.
   Qwen always selects contextual meanings first. When its selected evidence has
   no reviewed canonical/synonym phrase for that ID, the same local model gets a
   separate narrow yes/no meaning question. A rejection can only remove that
   proposal, never redirect it. A lexical phrase cannot create a selection.
   This added guard rejects unsupported forced choices but is not a guarantee
   of semantic accuracy; all development failures are preserved.
   Case-preserving literal phrase hints are supplied as retrieval evidence,
   never as automatic selections. Registered excluded phrases and a conservative
   English negation-clause veto can only remove proposals. Contrast words reset
   that negation scope; complex syntax can still cause abstention. Invalid
   evidence or a rejected unfamiliar meaning permits one bounded model repair,
   with both attempts and their costs retained. All original schema, source
   order, sense, review, path and checksum checks still run after repair. The narrow
   question uses the positive meaning, while initial selection retains the full
   registered description and exclusions. Its inference time is included in
   qwenMs, with individual verification metadata in the inference report.
8. Unavailable concepts are skipped and logged. Only registered eligible IDs
   reach the live player. Repeated valid occurrences remain repeated entries.
9. The player prepares assets while an earlier sign plays, appends without
   resetting that sign's clock, and displays each saved motion sequentially.
   Pending playback is limited to eight signs/20 seconds, with a short neutral
   gap between motions. Stop cancels the current motion and all pending items.

Qwen remains on CPU with 4096 context tokens and a five-minute keep-alive.
Repeated **exact** transcripts are cached with prompt/registry revisions, up to
64 results. Cache hits still enqueue each new utterance; they do not deduplicate
meaningful repetitions. No additional embedding or language model is loaded.
The speech model is loaded only when non-silent audio first arrives and never
downloads during runtime. `STT_MODEL_PATH`, if set, must point inside this
component; otherwise the local downloaded base directory is used.

## Evaluation and latency

Reports and local rotating JSONL logs are in `research/evaluation`. Raw audio
from listening is memory-only. The logs retain **transcript text**, language,
raw and accepted model proposals, missing/rejected vocabulary, order, errors and
latency for the requested research evaluation. `live-sessions/events.jsonl`
rotates at 5 MB with two backups. Synthetic test WAV/PCM files are in `.cache`;
they are generated fixtures, not recordings from the user’s shared tab.

Measured evidence includes:

- `source-integrity-results.json`: 59 source hashes match their inventories.
- `english-audio-initial-results.json`: first failed real speech selection.
- `english-audio-results.json`: real English audio through the fuller schema.
- `english-audio-compact-results.json`: compact schema, three correct IDs;
  ASR 1.67 s, Qwen generation 9.73 s, lookup 0.10 s, whole request 14.43 s.
- `live-audio-avatar-results.json`: real-paced PCM injection, actual local ASR,
  Qwen, WebSocket proxy, asset checks and DOM/SVG playback. Capture was mocked;
  visible browser playback was not verified.
- `live-semantic-initial-results.json` and `live-semantic-results.json`: actual
  English paraphrases, repeated concepts, unavailable concepts and Sinhala text.
  These are prompt-development examples, not held-out accuracy measurements.

The final real-paced integration run (`live-audio-avatar-results.json`) passed
CRY -> WALK -> LOOK, including body/hand rendering and stop cleanup. Its first
window took 2.99 s for ASR and 15.05 s for semantic processing (18.30 s server
total); the second took 2.40 s and 11.97 s (14.52 s server total). The first
stored CRY hand frame appeared after 20.70 s from the estimated audio-window
start. WALK and LOOK appeared after 31.59 s and 36.50 s from their shared window
start, including queued playback. Asset preparation took 34-60 ms. This run was
slower than the earlier compact request; both measurements are retained.
Actual Qwen generation and vocabulary lookup are separately recorded in the
speech-selection session logs; the earlier compact request above gives their
measured values rather than conflating them with complete semantic processing.

Final regression verification: 40 backend tests, 3 preprocessing tests and 51
frontend tests passed; two opt-in integration tests were skipped by the normal
frontend suite. The real audio-to-avatar opt-in test was run separately and
passed. The production TypeScript/Vite build and `git diff --check` passed.
The separate real-Qwen semantic development set passed 5/5 after prompt tuning;
the initial 4/5 result is preserved. This is not held-out accuracy evidence.

Client metrics record utterance-window duration, asset preparation time and
delay from the estimated window start to the first stored hand frame displayed.
That last metric includes segmentation, network/model/queue delays; it is not
physical system-audio capture latency or a laboratory measure of pixel motion.
Actual browser capture latency remains unmeasured. The measured CPU delays are
seconds, so **true real-time performance is not claimed**. Use shorter phrases
and pauses; overload stops listening rather than growing queues indefinitely.

## Tests

From the component directory:

```powershell
.venv\Scripts\python.exe -m unittest discover -s preprocessing -p 'test*.py'
Set-Location backend
..\.venv\Scripts\python.exe -m unittest discover -s tests
..\.venv\Scripts\python.exe scripts/evaluate_live_semantics.py
# With backend and frontend running, real audio-file -> live service:
..\.venv\Scripts\python.exe scripts/test_live_audio.py --audio ../.cache/english-sample.wav --reference 'Someone is crying. The child is walking and looking.' --expected CRY WALK LOOK --output ../research/evaluation/english-audio-results.json
Set-Location ../frontend
npm.cmd test
npm.cmd run build
```

The English fixture was generated offline using Windows System.Speech. To
recreate it from the component directory in PowerShell:

```powershell
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile((Join-Path (Get-Location) '.cache/english-sample.wav'))
$synth.Speak('Someone is crying. The child is walking and looking.')
$synth.Dispose()
.venv\Scripts\python.exe -c "import sys;sys.path.insert(0,'backend/scripts');from test_live_audio import pcm_windows;from pathlib import Path;Path('.cache/english-sample-16k.pcm').write_bytes(b''.join(pcm_windows(Path('.cache/english-sample.wav'))))"
```

Opt into actual audio-to-avatar DOM integration from `frontend` with the local
services running. It injects that PCM at real cadence in place of tab capture;
all recognition, inference, networking, validation and playback remain real:

```powershell
$env:LANKASIGNS_LIVE_AUDIO_TEST = '1'
npm.cmd test -- src/components/avatar/LiveAudioAvatar.test.tsx
Remove-Item Env:LANKASIGNS_LIVE_AUDIO_TEST
```

Ordinary unit tests use mocks for lifecycle/error paths and skip opt-in live
tests. The two test categories must not be described as equivalent evidence.
For the final visible demonstration, manually open `/translation`, click Listen,
share the tab with audio enabled, play a short sentence, observe the avatar,
then stop and confirm the browser's sharing indicator ends. This manual check
is still required because automation exposed no browser in this session.

## Principal implementation files

- Preprocessing: `preprocessing/extract_hand_landmarks.py`,
  `motion_validation.py`, `process_vocabulary.py`.
- Data: `datasets/metadata/vocabulary-reviews.json`, `dataset-vocabulary.json`,
  and the extended `sign-registry.json`.
- Backend: `app/services/speech.py`, `live_pipeline.py`, `sign_registry.py`,
  `semantic_agent.py`, `ollama_provider.py`, `app/api/audio_routes.py`, and `main.py`.
- Setup/evaluation: `requirements-speech.txt`, `scripts/setup_speech.py`,
  `test_live_audio.py`, `evaluate_live_semantics.py` and `.env.example`.
- Frontend: `src/services/audioCapture.ts`, `liveAudio.ts`,
  `public/audio-capture-worklet.js`, `ContinuousAvatar.tsx`,
  `HandSkeletonCanvas.tsx`, `animationSchema.ts`, `types/hands.ts`,
  `pages/VideoTranslation/LiveTranslation.tsx`, `styles/live.css`, `App.tsx`,
  and the WebSocket-enabled `vite.config.ts`.
- Tests: `backend/tests/test_audio_pipeline.py`, updated existing registry
  tests, `audioCapture.test.ts`, `LiveTranslation.test.tsx`,
  and opt-in `LiveAudioAvatar.test.tsx`.

API implementation references:
[browser display capture](https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia),
[faster-whisper](https://github.com/SYSTRAN/faster-whisper),
[MediaPipe pose](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python).
