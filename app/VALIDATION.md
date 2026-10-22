# Validation — 22 October 2026

## Checks completed

- Android debug APK built successfully with Flutter 3.38.9 / Java 21 / compile SDK 36.
  The installed preview APK targets the Pixel 9 x86_64 emulator. Phone/release builds
  need their appropriate ABI and signing configuration; no release is published.
- `flutter analyze`: no issues after the final retry implementation.
- Client API tests: **12 passed**. Password rules, case-normalized email login,
  logout revocation, per-account job/audio isolation, CSV schema/time/finiteness,
  deletion, Sinhala correction and resuming a failed translation without CSV replay.
- Dependency check: no broken Python requirements.
- Real emulator UI: landing, sign-up, redirected dashboard, logout, login, session
  restoration after an APK update, four dashboard cards, native CSV picker, progress
  animation, recognized words, generated sentence, Sinhala output, voice player,
  history, correction dialog and translation retry.
- The emulator selected the supplied motion-only sample CSVs. No answer keys were
  uploaded. Existing CNN model ID 9 / version 7 was consumed read-only.
- Normal sample predicted I | CAN | USE | LAPTOP. Qwen generated “I can use a laptop.”
  Sinhala output was “මට Laptop එකක් භාවිතා කරන්න පුළුවන්.” and a WAV was produced.
- Angry sample predicted I | HATE | BAT. HATE used the existing keyword rule.
  Both normal and simulated angry-style audio reached the Android audio system.
  Audio-focus start/end events confirmed real playback. A failed Sinhala stage was
  resumed through the Android Try again button, completed and automatically played.
- MongoDB credentials, runtime account/results storage, generated audio, APKs,
  Android reports and compiler files are ignored. Standard Gradle wrapper files are
  included for reproducible team builds. No GitHub operation or commit was made.

## Observed limitations

The first emulator run timed out while local AI competed with build tools for memory.
The final client uses a 240-second per-stage CPU timeout, a serial queue and resumable
translation/voice retries. Completed build workers were released. Inference still
requires the PC/service and can take minutes; it is not on-device Android inference.

M2M100 can mistranslate meaning. An observed “I hate bats.” became a Sinhala sentence
about hating lies; the retry of the conservative fallback “I hate bat.” transliterated
the noun instead. The app labels automatic output and allows Sinhala corrections.
Pipeline completion and voice playback do not establish translation correctness,
authentic SLSL accuracy or measured signer emotion.

MongoDB has not been connection-tested because no credentials have been provided.
Current accounts use the explicitly labelled SQLite development store. Physical BLE
glove scan/connect and live sensor decoding have not been hardware-tested; the team
has not selected a transport or packet format. Live decoding remains an extension
point, while CSV input is functional. Listen, Learn and Emergency remain placeholders.

The Windows native Flutter widget runner was blocked by Application Control. A browser
test attempt did not complete and was stopped. No automated widget-test pass is claimed;
Android flows were checked manually, and the widget test source remains for a supported
test environment. Security settings were not changed.
