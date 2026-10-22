"""Print actual public structured proposals when selection validation fails."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.ollama_provider import OllamaProvider
from app.services.semantic_agent import SemanticAgent
from app.services.sign_registry import Registry


class DiagnosticProvider(OllamaProvider):
    def select(self, *args, **kwargs):
        decision = super().select(*args, **kwargs)
        print(json.dumps({'actualModelProposal': decision.model_dump(), 'inference': self.last_inference}, indent=2), flush=True)
        return decision


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('text')
    parser.add_argument('--research-preview', action='store_true')
    args = parser.parse_args()
    try:
        result = SemanticAgent(Registry(preview=args.research_preview), DiagnosticProvider()).process(args.text, force_inference=True)
        print(json.dumps({'validatedSigns': result['signs']}, indent=2))
    except Exception as error:
        print(json.dumps({'validationError': str(error)}, indent=2))
        raise SystemExit(1)
