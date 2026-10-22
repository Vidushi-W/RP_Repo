"""Opt-in REAL inference check. Never replaces an unavailable model with a fake."""
import argparse
import json
import sys
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ollama_provider import AgentUnavailable, OllamaProvider
from app.services.semantic_agent import SemanticAgent
from app.services.sign_registry import Registry

CASES = [
    ('nurse', ['NURSE'], ['NURSE']),
    ('nursing professional', ['NURSE'], ['NURSE']),
    ('hospital nurse', ['NURSE'], ['NURSE']),
    ('cellphone', ['PHONE'], []),
    ('smartphone', ['PHONE'], []),
    ('The nurse has a smartphone', ['NURSE', 'PHONE'], ['NURSE']),
    ('A nurse greeted another nurse', ['NURSE', 'NURSE'], ['NURSE', 'NURSE']),
    ('Jupiter', ['JUPITER'], []),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    tested_at = datetime.now(timezone.utc).isoformat()
    provider = OllamaProvider()
    try:
        status = provider.status()
        if not status['modelAvailable']:
            raise AgentUnavailable(status['error'])
    except AgentUnavailable as error:
        report = {'testedAtUtc': tested_at, 'status': 'unavailable', 'realInferencePerformed': False, 'error': str(error)}
        print(json.dumps(report, indent=2))
        if args.output:
            args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
        return 2
    registry = Registry(preview=True)
    rows = []
    for text, expected_concepts, expected_signs in CASES:
        print(f'Running real inference: {text}', file=sys.stderr, flush=True)
        started = perf_counter()
        try:
            result = SemanticAgent(registry, provider).process(text, force_inference=True)
            concepts = [c['concept'] for c in result['concepts']]
            metadata = result['inference']
            real = metadata.get('performed') is True and metadata.get('evalCount', 0) > 0
            rows.append({'input': text, 'concepts': concepts, 'signs': result['signs'], 'inference': metadata,
                         'modelConcepts': [c.get('modelConcept', c['concept']) for c in result['concepts']],
                         'wallLatencySeconds': round(perf_counter() - started, 3),
                         'passed': real and concepts == expected_concepts and result['signs'] == expected_signs})
        except Exception as error:
            rows.append({'input': text, 'passed': False, 'error': str(error), 'inference': provider.last_inference or {},
                         'wallLatencySeconds': round(perf_counter() - started, 3)})
    report = {'testedAtUtc': tested_at, 'status': 'passed' if all(r['passed'] for r in rows) else 'failed',
              'realInferencePerformed': any(r.get('inference', {}).get('performed') for r in rows),
              'provider': 'ollama', 'model': provider.model, 'researchPreview': True,
              'labelStatus': 'development expectations, not human-reviewed study labels', 'results': rows}
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
