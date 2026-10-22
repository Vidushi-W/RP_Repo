"""Real audio -> local Whisper -> Qwen -> approved assets over the live socket.

This bypasses only the browser capture picker, not ASR, semantic reasoning or
animation eligibility. It does not claim visible playback or microphone testing.
"""
import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path
from time import perf_counter
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.sign_registry import ROOT


def pcm_windows(path):
    import av
    import numpy as np
    parts = []
    with av.open(str(path)) as source:
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        for frame in source.decode(audio=0):
            for out in resampler.resample(frame):
                parts.append(out.to_ndarray().reshape(-1))
        for out in resampler.resample(None):
            parts.append(out.to_ndarray().reshape(-1))
    data = np.concatenate(parts).astype('<i2').tobytes() if parts else b''
    return [data[offset:offset+192000] for offset in range(0, len(data), 192000) if len(data[offset:offset+192000]) >= 12800]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audio', type=Path, required=True)
    parser.add_argument('--reference', default='')
    parser.add_argument('--expected', nargs='*', default=None)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    audio = args.audio.resolve()
    if not audio.is_relative_to(ROOT):
        parser.error('Use an audio file inside this component')
    from websockets.sync.client import connect
    report = {'atUtc': datetime.now(timezone.utc).isoformat(), 'source': str(audio.relative_to(ROOT)),
              'referenceTranscript': args.reference, 'expectedConceptIds': args.expected,
              'realAudio': True, 'browserCaptureVerified': False, 'visiblePlaybackVerified': False,
              'audioSha256': hashlib.sha256(audio.read_bytes()).hexdigest(), 'windows': []}
    signs = []
    with connect('ws://127.0.0.1:8000/api/audio/live', origin='http://127.0.0.1:5173', open_timeout=10) as socket:
        ready = json.loads(socket.recv(timeout=10))
        assert ready['type'] == 'ready'
        start_ms = 0
        for seq, pcm in enumerate(pcm_windows(audio)):
            started = perf_counter()
            socket.send(json.dumps({'type': 'audio', 'seq': seq, 'startMs': start_ms, 'pcm16': base64.b64encode(pcm).decode()}))
            response = json.loads(socket.recv(timeout=180))
            response['requestWallMs'] = round((perf_counter() - started) * 1000, 2)
            response['captureWindowMs'] = len(pcm) / 32
            report['windows'].append(response)
            signs.extend(response.get('signs', []))
            start_ms += round(len(pcm) / 32)
    sessions = {w.get('session') for w in report['windows']}
    log = ROOT / 'research/evaluation/live-sessions/events.jsonl'
    events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
    report['speechAndSelection'] = [event for event in events if event.get('session') in sessions and event.get('type') == 'speech-selection']
    report['playbackOrder'] = signs
    successful = all(w.get('type') == 'selection' for w in report['windows'])
    report['status'] = ('observed' if args.expected is None else 'passed' if signs == args.expected else 'failed') if successful else 'failed'
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    args.output.write_text(rendered, encoding='utf-8')
    print(rendered)
    return 0 if report['status'] in ('passed', 'observed') else 1


if __name__ == '__main__':
    raise SystemExit(main())
