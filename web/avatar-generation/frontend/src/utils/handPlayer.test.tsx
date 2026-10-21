// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { renderToStaticMarkup } from 'react-dom/server';
import { HandSkeletonCanvas } from '../components/avatar/HandSkeletonCanvas';
import { parseAnimation, frameAt } from '../services/animationSchema';
import { AnimationScheduler, type FrameDriver } from './animationScheduler';
import { useAnimationClock } from '../hooks/useAnimationClock';

const points = Array.from({length:21}, (_,i) => ({x:0.1 + i * 0.01, y:0.2 + i * 0.01}));
export const fixture = {schemaVersion:1,signId:'TEST_ONLY',durationMs:1000,metadata:{sourceWidth:640,sourceHeight:480,extractionVersion:'unit-test',fixture:true},frames:[{timestampMs:0,leftHand:points,rightHand:points},{timestampMs:100,leftHand:null,rightHand:points},{timestampMs:900,leftHand:points,rightHand:null}]};
function driver() {
  let now = 0; let index = 0;
  const callbacks = new Map<number,FrameRequestCallback>();
  const api: FrameDriver = { now: () => now, request: callback => { callbacks.set(++index, callback); return index; }, cancel: id => { callbacks.delete(id); } };
  return { api, callbacks, step: (delta:number) => { now += delta; const queue=[...callbacks.values()]; callbacks.clear(); queue.forEach(callback => callback(now)); } };
}
describe('phase 1: saved samples, rendering, and a single-animation clock', () => {
  it('validates data and rejects partial hands or invalid timestamps', () => {
    expect(parseAnimation(fixture).frames).toHaveLength(3);
    expect(() => parseAnimation({...fixture,frames:[{...fixture.frames[0],leftHand:[]}]})).toThrow();
    expect(() => parseAnimation({...fixture,frames:[fixture.frames[1],fixture.frames[0]]})).toThrow();
    expect(() => parseAnimation(fixture,'OTHER')).toThrow();
    expect(() => parseAnimation({...fixture,frames:[{...fixture.frames[0],rightHand:[...points.slice(1),{x:NaN,y:0}]}]})).toThrow();
  });
  it('draws 21 landmarks and 21 standard connections per visible hand at source aspect', () => {
    const animation=parseAnimation(fixture);
    const markup=renderToStaticMarkup(<HandSkeletonCanvas frame={animation.frames[0]} metadata={animation.metadata}/>);
    const container=document.createElement('div'); container.innerHTML=markup;
    expect(container.querySelectorAll('circle')).toHaveLength(42);
    expect(container.querySelectorAll('line')).toHaveLength(42);
    expect(container.querySelector('svg')?.getAttribute('viewBox')).toBe('0 0 640 480');
    expect(container.querySelector('circle')?.getAttribute('cx')).toBe('64');
    expect(container.querySelector('circle')?.getAttribute('cy')).toBe('96');
  });
  it('hides undetected hands and stale gaps, without fabricating positions', () => {
    const animation=parseAnimation(fixture);
    expect(frameAt(animation,100)?.leftHand).toBeNull();
    expect(frameAt(animation,600)).toBeNull();
    expect(frameAt(animation,-1)).toBeNull();
    expect(frameAt(animation,1001)).toBeNull();
    const markup=renderToStaticMarkup(<HandSkeletonCanvas frame={{timestampMs:0,leftHand:null,rightHand:points}}/>);
    expect((markup.match(/<circle /g)||[]).length).toBe(21);
    expect(renderToStaticMarkup(<HandSkeletonCanvas frame={null}/>)).toContain('No saved hand detections');
  });
  it('plays once, pauses, resumes, changes speed, restarts and explicitly replays', () => {
    const time=driver(); const player=new AnimationScheduler(1000,time.api);
    player.play(); time.step(200); expect(player.getSnapshot().elapsedMs).toBe(200);
    player.pause(); time.step(300); expect(player.getSnapshot().elapsedMs).toBe(200);
    player.play(); time.step(100); player.setSpeed(2); time.step(100);
    expect(player.getSnapshot().elapsedMs).toBe(500);
    time.step(300); expect(player.getSnapshot().status).toBe('ended');
    player.play(); expect(time.callbacks.size).toBe(0);
    player.restart(); expect(player.getSnapshot().elapsedMs).toBe(0);
    player.replay(); time.step(50); expect(player.getSnapshot().elapsedMs).toBe(100);
    player.dispose(); expect(time.callbacks.size).toBe(0);
  });
  it('does not schedule an empty animation and rejects invalid speeds', () => {
    const time=driver(); const player=new AnimationScheduler(0,time.api);
    player.play(); expect(time.callbacks.size).toBe(0);
    expect(() => player.setSpeed(0)).toThrow();
    expect(() => player.setSpeed(NaN)).toThrow();
  });
  it('cancels requestAnimationFrame on React unmount', async () => {
    Object.assign(globalThis, {IS_REACT_ACT_ENVIRONMENT:true});
    const request=vi.spyOn(globalThis,'requestAnimationFrame').mockReturnValue(123);
    const cancel=vi.spyOn(globalThis,'cancelAnimationFrame').mockImplementation(() => {});
    let controls: ReturnType<typeof useAnimationClock>;
    function Harness() { controls=useAnimationClock(1000,1); return null; }
    const root=createRoot(document.createElement('div'));
    await act(async () => root.render(<Harness/>));
    await act(async () => controls.play());
    expect(request).toHaveBeenCalled();
    await act(async () => root.unmount());
    expect(cancel).toHaveBeenCalledWith(123);
    request.mockRestore(); cancel.mockRestore();
  });
});
