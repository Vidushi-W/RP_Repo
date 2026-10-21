# Architecture and asset contract

The existing Aware Expo app remains at the repository root. This isolated component does not import its source, share its dependencies, or require moving it to mobile/aware.

## Web runtime
React pages -> reusable player/avatar components -> useVideoSync -> pure timestamp synchronization.
The HTML video currentTime is authoritative. Frame sampling plus media events recompute the active cue and cue-local time; pause and buffering stop progression. Seeking backwards and replay recompute from time rather than advancing a queue. Intervals are [start, end), uniquely identified, non-overlapping and in seconds.

The bundled demo JSON has three synthetic timing markers, no video, no avatar, and no real SLSL words. Users can select a local video to test playback; its speech is not analyzed. The manual inspector works without a video. Files are held as browser object URLs, revoked on removal/unmount, and never uploaded.

## Integrating a prepared PP1 study
1. Obtain the exact Kaggle dataset URL, license, citation, signer consent conditions and ten reviewed vocabulary labels. Store provenance in datasets/metadata; keep source recordings out of Git.
2. Copy a permitted educational video locally to frontend/public/sample-videos. Replace demo.json videoUrl with /sample-videos/your-video.mp4, title, and manually reviewed word timestamps. Set demonstration to false only after replacing all synthetic markers. Cue wordId values must match vocabulary IDs.
3. Add each real entry to src/data/vocabulary.json with id, word, datasetReference, sourceVideo, animationStatus (available/processing/unavailable), validated, animationUrl and clipName. Do not mark available/validated until reviewed.
4. Prepare a rigged GLB (Blender), correctly scaled and centered. Put neutral rig in public/avatars; put self-contained rig+clip GLBs in public/animations. The current loader expects a complete rig with its named clip, not an animation-only asset; animation-only clips need an explicit shared-skeleton binding adapter.
5. Set avatarUrl in the manifest. The renderer clones the skeleton, selects a reviewed entry's asset/clip, and samples its mixer from video time. Pending or missing entries leave a neutral avatar. Exported motion length must fit the cue and be reviewed at intended speed.
6. Have SLSL experts validate handshape, palm orientation, movement, location, facial/nonmanual features, transitions and intelligibility. The placeholder performs no signs.

## Offline research pipeline (not implemented)
Kaggle recording -> OpenCV frames -> MediaPipe pose/hand landmarks -> cleaned motion -> skeleton retargeting in Blender -> reviewed GLB clip -> vocabulary JSON -> browser rendering.

Extraction, retargeting, and validation live in separate backend service modules and explicitly raise NotImplementedError. MediaPipe landmarks alone are not evidence of accurate sign-language animation; occluded fingers, depth ambiguity, facial cues and rig differences need research.

FastAPI currently exposes GET /api/health only. No speech recognition, agent orchestration, AI processing API, training, automatic timestamp extraction, database or upload endpoint exists. Future integration should use versioned schemas and documented component APIs rather than importing the mobile runtime.

## Folder map
- frontend/public/{avatars,animations,sample-videos}: local assets, ignored in Git.
- frontend/src/components/{avatar,video,layout,common}: reusable rendering and UI.
- frontend/src/pages: Dashboard, VideoTranslation, VocabularyLibrary, Settings.
- frontend/src/hooks: video clock and browser preferences.
- frontend/src/services: reviewed vocabulary lookup, future API adapters.
- frontend/src/types: shared frontend contracts.
- frontend/src/data: small tracked JSON manifests, never binary datasets.
- frontend/src/utils: pure synchronization and tests.
- backend/app/{api,services,models,schemas,core}: API routes, processing boundaries, model provenance and configuration.
- backend/scripts, backend/tests: future offline jobs and API tests.
- datasets/{raw,processed,metadata}: ignored recordings/derived output, tracked provenance.
- research/{experiments,evaluation}: study protocols and results; no fabricated metrics.
- docs: integration and architecture notes.

## Scope and privacy
Preferences use browser localStorage; blocked storage falls back to session state. No analytics, remote requests for videos, or model calls are configured. The renderer needs WebGL and provides a fallback message when unavailable. Phone vibration and glove integration belong to the independent Aware component.
