import raw from '../data/vocabulary.json';
import type { VocabularyEntry } from '../types';
// Only reviewed dataset entries belong here. Timing markers are never vocabulary.
export const vocabulary: VocabularyEntry[] = raw;
export function findVocabulary(id: string, entries = vocabulary) { return entries.find(entry => entry.id === id); }
export function isPlayable(entry?: VocabularyEntry) { return !!entry && entry.validated && entry.animationStatus === 'available' && !!entry.animationUrl && !!entry.clipName; }
