import type { AnimationManifest, HandAnimation, SignEntry } from '../types/hands';
import { parseAnimation, record, validSignId } from './animationSchema';

export function assetUrl(path: string): string {
  if (!/^[\p{L}\p{M}\p{N}_./ -]+\.json$/u.test(path) || path.startsWith('/') || path.split('/').some(part=>part==='..'||part==='.')) throw new Error('Animation paths must be relative local JSON assets.');
  return import.meta.env.BASE_URL + path.split('/').map(encodeURIComponent).join('/');
}
export function parseManifest(value: unknown, allowUnreviewed = false): AnimationManifest {
  if (!record(value) || value.schemaVersion !== 1 || typeof value.fixture !== 'boolean' || !Array.isArray(value.signs)) throw new Error('Invalid animation manifest.');
  const ids = new Set<string>(), aliases = new Set<string>();
  const signs: SignEntry[] = value.signs.map(entry => {
    if (!record(entry) || !validSignId(entry.signId) || ids.has(entry.signId) || typeof entry.label !== 'string' || !entry.label.trim() || typeof entry.animationUrl !== 'string' || !Array.isArray(entry.aliases) || typeof entry.datasetReference !== 'string' || !entry.datasetReference.trim() || typeof entry.reviewed !== 'boolean') throw new Error('Invalid or duplicate sign entry.');
    assetUrl(entry.animationUrl);
    if (!value.fixture && !entry.reviewed && !allowUnreviewed) throw new Error('Only reviewed dataset signs belong in the real playback manifest.');
    const normalized = entry.aliases.map(alias => {
      if (typeof alias !== 'string' || !alias.trim()) throw new Error('Empty sign alias.');
      const word = alias.normalize('NFKC').toLowerCase().trim();
      if (aliases.has(word)) throw new Error('Ambiguous vocabulary alias.');
      aliases.add(word); return word;
    });
    ids.add(entry.signId);
    if(entry.sha256!==undefined && (typeof entry.sha256!=='string'||!/^[a-f0-9]{64}$/.test(entry.sha256)))throw new Error('Invalid animation checksum.');
    return { signId: entry.signId, label: entry.label, aliases: normalized, animationUrl: entry.animationUrl, datasetReference: entry.datasetReference, reviewed: entry.reviewed, sha256:entry.sha256 as string|undefined };
  });
  return { schemaVersion: 1, fixture: value.fixture, signs };
}
export async function loadManifest(fixture = false, signal?: AbortSignal): Promise<AnimationManifest> {
  const response = await fetch(assetUrl(fixture ? 'hand-animations/fixtures/manifest.json' : 'hand-animations/manifest.json'), { signal });
  if (!response.ok) throw new Error('The animation manifest could not be loaded.');
  const manifest = parseManifest(await response.json());
  if (manifest.fixture !== fixture) throw new Error('Fixture and real SLSL libraries must remain separate.');
  return manifest;
}
export async function loadAnimation(signId: string, manifest: AnimationManifest, signal?: AbortSignal): Promise<HandAnimation> {
  const entry = manifest.signs.find(item => item.signId === signId);
  if (!entry) throw new Error(`No saved animation for ${signId}. No substitute was selected.`);
  const response = await fetch(assetUrl(entry.animationUrl), { signal });
  if (!response.ok) throw new Error(`Saved animation for ${signId} could not be loaded (${response.status}).`);
  let data:unknown;
  if(entry.sha256){
    const bytes=await response.arrayBuffer();
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
    if(digest!==entry.sha256)throw new Error('Animation checksum changed. Playback stopped.');
    data=JSON.parse(new TextDecoder().decode(bytes));
  }else data=await response.json();
  const animation = parseAnimation(data, signId);
  if (!!animation.metadata.fixture !== manifest.fixture) throw new Error('Fixture data cannot be played as real SLSL.');
  return animation;
}
