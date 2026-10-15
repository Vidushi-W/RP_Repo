# Haptic language

The pattern composer is independent from React Native and hardware. It combines three channels:

- **Category → rhythm:** each recognized sound category has a distinct pulse sequence.
- **Urgency → intensity:** urgency selects a configurable intensity level and normalized amplitude.
- **Direction → position:** explicit direction evidence selects front, back, left, or right. Missing/uncertain direction uses an undirected four-position pattern.

The sequences and thresholds are provisional cues for evaluation with Deaf and hard-of-hearing users. Fire alarm patterns are marked critical and use the strongest intensity. The UI may animate a simulation and optionally request a phone vibration, but phone vibration is only a rough preview: it cannot reproduce glove position, amplitude, or tested motor timings.

`bleActuatorAdapter.mjs` describes a protocol-neutral command boundary for a future BLE transport. It reports writes as unverified; no glove transport is currently connected and motor actuation has not been tested.
