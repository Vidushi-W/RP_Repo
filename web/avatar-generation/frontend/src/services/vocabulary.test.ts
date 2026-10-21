import { describe, it, expect } from 'vitest';
import { findVocabulary, isPlayable, vocabulary } from './vocabulary';
import type { VocabularyEntry } from '../types';
const entry: VocabularyEntry = { id:'reviewed-fixture',word:'Test fixture only',datasetReference:'test-only',sourceVideo:'fixture.mp4',animationStatus:'available',animationUrl:'/animations/fixture.glb',clipName:'fixture',validated:true };
describe('reviewed vocabulary mapping', () => {
  it('maps by stable vocabulary ID rather than display text', () => {
    expect(findVocabulary(entry.id,[entry])).toEqual(entry);
    expect(findVocabulary('missing',[entry])).toBeUndefined();
  });
  it('requires a reviewed asset and named animation clip', () => {
    expect(isPlayable(entry)).toBe(true);
    expect(isPlayable({...entry,validated:false})).toBe(false);
    expect(isPlayable({...entry,animationStatus:'processing'})).toBe(false);
    expect(isPlayable({...entry,animationUrl:undefined})).toBe(false);
    expect(isPlayable({...entry,clipName:undefined})).toBe(false);
    expect(isPlayable()).toBe(false);
  });
  it('does not count demonstration timing markers as real SLSL vocabulary', () => {
    expect(new Set(vocabulary.map(item => item.id)).size).toBe(vocabulary.length);
    expect(vocabulary.some(item => item.id.startsWith('timing-marker-'))).toBe(false);
    expect(vocabulary.every(item => !!item.datasetReference && !!item.sourceVideo)).toBe(true);
  });
});
