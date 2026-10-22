"""Live HTTP preview/availability checks through the running frontend proxy."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.sign_registry import ROOT

BASE = 'http://127.0.0.1:5173'


def request(url, body=None):
    data = None if body is None else json.dumps(body).encode()
    try:
        with urlopen(Request(url, data=data, headers={'Content-Type': 'application/json'}), timeout=150) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def main():
    report = {'testedAtUtc': datetime.now(timezone.utc).isoformat(), 'baseUrl': BASE,
              'verificationType': 'real HTTP API and asset checks; visible browser playback not verified', 'results': []}
    for text, preview, expected in [('nurse', False, []), ('cellphone', True, []), ('nurse', True, ['NURSE'])]:
        started = perf_counter()
        status, raw = request(BASE + '/api/agent/process', {'text': text, 'researchPreview': preview})
        body = json.loads(raw)
        row = {'input': text, 'researchPreview': preview, 'httpStatus': status,
               'wallLatencySeconds': round(perf_counter() - started, 3), 'response': body}
        # A rejected unreviewed request is safely blocked, but retain its error.
        row['passed'] = (status == 200 and body['signs'] == expected) or (not preview and status == 422)
        if status == 200 and text == 'cellphone':
            row['passed'] &= any(c['concept'] == 'PHONE' and not c['animationAvailable'] for c in body['concepts'])
        if status == 200 and expected:
            entry = body['manifest']['signs'][0]
            asset_status, asset = request(BASE + '/' + entry['animationUrl'])
            animation = json.loads(asset)
            row['asset'] = {'httpStatus': asset_status, 'sha256': hashlib.sha256(asset).hexdigest(),
                            'frameCount': len(animation['frames']), 'signId': animation['signId']}
            row['passed'] &= asset_status == 200 and row['asset']['sha256'] == entry['sha256'] and animation['signId'] == 'NURSE'
        report['results'].append(row)
    for path in ['version', 'ps']:
        status, raw = request('http://localhost:11434/api/' + path)
        report['ollama' + path.title()] = {'httpStatus': status, 'response': json.loads(raw)}
    report['status'] = 'passed' if all(row['passed'] for row in report['results']) else 'failed'
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    (ROOT / 'research/evaluation/live-api-results.json').write_text(rendered, encoding='utf-8')
    print(rendered)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
