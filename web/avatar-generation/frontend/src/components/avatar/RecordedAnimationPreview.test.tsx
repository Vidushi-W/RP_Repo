// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { RecordedAnimationPreview } from './RecordedAnimationPreview';
import fixture from '../../../public/hand-animations/fixtures/calibration-a.json';

afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});
describe('local unreviewed recording preview',()=>{
  it('plays a schema-valid recording without registering it as reviewed',async()=>{
    Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
    vi.stubGlobal('requestAnimationFrame',vi.fn().mockReturnValue(77));
    const cancel=vi.fn();vi.stubGlobal('cancelAnimationFrame',cancel);
    const container=document.createElement('div');const root=createRoot(container);
    await act(async()=>root.render(<RecordedAnimationPreview/>));
    const input=container.querySelector('input')!;
    Object.defineProperty(input,'files',{value:[{size:100,text:async()=>JSON.stringify({...fixture,signId:'NURSE',metadata:{...fixture.metadata,fixture:false}})}],configurable:true});
    await act(async()=>input.dispatchEvent(new Event('change',{bubbles:true})));
    expect(container.textContent).toContain('unreviewed source recording');
    expect(container.querySelectorAll('circle')).toHaveLength(42);
    const button=[...container.querySelectorAll('button')].find(item=>item.textContent==='Play preview')!;
    await act(async()=>button.click());
    expect(container.textContent).toContain('Pause preview');
    await act(async()=>root.unmount());
    expect(cancel).toHaveBeenCalledWith(77);
  });
  it('reports invalid JSON instead of starting playback',async()=>{
    Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
    const container=document.createElement('div');const root=createRoot(container);
    await act(async()=>root.render(<RecordedAnimationPreview/>));
    const input=container.querySelector('input')!;
    Object.defineProperty(input,'files',{value:[{size:10,text:async()=>'{bad'}]});
    await act(async()=>input.dispatchEvent(new Event('change',{bubbles:true})));
    expect(container.querySelector('[role=alert]')).not.toBeNull();
    expect(container.querySelectorAll('circle')).toHaveLength(0);
    await act(async()=>root.unmount());
  });
});
