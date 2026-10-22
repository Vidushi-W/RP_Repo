"""Live evaluation; failed API requests count as errors, never as correct abstentions."""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.semantic_agent import SemanticAgent
from app.services.sign_registry import ROOT, Registry


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path, default=ROOT / 'research/evaluation/semantic-cases.json')
    parser.add_argument('--research-preview', action='store_true')
    parser.add_argument('--allow-draft-labels', action='store_true')
    parser.add_argument('--force-inference', action='store_true', help='Use Qwen even for standalone canonical labels')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    dataset = json.loads(args.dataset.read_text(encoding='utf-8'))
    if not dataset.get('reviewedBy') and not args.allow_draft_labels:
        parser.error('Labels need human review. For development only, use --allow-draft-labels.')
    registry = Registry(preview=args.research_preview)
    available = {e['signId'] for e in registry.available()}
    required = {sid for case in dataset['cases'] for sid in case['expectedSigns']}
    if not required <= available:
        parser.error(f'Dataset expects unavailable signs: {sorted(required - available)}. Register reviewed files or explicitly enable research preview.')
    results = []
    for case in dataset['cases']:
        try:
            result = SemanticAgent(registry).process(case['input'], force_inference=args.force_inference)
            predicted = result['signs']
            recognized = [c['concept'] for c in result['concepts']]
            row = {**case, 'predictedSigns': predicted, 'recognizedConcepts': recognized,
                   'correct': predicted == case['expectedSigns'], 'inference': result['inference']}
            if 'expectedConcepts' in case:
                row['conceptsCorrect'] = case['expectedConcepts'] == recognized
        except Exception as error:
            row = {**case, 'predictedSigns': None, 'correct': False, 'error': str(error)}
        results.append(row)
    count = len(results)
    correct = sum(r['correct'] for r in results)
    concept_rows = [r for r in results if 'expectedConcepts' in r]
    report = {'provider': 'ollama', 'model': os.getenv('OLLAMA_MODEL', 'qwen3:1.7b'), 'researchPreview': args.research_preview,
              'labelsReviewedBy': dataset.get('reviewedBy'), 'cases': count, 'correct': correct,
              'orderedSequenceAccuracy': correct / count if count else None,
              'conceptAccuracy': sum(r.get('conceptsCorrect', False) for r in concept_rows) / len(concept_rows) if concept_rows else None,
              'inferenceCases': sum(r.get('inference', {}).get('performed', False) for r in results),
              'errors': sum('error' in r for r in results), 'incorrectPredictions': [r for r in results if not r['correct']],
              'categories': {category: {'total': sum(r['category'] == category for r in results), 'correct': sum(r['category'] == category and r['correct'] for r in results)} for category in sorted({r['category'] for r in results})}}
    rendered = json.dumps(report, indent=2, ensure_ascii=False)
    print(rendered)
    if args.output:
        args.output.write_text(rendered, encoding='utf-8')
    return 0 if correct == count else 1


if __name__ == '__main__':
    raise SystemExit(main())
