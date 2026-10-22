"""Closed vocabulary: paths, hashes and review provenance are application data."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PUBLIC = ROOT / 'frontend/public'
REGISTRY = ROOT / 'datasets/metadata/sign-registry.json'


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


class Registry:
    def __init__(self, path=REGISTRY, public=PUBLIC, preview=False):
        self.public = public.resolve()
        self.preview = preview
        self.entries = {}
        for entry in json.loads(path.read_text(encoding='utf-8'))['signs']:
            sid = entry['signId']
            if not re.fullmatch(r'[A-Z0-9_]{1,64}', sid) or sid in self.entries:
                raise ValueError('Invalid or duplicate registry sign ID')
            if entry['reviewStatus'] not in ('approved', 'pending'):
                raise ValueError('Invalid review status')
            if entry['reviewStatus'] == 'approved' and not entry.get('reviewedBy'):
                raise ValueError('Approved mappings require named reviewer provenance')
            self.entries[sid] = entry

    def details(self, sign_id):
        entry = self.entries.get(sign_id)
        if not entry or (entry['reviewStatus'] != 'approved' and not self.preview):
            raise ValueError('Sign is not approved or available in this mode')
        if entry.get('processor') == 'vocabulary-batch-v1' and not entry.get('mappingReviewed'):
            raise ValueError('The source vocabulary meaning has not been reviewed')
        return entry

    def resolve(self, sign_id):
        entry = self.details(sign_id)
        relative = Path(entry['animationFile'])
        asset = (self.public / relative).resolve()
        if relative.is_absolute() or '..' in relative.parts or not asset.is_relative_to(self.public / 'hand-animations') or asset.suffix != '.json':
            raise ValueError('Animation path is outside the approved library')
        raw = asset.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Animation checksum changed; review the registry')
        animation = json.loads(raw)
        if animation.get('signId') != sign_id or animation.get('schemaVersion') != 1 or animation.get('metadata', {}).get('fixture') or not animation.get('frames'):
            raise ValueError('Animation metadata does not match the registry')
        if entry.get('processor') == 'vocabulary-batch-v1':
            # Offline batch validation is repeated when serving a registered asset.
            import sys
            sys.path.insert(0, str(ROOT / 'preprocessing')) if str(ROOT / 'preprocessing') not in sys.path else None
            from motion_validation import validate_motion
            validate_motion(animation, sign_id)
        return {'animationId': sign_id, 'animationFile': entry['animationFile'], 'sha256': entry['sha256']}

    def available(self):
        result = []
        for sid in self.entries:
            try:
                self.resolve(sid)
                result.append(self.details(sid))
            except (ValueError, OSError):
                continue
        return result

    def candidates(self, text):
        text = normalize(text)
        result = []
        for entry in self.available():
            # Whole phrases prevent matching nurse in nursery or nursing a grievance.
            aliases = [entry['canonicalLabel'], *entry['verifiedSynonyms']]
            hits = [a for a in aliases if re.search(r'(?<!\w)' + re.escape(normalize(a)) + r'(?!\w)', text)]
            result.append({'signId': entry['signId'], 'description': entry['description'], 'verifiedPhraseHits': hits})
        return sorted(result, key=lambda item: bool(item['verifiedPhraseHits']), reverse=True)

    def manifest(self, signs):
        entries = []
        for sid in dict.fromkeys(signs):
            self.resolve(sid)
            entry = self.details(sid)
            entries.append({'signId': sid, 'label': entry['canonicalLabel'], 'aliases': [entry['canonicalLabel'], *entry['verifiedSynonyms']], 'animationUrl': entry['animationFile'], 'sha256': entry['sha256'], 'datasetReference': entry['provenance'], 'reviewed': entry['reviewStatus'] == 'approved'})
        return {'schemaVersion': 1, 'fixture': False, 'signs': entries}
