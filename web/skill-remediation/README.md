# Component 3: SLSL Kinematics MVP

Browser-based SLSL sign-practice page with a Python/FastAPI backend for reference comparison and kinematic error diagnosis. The browser displays the reference, captures camera samples, and lets the learner move manually between signs. The OpenCV desktop interface remains available for research and data collection.

## Project layout

- `frontend/web/`: browser learning interface (HTML, CSS, JavaScript).
- `frontend/`: Python data collection and research utilities.
- `backend/`: FastAPI service, scoring and reference modules, local attempt storage, and model/evaluation commands.
- `references/`, `data/`, and `research_evaluation/`: local reference assets and research data.
- `.env`: local API/database configuration; keep it private.

## Setup

Use Python 3.10 or newer in a virtual environment:

```powershell
cd "web/skill-remediation"
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env and replace DB_USERNAME and URL_ENCODED_PASSWORD with your Atlas credentials.
python -m backend.process_references
```

The MediaPipe Tasks model `hand_landmarker.task` must be in this folder. The browser asks for camera permission after you open the learning page.

## MongoDB API

Set `MONGODB_URI` in `web/skill-remediation/.env` using the Atlas connection string. URL-encode special characters in the database password. Keep `.env` private; it is ignored by git. The app uses the `slsl_research_db` database and writes attempts to the `component3_kinematic_attempts` collection. Each record includes the user/sign ids, UTC timestamp, detected/expected hand counts, completion or skip status, DTW/similarity/latency metrics, measured finger angles, error codes, and any remediation recommendation. For completed attempts with detected errors, it also stores up to 120 sampled frames of normalized landmark coordinates under `kinematic_observation`; it never stores webcam images or video.

Verify the configured Atlas connection and insert a clearly marked test-only record (no guessed score) with:

```powershell
python -m backend.seed_mongodb
```

The script inserts and reads back a document with `record_type: CONNECTION_TEST` and `user_id: __connection_test__`; it is not counted as a learner attempt. Refresh Atlas at `slsl_research_db` → `component3_kinematic_attempts` to see it.

Start the local API in one terminal:

```powershell
cd "web/skill-remediation"
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/` for the browser learning experience. The browser asks for camera permission; use localhost or an HTTPS deployment. `/api/lesson` lists signs with processed references, and `/api/analyze` sends sampled camera images to Python for MediaPipe landmarks, DTW reference comparison, and the approved Random Forest model. The diagnosis model currently supports only `like`; other signs still receive reference comparison and explain that the model does not cover that sign. The reference similarity is a prototype measure, not signing accuracy. Lesson navigation is always manual, and navigating away clears prior feedback.

Open `http://127.0.0.1:8000/health` to verify the MongoDB connection. If Atlas DNS or network access is down, the learning page still starts and practice results are kept in local SQLite. MongoDB is retried for new attempts once the connection is available; older SQLite-only results are not automatically uploaded. To open the separate research webcam client (not the learner-facing web page), run:

```powershell
cd "web/skill-remediation"
python -m frontend.main
```

The OpenCV practice client submits completed attempts to the API, which persists them in MongoDB. The client also maintains a local SQLite history cache for offline recurrence recommendations. Check Atlas Network Access and ensure the database user has read/write permission on the configured database if the health check fails.

## Reference data

Put source photos or videos in `references/<sign-label>/`. The offline extractor samples video frames, detects up to two hands, extracts the 21 XYZ landmarks, translates the wrist to the origin, and scales by maximum wrist-relative distance. It writes `references/processed/<label>.npy` arrays plus JSON metadata with source filenames, frame numbers, and hand indices. Still JPG, PNG, BMP, and WebP images are also supported.

The processed templates contain `book-sign` (2 hands in one image), `house-sign` (2 hands in one image), and `pen-sign` (1) from images; and `come`, `go`, and `like` from videos. For the two-hand still references, if full-image detection misses a hand, extraction detects each hand from overlapping, square-padded crops and combines them into the same reference frame.

The extractor requests two hands and uses a lower detection threshold to recover hands in still images. `references/sign_requirements.json` declares that book-sign and house-sign require two hands. The live scorer refuses to output a similarity when the learner or the template is missing a required hand, instead of comparing incomplete data.

To add a better reference pose, copy a source photo or preferably a short, clear video into that sign's folder. For example, from this project directory in PowerShell:

```powershell
Copy-Item "C:\path\to\book-reference.mp4" ".\references\book-sign\book-reference-02.mp4"
.\.venv\Scripts\python.exe -m backend.process_references
```

Use the same pattern for `references\like`, `references\come`, and the other sign folders. The extractor rebuilds `references\processed\<sign>.npy` and its JSON metadata from every source in each sign folder; the loader keeps each source video as its own ordered sequence. For a new two-hand sign, add its required count before processing, for example `"new-two-hand-sign": { "expected_hands": 2 }` in `references\sign_requirements.json`. Two-hand photos and videos use a crop fallback when the full-frame detector misses one hand. Confirm the processing output says it extracted both hands; the live loader ignores incomplete frames for signs marked as two-hand.

`backend/reference_loader.py` keeps frames grouped by source file and in temporal order. For a video reference, `backend/metrics.py` uses dynamic time warping (DTW) to align the learner's captured movement with the reference movement, allowing different signing speeds. A still image is a one-frame pose reference. Frames with different detected hand counts are not paired; the capture keeps its dominant hand count.

## Browser learning experience

Start the FastAPI service using the command above, then open `http://127.0.0.1:8000/`. The page serves the available reference images and videos and displays the webcam inside the browser. The learner presses **Sign now** to capture a short attempt; temporary camera snapshots go to Python for MediaPipe hand tracking and are not saved. Only normalized landmark data from attempts with a model-predicted error may be retained in history. Camera access requires localhost or HTTPS.

The page compares attempts with processed reference sequences using DTW, and runs the approved Random Forest only for signs included in its training bundle (currently `like`). Unsupported signs still receive reference comparison. It labels reference similarity separately from model diagnosis, does not show uncalibrated confidence as a score, and never advances automatically. Previous/Next navigation clears old feedback and ignores an analysis result if the learner has changed signs. Repeated diagnosed errors can trigger a practice suggestion through the existing remediation graph.

## Legacy desktop practice interface

Run `python -m frontend.main`. The UI shows the actual source image, or the first frame of the source video, as its cue. For each sign it:

1. Shows the cue for 4.5 seconds.
2. Counts down for 3 seconds.
3. Records 4 seconds of signing automatically.
4. Shows a locked result for 4 seconds, then advances to the next sign.

No keypress is needed while signing. `N` skips to the next cue, `1`–`6` selects a sign, `R` restarts its prompt, `P` pauses/resumes, and `Q` quits.

The similarity uses extracted MediaPipe landmarks from the source reference and live camera, not fixed example scores. Each aligned frame distance is the mean of per-landmark Euclidean distances; the sequence distance averages those frame distances along the DTW path, then maps to `max(0, (1 - 2*d) * 100)`. Because the camera preview is mirrored, the scorer reverses the normalized horizontal coordinate before comparing with unmirrored source media. Video comparison trims idle frames at the beginning and end and allows tempo differences while retaining landmark order. This formula can bottom out at 0 for substantial pose differences; it is a prototype pose/sequence similarity, not calibrated accuracy, probability, or validated sign recognition. Closest-template comparisons can overstate a match, especially with only one source video per sign.

The currently displayed thumb and index statuses compare those finger angles against the closest reference along the DTW alignment; differences over 20 degrees show `Needs adjustment`. These are reference deviations, not classifier diagnoses.

## Persistent attempts and remediation

The backend supports attempt persistence in MongoDB and a local SQLite cache at `data/attempts.sqlite3`. Set `SLSL_USER_ID` in `.env` to separate learners; the default is `student_01`.

`backend/remediation_engine.py` defines a NetworkX directed graph from error codes to skills and exercises, with the six signs represented as graph nodes. After a completed attempt, the client checks up to the previous four attempts plus the current attempt; an error seen at least three times can trigger a suggested exercise. MongoDB history is preferred and SQLite history is used when the API is unreachable. The graph, labels, and threshold are prototype scaffolding and require review with SLSL instructors and learner evidence before being described as validated remediation.

## Empirical evaluation

The webcam module records analysis latency for each attempt. To evaluate rather than assume performance, annotate real trials in `research_evaluation/trials.csv` and run `python -m backend.evaluate_trials`. The script reports the supplied intentional-error detection rate, conventional diagnostic precision, mean/median analysis latency, and the mean score difference between fast and slow attempts of the same sign. Collect at least 20 intentional-error trials and paired fast/slow trials; no empirical accuracy claim is made until those rows are collected from real signing sessions.

## Optional trained kinematic error classifier

MediaPipe remains the pretrained landmark detector; the Random Forest is a separate, locally trained diagnostic model. It predicts only among the labels in the collected dataset and only for sign IDs represented in that dataset. Model confidence is an uncalibrated classifier score, not a probability or accuracy percentage.

Install the additional requirements with `python -m pip install -r requirements.txt`. Collect labeled examples for one sign at a time (the collector uses one hand):

```powershell
python -m frontend.collect_training_data --sign-id like --signer-id signer_01
```

In the camera window, press `1` for `NORMAL`, `2` for `ERR_PINKY_FLEX`, `3` for `ERR_INDEX_EXT`, or `4` for `ERR_WRIST_ROTATION`. Each press records 50 detected frames by default as one capture session. Repeat each label across multiple separate captures. Make sure the pose actually reflects the selected sign and error; labels are ground truth supplied by the collector, not inferred by the software. Use pseudonymous signer IDs and obtain participant consent. For other signs or participants, use their own IDs, for example `--sign-id book-sign --signer-id signer_02`. Press `Q` to close.

The extractor centers landmarks at the wrist and scales the pose, so its XYZ inputs are already invariant to where the hand appears and its overall size. The feature vector also includes the 15 joint angles. Angle-only features were tried against the current sessions and performed worse, so training retains both normalized geometry and angles.

Train and save the model:

```powershell
python -m backend.train_model
```

Training evaluates with three-fold `GroupKFold`, grouping by whole capture sessions (or whole signers once multiple signer IDs exist). It reports both out-of-fold frame accuracy and session-level accuracy after the same majority vote used during live inference. Then it fits a research artifact on all labeled samples. The app will load the model for live inference only after held-out session accuracy and recall for every class reach 45%, each class has at least three capture sessions, and the dataset includes at least one signer. A saved research model below those requirements is deliberately disabled in the webcam UI and is not logged as a diagnosis.

The current dataset has 8,000 frames from 160 capture sessions and one signer. Grouped cross-validation measured 62.90% frame accuracy and 63.12% session majority accuracy. Session recall is 59% for `ERR_INDEX_EXT`, 47% for `ERR_PINKY_FLEX`, 59% for `ERR_WRIST_ROTATION`, and 78% for `NORMAL`. At the 45% threshold and one-signer requirement, this dataset meets the current approval gates. It covers only `like` and the labels `NORMAL`, `ERR_INDEX_EXT`, `ERR_PINKY_FLEX`, and `ERR_WRIST_ROTATION`. Vary distance and mild hand angle between sessions, but keep the label tied to the actual visible hand pose; do not label frames based only on the key pressed. Re-train after collecting data and use the grouped session report before enabling inference.

For a supported one-hand sign, the app predicts on captured frames and would use the majority label as the attempt diagnosis when the model meets the validation gate. Inputs include normalized landmark coordinates and 15 joint angles. The UI shows Random Forest diagnosis separately from DTW pose similarity. Class confidence is an uncalibrated model score, not accuracy or probability. MongoDB stores a predicted label only when an approved model is active; for a predicted error, up to 120 normalized landmark frames are stored as `kinematic_observation`. No training CSV or raw webcam video is sent to MongoDB. Unsupported signs and multi-hand captures do not receive an RF diagnosis.

## Modules

- `backend/normalization.py`: wrist-origin and scale normalization.
- `backend/metrics.py`: landmark distance, similarity mapping, DTW sequence comparison, and joint angles.
- `backend/extract_references.py` / `backend/process_references.py`: offline landmark extraction.
- `backend/reference_loader.py`: local template and sequence loading.
- `frontend/web/`: browser learning page and in-browser camera controls.
- `frontend/main.py`: separate OpenCV research and data-collection interface.
- `backend/attempt_store.py` / `backend/app.py`: local history and MongoDB API persistence.
- `backend/seed_mongodb.py`: test-only insert and read-back verification.
- `backend/remediation_engine.py`: NetworkX error-to-skill-to-exercise graph.
- `backend/evaluate_trials.py`: summary metrics for manually annotated real trials.
- `backend/ml_features.py`, `backend/dataset_schema.py`, `frontend/collect_training_data.py`, `backend/train_error_model.py`, `backend/ml_classifier.py`: model data collection, training, and inference modules.

Record source and signer provenance for academic presentation. Avoid treating unclear or unlabeled images as ground truth.
