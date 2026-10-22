# Local Qwen3 semantic sign selection

The existing agent now uses **Ollama and `qwen3:1.7b`**. No paid API, API key,
cloud embedding call or cloud fallback remains. Changes stay inside this
component. Existing JSON recordings, manual preview, checksum validation,
skeleton renderer and sequential player are preserved.

## What changed

The former Responses client was not an Ollama-compatible transport. Its
replacement calls local `/api/chat`, with a JSON schema in `format`,
`stream: false`, and `think: false`. It uses the Python standard library and
existing Pydantic; no new SDK/framework is required.

This is **structured-output orchestration controlled by the backend, not native
model-driven function calling**. Native tool-call reliability for this small
model has not been measured here. The backend executes existing
`listAvailableSigns`, `findMatchingSign` and `getSignDetails` before inference.
Qwen interprets concepts against those retrieved meanings. After validating
clear registered meanings, the backend executes `resolveAnimation` and
`queueAnimation`. These are actual application tools; no native model tool calls
are fabricated. The existing injected native-tool adapter remains for contract
compatibility; production constructs only the Ollama provider.

The model returns concept labels, exact source evidence, optional registered
IDs/senses, qualitative support, and short explanations. Application validation
rejects unknown IDs, inconsistent concepts, wrong senses, missing/reordered
evidence, missing or modified files and pending signs outside preview. The
browser verifies SHA-256 bytes and renders stored keyframes with the existing
player. These checks do not prove semantic correctness; evaluate that separately.

`findMatchingSign` retrieves verified phrase hits and registered descriptions.
Qwen performs semantic comparison over those meanings; a second embedding model
is unnecessary. Standalone registered labels/synonyms retain the deterministic
shortcut. Sentences/paraphrases invoke real inference, with no keyword fallback
on model failure. UI and response metadata disclose whether inference happened.

## Available concepts versus playable recordings

NURSE is the only extracted real recording in this checkout and remains pending
linguistic/handedness review. Enable **Research preview: include pending
recordings** to test it. PHONE has no existing animation. Proposed English
synonyms are not promoted to verified SLSL mappings.

| Input | Intended concepts | Current research-preview playback |
| --- | --- | --- |
| nurse | NURSE | NURSE via standalone registry shortcut |
| nursing professional / hospital nurse | NURSE | NURSE if Qwen selects a validated equivalent |
| cellphone / smartphone / mobile phone | PHONE | None; no eligible PHONE recording |
| The nurse has a smartphone | NURSE, PHONE | NURSE only |
| He will phone his mother | CALL, MOTHER | None; do not substitute the PHONE object |

These are development expectations, not measured model accuracy. The UI
separates recognized concepts from the actual playback queue. English mention
order is not claimed to be SLSL grammar. Face/body/nonmanual features are absent.

For unavailable device concepts only, equivalent model labels such as CELLPHONE
are normalized to PHONE after actual inference. The original `modelConcept` is
retained in results. This does not grant a sign ID or animation eligibility,
change registry synonyms, or replace inference with input keyword matching.

## Install Ollama on Windows 11

Download the official Windows installer and complete its interactive setup:

```powershell
Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile "$env:TEMP\OllamaSetup.exe"
& "$env:TEMP\OllamaSetup.exe"
```

Open a new PowerShell after installation so `ollama` is on PATH. The tray app
may already serve port 11434. For the explicit configuration below, **quit the
Ollama tray app first**, then start one server:

```powershell
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_QUEUE = '1'
$env:OLLAMA_CONTEXT_LENGTH = '4096'
ollama serve
```

These session settings belong to the Ollama server. Setting them only in
backend `.env` does not reconfigure an existing Ollama process. Keep this
terminal running. In another PowerShell:

```powershell
ollama --version
ollama pull qwen3:1.7b
ollama show qwen3:1.7b
Invoke-RestMethod -Uri 'http://localhost:11434/api/tags'
```

The download needs internet once; inference uses local weights. The official
tag currently lists Q4_K_M quantization and a download around 1.4 GB. Verify
your revision using `ollama show`; download size is not a RAM usage guarantee.

The backend loads the model when needed; no separate interactive model process
is required. An optional direct check is `ollama run qwen3:1.7b` followed by a
short message and `/bye`. Run `ollama ps` after an application request to check
the processor column. Run `ollama stop qwen3:1.7b` to unload it explicitly.

## Configure and start the Python backend

From the repository root:

```powershell
Set-Location web/avatar-generation/backend
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --env-file .env
```

For a fresh clone, create `.venv` first using `py -3.11 -m venv .venv` from the
component directory. Edit rather than overwrite an existing backend `.env`:

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:1.7b
OLLAMA_NUM_CTX=4096
OLLAMA_NUM_PREDICT=1024
OLLAMA_NUM_THREAD=4
OLLAMA_TIMEOUT_SECONDS=120
```

Old `OPENAI_*` variables are ignored. The provider accepts only an HTTP loopback
URL without credentials/path/query. System proxies and HTTP redirects are
disabled. Non-Ollama providers and recognized cloud tags fail closed. Use
`OLLAMA_NO_CLOUD=1` on the server as shown above.

CPU settings request `num_gpu: 0`, four threads, 4096 context tokens, 1024 output
tokens, thinking disabled and a two-minute idle keep-alive. No GPU is assumed.
A nonblocking semaphore limits inference to one request per backend process;
use one worker. Ollama server limits also prevent parallel model loading across
clients. A busy model returns a retryable error instead of spawning another
inference. No new background service is started by the application.

Keep transcripts to 1000 characters. Oversized vocabulary/input is rejected
rather than silently dropping meaning descriptions. Truncated/malformed model
output stops playback. Increase timeout up to 300 seconds if cold CPU loading
needs it. Latency and RAM usage have not been benchmarked on this laptop.

## Start the frontend and test matching

In another terminal from the repository root:

```powershell
Set-Location web/avatar-generation/frontend
npm.cmd ci
npm.cmd run dev
```

Open http://127.0.0.1:5173/research and use **Select signs with the AI agent**.
Enable Research preview for the current NURSE file, then try the table above.
The panel displays transcript, concepts, availability, explanations, selected
filenames, inference provenance and automatic playback. Manual JSON preview
remains available. Vite proxies `/api` to localhost:8000.

With the backend running:

```powershell
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/agent/status'
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/agent/process' -ContentType 'application/json' -Body '{"text":"The nursing professional is here.","researchPreview":true}'
```

`/agent/status` distinguishes unreachable Ollama from an absent installed model.
`/agent/vocabulary` reports configuration and approved intact vocabulary;
configured does not imply server reachability. Connection/model failures tell
you to start Ollama/pull the model. Public hosting would require authentication
and request limits; these endpoints are for local development.

The existing `processTranscript(text, preview, signal)` frontend function is
still the speech-to-text interface. Feed its validated signs and manifest to
the player with `autoPlay`. Actual audio/video transcription remains external.

## Automated tests and actual inference verification

From `backend`:

```powershell
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\.venv\Scripts\python.exe scripts/test_ollama_integration.py --output ../research/evaluation/ollama-integration-results.json
```

The automated suite mocks transport or injects providers. It tests application
contracts, not real model accuracy. The integration script is different: it
uses the actual HTTP API, requires the selected installed model and positive
generated-token counts, and **forces inference even for nurse**, bypassing the
deterministic shortcut. It records per-case model, token and timing metadata,
checks concepts separately from animation IDs, and exercises repeated signs.
Exit 0 means all development expectations passed; 1 means inference/selection
checks failed; 2 means Ollama/model is unavailable. No fake replaces an
unavailable model. Update its eight expectations when the current NURSE-only
registry changes. A reachable server alone does not prove model inference.

From `frontend`:

```powershell
npm.cmd test
npm.cmd run build
```

Tests cover malformed output, unsupported concepts, missing/tampered animations,
preview restrictions, unsafe URLs, busy/unavailable inference, concept/playback
separation and existing automatic sequential playback. Semantic errors can
still occur with a 1.7B model; no numeric confidence is treated as calibrated.

## Expand vocabulary and evaluate semantic accuracy

Extend `datasets/metadata/sign-registry.json` using only actual existing JSON
files. Include unique ID, canonical English/Sinhala labels (null when unknown),
verified synonyms, precise description/exclusions, `senseId`, examples,
unchanged relative filename, SHA-256, reviewer and provenance. Preserve Sinhala
filenames: the loader URL-encodes Unicode segments. Approved entries require
named `reviewedBy`; pending ones remain preview-only. Never manufacture PHONE
by renaming another recording. From `backend`, compute file hashes with:

```powershell
Get-FileHash ../frontend/public/hand-animations/recorded/nurse.json -Algorithm SHA256
```

Store lowercase hex; changed recordings require review before updating hashes.
Extracted assets are ignored by existing Git rules. A fresh clone must supply
the same existing recording; see `nurse-preview.md` for provenance.

The evaluation dataset includes exact vocabulary, paraphrases, ambiguity,
negation, unsupported concepts, multiple mentions and prompt injection. Labels
are draft; have a named human reviewer verify them and set `reviewedBy` before
reporting study accuracy. With Ollama running, from `backend`:

```powershell
..\.venv\Scripts\python.exe -m dotenv -f .env run -- ..\.venv\Scripts\python.exe scripts/evaluate_semantic_agent.py --research-preview --allow-draft-labels --force-inference --output ../research/evaluation/latest-semantic-results.json
```

The report separates ordered playback-sequence accuracy from concept accuracy
on concept-labeled cases, includes inference counts, and counts API errors as
failures. Positive expectations must have available files in the chosen mode.
Remove preview/draft flags once assets and labels are reviewed. Record model
digest (`ollama show`), settings, prompt and registry revisions and repeated
runs. Improving instructions/examples does not alter pretrained model weights.

Official sources: [Windows](https://docs.ollama.com/windows),
[Qwen3 1.7B](https://ollama.com/library/qwen3:1.7b),
[chat API](https://docs.ollama.com/api/chat),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs),
[local-only mode and server limits](https://docs.ollama.com/faq).

## Files changed for this local migration

- `backend/app/services/ollama_provider.py`: local transport, JSON schema, CPU limits and errors.
- `backend/app/services/local_semantic_instructions.txt`: local concept-selection instructions.
- `backend/app/services/semantic_agent.py`: existing tools plus structured orchestration.
- `backend/app/api/semantic_routes.py`: local configuration and model-status endpoint.
- `backend/.env.example`: local-only model configuration.
- `backend/scripts/test_ollama_integration.py`: opt-in real inference verification.
- `backend/scripts/evaluate_semantic_agent.py`: local model/concept evaluation metadata.
- `backend/tests/test_ollama_provider.py`: local transport/orchestration contract tests.
- `backend/tests/test_semantic_agent.py`: existing regression tests adapted to local failures.
- `backend/tests/test_semantic_routes.py`: local API configuration/status tests.
- `frontend/src/services/semanticAgent.ts`: validated concepts and inference metadata.
- `frontend/src/services/semanticAgent.test.ts`: concept versus animation response checks.
- `frontend/src/components/avatar/SemanticAgentPanel.tsx`: local inference and concept display.
- `research/evaluation/semantic-cases.json`: concept expectations alongside animation labels.
- `research/evaluation/ollama-integration-results.json`: actual environment-check result.
- `README.md` and `docs/semantic-agent.md`: local setup and research limitations.

The registry, animation files, renderer, player and manual preview were not
modified during this local-provider migration.

## Real local verification

The real Qwen run and automated playback were subsequently exercised on Ollama
0.40.8. See the recorded reports in `research/evaluation/`:

- `ollama-integration-initial-results.json`: initial real-model failures, retained.
- `ollama-integration-results.json`: revised prompt; eight development cases passed
  with real generated-token counts and per-request wall latency. Raw model
  concept labels are recorded alongside normalized application concepts.
- `live-api-results.json`: actual HTTP checks through Vite, pending NURSE blocked
  with HTTP 422 outside preview, unavailable PHONE with an empty queue, and a
  valid NURSE asset/hash in preview. The 422 is a validation rejection, not a
  normal successful unsupported response; that usability limitation remains.
- `live-playback-results.json`: real Qwen -> frontend API proxy -> validated
  NURSE JSON -> React/SVG player with real timers in jsdom. Stored frames 15
  and 18 were observed, 42 landmarks were drawn, and 3360 ms playback completed.
  This is automated DOM verification, not visible Windows-browser confirmation.

The initial failures included omitted mixed/repeated concepts and fabricated
evidence. Prompt examples improved those development cases; strict application
validation remains intact. Eight prompt-development examples do not establish
held-out semantic accuracy. Broader errors remain possible with this small model.

To reproduce (backend and frontend must already be running), from `backend`:

```powershell
..\.venv\Scripts\python.exe scripts/test_ollama_integration.py --output ../research/evaluation/ollama-integration-results.json
..\.venv\Scripts\python.exe scripts/verify_local_workflow.py
# Optional: inspect actual public proposals when a sentence fails validation.
..\.venv\Scripts\python.exe scripts/diagnose_local_selection.py 'nursing professional' --research-preview
```

From `frontend`, opt into the test that makes real local inference requests and
uses actual HTTP responses, actual SHA-256 and real playback timers:

```powershell
$env:LANKASIGNS_LIVE_TEST = '1'
npm.cmd test -- src/components/avatar/LiveSemanticWorkflow.test.tsx
Remove-Item Env:LANKASIGNS_LIVE_TEST
```

Ordinary `npm.cmd test` skips that live test. The live test bridges relative
development URLs and jsdom/Node buffer realms; it does not mock inference,
animation responses, hashes or the animation clock. A visible browser was not
connected to the verification session, so visual demonstration still requires
opening `/research`, enabling Research preview, and processing a paraphrase.
