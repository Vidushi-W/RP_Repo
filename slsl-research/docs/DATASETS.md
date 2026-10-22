# Dataset Management (Step 2)

## Sensor CSV format

Recording files contain **only** the 23 sensor measurement columns. Labels never appear in sensor CSVs.

## Manifest canonical schema

| Column | Accepted aliases |
|--------|------------------|
| recording_id | id, sample_id |
| filepath | file, file_path, path |
| signer_id | signer |
| provenance | source_type, source |
| ordered_sign_labels | sign_labels, labels, gloss_sequence |
| emotion_label | emotion |
| reference_english_sentence | sentence_reference, english_sentence |
| split | dataset_split |
| collection_date | recorded_at, date |

## Synthetic data disclaimer

Generated gestures are artificial prototype patterns assigned to concept classes. They are **not** genuine Sri Lankan Sign Language recordings and must not be reported as real-user performance.

Synthetic signer IDs (e.g. `SYNTHETIC_SIGNER_01`) are software identifiers, not human participants.

## Split policy

- Splits are assigned per recording group, never per frame.
- Default suggested ratio: 70% train / 15% validation / 15% test.
- Imported splits are preserved when `preserve_existing` is true.
- Normalization parameters must be fitted on training data only (enforced in later training step).
