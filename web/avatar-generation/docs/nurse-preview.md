# NURSE: first extracted recording

Source supplied by the repository owner: [Sinhala Sign Language Video Dataset on Kaggle](https://www.kaggle.com/datasets/dckahawearachchi/sinhala-sign-language-dataset).
Local input: datasets/raw/nurse.mp4. The original video is unchanged.

## Result
- Sign identifier: NURSE (from the provided filename, not independently linguistically validated).
- Saved file: frontend/public/hand-animations/recorded/nurse.json.
- Duration: 3360 ms; source: 1280 x 720 at 25 fps.
- Samples: 84; predicted left hand in 39, predicted right in 39, both in 35.
- 41 frames have no hand detections: 15 leading frames, 25 trailing frames, and one internal gap at 2040 ms.
- Missing hands remain null. No interpolation or invented motion was inserted.
- Python helper tests: 3 passed; frontend suite: 32 passed; production build and schema validation passed.
- Handedness and sign correctness remain pending expert review. These detection counts are not accuracy metrics.

The reviewed vocabulary manifest remains unchanged. The extracted recording can be inspected separately without falsely approving it.

## Watch it locally
From the repository root:
```powershell
cd web/avatar-generation/frontend
npm.cmd run dev
```
Open http://127.0.0.1:5173/translation, expand **Preview an extracted recording before review**, choose **Extracted animation JSON**, and select:
```text
C:\Users\ASUS\Desktop\RP_Repo\web\avatar-generation\frontend\public\hand-animations\recorded\nurse.json
```
Press Play preview. The first ~0.6 seconds are blank because the source's hands are not detected yet. Controls support pause/resume, restart, replay and speed changes. This file is a real extracted recording, not a synthetic diagnostic, but it is not a reviewed sign-library entry.

## Extraction environment
All runtime files are inside this component:
- .tools/python-3.11.9: official Python NuGet distribution.
- .venv: isolated Python environment.
- preprocessing/models/hand_landmarker.task: Google's official model.
- .cache: dependency/runtime caches and a sampled source-with-landmarks contact sheet.
- preprocessing/requirements-windows-py311.lock.txt: tested package versions.

From this component directory:
```powershell
.venv\Scripts\python.exe -m unittest discover -s preprocessing
.venv\Scripts\python.exe -m pip check
```
To re-extract without overwriting the original output:
```powershell
.venv\Scripts\python.exe preprocessing/extract_hand_landmarks.py --input datasets/raw/nurse.mp4 --model preprocessing/models/hand_landmarker.task --sign-id NURSE --dataset-reference "https://www.kaggle.com/datasets/dckahawearachchi/sinhala-sign-language-dataset" --output frontend/public/hand-animations/recorded/nurse-v2.json
```
The extractor refuses an existing output path. Python need not be installed system-wide to use the existing local environment.

Detailed file/model hashes, versions and review status are recorded in [nurse-extraction.json](../datasets/metadata/nurse-extraction.json). Raw video, model, environment, generated landmarks and runtime caches are ignored by Git; provenance, code and documentation remain reviewable.
