# Training (Step 3)

## Architecture

Sensor frames `[T, 22]` → 1D CNN → BiLSTM → frame logits → CTC decode → gloss sequence.

- CTC blank index: 0
- Default: 32 CNN channels, 32 BiLSTM hidden, batch 4, Adam lr 0.001, 20 epochs
- Training runs in a **separate subprocess** (`scripts/train_worker.py`)
- Test split is never used for training

## Model bundle

Each trained model is saved under `artifacts/models/job_{id}/`:

- `model.pt` — PyTorch state_dict
- `vocabulary.json`, `preprocessing.json`, `model_config.json`
- `feature_schema.json`, `training_settings.json`, `validation_results.json`
- `emotion_model.pkl` (optional, motion-based sklearn model)

## Fresh training vs reset

- **Start Fresh Training** — new random weights, new normalization from train split only
- **Reset Workspace** — deactivate/archive models; requires typing `RESET`; defaults to archive not delete

## Emotion model

Trained separately on motion features when train split has neutral/angry labels. Not available if insufficient labels.

## Verified behavior (Step 3)

- 23 backend tests pass, including CTC decode/alignment, checkpoint save/reload, and inference on sensor tensors
- End-to-end training on 50 synthetic recordings (2 epochs) completes via subprocess worker
- Test split is excluded from training; preview warns when test recordings exist
- Model bundles saved under `artifacts/models/job_{id}/` with `model.pt`, vocabulary, preprocessing, and optional emotion model
- Activation, archive, and typed `RESET` workspace flow tested
