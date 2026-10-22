# Model Bundle Contract

Each trained model is stored under `artifacts/models/job_{id}/` (or imported equivalent).

## Required files

| File | Purpose |
|------|---------|
| `model.pt` | PyTorch `state_dict` only (loaded with `weights_only=True`) |
| `vocabulary.json` | Gloss ↔ id mapping, blank index 0 |
| `preprocessing.json` | Train-split normalization parameters |
| `model_config.json` | Architecture dimensions |

## Optional files

| File | Purpose |
|------|---------|
| `emotion_model.pkl` | sklearn classifier (motion features) |
| `emotion_metadata.json` | Emotion model provenance |
| `validation_results.json` | Training/val metrics |
| `bundle_manifest.json` | Version and lineage |

## Import safety

- ZIP path traversal blocked
- Only `.pt`, `.json`, `.pkl` files accepted
- Vocabulary and preprocessing required before activation
- Arbitrary Python pickles outside emotion model are rejected
