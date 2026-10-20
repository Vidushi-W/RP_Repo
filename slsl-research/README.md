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

Emotion recognition is disabled. Physical glove streaming and public deployment are future work.

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
