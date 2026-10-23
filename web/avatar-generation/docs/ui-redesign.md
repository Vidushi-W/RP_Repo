# LankaSigns interface redesign

Implemented the green and ivory product design around **Share a Tab. See the Signs.** Homepage calls to action navigate to `/translation`, where the existing click handler opens browser tab sharing. No sharing is triggered automatically on navigation.

## Presentation changes

- New two-column homepage, hand-themed illustration, three-step explanation, sharing feature, accessibility message and final call to action.
- Prominent studio sharing controls, permission guidance, actual existing status values and a large avatar panel.
- Responsive navigation, library cards with source details, friendly empty states, settings copy and additional playback copy.
- Visible keyboard focus, live status messages and reduced-motion styles. No new dependencies, animation assets, fake audio activity, shared-content preview or picture-in-picture.
- Library data remains sourced from its existing manifest; the interface explains that live audio has a separate vocabulary. No vocabulary was added or marked available.

## Preservation

No backend, APIs, models, sign datasets, capture services, inference, matching, avatar rendering, playback timing or synchronization logic changed. The live studio, text playback, sign sequence player and semantic panel retain identical code before their JSX return, aside from an icon import. Existing handlers and component props are preserved. Changes to player components are visible labels only.

## Verification

- `npm.cmd run build -- --configLoader runner`: passed (TypeScript and production build).
- `npm.cmd test -- --configLoader runner`: 51 passed, 3 skipped; 12 passing test files. Two existing test assertions were updated to use the new visible labels.
- The alternate config loader is needed because the default Vite config bundler cannot read an ancestor directory in this Windows sandbox.
- Headless Chrome: reviewed desktop homepage/studio and mobile homepage/studio screenshots; loaded library, settings and additional playback routes. Checked 390px viewport layout: no horizontal overflow. All three homepage share links target `/translation`. No browser runtime exceptions or logged browser errors across those page loads.
- `git diff --check`: passed.

Not repeated: real browser share picker permissions, actual shared audio capture, live speech recognition/Qwen selection, and visible signing driven by real shared audio. The three opt-in live integration tests were skipped. Passing mocked and fixture tests does not establish live translation accuracy.

## Modified files

Paths are relative to `web/avatar-generation/`:

- `frontend/index.html`
- `frontend/src/App.tsx`
- `frontend/src/components/avatar/AvatarGenerationPage.tsx`
- `frontend/src/components/avatar/HandStudio.test.tsx`
- `frontend/src/components/avatar/RecordedAnimationPreview.tsx`
- `frontend/src/components/avatar/SemanticAgentPanel.tsx`
- `frontend/src/components/avatar/SignSequencePlayer.tsx`
- `frontend/src/components/avatar/TranslationPanel.tsx`
- `frontend/src/components/layout/AppLayout.tsx`
- `frontend/src/pages/Dashboard/index.tsx`
- `frontend/src/pages/Settings/index.tsx`
- `frontend/src/pages/VideoTranslation/LiveTranslation.test.tsx`
- `frontend/src/pages/VideoTranslation/LiveTranslation.tsx`
- `frontend/src/pages/VideoTranslation/index.tsx`
- `frontend/src/pages/VocabularyLibrary/index.tsx`
- `frontend/src/styles/index.css`
- `frontend/src/styles/live.css`
- `docs/ui-redesign.md` (this implementation and verification report)

The existing modified `research/evaluation/live-sessions/events.jsonl` log was not edited by this redesign. Temporary browser verification scripts, profiles and screenshots are in the ignored `.cache/` directory.
