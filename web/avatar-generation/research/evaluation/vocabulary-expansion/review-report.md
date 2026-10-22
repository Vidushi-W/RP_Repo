# Vocabulary expansion review

Reviewed on 23 October 2026 (Asia/Colombo). All work is inside `web/avatar-generation`.

59 recordings remain processed. There are 11 distinct reviewed source recordings: the original three, seven requested candidates, and EAT as a replacement. Ten concepts are approved for prototype research playback; 49 recordings remain pending. ASK was reviewed but not approved. Approval follows the existing repository-owner authorization for assistant lexical/source review. It is not independent SLSL linguistic certification.

## Decisions and evidence

| Candidate | Actual source | Hand-visible / sampled frames | Pose / face detections | Decision |
|---|---|---:|---:|---|
| DRINK | `bonawa.mp4` | 20 / 50 | 50 / 50 | Approved for research |
| RUN | `duwanawa.mp4` | 35 / 56 | 56 / 56 | Approved for research |
| GIVE | `denawa.mp4` | 24 / 41 | 41 / 41 | Approved for research |
| TAKE | `gannawa.mp4` | 26 / 51 | 51 / 51 | Approved for research |
| ASK | `ahanawa.mp4` | 18 / 38 | 38 / 38 | Pending: conflicting meaning |
| SEE | `dakinawa.mp4` | 22 / 44 | 44 / 44 | Approved for research |
| DRAW | `andinawa(draw).mp4` | 45 / 69 | 69 / 69 | Approved for research |
| EAT | `kanawa.mp4` | 18 / 52 | 52 / 52 | Approved for research |

Hand-visible counts mean at least one hand; the audit also retains the per-hand detection sum. Every source frame decoded, and counts match video metadata. Every sampled timestamp is ordered, coordinates are finite/in range, and detected landmark counts meet the existing schema. Missing detections are null and remain missing in playback. These are prototype assets with tracking loss, not complete or clinically validated motion captures.

### DRINK: `bonawa.mp4`

Research eligibility: Sinhala/English lexical review, six source-frame observations and existing extracted-motion audit. Hand forms a cup-like shape and moves to the mouth, then returns. Missing hand detections and tracking discontinuities remain unaltered and are documented in the expansion report. Not independent SLSL linguistic certification.

Source contact sheet: [six sampled frames](source-drink.jpg). Motion statistics and hashes: [audit](motion-audit.json).

Registered sense: `person-drinking-liquid`. A person drinking or sipping liquid. Excludes eating food, absorbing information, and the noun beverage.

Duration 3360 ms; 84 of 84 raw frames decoded. Hand-detection intervals: `[[760, 1960], [2160, 2160]]` ms. Largest adjacent same-side point displacement: 0.0893 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=85).

### RUN: `duwanawa.mp4`

Research eligibility: Sinhala/English lexical review, six source-frame observations and existing extracted-motion audit. Alternating bent arms and fists pump forward and back in front of the torso. Missing hand detections and tracking discontinuities remain unaltered and are documented in the expansion report. Not independent SLSL linguistic certification.

Source contact sheet: [six sampled frames](source-run.jpg). Motion statistics and hashes: [audit](motion-audit.json).

Registered sense: `person-running-on-foot`. A person running on foot. Excludes running software, operating a business or machine, flowing liquids, and walking.

Duration 3720 ms; 93 of 93 raw frames decoded. Hand-detection intervals: `[[480, 600], [760, 1000], [1160, 1200], [1360, 1400], [1560, 2000], [2160, 3080]]` ms. Largest adjacent same-side point displacement: 0.1725 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=209).

### GIVE: `denawa.mp4`

Research eligibility: Sinhala/English lexical review, six source-frame observations and existing extracted-motion audit. An open palm moves from the torso outward toward the recipient direction. Missing hand detections and tracking discontinuities remain unaltered and are documented in the expansion report. Not independent SLSL linguistic certification.

Source contact sheet: [six sampled frames](source-give.jpg). Motion statistics and hashes: [audit](motion-audit.json).

Registered sense: `person-giving-physical-object`. A person handing a physical object to another person. Excludes giving up, giving advice, causing illness, and figurative giving.

Duration 2760 ms; 69 of 69 raw frames decoded. Hand-detection intervals: `[[360, 680], [800, 880], [1000, 1000], [1160, 2080]]` ms. Largest adjacent same-side point displacement: 0.15566 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=112).

### TAKE: `gannawa.mp4`

Research eligibility: Sinhala/English lexical review, six source-frame observations and existing extracted-motion audit. Open hand extends forward, closes and retracts toward the torso; direction differs from GIVE. Missing hand detections and tracking discontinuities remain unaltered and are documented in the expansion report. Not independent SLSL linguistic certification.

Source contact sheet: [six sampled frames](source-take.jpg). Motion statistics and hashes: [audit](motion-audit.json).

Registered sense: `person-taking-physical-object`. A person reaching for and taking a physical object into their possession. Excludes taking time, taking care, taking a photo, understanding, purchasing and transporting a person.

Duration 3400 ms; 85 of 85 raw frames decoded. Hand-detection intervals: `[[1080, 1200], [1360, 2800]]` ms. Largest adjacent same-side point displacement: 0.22434 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=236).

### ASK: `ahanawa.mp4`

ASK candidate reviewed but not approved: ahanavaa can mean ask or listen. Actual clip cups a hand behind the ear, consistent with listening/hearing. This conflicts with the proposed question-asking sense. Requires signer or qualified SLSL reviewer clarification. Do not expose ASK or LISTEN as playable from this source.

Source contact sheet: [six sampled frames](source-ask.jpg). Motion statistics and hashes: [audit](motion-audit.json).

The dictionary lists ahanavaa for both asking and listening. The ear-cupping clip does not establish a question-asking sign. ASK, LISTEN and HEAR therefore remain unavailable from this recording. EAT was inspected separately rather than relabeling this clip.

Duration 2520 ms; 63 of 63 raw frames decoded. Hand-detection intervals: `[[480, 1560], [1760, 1760]]` ms. Largest adjacent same-side point displacement: 0.0584 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=27).

### SEE: `dakinawa.mp4`

Research eligibility: Sinhala/English lexical review, six source-frame observations and existing extracted-motion audit. A single raised index finger is positioned near the eye, then moves outward/down; differs from LOOK two-finger eye gesture. Missing hand detections and tracking discontinuities remain unaltered and are documented in the expansion report. Not independent SLSL linguistic certification.

Source contact sheet: [six sampled frames](source-see.jpg). Motion statistics and hashes: [audit](motion-audit.json).

Registered sense: `person-visually-perceiving`. A person visually perceiving something with their eyes. Excludes understanding, meeting a person, seeing to a task, and deliberately looking or watching (LOOK).

Duration 2920 ms; 73 of 73 raw frames decoded. Hand-detection intervals: `[[480, 1880]]` ms. Largest adjacent same-side point displacement: 0.28536 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=214).

### DRAW: `andinawa(draw).mp4`

Research eligibility: Sinhala/English lexical review, six source-frame observations and existing extracted-motion audit. Dominant hand traces strokes across the open opposite palm; the supplied filename explicitly disambiguates draw. Missing hand detections and tracking discontinuities remain unaltered and are documented in the expansion report. Not independent SLSL linguistic certification.

Source contact sheet: [six sampled frames](source-draw.jpg). Motion statistics and hashes: [audit](motion-audit.json).

Registered sense: `person-drawing-picture`. A person drawing or sketching a picture or diagram. Excludes pulling, dressing, writing words, drawing curtains, drawing breath, and a tied game.

Duration 4600 ms; 115 of 115 raw frames decoded. Hand-detection intervals: `[[680, 960], [1080, 1160], [1280, 3600], [3760, 3760], [3880, 3880]]` ms. Largest adjacent same-side point displacement: 0.42952 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=84).

### EAT: `kanawa.mp4`

Research eligibility: Sinhala/English lexical review, six source-frame observations and existing extracted-motion audit. Grouped fingertips repeatedly approach the mouth; hand shape differs from the cup-like DRINK gesture. Missing hand detections and tracking discontinuities remain unaltered and are documented in the expansion report. Not independent SLSL linguistic certification.

Source contact sheet: [six sampled frames](source-eat.jpg). Motion statistics and hashes: [audit](motion-audit.json).

Registered sense: `person-eating-food`. A person eating food. Excludes drinking liquid, figurative consuming, corrosion, and eating ones words.

Duration 3440 ms; 86 of 86 raw frames decoded. Hand-detection intervals: `[[1160, 1360], [1480, 2280], [2480, 2480]]` ms. Largest adjacent same-side point displacement: 0.07472 normalized units. This diagnostic can reflect fast motion or tracking/side reassignment and is not proof of biomechanical continuity.

Lexical evidence: [Tufto dictionary](https://atufto.no/HELP/sinhala/2025_Tufto_English-Sinhala_dictionary.pdf#page=88).

## Preservation and playback checks

The seven newly registered JSON assets reuse their original extracted files. Only the top-level sign ID changed for canonical registration; frames, duration and metadata are identical. No MP4 extraction or new training was needed. Original raw-ID motion files remain untouched. CRY, WALK and LOOK retain their existing checksums. All 59 raw MP4 source hashes still match the review baseline.

Backend registry path, identity, review and SHA checks remain intact. Pending batch meanings remain blocked even in research-preview mode; NURSE retains its existing preview restriction. The live interface never enables preview. LOOK and SEE have distinct senses and aliases.

[Playback results](playback-results.json) record actual HTTP asset loading, checksum/schema checks, real-time React playback, and exact matches between rendered hand coordinates and stored samples. All ten assets showed distinct saved hand frames and completed. Sequences include CRY-WALK-LOOK, DRINK-RUN, GIVE-TAKE, LOOK alone for the unsupported ASK-LOOK request, DRAW-SEE, and EAT. Rendered SVG samples are saved beside this report. This is DOM/SVG verification; no visible browser was available.

Qwen text and real generated-English-audio results are recorded separately in this directory. Initial failures are retained and must not be counted as passes. Audio uses Windows offline synthesized speech, not a human microphone or shared-tab recording. Sinhala speech is not verified by this expansion. No grammatical SLSL sentence claim is made.

## Reproduce

Backend/frontend startup and local model setup: [live-audio guide](../../../docs/live-audio.md). The user-facing route remains `/translation`, with Listen/Stop and avatar only. Research tools remain `/research`.

Run `backend/scripts/evaluate_vocabulary_expansion.py --output research/evaluation/vocabulary-expansion/qwen-rerun.json` from the component using `.venv/Scripts/python.exe`. It calls real local Qwen and refuses to overwrite evidence.

For saved-motion DOM playback, from `frontend`, set `$env:LANKASIGNS_EXPANSION_PLAYBACK_TEST="1"` and run `npm.cmd test -- src/components/avatar/VocabularyExpansionPlayback.test.tsx`. Preserve/rename the previous playback-results.json before an intentional rerun.

For real generated-speech -> local ASR/Qwen -> DOM avatar checks, keep the backend
and frontend running, then from the component run:

```powershell
.\backend\scripts\test_expansion_audio.ps1
```

This generates offline Windows voice fixtures and runs three actual inference
and playback tests. Browser capture alone is mocked; no ASR, Qwen, socket,
asset/hash check, or player is mocked. Choose a new `-ReportPrefix` for later
runs; existing reports are never overwritten. This does not verify a human
speaker, live system audio, Sinhala speech, or visible browser pixels.

## Expansion implementation files

- `datasets/metadata/vocabulary-reviews.json`, `dataset-vocabulary.json`, and
  `sign-registry.json`: seven approved additions, one documented pending review.
- `preprocessing/process_vocabulary.py`: reuse checksum-verified motion for
  canonical IDs, reject changed sources, and allow a separate evaluation report.
- `preprocessing/review_vocabulary_expansion.py`: raw-frame decode, motion,
  tracking continuity and immutable baseline audit; no approval automation.
- `backend/app/services/local_semantic_instructions.txt`, `live_pipeline.py`,
  and `ollama_provider.py`: registered action meanings, compact selection input,
  explicit abstention and supplementary unfamiliar-paraphrase meaning checks.
- `backend/scripts/evaluate_vocabulary_expansion.py` and
  `test_expansion_audio.ps1`: real inference/evaluation reproduction.
- `backend/tests/test_audio_pipeline.py` and `test_vocabulary_expansion.py`:
  review/integrity, abstention, semantic guard and unchanged-motion regressions.
- `frontend/src/components/avatar/VocabularyExpansionPlayback.test.tsx` and
  `LiveAudioAvatar.test.tsx`: real asset/clock playback, generated-PCM inference
  and preserved per-example evaluation reports.
- `README.md`, `docs/live-audio.md`, and this evaluation directory: current
  vocabulary status, review decisions and actual test evidence.
- Seven generated assets under
  `frontend/public/hand-animations/recorded/batch/`: `drink.json`, `run.json`,
  `give.json`, `take.json`, `see.json`, `draw.json`, `eat.json`. Generated assets
  remain under the existing Git-ignore policy; keep them with this local demo.

No production frontend page or renderer changes were needed for this expansion.
The original 3 animations and all older evaluation reports remain intact.

## Semantic evaluation policy

The earlier guarded pipeline scored 14/19 in `qwen-results.json`; its raw model
errors and all earlier development reports are retained. These are pipeline development examples,
not held-out accuracy. `qwen-final-results.json` records the final guarded
pipeline separately; do not substitute its score for raw model accuracy.

LOOK's English scope was clarified as deliberate visual attention, with SEE
reserved for perception. Its existing animation and checksum are unchanged.
Reviewed English exclusion phrases, including nonliteral run/give/take/see/draw
uses and LOOK/SEE contrasts, are stored with the vocabulary. The live processor
may reject those phrases or negated English clauses; it never creates a
selection from them. Qwen remains responsible for every proposed ID and context.
Clear inflections such as sips and hands over were added to reviewed synonyms.
Literal phrase hints help preserve source case but cannot enqueue anything.
One failed-evidence/meaning correction attempt is allowed, still subject to all
original validators. Failed repairs abstain. Logs keep both attempts and costs.
