import { describe, expect, it } from 'vitest';
import { parseAgentResult, parseSegments, requestAgent } from './agentAdapter';
import { videoSignPosition } from '../utils/videoSignSync';
import type { SequenceItem } from '../utils/signSequence';
const segments=[{startMs:1000,endMs:4000,signs:['TEST_A','TEST_B']},{startMs:5000,endMs:5500,signs:['TEST_A']}];
const items:SequenceItem[]=[{signId:'TEST_A',animation:null,durationMs:1000},{signId:'TEST_B',animation:null,durationMs:1000}];
describe('phase 4: explicit agent IDs and video-driven synchronization', () => {
  it('accepts supplied translation without generating grammar or replacing IDs', () => {
    const data={englishText:'Example',sinhalaText:'පරීක්ෂණය',signs:['UNKNOWN']};
    expect(parseAgentResult(data)).toEqual(data);
  });
  it('requires a real injected agent and rejects malformed or inconsistent payloads', async () => {
    await expect(requestAgent(null,'hello')).rejects.toThrow('pending');
    expect(()=>parseAgentResult({englishText:'x',signs:['../bad']})).toThrow();
    expect(()=>parseSegments([{startMs:2,endMs:1,signs:[]}])).toThrow();
    expect(()=>parseSegments([{startMs:0,endMs:3,signs:[]},{startMs:2,endMs:4,signs:[]}])).toThrow();
    expect(()=>parseAgentResult({englishText:'x',signs:['A'],segments:[{startMs:0,endMs:2,signs:['B']}]})).toThrow();
  });
  it('derives current sign from video time, including boundary, pause, resume and backwards seek', () => {
    expect(videoSignPosition(segments,items,999,true)).toBeNull();
    expect(videoSignPosition(segments,items,1000,true)?.current?.item.signId).toBe('TEST_A');
    expect(videoSignPosition(segments,items,2000,true)?.current?.item.signId).toBe('TEST_B');
    expect(videoSignPosition(segments,items,2500,false)).toMatchObject({playing:false,current:{localTimeMs:500}});
    expect(videoSignPosition(segments,items,2500,true)?.playing).toBe(true);
    expect(videoSignPosition(segments,items,1100,false)?.current?.localTimeMs).toBe(100);
    expect(videoSignPosition(segments,items,4000,true)).toBeNull();
  });
  it('does not retrigger finished sequences and explicitly flags short-segment clipping', () => {
    expect(videoSignPosition(segments,items,3500,true)?.current).toBeNull();
    expect(videoSignPosition(segments,items,5200,true)?.clipped).toBe(true);
    expect(videoSignPosition(segments,items,5500,true)).toBeNull();
    expect(videoSignPosition(segments,items,1500,true,2)?.current?.item.signId).toBe('TEST_B');
    expect(videoSignPosition([],[],1000,true)).toBeNull();
  });
});