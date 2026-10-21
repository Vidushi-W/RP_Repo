# Component 3: SLSL Kinematics MVP

Standalone Python webcam prototype for Component 3. It is separate from the Expo app and other members' components. MongoDB is not connected; reference templates load locally.

## Setup

Use Python 3.10 or newer in a virtual environment:

```powershell
cd component-3-slsl
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python process_references.py
python main.py
```

The MediaPipe Tasks model `hand_landmarker.task` must be in this folder. Allow camera access when prompted.

## Reference data

Put source photos or videos in `references/<sign-label>/`. The offline extractor samples video frames, detects up to two hands, extracts the 21 XYZ landmarks, translates the wrist to the origin, and scales by maximum wrist-relative distance. It writes `references/processed/<label>.npy` arrays plus JSON metadata with source filenames, frame numbers, and hand indices. Still JPG, PNG, BMP, and WebP images are also supported.

The current user-provided templates contain `book-sign` (1 hand pose), `house-sign` (1), and `pen-sign` (1) from images; and `come` (12 frames), `go` (26), and `like` (25) from videos. The house picture visibly has two hands, but MediaPipe detected one, so the stored reference is incomplete for a two-hand sign.

`reference_loader.py` keeps frames grouped by source file and in temporal order. For a video reference, `metrics.py` uses dynamic time warping (DTW) to align the learner's captured movement with the reference movement, allowing different signing speeds. A still image is a one-frame pose reference. Frames with different detected hand counts are not paired; the capture keeps its dominant hand count.

## Hands-free practice UI

Run `python main.py`. The UI shows a picture cue without relying on a written sign name. For each sign it:

1. Shows the cue for 4.5 seconds.
2. Counts down for 3 seconds.
3. Records 4 seconds of signing automatically.
4. Shows a locked result for 4 seconds, then advances to the next sign.

No keypress is needed while signing. `N` skips to the next cue, `1`–`6` selects a sign, `R` restarts its prompt, `P` pauses/resumes, and `Q` quits.

The similarity uses the supplied formula. Each aligned frame distance is the mean of the per-landmark Euclidean distances, `d = (1/21) * sum(norm(live[i] - reference[i]))`; the sequence distance averages those frame distances along the DTW path, then maps to `max(0, (1 - 2*d) * 100)`. Video comparison trims idle frames at the beginning and end and allows tempo differences while retaining landmark order. It is a prototype pose/sequence similarity, not calibrated accuracy, probability, or validated sign recognition. Closest-template comparisons can overstate a match, especially with only one source video per sign.

Thumb IP angles (landmarks 2, 3, 4) and index PIP flexion (5, 6, 7) are compared along the aligned frames. Median angle differences over 20 degrees are shown as preliminary diagnostic flags, not validated instructional thresholds. Landmarks 5, 6, 7 describe the index PIP angle, not the MCP angle. Two-hand frames are paired jointly when both reference and learner have the same detected hand count, but the house reference currently has only one detected hand.

## Modules

- `normalization.py`: wrist-origin and scale normalization.
- `metrics.py`: landmark distance, similarity mapping, DTW sequence comparison, and joint angles.
- `extract_references.py` / `process_references.py`: offline landmark extraction.
- `reference_loader.py`: local template and sequence loading.
- `main.py`: picture prompts, automatic camera capture, and locked feedback.

Record source and signer provenance for academic presentation. Avoid treating unclear or unlabeled images as ground truth.
