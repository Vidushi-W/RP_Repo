import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadAnimation, parseManifest, loadManifest, assetUrl } from './animationLoader';
import calibration from '../../public/hand-animations/fixtures/calibration-a.json';
const manifest = {schemaVersion:1 as const,fixture:true,signs:[{signId:'TEST_CALIBRATION_A',label:'Coordinate fixture A',aliases:['test-a'],animationUrl:'hand-animations/fixtures/calibration-a.json',datasetReference:'Synthetic coordinate diagnostic, not SLSL',reviewed:false}]};
afterEach(() => vi.unstubAllGlobals());
describe('phase 2: animation library and extraction contract', () => {
  it('loads a saved JSON file with the requested sign identifier', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async () => calibration}));
    const animation=await loadAnimation('TEST_CALIBRATION_A',manifest);
    expect(animation.frames[0].leftHand).toHaveLength(21);
    expect(animation.frames[0].rightHand).toHaveLength(21);
    expect(animation.metadata.fixture).toBe(true);
  });
  it('reports missing assets, malformed responses and unavailable signs', async () => {
    await expect(loadAnimation('UNKNOWN',manifest)).rejects.toThrow('No saved animation');
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:404}));
    await expect(loadAnimation('TEST_CALIBRATION_A',manifest)).rejects.toThrow('404');
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async () => ({})}));
    await expect(loadAnimation('TEST_CALIBRATION_A',manifest)).rejects.toThrow();
  });
  it('keeps fixture libraries out of real SLSL playback', async () => {
    expect(() => parseManifest({...manifest,fixture:false})).toThrow('reviewed');
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async () => calibration}));
    await expect(loadAnimation('TEST_CALIBRATION_A',{...manifest,fixture:false})).rejects.toThrow('Fixture');
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async () => manifest}));
    await expect(loadManifest(false)).rejects.toThrow('separate');
  });
  it('rejects duplicate IDs and remote/traversal URLs', () => {
    expect(() => parseManifest({...manifest,signs:[manifest.signs[0],manifest.signs[0]]})).toThrow();
    expect(() => assetUrl('../secret.json')).toThrow();
    expect(() => assetUrl('https://example.com/animation.json')).toThrow();
    expect(() => assetUrl('/outside.json')).toThrow();
    expect(parseManifest(manifest).signs[0].aliases).toEqual(['test-a']);
  });
});