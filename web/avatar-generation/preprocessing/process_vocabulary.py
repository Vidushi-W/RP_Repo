"""Recursively discover original MP4s, extract once, and register audited assets."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from types import SimpleNamespace
from time import perf_counter
from extract_hand_landmarks import COMPONENT_ROOT, extract, within_component
from motion_validation import validate_motion


def discover(raw):
    return sorted((p for p in raw.rglob('*') if p.is_file() and p.suffix.lower() == '.mp4' and p.resolve().is_relative_to(raw.resolve())), key=lambda p: p.relative_to(raw).as_posix().casefold())


def source_id(path, raw):
    relative = path.relative_to(raw).as_posix()
    stem = re.sub(r'[^A-Z0-9]+', '_', path.stem.upper()).strip('_')[:42] or 'VIDEO'
    return 'RAW_' + stem + '_' + hashlib.sha256(relative.encode()).hexdigest()[:6].upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, default=COMPONENT_ROOT / 'datasets/raw')
    parser.add_argument('--sample-fps', type=float, default=15)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--report', type=Path, default=COMPONENT_ROOT / 'research/evaluation/dataset-processing-results.json')
    args = parser.parse_args()
    report_path = within_component(args.report)
    raw = within_component(args.raw)
    if not raw.is_dir():
        parser.error('The raw dataset directory does not exist')
    reviews_path = COMPONENT_ROOT / 'datasets/metadata/vocabulary-reviews.json'
    reviews = json.loads(reviews_path.read_text(encoding='utf-8')) if reviews_path.exists() else {}
    registry_path = COMPONENT_ROOT / 'datasets/metadata/sign-registry.json'
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    previous_entries = {entry.get('sourceFile'): entry for entry in registry['signs'] if entry.get('processor') == 'vocabulary-batch-v1'}
    previous_sources = {source: entry.get('sourceSha256') for source, entry in previous_entries.items()}
    # Only replace this batch's entries, retaining the existing NURSE evidence.
    registry['signs'] = [e for e in registry['signs'] if e.get('processor') != 'vocabulary-batch-v1']
    records = []
    files = discover(raw)
    for source in files[:args.limit] if args.limit else files:
        started = perf_counter()
        relative = source.relative_to(raw).as_posix()
        review = reviews.get(relative, {})
        sid = review.get('conceptId') or source_id(source, raw)
        # Do not re-register the legacy pending NURSE under another ID.
        if source.stem.casefold() == 'nurse':
            sid = source_id(source, raw)
            review = {}
        output = COMPONENT_ROOT / 'frontend/public/hand-animations/recorded/batch' / (sid.lower() + '.json')
        record = {'signId': sid, 'conceptId': review.get('conceptId'), 'sourceFile': relative,
                  'originalFilename': source.name, 'romanizedLabel': source.stem,
                  'sinhalaLabel': review.get('sinhalaLabel'), 'englishMeaning': review.get('englishMeaning'),
                  'synonyms': review.get('synonyms', []), 'sourceSha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                  'reviewStatus': review.get('status', 'pending'), 'provenance': 'Owner-supplied local MP4; original file preserved',
                  'animationAvailable': False, 'processingStatus': 'pending'}
        try:
            if previous_sources.get(relative) not in (None, record['sourceSha256']):
                raise ValueError('Source video changed since extraction. Use a separately reviewed, versioned output.')
            if not output.exists():
                previous = previous_entries.get(relative)
                if previous and previous.get('animationFile') and previous_sources.get(relative) == record['sourceSha256']:
                    # A reviewed concept can reuse the immutable extracted motion.
                    # Change only its registered identity, never its samples.
                    original = within_component(COMPONENT_ROOT / 'frontend/public' / previous['animationFile'])
                    raw_motion = original.read_bytes()
                    if hashlib.sha256(raw_motion).hexdigest() != previous['sha256']:
                        raise ValueError('Existing extracted motion checksum changed')
                    animation = json.loads(raw_motion)
                    validate_motion(animation, previous['signId'])
                    if animation['metadata']['sourceFile'] != source.name:
                        raise ValueError('Existing extraction belongs to another video')
                    animation['signId'] = sid
                    output.write_text(json.dumps(animation, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')
                else:
                    extract(SimpleNamespace(input=source, model=COMPONENT_ROOT / 'preprocessing/models/hand_landmarker.task',
                    pose_model=COMPONENT_ROOT / 'preprocessing/models/pose_landmarker_lite.task',
                    face_model=COMPONENT_ROOT / 'preprocessing/models/face_landmarker.task',
                    output=output, sign_id=sid, sample_fps=args.sample_fps, handedness_threshold=0.65,
                    swap_handedness=False, dataset_reference=record['provenance']))
            animation = json.loads(output.read_text(encoding='utf-8'))
            if animation['metadata']['sourceFile'] != source.name:
                raise ValueError('Existing output belongs to another video')
            stats = validate_motion(animation, sid)
            record.update(animationAvailable=True, processingStatus='processed', animationFile=output.relative_to(COMPONENT_ROOT / 'frontend/public').as_posix(),
                          sha256=hashlib.sha256(output.read_bytes()).hexdigest(), validation=stats)
            entry = {'signId': sid, 'canonicalLabel': review.get('englishMeaning') or source.stem, 'sinhalaLabel': record['sinhalaLabel'],
                     'romanizedLabel': source.stem, 'verifiedSynonyms': review.get('synonyms', []),
                     'description': review.get('description', 'Unreviewed source label; English meaning not established.'),
                     'senseId': review.get('senseId', 'unreviewed-source-label'), 'examples': [],
                     'animationFile': record['animationFile'], 'sha256': record['sha256'], 'sourceFile': relative,
                     'sourceSha256': record['sourceSha256'], 'processingStatus': 'processed', 'animationAvailable': True,
                     'reviewStatus': review.get('status', 'pending'), 'reviewedBy': review.get('reviewedBy'),
                     'mappingReviewed': review.get('status') == 'approved', 'reviewScope': review.get('reviewScope'),
                     'reviewSources': review.get('sources', []), 'linguisticallyCertified': False,
                     'excludedPhrases': review.get('excludedPhrases', []),
                     'processor': 'vocabulary-batch-v1', 'provenance': record['provenance']}
            registry['signs'].append(entry)
        except Exception as error:
            record.update(processingStatus='failed', error=str(error))
        record['processingSeconds'] = round(perf_counter() - started, 3)
        records.append(record)
        print(relative, record['processingStatus'], flush=True)
        # Checkpoint after each original video, retaining failures for diagnosis.
        (COMPONENT_ROOT / 'datasets/metadata/dataset-vocabulary.json').write_text(json.dumps({'discovered': len(files), 'records': records}, indent=2, ensure_ascii=False), encoding='utf-8')
        registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding='utf-8')
    summary = {'discovered': len(files), 'processed': sum(r['animationAvailable'] for r in records),
               'failed': sum(r['processingStatus'] == 'failed' for r in records), 'records': records}
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in summary.items() if k != 'records'}))


if __name__ == '__main__':
    main()
