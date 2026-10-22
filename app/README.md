# SLSL Connect — Android client

This app is separate from `../slsl-research` (the admin training dashboard).
It never trains, resets, or writes to that dashboard. MongoDB credentials belong
only in `server/.env`, which is ignored by Git. The APK contains no database secrets.

## Current features

- Green landing page, username/email/password sign-up, email/password login.
- Argon2 password hashing; 12–128 characters, upper/lowercase, number, symbol;
  name/email excluded. Random opaque seven-day sessions stored hashed on server,
  token in Android secure storage. Login/signup attempt limits; revocable logout.
- Personalized dashboard with Talk, Listen, Learn and Emergency entry points.
  Only Talk is implemented. The other routes are explicit teammate placeholders.
- Motion-only CSV → existing CNN–BiLSTM–CTC → Qwen sentence → M2M100 Sinhala →
  Piper Sinhala audio, automatically played on completion. Text, pause/replay,
  Sinhala correction/regeneration, resumable translation/voice retries, private history and deletion are available.
- SQLite caches conversation text on the phone. Recognition/audio require a
  connection to this PC's service; the models do not execute on the handset.
- BLE device scan/connect/disconnect on physical Android, with runtime permissions.
  The glove protocol is undecided: live sensor capture is **not implemented**.
  A connected BLE device is not proof that it is a compatible glove.

## Run on this PC

1. Install `server/requirements.txt` into the existing admin backend venv (same ML runtime).
2. Run `./scripts/run-server.ps1` in one PowerShell window.
3. Start the existing Pixel_9 emulator in Android Studio Device Manager.
4. Run `./scripts/run-mobile.ps1 -JavaHome <Java-21-folder>` in another window.

On this development machine the portable JDK is `C:\CHATGPT\slsl-java\jdk-21.0.12.1+1`.
The helper avoids the broken installed `flutter.bat` launcher without modifying the SDK.
On a normal setup, use `flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8010`
from `mobile/`. Use Java 17/21. Android compile SDK 36 and build tools are required;
Flutter dependencies may require a newer compile SDK as listed by Gradle.
The build helper uses ADB reverse and loopback for either an emulator or a USB phone.
The build helper installs a debug APK. Release signing/publishing is not configured.

## MongoDB

`server/.env` has empty `MONGODB_URI` and `MONGODB_DATABASE=slsl_connect`.
Until credentials are supplied, accounts and results use
`server/runtime/client-development.sqlite3`. This is a development fallback,
**not MongoDB**. Configured MongoDB failures fail startup instead of silently
falling back. Switching stores does not migrate existing accounts; export/import
must be planned when moving from development to MongoDB.
Set `APP_ENV=production` to require MongoDB. Mobile access is only through the API.
Opaque-session expiry is checked on every authenticated request.

## CSV / hardware contract

Use motion-only CSVs with these 23 headers; no labels or answer key:

```
timestamp_ms,left_flex_1,left_flex_2,left_flex_3,left_flex_4,left_flex_5,left_acc_x_g,left_acc_y_g,left_acc_z_g,left_gyro_x_dps,left_gyro_y_dps,left_gyro_z_dps,right_flex_1,right_flex_2,right_flex_3,right_flex_4,right_flex_5,right_acc_x_g,right_acc_y_g,right_acc_z_g,right_gyro_x_dps,right_gyro_y_dps,right_gyro_z_dps
```

Both hands synchronized, flex 0–1, acceleration g, gyro degrees/second;
strictly increasing nonnegative milliseconds, >=4 frames, <=5 minutes / 15,000 frames,
60 ms minimum duration, finite numeric values, <=8 MB. Server validates before enqueueing. CSVs are temporary
and deleted after processing. Outputs remain until their owner deletes them.
Use `mobile/lib/features/talk/motion_source.dart` to implement the future hardware
adapter; it must produce the same canonical recording. Do not invent BLE UUIDs,
finger mapping, calibration or packet decoding. Finalize these with the hardware team.

## Team boundaries

```
mobile/lib/core/               shared theme, API, session, local history
mobile/lib/features/auth/     account screens
mobile/lib/features/home/     dashboard and feature entry points
mobile/lib/features/talk/     motion input, recognition state and voice UI
mobile/lib/features/gloves/   isolated transport + device screen
mobile/lib/features/shared/   placeholder routes for three future modules
server/client_api/            auth, storage repository, inference-only API
```

Teammates replace placeholder routes from `home_screen.dart` with their own feature
folders. Reuse `Session.api` for authenticated calls. Server route contracts are at
`http://127.0.0.1:8010/docs`. Status polling exposes raw words before sentence,
then Sinhala before audio. Jobs and audio are scoped to the authenticated owner.
CPU generation can take several minutes, particularly with an emulator and other apps
open. Close completed build tools to release memory. The client-only AI timeout defaults
to 240 seconds per stage (`LOCAL_AI_TIMEOUT_SECONDS`, 30�600). Failed translation/voice
can be resumed with Try again without rerunning the CNN.
One worker serializes model work to limit memory use; at most four queued/active
recordings and one active recording per account. Current model is pinned per job.
By default the service reads the admin's active bundle from its SQLite database in
read-only mode. An exported bundle can be selected with `MODEL_BUNDLE_DIR`.

## Accuracy, voice and deployment limits

This is the same research model, not a newly trained mobile model. Synthetic training
does not establish accuracy on real SLSL or physical gloves. Qwen uses conservative
fallbacks when generation fails; unknown labels are not guessed. Automatic Sinhala
translation can change meaning: review the displayed text and use Edit Sinhala.
Angry is the existing configured keyword annotation, with simulated voice prosody;
normal speech has no emotion effect. None of these are measured signer emotion.
The audio starts automatically as requested, so model mistakes can also be spoken.
Windows desktop widget testing may be blocked by local Application Control; do not
disable security to run tests. API tests are in `server/tests`, Flutter tests in
`mobile/test`. Physical glove decoding and hardware audio are not emulator-testable.

Before public deployment: use HTTPS, a real signing key, production MongoDB, shared
durable rate limiting/session cleanup, account recovery/privacy and retention choices,
device protocol validation, real-sign testing and review model/data/runtime licenses.
Piper's runtime has GPL obligations. No deployment, GitHub action or commit is made.

## Design / architecture references

- Flutter architecture: https://docs.flutter.dev/app-architecture/guide
- Android Bluetooth permissions: https://developer.android.com/develop/connectivity/bluetooth/bt-permissions
- FastAPI authentication: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- SQLite package: https://pub.dev/packages/sqflite
- Audio: https://pub.dev/packages/audioplayers
- Secure token storage: https://pub.dev/packages/flutter_secure_storage

For checked behavior and remaining limits, see [VALIDATION.md](VALIDATION.md).
