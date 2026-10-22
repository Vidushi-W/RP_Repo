param([string]$ReportPrefix = 'audio')
$ErrorActionPreference = 'Stop'
$expansionRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
if ($ReportPrefix -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Use a simple new report prefix.' }
$expansionCases = @(
    @('drink-run', 'She is drinking water. The boy is running.', 'DRINK,RUN'),
    @('give-take', 'Give me the book. Take the bag.', 'GIVE,TAKE'),
    @('draw-see-eat', 'Draw a picture. I can see the house. She is eating rice.', 'DRAW,SEE,EAT')
)
foreach ($expansionCase in $expansionCases) {
    $report = Join-Path $expansionRoot ('research/evaluation/vocabulary-expansion/' + $ReportPrefix + '-' + $expansionCase[0] + '.json')
    if (Test-Path -LiteralPath $report) { throw "Preserve existing evidence; choose a new ReportPrefix: $report" }
}
# Offline installed Windows voice; these are generated speech fixtures, not tab
# recordings or a substitute for eventual visible browser-capture verification.
Add-Type -AssemblyName System.Speech
$expansionSynth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    foreach ($expansionCase in $expansionCases) {
        $expansionSynth.SetOutputToWaveFile((Join-Path $expansionRoot ('.cache/expansion-' + $expansionCase[0] + '.wav')))
        $expansionSynth.Speak($expansionCase[1])
        $expansionSynth.SetOutputToNull()
    }
} finally { $expansionSynth.Dispose() }
Push-Location $expansionRoot
try {
    @'
from pathlib import Path
import av, numpy as np
for name in ['drink-run','give-take','draw-see-eat']:
    parts=[]
    with av.open('.cache/expansion-'+name+'.wav') as source:
        resampler=av.AudioResampler(format='s16',layout='mono',rate=16000)
        for frame in source.decode(audio=0):
            parts.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(frame))
        parts.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(None))
    Path('.cache/expansion-'+name+'.pcm').write_bytes(np.concatenate(parts).astype('<i2').tobytes())
'@ | & .\.venv\Scripts\python.exe -
    if ($LASTEXITCODE -ne 0) { throw 'Speech-fixture conversion failed.' }
    Set-Location frontend
    $expansionNames = @('LANKASIGNS_LIVE_AUDIO_TEST','LANKASIGNS_AUDIO_PCM','LANKASIGNS_AUDIO_EXPECTED','LANKASIGNS_AUDIO_REFERENCE','LANKASIGNS_AUDIO_REPORT')
    $expansionPrevious = @{}
    foreach ($name in $expansionNames) { $expansionPrevious[$name] = [Environment]::GetEnvironmentVariable($name,'Process') }
    $expansionFailures = 0
    try {
        $env:LANKASIGNS_LIVE_AUDIO_TEST = '1'
        foreach ($expansionCase in $expansionCases) {
            $env:LANKASIGNS_AUDIO_PCM = '../.cache/expansion-' + $expansionCase[0] + '.pcm'
            $env:LANKASIGNS_AUDIO_EXPECTED = $expansionCase[2]
            $env:LANKASIGNS_AUDIO_REFERENCE = $expansionCase[1]
            $env:LANKASIGNS_AUDIO_REPORT = '../research/evaluation/vocabulary-expansion/' + $ReportPrefix + '-' + $expansionCase[0] + '.json'
            & npm.cmd test -- src/components/avatar/LiveAudioAvatar.test.tsx
            if ($LASTEXITCODE -ne 0) { $expansionFailures++ }
        }
    } finally {
        foreach ($name in $expansionNames) { [Environment]::SetEnvironmentVariable($name,$expansionPrevious[$name],'Process') }
    }
    if ($expansionFailures) { throw "$expansionFailures real audio integration tests failed; see preserved reports." }
} finally { Pop-Location }
