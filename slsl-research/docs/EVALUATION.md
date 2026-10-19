# Evaluation (Step 4)

## Purpose

Measure whether a trained CTC model predicts ordered sign-gloss sequences from unseen glove sensor recordings.

**Critical rule:** inference receives sensor features only. Reference gloss labels, English sentences, and emotion labels are compared **after** decoding.

## Workflow

1. Choose Model
2. Choose Dataset
3. Check Compatibility (vocabulary, splits, signer overlap)
4. Run Evaluation
5. Review Results

## Metrics

### Recognition (gloss tokens)

- Word Error Rate — token edit distance ÷ reference length
- Exact sequence accuracy
- Insertions, deletions, substitutions (per recording and aggregate)
- Mean / median inference latency (ms)

### Emotion (when labels exist)

- Accuracy, precision, recall, F1, confusion matrix
- Hidden when no `neutral`/`angry` ground truth in the evaluation split

Decoder scores are labelled **uncalibrated_decoder_score** — not correctness probabilities.

## Artifacts

Results saved under `artifacts/evaluations/eval_{id}/results.json` with per-recording predictions and aggregate metrics.

## Limitations

- No estimated sign boundaries (gloss-level only)
- Generated English is simple gloss concatenation, not translation
- Synthetic prototype results are labelled separately from real SLSL data
- Validation/train splits may be used for diagnostics but are warned against for final reporting
