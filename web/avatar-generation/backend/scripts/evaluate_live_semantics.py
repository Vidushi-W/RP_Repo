"""Small real-Qwen development check; Sinhala TEXT is not Sinhala audio testing."""
import json
import sys
from pathlib import Path
from time import perf_counter
from datetime import datetime, timezone
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.live_pipeline import LivePipeline
from app.services.sign_registry import ROOT

CASES = [
    ('She started weeping.', ['CRY'], 'en'),
    ('The woman is shedding tears.', ['CRY'], 'en'),
    ('The nurse is crying and smiling.', ['CRY'], 'en'),
    ('She is crying, then crying again.', ['CRY', 'CRY'], 'en'),
    ('මම අඬනවා.', ['CRY'], 'si'),
]

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    pipeline = LivePipeline()
    rows = []
    for text, expected, language in CASES:
        started = perf_counter()
        try:
            result = pipeline.semantic(text)
            rows.append({'input': text, 'inputLanguage': language, 'expected': expected,
                'predicted': result['signs'], 'inference': result['inference'], 'cacheHit': result['cacheHit'],
                'missingOrRejected': result['missingVocabulary'], 'passed': expected == result['signs'],
                'latencyMs': round((perf_counter() - started) * 1000, 2)})
        except Exception as error:
            rows.append({'input': text, 'inputLanguage': language, 'expected': expected, 'passed': False, 'error': str(error)})
    report = {'atUtc': datetime.now(timezone.utc).isoformat(), 'sourceType': 'text, not speech',
              'labels': 'Owner-authorized assistant lexical review; development cases, not held-out accuracy',
              'passed': sum(row['passed'] for row in rows), 'total': len(rows), 'results': rows}
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    (ROOT / 'research/evaluation/live-semantic-results.json').write_text(rendered, encoding='utf-8')
    print(rendered)
    raise SystemExit(0 if report['passed'] == len(rows) else 1)
