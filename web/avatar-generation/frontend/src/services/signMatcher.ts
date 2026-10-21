import type { AnimationManifest } from '../types/hands';
export interface WordMatch { text: string; signId: string | null }
export function matchWords(text: string, manifest: AnimationManifest): { signs: string[]; words: WordMatch[]; missing: string[] } {
  // Development resolver only: exact aliases, in English token order, no grammar decisions.
  const aliases = new Map(manifest.signs.flatMap(entry => entry.aliases.map(alias => [alias,entry.signId] as const)));
  const tokens = text.normalize('NFKC').toLowerCase().match(/[a-z0-9]+(?:-[a-z0-9]+)*/g) || [];
  const words = tokens.map(token => ({text:token,signId:aliases.get(token) || null}));
  return { signs: words.flatMap(word => word.signId ? [word.signId] : []), words, missing: [...new Set(words.filter(word => !word.signId).map(word => word.text))] };
}
