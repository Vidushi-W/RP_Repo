"""Real local Qwen checks for the reviewed expansion; no mocked responses."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.live_pipeline import LivePipeline
from app.services.sign_registry import ROOT

CASES = [
    ('She is drinking water.', ['DRINK']),
    ('The boy is running.', ['RUN']),
    ('Give me the book.', ['GIVE']),
    ('Take the bag.', ['TAKE']),
    ('Ask a question.', []),
    ('I can see the house.', ['SEE']),
    ('Draw a picture.', ['DRAW']),
    ('She is eating rice.', ['EAT']),
    ('She is crying, walking and looking.', ['CRY', 'WALK', 'LOOK']),
    ('Drink water, then run.', ['DRINK', 'RUN']),
    ('Give the book, then take the bag.', ['GIVE', 'TAKE']),
    ('Ask a question, then look at the house.', ['LOOK']),
    ('Draw a picture, then see the house.', ['DRAW', 'SEE']),
    ('Eat rice, then drink water.', ['EAT', 'DRINK']),
    ('Take the book, then take the bag.', ['TAKE', 'TAKE']),
    ('I see a bird, then look at the tree.', ['SEE', 'LOOK']),
    ('She sips water, sprints, hands over the book, and sketches a picture.', ['DRINK', 'RUN', 'GIVE', 'DRAW']),
    ('Run a program. Give up. Take care. I see what you mean. Draw the curtains.', []),
    ('Do not drink water or run.', []),
]


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='research/evaluation/vocabulary-expansion/qwen-results.json')
    args = parser.parse_args()
    output = (ROOT/args.output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        parser.error('Use a new report path inside this component; evidence is not overwritten')
    pipeline = LivePipeline()
    report = {'atUtc':datetime.now(timezone.utc).isoformat(),
        'sourceType':'English text; separate audio results are required for speech claims',
        'evaluationScope':'Prompt-development checks, not held-out linguistic accuracy',
        'results':[]}
    for text, expected in CASES:
        started = perf_counter()
        row = {'input':text, 'expected':expected}
        try:
            result = pipeline.semantic(text)
            row.update(predicted=result['signs'], passed=result['signs']==expected,
                inference=result['inference'], cacheHit=result['cacheHit'],
                rawModelMatches=result['rawModelMatches'], missingOrRejected=result['missingVocabulary'],
                manifest=result['manifest'], qwenMs=result['qwenMs'], lookupMs=result['lookupMs'])
        except Exception as error:
            row.update(passed=False, error=str(error))
        row['wallMs'] = round((perf_counter()-started)*1000,2)
        report['results'].append(row)
        report.update(passed=sum(r['passed'] for r in report['results']), total=len(CASES), completed=len(report['results']))
        output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(json.dumps({k:row.get(k) for k in ('input','expected','predicted','passed','error','wallMs')}),flush=True)
    raise SystemExit(0 if report['passed']==report['total'] else 1)
