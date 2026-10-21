# Files created and modified

All paths below are relative to web/avatar-generation/. Git was clean at task start; no files outside this component were changed.

## Created

- docs/hand-animation-engine.md
- docs/implementation-files.md
- frontend/public/hand-animations/fixtures/calibration-a.json
- frontend/public/hand-animations/fixtures/calibration-b.json
- frontend/public/hand-animations/fixtures/manifest.json
- frontend/public/hand-animations/manifest.json
- frontend/public/hand-animations/recorded/.gitkeep
- frontend/src/components/avatar/AvatarGenerationPage.tsx
- frontend/src/components/avatar/HandSkeletonCanvas.tsx
- frontend/src/components/avatar/HandSkeletonPlayer.tsx
- frontend/src/components/avatar/HandStudio.test.tsx
- frontend/src/components/avatar/SignSequencePlayer.tsx
- frontend/src/components/avatar/TranslationPanel.tsx
- frontend/src/hooks/useAnimationClock.ts
- frontend/src/hooks/useAnimationLibrary.ts
- frontend/src/services/agentAdapter.ts
- frontend/src/services/agentAndSync.test.ts
- frontend/src/services/animationLoader.test.ts
- frontend/src/services/animationLoader.ts
- frontend/src/services/animationSchema.ts
- frontend/src/services/signMatcher.ts
- frontend/src/types/hands.ts
- frontend/src/utils/animationScheduler.ts
- frontend/src/utils/handConnections.ts
- frontend/src/utils/handPlayer.test.tsx
- frontend/src/utils/signSequence.test.ts
- frontend/src/utils/signSequence.ts
- frontend/src/utils/videoSignSync.ts
- preprocessing/dataset/.gitkeep
- preprocessing/extract_hand_landmarks.py
- preprocessing/models/.gitkeep
- preprocessing/requirements.txt
- preprocessing/test_extractor.py

## Modified

- .gitignore
- docs/architecture.md
- frontend/package.json
- frontend/package-lock.json
- frontend/src/components/avatar/AvatarRenderer.tsx
- frontend/src/components/video/VideoWorkspace.tsx
- frontend/src/pages/Dashboard/index.tsx
- frontend/src/pages/Settings/index.tsx
- frontend/src/pages/VideoTranslation/index.tsx
- frontend/src/pages/VocabularyLibrary/index.tsx
- frontend/src/styles/index.css
- README.md

## Verification

Production build: passed. Vitest: 30 tests across 7 files passed. Production HTTP checks: all four routes, real manifest, and coordinate fixture passed. Browser visual inspection unavailable. Python/MediaPipe extraction not executed: no Python interpreter, model or dataset videos supplied.