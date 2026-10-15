# Sound analysis boundary

The repository currently contains no sound model, model weights, notebook, Python inference code, or inference API. The UI project therefore uses `unavailableInferenceAdapter` by default. It does not claim to classify audio, train a model, or monitor the microphone continuously.

## Result contract

`createSoundAnalyzer({ adapter, threshold, now }).analyzeAudioFile({ uri, mimeType })` returns:

```js
{
  label: 'fire_alarm' | 'siren_emergency_vehicle' | 'vehicle_horn' |
         'doorbell' | 'human_calling_shouting' | 'unknown_sound',
  score: 0..1 | null,
  timestamp: 'ISO-8601',
  modelStatus: { status: 'ready' | 'unavailable' | 'error', modelName: string | null },
  reason: 'classified' | 'low_confidence' | 'unsupported_sound' |
          'unknown_sound' | 'invalid_score' | 'inference_unavailable' |
          'inference_error' | 'invalid_audio_file',
  candidateLabel: string | null
}
```

Predictions below the configured threshold become `unknown_sound` with the original candidate and score preserved. Unsupported labels remain unknown. In particular, generic `vehicle` is never promoted to an emergency siren. Direction is intentionally absent: a single microphone cannot establish it reliably.

## Adapter contract and privacy

An inference adapter implements `analyzeAudioFile({ uri, mimeType })` and returns `{ label, score, modelStatus: { status, modelName } }`. This keeps the app independent of a future on-device model or a deliberately configured API. A Python/Colab notebook can be wrapped behind an explicit file-inference bridge, but Colab is not a continuous phone service. No remote upload is implemented. The default adapter does no I/O, and neither the analyzer nor the UI stores the selected URI or raw audio after the one-off file check.

To attach a real model, implement and inject an adapter, then evaluate it against representative recordings. Keep the training/evaluation provenance with the model; inference code alone is not evidence of training.

## Deterministic alert reasoning

`reasoning.mjs` is a separate policy layer: it consumes the classifier's sound category and confidence plus an urgency estimate, attention state, and optional direction evidence. It returns an event state (`confirmed`, `uncertain`, or `unknown`), priority, `interrupt`/`queue`/`record` decision, explanation, haptic recommendation, and a `decisionLog` explaining the inputs and policy steps. It does not classify audio.

Defaults for minimum decision confidence (`0.65`) and direction-evidence confidence (`0.70`) are provisional and configurable. Evaluate them against representative data before operational use. A sufficiently confident fire-alarm candidate is always critical and interrupts even while attention is busy. Siren labels alone do not imply danger; sirens use the supplied urgency estimate. Non-fire critical urgency is capped at high. Horn urgency is never derived from direction evidence. Direction cues require explicit sourced evidence above the provisional threshold, and single/mono microphone evidence is rejected.

The engine does not send a vibration or persist events. Its structured `decisionLog` is the audit record for each call; an app/service may store that metadata separately if desired. The haptic message is only a recommendation until a glove adapter is implemented.
