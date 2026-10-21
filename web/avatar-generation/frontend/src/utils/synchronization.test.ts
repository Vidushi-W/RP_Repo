import { describe, it, expect } from 'vitest';
import { synchronize, validateCues } from './synchronization';
const cues = validateCues([{id:'a',wordId:'word-a',label:'Test A',start:1,end:3},{id:'b',wordId:'word-b',label:'Test B',start:3,end:5}]);
describe('video-driven timestamp synchronization', () => {
  it('uses inclusive starts and exclusive ends', () => {
    expect(synchronize(cues, 0, true).cue).toBeNull();
    expect(synchronize(cues, 1, true).cue?.id).toBe('a');
    expect(synchronize(cues, 3, true).cue?.id).toBe('b');
    expect(synchronize(cues, 5, true).cue).toBeNull();
  });
  it('freezes animation playback during pause while retaining its position', () => {
    expect(synchronize(cues, 2.5, false)).toMatchObject({animationTime:1.5,playing:false});
  });
  it('recomputes on forward and backwards seeks and replay without stale state', () => {
    expect(synchronize(cues, 4, true).cue?.id).toBe('b');
    expect(synchronize(cues, 1.25, false)).toMatchObject({animationTime:0.25,playing:false,cue:{id:'a'}});
    expect(synchronize(cues, 0, true)).toMatchObject({cue:null,animationTime:0,playing:false});
  });
  it('scales cue-local time without shifting video boundaries', () => {
    expect(synchronize(cues, 2, true, 0.5).animationTime).toBe(0.5);
    expect(synchronize(cues, 3, true, 1.5).cue?.id).toBe('b');
  });
  it('rejects ambiguous or invalid manifests', () => {
    expect(() => validateCues([...cues, {...cues[0],id:'c',start:2,end:4}])).toThrow();
    expect(() => validateCues([{...cues[0],end:NaN}])).toThrow();
    expect(() => validateCues([cues[0],{...cues[1],id:'a'}])).toThrow();
    expect(() => synchronize(cues, 1, true, 0)).toThrow();
  });
  it('treats invalid or out-of-range times as inactive', () => {
    expect(synchronize(cues, NaN, true).cue).toBeNull();
    expect(synchronize(cues, -1, true).cue).toBeNull();
  });
});
