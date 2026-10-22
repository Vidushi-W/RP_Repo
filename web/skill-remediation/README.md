# Component 3: SLSL Kinematics MVP

Standalone Python sign-practice prototype and API backend for Component 3. The current interface is a local OpenCV webcam client; there is no browser-based frontend yet. The API is a separate backend service. Reference templates and local data remain in this project folder.

## Project layout

- `frontend/`: OpenCV webcam practice client, its API client, and webcam data collection UI.
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

The MediaPipe Tasks model `hand_landmarker.task` must be in this folder. Allow camera access when prompted.
The webcam uses its default working resolution and preserves the input aspect ratio in the display. Optionally set both `SLSL_CAMERA_WIDTH` and `SLSL_CAMERA_HEIGHT` to request a different mode; `SLSL_CAMERA_INDEX` and `SLSL_CAMERA_BACKEND` select the device/backend. The preview draws the hand skeleton with markers only at the wrist and fingertips to keep the view clear.

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

Open `http://127.0.0.1:8000/health`; a successful response confirms that MongoDB is reachable. In another terminal, run the webcam demo:

```powershell
cd "web/skill-remediation"
python -m frontend.main
```

The API service persists submitted attempts in MongoDB. The OpenCV client is currently a standalone practice interface; it can be connected to the API as the component evolves. Check Atlas Network Access and ensure the database user has read/write permission on the configured database if the health check fails.

## Reference data

Put source photos or videos in `references/<sign-label>/`. The offline extractor samples video frames, detects up to two hands, extracts the 21 XYZ landmarks, translates the wrist to the origin, and scales by maximum wrist-relative distance. It writes `references/processed/<label>.npy` arrays plus JSON metadata with source filenames, frame numbers, and hand indices. Still JPG, PNG, BMP, and WebP images are also supported.

The current user-provided templates contain `book-sign` (1 hand pose), `house-sign` (2 hands in one frame), and `pen-sign` (1) from images; and `come` (12 frames), `go` (28), and `like` (25) from videos. The house image's touching hands are difficult to separate in a full-frame detection, so still-image extraction uses an overlapping crop fallback for the missing hand.

The video extractor requests two hands and uses 0.3 detection/presence/tracking confidence. Still-image crop recovery uses a lower detection threshold. `references/sign_requirements.json` declares that house-sign requires two hands. The live scorer refuses to output a similarity when the learner or the template is missing a required hand, instead of comparing incomplete data.

`backend/reference_loader.py` keeps frames grouped by source file and in temporal order. For a video reference, `backend/metrics.py` uses dynamic time warping (DTW) to align the learner's captured movement with the reference movement, allowing different signing speeds. A still image is a one-frame pose reference. Frames with different detected hand counts are not paired; the capture keeps its dominant hand count.

## Hands-free practice UI

Run `python -m frontend.main`. The UI shows a picture cue without relying on a written sign name. For each sign it:

1. Shows the cue for 4.5 seconds.
2. Counts down for 3 seconds.
3. Records 4 seconds of signing automatically.
4. Shows a locked result for 4 seconds, then advances to the next sign.

No keypress is needed while signing. `N` skips to the next cue, `1`–`6` selects a sign, `R` restarts its prompt, `P` pauses/resumes, and `Q` quits.

The similarity uses the supplied formula. Each aligned frame distance is the mean of the per-landmark Euclidean distances, `d = (1/21) * sum(norm(live[i] - reference[i]))`; the sequence distance averages those frame distances along the DTW path, then maps to `max(0, (1 - 2*d) * 100)`. Video comparison trims idle frames at the beginning and end and allows tempo differences while retaining landmark order. It is a prototype pose/sequence similarity, not calibrated accuracy, probability, or validated sign recognition. Closest-template comparisons can overstate a match, especially with only one source video per sign.

The engine compares thumb MCP/IP, thumb-spread proxy, and MCP/PIP/DIP flexion angles for index, middle, ring, and pinky along the DTW alignment. Median differences over 20 degrees produce provisional error codes. `ERR_WRIST_ROTATION` is based on palm-plane orientation because MediaPipe Hands does not supply wrist articulation landmarks. These are initial diagnostic heuristics, not validated clinical or instructional thresholds.

## Persistent attempts and remediation

The backend supports attempt persistence in MongoDB and a local SQLite cache at `data/attempts.sqlite3`. Set `SLSL_USER_ID` in `.env` to separate learners; the default is `student_01`.

`backend/remediation_engine.py` defines a NetworkX directed graph from error codes to skills and exercises, with the six signs represented as graph nodes. The graph and thresholds are prototype scaffolding and require review with SLSL instructors and learner evidence before being described as validated remediation.

## Empirical evaluation

The webcam module records analysis latency for each attempt. To evaluate rather than assume performance, annotate real trials in `research_evaluation/trials.csv` and run `python -m backend.evaluate_trials`. The script reports the supplied intentional-error detection rate, conventional diagnostic precision, mean/median analysis latency, and the mean score difference between fast and slow attempts of the same sign. Collect at least 20 intentional-error trials and paired fast/slow trials; no empirical accuracy claim is made until those rows are collected from real signing sessions.

## Optional trained kinematic error classifier

MediaPipe remains the pretrained landmark detector; the Random Forest is a separate, locally trained diagnostic model. It predicts only among the labels in the collected dataset and only for sign IDs represented in that dataset. Model confidence is an uncalibrated classifier score, not a probability or accuracy percentage.

Install the additional requirements with `python -m pip install -r requirements.txt`. Collect labeled examples for one sign at a time (the collector uses one hand):

```powershell
python -m frontend.collect_training_data --sign-id like --signer-id signer_01
```

In the camera window, press `1` for `NORMAL`, `2` for `ERR_PINKY_FLEX`, `3` for `ERR_INDEX_EXT`, or `4` for `ERR_WRIST_ROTATION`. Each press records 50 detected frames by default as one capture session. Repeat each label across multiple separate captures. Make sure the pose actually reflects the selected sign and error; labels are ground truth supplied by the collector, not inferred by the software. Use pseudonymous signer IDs and obtain participant consent. For other signs or participants, use their own IDs, for example `--sign-id book-sign --signer-id signer_02`. Press `Q` to close.

Train and save the model:

```powershell
python -m backend.train_error_model
```

The script reports a held-out score only when it can keep groups separate and all labels represented on each side. With multiple signer IDs it holds out entire signers; with one signer it holds out capture sessions and explicitly reports that this does not measure generalization to new signers. Collect every label in multiple distinct sessions (and, for signer-independent evaluation, across multiple signers). A frame-level score still weights long recordings more heavily and should be described as a pilot result, not validated system accuracy. If a CSV header is from the earlier feature format, `dataset_schema.py` repairs it while keeping a `.bak` copy. It saves `kinematic_error_classifier.pkl`, which is ignored by git; run `python -m frontend.main` again to load it. For each completed attempt, the app predicts on individual captured frames and uses the majority label as the stable classifier result. Inputs include 63 normalized landmark coordinates, finger angles, and a palm-plane normal feature for orientation. The result and MongoDB `metrics` include its predicted label and mean per-frame class confidence. If that attempt has a detected error, its normalized sequence is stored as `kinematic_observation`; no training CSV or raw webcam video is sent to MongoDB.

## Modules

- `backend/normalization.py`: wrist-origin and scale normalization.
- `backend/metrics.py`: landmark distance, similarity mapping, DTW sequence comparison, and joint angles.
- `backend/extract_references.py` / `backend/process_references.py`: offline landmark extraction.
- `backend/reference_loader.py`: local template and sequence loading.
- `frontend/main.py`: picture prompts and local webcam practice interface.
- `backend/attempt_store.py` / `backend/app.py`: local history and MongoDB API persistence.
- `backend/seed_mongodb.py`: test-only insert and read-back verification.
- `backend/remediation_engine.py`: NetworkX error-to-skill-to-exercise graph.
- `backend/evaluate_trials.py`: summary metrics for manually annotated real trials.
- `backend/ml_features.py`, `backend/dataset_schema.py`, `frontend/collect_training_data.py`, `backend/train_error_model.py`, `backend/ml_classifier.py`: model data collection, training, and inference modules.

Record source and signer provenance for academic presentation. Avoid treating unclear or unlabeled images as ground truth.
