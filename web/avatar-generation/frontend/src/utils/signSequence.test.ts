import { afterEach, describe, it, expect, vi } from 'vitest';
import { matchWords } from '../services/signMatcher';
import { parseManifest } from '../services/animationLoader';
import { loadSequence, sequenceAt, sequenceDuration } from './signSequence';
import fixture from '../../public/hand-animations/fixtures/calibration-a.json';
import rawManifest from '../../public/hand-animations/fixtures/manifest.json';
const manifest=parseManifest(rawManifest);
afterEach(()=>vi.unstubAllGlobals());
describe('phase 3: exact matching and sequential playback', () => {
  it('matches exact case-insensitive aliases in input order and reports all unsupported tokens', () => {
    const result=matchWords('TEST-B, test-a test-a laptop table.',manifest);
    expect(result.signs).toEqual(['TEST_CALIBRATION_B','TEST_CALIBRATION_A','TEST_CALIBRATION_A']);
    expect(result.missing).toEqual(['laptop','table']);
    expect(matchWords('contest-a',manifest).signs).toEqual([]);
    expect(matchWords('',manifest).signs).toEqual([]);
  });
  it('loads repeated signs once, retains their order and waits for durations', async () => {
    const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>fixture});
    vi.stubGlobal('fetch',fetcher);
    const items=await loadSequence(['TEST_CALIBRATION_A','TEST_CALIBRATION_A'],manifest);
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(sequenceDuration(items)).toBe(2400);
    expect(sequenceAt(items,1199)?.index).toBe(0);
    expect(sequenceAt(items,1200)).toMatchObject({index:1,localTimeMs:0});
    expect(sequenceAt(items,2400)).toMatchObject({index:1,localTimeMs:1200});
  });
  it('keeps a visible blank error slot for unavailable signs and handles an empty queue', async () => {
    const items=await loadSequence(['UNAVAILABLE'],manifest);
    expect(items[0]).toMatchObject({signId:'UNAVAILABLE',animation:null,durationMs:800});
    expect(items[0].error).toContain('No saved animation');
    expect(sequenceAt([],0)).toBeNull();
    expect(sequenceDuration([])).toBe(0);
    expect(await loadSequence([],manifest)).toEqual([]);
  });
  it('does not relabel a mismatched loaded asset', async () => {
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>fixture}));
    const items=await loadSequence(['TEST_CALIBRATION_B'],manifest);
    expect(items[0].animation).toBeNull();
    expect(items[0].error).toContain('identifier');
  });
});
