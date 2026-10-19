# Playground (Step 5)

## Tabs

1. **Recognition** — Upload unknown sensor CSV; run active model; chat-style message history
2. **Live Input** — CSV playback with pause/resume/finalize; hardware stub for future gloves
3. **Dictionary** — Model vocabulary and sentence-pattern explorer (not proof of reliable recognition)

## Rules

- No LLM chatbot; no fabricated answers from filenames or reference sentences
- Inference uses sensor features only; no ground-truth labels in recognition path
- Decoder scores labelled as uncalibrated
- Uncertain recognition triggers repeat-request feedback (simulated vibration event)
- BiLSTM provisional predictions note bidirectional lookahead limitation

## Sentence generation

Configurable gloss-pattern mappings in `app/ml/sentence_generator.py`. Unsupported patterns fall back to literal gloss concatenation.

## Hardware

See `docs/HARDWARE_CONTRACT.md`. `HardwareSensorSource.is_available()` returns `False` until a real adapter is configured.
