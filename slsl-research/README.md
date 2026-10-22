# SLSL AI Studio

A local workspace for one continuously trained CNN-BiLSTM-CTC sign-sequence model.

**Data → Train → Test → Improve**

## Start

Run in PowerShell from this directory:

```powershell
.\scripts\start-dev.ps1
```

Open http://localhost:5173. The existing Python environment and frontend dependencies are required.

## The five pages

- **Overview:** current model, vocabulary, latest sequence test accuracy, and next steps.
- **Data:** separate training and test uploads. Check which training collections to include.
- **Train:** one Train Model button. Continuing training reuses learned weights, stable vocabulary IDs, normalization, and available optimizer state. New signs extend the vocabulary. Successful sessions automatically become the current model; recovery checkpoints stay internal.
- **Test:** recognize full sequences or play a CSV progressively. An optional answer key enables scoring. Provisional playback output may change until the complete sequence arrives.
- **Dictionary:** search the current model vocabulary and recording examples.

A learned emotion classifier is disabled. The Test page supports a configurable angry keyword expression rule; it does not measure signer emotion. Physical glove streaming and public deployment are future work.

## CSV data

Each motion row is one timestamped frame. Required columns are:

```csv
timestamp_ms,left_flex_1,left_flex_2,left_flex_3,left_flex_4,left_flex_5,left_acc_x_g,left_acc_y_g,left_acc_z_g,left_gyro_x_dps,left_gyro_y_dps,left_gyro_z_dps,right_flex_1,right_flex_2,right_flex_3,right_flex_4,right_flex_5,right_acc_x_g,right_acc_y_g,right_acc_z_g,right_gyro_x_dps,right_gyro_y_dps,right_gyro_z_dps
```

Use normalized finger bends, acceleration in g, and angular velocity in degrees per second. Timestamps must increase strictly; values must be finite. At least four frames are required, and labelled sequences need sufficient frames for CTC.

### Training

Add an `ordered_sign_labels` column containing the complete sequence, for example `I|NEED|WATER`. Put it on the first row or repeat the same sequence on every row. `sign_labels` and `meaning` are accepted aliases.

One CSV can contain multiple recordings using a `recording_id` column. Reset timestamps for each recording and give each recording its own complete ordered sequence.

Alternatively upload sensor-only CSVs with a separate manifest:

```csv
recording_id,ordered_sign_labels
example_01,I|NEED|WATER
```

The identifier matches the CSV filename without `.csv`, or the recording_id inside a combined training file. Labels are separated from motion before storage and model input. Filenames never determine predictions.

### Testing

Upload motion-only CSVs separately. Each test CSV is one full recording. Optionally provide an answer-key CSV:

```csv
recording_id,ordered_sign_labels
unknown_01,I|NEED|WATER
```

This refers to `unknown_01.csv`. The model receives only motion; answers are compared after prediction. Re-uploading the same motion updates its test entry instead of counting it twice. A copied training recording can be recognized but is excluded from accuracy.

**Sequence test accuracy** is the percentage of scored test recordings whose entire predicted sign sequence matches the answer. Without an answer key, results are predictions without accuracy. Previous-model results are marked and excluded from current-model accuracy.

## Continued training and reset

Selected collections are replayed together. Training and held-out splits remain separate, and duplicate source content cannot cross those splits. More training does not guarantee improvement; check independent test recordings after each session.

Reset archives the current model and clears its active vocabulary without deleting recordings. Before starting with glove data, uncheck earlier practice collections on the Data page and select the new recordings.

Generated glove-format data tests software behavior. Its accuracy does not establish physical-glove or genuine SLSL accuracy. Video-derived features from the earlier conversion use a different schema and must not be renamed into physical IMU measurements. Data origin can remain in metadata without separate dashboard workflows.

The Test page keeps the motion recognizer and spoken-English model separate. Clicking **Recognize** shows **Predicting motion…**, then the raw recognized words, then **Forming sentence…**, followed by a suggested spoken sentence from a local Qwen2.5-0.5B-Instruct model. The sentence is a suggestion, not a corrected motion prediction. Only the motion model's raw words are scored against the answer key. **Run all tests** scores motion recognition without running the language model on every file.

The sentence endpoint reads only the stored prediction and uncertainty flag; reference answers, filenames, and reference sentences never enter the language model. Content-word checks reject many additions or omissions, but do not prove semantic or SLSL equivalence. Uncertain predictions and untranslated `SOURCE1` labels are kept literal. If the local model is missing, busy, fails, or times out, the recognized words remain visible with a retry option where appropriate. Sentence results are saved alongside their exact recognition ID; rerunning motion recognition invalidates older sentence suggestions.

### Local sentence model setup

Install backend requirements, then download the pinned official model once (approximately 1 GB):

```powershell
cd backend
.\.venv\Scripts\python.exe scripts/setup_sentence_model.py --destination C:/CHATGPT/local-ai-models/qwen2.5-0.5b-instruct
```

Set `SLSL_SENTENCE_MODEL_DIR` in `backend/.env` to that directory. The current machine is already configured to use this location. It is kept outside training artifacts, so model resets do not delete it.

Model source: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct (revision `7ae557604adf67be50417f59c2c2f167def9a775`). The installer verifies the official weights SHA-256 and retains the model license. After installation, requests use local files only and offline environment flags; no cloud inference or API key is needed. A CPU worker uses at most two PyTorch threads, bounded output, and a 120-second timeout. It exits after generation to free its model memory. Repeated identical word sequences can reuse a bounded in-memory cache. On a modest CPU, loading and generation can take several seconds. Use the motion model as the source of recognition accuracy, not the fluency of the sentence suggestion.

## Verification

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -q
cd ..\frontend
npm run typecheck
npm run test
npm run build
```

The studio tests cover label separation, answer-key isolation, duplicate-test protection, vocabulary expansion, optimizer continuation, normalization preservation, collection selection, and reset safety. Existing database fields and legacy endpoints are retained for compatibility; the primary UI uses the simplified studio workflow.


## Angry expression rule and synthetic add-on

On **Test -> Angry expression rule**, the default triggers are `HATE, DIE, STOP, ENOUGH, ANNOYING, IDIOT, LOSER, DISGUST, STUPID`. Edit the comma/newline-separated list, save it, or switch the rule off. Settings persist locally in ignored `data/expression_rules.json`.

A case-insensitive, exact whole recognized label matching the configured list adds `[angry]` after the suggested sentence. For example: `I | HATE | BAT` can become `I hate this bat. [angry]`. The raw words and sign accuracy remain unchanged. The language model still receives only predicted words; it does not receive answer keys or generate the emotion label. The API preserves plain `text` and exposes the bracketed version as `display_text`, with the matched trigger words in `expression` metadata. Rerun recognition after editing a rule to update an existing result.

This is an explicit user-configured expression annotation, not a learned classifier or proof of a signer's emotional state. Any matching word triggers the rule, including negated phrases; `BUS STOP` does not match the whole-label trigger `STOP`. No matching label adds no tag, rather than guessing neutral emotion. CNN training learns the added word motion patterns, not emotion.

The supplied **SLSL_Angry_Words_Addon_v1** package contains 540 labelled training recordings in 18 CSV shards and 72 motion-only tests with a separate answer key. It introduces eight new trigger labels plus BAT; STOP reuses the previous exact frozen prototype. Existing word prototypes are retained. New word motions are invented procedural software-test patterns, not verified SLSL gestures or measured glove signals. Dataset metadata documents the provenance, assumptions, seeds, and validation.

To continue the existing model: upload all `training/training_*.csv` files as an add-on collection, keep both the earlier full collection and this collection checked, then use **Train Model**. Do not reset the model. Existing vocabulary IDs and weights are preserved while new labels are added. Upload `tests/*.csv` separately with `test_answer_key.csv` and test after training completes. The optional expected-expression columns in that key are for manual rule checks; motion accuracy still scores words only.


### Interpreting test accuracy

Test sequence accuracy is exact recognized-word matches divided by scored, labelled recordings for the current model. It is recomputed from raw CNN words and answers after inference; sentence wording and expression annotations never affect it. The overview also shows pending tests, missing answer keys, exclusions, sign error rate and an approximate 95% Wilson interval (assuming independent test cases). Synthetic examples share prototypes, so the interval does not establish real-glove generalization. A finite set can legitimately score 100%; never cap or add errors to force a lower score.

Evaluation version 2 excludes numerical copies of training or validation recordings across known continued-training ancestors, ignoring CSV formatting and absolute clock origin. Older evaluations need rerunning under the new checks. Older bundles without source manifests use a conservative current-library exposure fallback; deleted source files cannot be reconstructed for historical overlap checks. Keep independent test signals and their variations out of training. Use the same fixed, labelled benchmark for checkpoint comparisons and a later untouched glove/signer set for final validation. More training is not guaranteed to improve accuracy.


### Offline Sinhala text and speech

On Test, Recognize now runs motion recognition, English phrasing, Sinhala translation and local speech preparation in stages. The new Sinhala panel shows the translation, an audio player, download link and retry controls. Playback is manual; no surprise autoplay. Cached translation/audio avoids repeating model work for identical inputs. Models run in short-lived CPU subprocesses, offline, to release memory between requests.

English uses the existing Qwen2.5-0.5B model. Valid known word sequences now receive a clearly labelled word-based fallback if Qwen is unavailable, busy, uncertain, times out or changes the content. Empty predictions and unknown SOURCE1 labels still cannot yield invented meanings. A fallback is not claimed to be fluent AI interpretation. CNN word scoring remains unchanged.

Translation uses Meta M2M100-418M (English `en` to Sinhala `si`), and speech uses the Dilu Sinhala Piper ONNX voice. These are pretrained models; this feature does not train Qwen, translation or speech, and it does not use Kaggle data. Sinhala output is a machine translation requiring native-speaker review, especially for negation, ambiguity, numbers, insults and names. Basic character/format validation does not prove semantic correctness.

Emotion is a separate optional field, never a spoken `[angry]` suffix. No expression selects the normal voice, without inferring neutral emotion. `angry` selects a simulated faster/stronger prosody preset. This is not a naturally acted or emotion-trained voice. Add future supported styles in `backend/app/ml/speech_styles.py`, or replace the speech worker with an emotion-conditioned model while preserving the same API; CNN changes are unnecessary. Unsupported future emotions return an explicit error instead of silently using an unrelated style.

Install backend requirements, then run from the project root:

```powershell
backend\.venv\Scripts\python.exe backend/scripts/setup_sinhala_models.py
```

The installer pins revisions, checks published SHA-256 weight checksums, supports resumable chunks, and defaults to `local_models/`. `--destination C:/path/to/models` supports a different folder; set `SLSL_TRANSLATION_MODEL_DIR` and `SLSL_SINHALA_VOICE_DIR` in backend/.env accordingly. `--verify-only` checks an existing installation without downloading. Combined translator/voice weights are about 2 GB; the existing Qwen model is separate. Inference never downloads missing models automatically.

Model information and notices: https://huggingface.co/facebook/m2m100_418M (MIT); https://huggingface.co/chaturadilan/dilu-tts (published MIT model card; includes upstream voice acknowledgements); https://github.com/OHF-Voice/piper1-gpl (GPL-3.0 runtime). Preserve applicable model/runtime and upstream notices for redistribution. No Path Nirvana speech dataset is downloaded or used by this setup.

Translation and speech use only the stored predicted sentence and configured expression, never filenames or answers. Every request is tied to the recognition ID, active model and translation ID. Old audio becomes unavailable after recognition/model changes; retrying the English sentence clears stale translations/audio. Deleting a test removes its generated WAVs. Generated audio, downloaded weights and local .env paths are ignored by Git.


The Sinhala panel includes **Edit Sinhala** and **Save & regenerate voice**. Corrections preserve the original machine wording in metadata, invalidate the old audio URL and synthesize only the corrected text. Voice retry preserves corrections instead of translating them away. This is important: an actual M2M100 smoke test translated “I hate bats” with the Sinhala word for “lies”; successful Sinhala-script output is not proof of meaning preservation. Review before playback, and use corrections when needed. This implementation does not claim universally correct automatic translation or native emotional acting.
