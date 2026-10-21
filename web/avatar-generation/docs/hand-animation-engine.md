# Saved 2D hand animation design

## Current implementation
English input -> exact aliases (development only), or externally supplied agent IDs -> local saved JSON library -> SVG skeleton -> finite sequential playback.
Optional video currentTime -> prepared timestamped segments -> pure cue-local position lookup.
No synthesis, live camera input, 3D renderer or translation service is involved.

## Schema v1
Every animation has:
- schemaVersion: 1
- signId: uppercase A-Z, digits and underscores; 1–64 characters
- durationMs: positive finite milliseconds
- frames: 1–200000 samples in strictly increasing timestamp order, within durationMs
- each sample: timestampMs, leftHand, rightHand
- a detected hand: exactly 21 ordered {x,y} coordinates in [0,1]
- a missing hand: null, never an empty array
- metadata: positive sourceWidth and sourceHeight, extractionVersion; optional sampleIntervalMs, fixture flag and provenance

The extractor and TypeScript loader implement this same structure. Left/right are model predictions, not guaranteed anatomical identity. The extractor records source dimensions, extraction/library versions, model checksum, dataset reference and handedness convention.

SVG uses the full source coordinate system with preserveAspectRatio="xMidYMid meet"; both hands share a single viewBox. Colors distinguish sides. All 21 points and the standard 21 MediaPipe connections are drawn. No per-hand recentering, mirroring or stretching occurs. Playback selects saved samples by binary search, with no fabricated interpolation. Missing samples stay blank. To avoid freezing stale detections indefinitely, a sample is hidden after max(250ms,1.5*sampleIntervalMs), capped at 2000ms.

The official MediaPipe [Python Hand Landmarker guide](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python) describes VIDEO mode, model setup and timestamped detect_for_video calls. The [HandLandmarkerResult API](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/HandLandmarkerResult) defines normalized hand landmarks and predicted handedness. Verify handedness against each source's mirroring convention rather than treating detection labels as research ground truth.

## Library serving
frontend/public/hand-animations/manifest.json is the real SLSL library and starts empty.
frontend/public/hand-animations/fixtures/manifest.json is exclusively synthetic diagnostic data.
Loader checks prevent fixture assets being played through a real manifest.
Only reviewed entries are accepted into the real library. Human approval is recorded in the manifest; it must be justified by the study's review records.
animationUrl is relative to public, e.g. hand-animations/recorded/laptop.json. Remote URLs, absolute paths and traversal are rejected.
Generated data is ignored, not bundled with this repository. Vite copies public assets into the build. Use base-relative URLs when deploying at a subpath; configuring a subpath inside this frontend may be required by the chosen host.

## Components
```tsx
<HandSkeletonPlayer signId="LAPTOP" />
<SignSequencePlayer signs={["LAPTOP", "TABLE", "PUT"]} />
```
These are illustrative IDs. Without registered files they produce explicit missing-asset messages. Pass manifest to use a specific reviewed or fixture library. Otherwise the real public manifest is loaded. HandSkeletonCanvas is the pure SVG view; animationScheduler is the cancellable requestAnimationFrame controller.

Single and sequential playback support Play, Pause/Resume, Restart (rewind and stop), Replay (rewind and play), and speed 0.5–1.5× in the UI. Completion never automatically restarts. Missing IDs retain a labelled 800ms blank slot so unsupported signs do not disappear silently. Repeated sign IDs replay in order, while each unique file is loaded once per queue request.

Library/queue effects use AbortController and stale-result guards. Clocks are created inside effects and disposed on cleanup, including StrictMode's setup/cleanup cycle.

## Exact-match resolver versus agent
The development resolver recognizes exact single-token English aliases, normalized by case and NFKC, and reports every unsupported token. Repetitions and English order are preserved. Multiword grammar is not inferred.

An AgentClient receives English text and returns a structurally validated payload:
```json
{
  "englishText": "Put the laptop on the table.",
  "sinhalaText": "ලැප්ටොප් එක මේසය මත තබන්න.",
  "signs": ["LAPTOP", "TABLE", "PUT"],
  "segments": [
    {"startMs": 1000, "endMs": 2500, "signs": ["LAPTOP"]},
    {"startMs": 2600, "endMs": 5000, "signs": ["TABLE", "PUT"]}
  ]
}
```
This is an illustrative, linguistically unvalidated example. Sinhala text is only displayed when provided; it is never generated locally or treated as sign equivalence. requestAgent(null, ...) throws an integration-pending error. No teammate's agent code is imported or changed. The studio accepts pasted real output for manual integration testing and displays unsupported IDs without substituting other signs.

Segments are ordered, non-overlapping [startMs,endMs) intervals in milliseconds. Flattened segment IDs must equal top-level signs. The adapter caps each sign list at 200 IDs and segments at 1000 to keep inputs bounded.

## Video synchronization
SignSequencePlayer optionally receives segments and videoClock={currentTimeMs,playing}. It derives the active segment/sign/sample from video time; repeated clock updates do not trigger play/restart commands. Paused/buffering video retains its current saved frame. Seeking backwards immediately samples the earlier sign. Gaps and finished sequences remain blank, and the exclusive end boundary stops the sign.

Selected speed scales cue-local playback time. If the sequence would exceed its segment, the UI warns and clips motion at the segment end. It never guesses a faster signing speed or carries a sign into a different interval. Researchers must adjust annotations before evaluation. The development timing fixture deliberately includes a short segment to test this warning. User-uploaded video speech is never associated with synthetic markers as if it had been transcribed.

## Verification and limitations
Automated tests cover strict schemas, 21 landmarks/21 connections per hand, missing hands/gaps, file loading, fixture separation, exact matching, finite single/sequential clocks, empty/missing queues, pause/resume/restart/replay/speed, React StrictMode/unmount abort and frame cancellation, agent parsing and video seeks/clipping.

The offline extractor has now run end-to-end on the user-supplied nurse.mp4 using a component-local Python 3.11.9 runtime, MediaPipe 0.10.35 and the official Hand Landmarker model. It produced 84 samples over 3360 ms and passed frontend schema validation. Provenance and detection counts are recorded in datasets/metadata/nurse-extraction.json. The source recording and extraction remain pending handedness/linguistic review; no gesture correctness, accuracy or complete SLSL communication is claimed. See nurse-preview.md for local inspection steps.
