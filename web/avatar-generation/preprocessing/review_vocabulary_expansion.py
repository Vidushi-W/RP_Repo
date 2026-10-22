"""Audit existing recordings/motion without extracting or approving anything."""
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
import cv2
from motion_validation import validate_motion

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = {
    'DRINK': 'bonawa.mp4', 'RUN': 'duwanawa.mp4', 'GIVE': 'denawa.mp4',
    'TAKE': 'gannawa.mp4', 'ASK': 'ahanawa.mp4', 'SEE': 'dakinawa.mp4',
    'DRAW': 'andinawa(draw).mp4', 'EAT': 'kanawa.mp4',
}


def audit(entry):
    source = ROOT / 'datasets/raw' / entry['sourceFile']
    asset = ROOT / 'frontend/public' / entry['animationFile']
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    raw = asset.read_bytes()
    data = json.loads(raw)
    stats = validate_motion(data, entry['signId'])
    capture = cv2.VideoCapture(str(source))
    declared = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = capture.get(cv2.CAP_PROP_FPS)
    decoded = 0
    while True:
        ok, image = capture.read()
        if not ok:
            break
        if image is None or image.size == 0:
            raise ValueError('Empty decoded source frame')
        decoded += 1
    capture.release()
    frames = data['frames']
    times = [f['timestampMs'] for f in frames]
    detected = [bool(f['leftHand'] or f['rightHand']) for f in frames]
    runs = []
    start = None
    for i, present in enumerate(detected + [False]):
        if present and start is None:
            start = i
        if not present and start is not None:
            runs.append([times[start], times[i-1]])
            start = None
    jumps = []
    for a, b in zip(frames, frames[1:]):
        for side in ('leftHand', 'rightHand'):
            if a[side] and b[side]:
                jumps.extend(math.hypot(p['x']-q['x'], p['y']-q['y']) for p, q in zip(a[side], b[side]))
    hand_points = [p for f in frames for side in ('leftHand', 'rightHand') for p in (f[side] or [])]
    ranges = {axis: round(max(p[axis] for p in hand_points)-min(p[axis] for p in hand_points), 5) for axis in ('x', 'y')}
    if decoded != declared or source_hash != entry['sourceSha256'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError('Source decode/count or source/asset integrity mismatch')
    return {
        'sourceFile': entry['sourceFile'], 'sourceSha256': source_hash,
        'originalMotionFile': entry['animationFile'], 'originalMotionSha256': entry['sha256'],
        'originalSignId': entry['signId'], 'structuralValidation': stats,
        'sourceFps': fps, 'declaredSourceFrames': declared, 'decodedSourceFrames': decoded,
        'corruptOrMissingSourceFrames': declared-decoded,
        'handVisibleFrames': sum(detected), 'handMissingFrames': len(frames)-sum(detected),
        'handDetectionIntervalsMs': runs, 'maxTimestampGapMs': max(b-a for a,b in zip(times,times[1:])),
        'lastTimestampMs': times[-1], 'tailToDurationMs': data['durationMs']-times[-1],
        'maxAdjacentSameSideLandmarkDisplacement': round(max(jumps, default=0),5),
        'handCoordinateRanges': ranges,
        'distinctHandSamples': len({json.dumps([f['leftHand'],f['rightHand']],sort_keys=True) for f in frames if f['leftHand'] or f['rightHand']}),
        'note': 'Missing hand samples are retained as null; no interpolation, relabeling of handedness, or fabricated motion. Structural checks do not certify meaning.',
    }


if __name__ == '__main__':
    inventory = json.loads((ROOT/'datasets/metadata/dataset-vocabulary.json').read_text(encoding='utf-8'))['records']
    entries = {e['sourceFile']:e for e in inventory}
    destination = ROOT/'research/evaluation/vocabulary-expansion'
    destination.mkdir(parents=True, exist_ok=True)
    report = {'atUtc':datetime.now(timezone.utc).isoformat(), 'candidates':{sid:audit(entries[name]) for sid,name in CANDIDATES.items()},
        'baselineApprovedAssets':{e['conceptId']:e['sha256'] for e in inventory if e['reviewStatus']=='approved'},
        'allSourceHashes':{e['sourceFile']:hashlib.sha256((ROOT/'datasets/raw'/e['sourceFile']).read_bytes()).hexdigest() for e in inventory}}
    output = destination/'motion-audit.json'
    if output.exists():
        raise SystemExit('Refusing to overwrite the baseline review evidence')
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    for sid, row in report['candidates'].items():
        print(sid, row['structuralValidation']['frames'], row['handVisibleFrames'], row['handDetectionIntervalsMs'], row['maxAdjacentSameSideLandmarkDisplacement'])
