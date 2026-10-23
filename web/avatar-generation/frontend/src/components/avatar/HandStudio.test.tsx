// @vitest-environment jsdom
import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { StrictMode, act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { PreferencesProvider } from '../../hooks/usePreferences';
import { AvatarGenerationPage } from './AvatarGenerationPage';
import { SignSequencePlayer } from './SignSequencePlayer';
import { parseManifest } from '../../services/animationLoader';
import realManifest from '../../../public/hand-animations/manifest.json';
import fixtureManifest from '../../../public/hand-animations/fixtures/manifest.json';
import fixtureA from '../../../public/hand-animations/fixtures/calibration-a.json';
import fixtureB from '../../../public/hand-animations/fixtures/calibration-b.json';
let container:HTMLDivElement,root:Root,now:number,nextId:number;
let frames:Map<number,FrameRequestCallback>;
function button(text:string) {const found=[...container.querySelectorAll('button')].find(button=>button.textContent?.trim()===text);if(!found)throw new Error('Button not found: '+text);return found;}
async function advance(ms:number) {now+=ms;await act(async()=>{const callbacks=[...frames.values()];frames.clear();callbacks.forEach(callback=>callback(now));});}
beforeEach(()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
  localStorage.clear();now=0;nextId=0;frames=new Map();
  vi.spyOn(performance,'now').mockImplementation(()=>now);
  vi.stubGlobal('requestAnimationFrame',(callback:FrameRequestCallback)=>{frames.set(++nextId,callback);return nextId;});
  vi.stubGlobal('cancelAnimationFrame',(id:number)=>frames.delete(id));
  vi.stubGlobal('fetch',vi.fn().mockImplementation(async(url:string)=>({ok:true,json:async()=>url.endsWith('calibration-a.json')?fixtureA:url.endsWith('calibration-b.json')?fixtureB:url.includes('/fixtures/')?fixtureManifest:realManifest})));
  container=document.createElement('div');document.body.append(container);root=createRoot(container);
});
afterEach(async()=>{await act(async()=>root.unmount());container.remove();vi.restoreAllMocks();vi.unstubAllGlobals();});
describe('hand studio integration',()=>{
  it('processes only explicit test aliases, draws both hands and supports controls in StrictMode',async()=>{
    await act(async()=>root.render(<StrictMode><PreferencesProvider><AvatarGenerationPage/></PreferencesProvider></StrictMode>));
    expect(container.textContent).toContain('No signs are available in this playback library yet.');
    const diagnostic=container.querySelector('.fixture-toggle input') as HTMLInputElement;
    await act(async()=>diagnostic.click());
    expect((container.querySelector('#english-input') as HTMLTextAreaElement).value).toBe('test-a test-b');
    await act(async()=>button('Process input').click());
    expect(container.querySelectorAll('circle')).toHaveLength(42);
    expect(container.textContent).toContain('synthetic test data');
    await act(async()=>button('Play').click());await advance(500);
    expect(container.querySelector('.current-sign strong')?.textContent).toBe('TEST_CALIBRATION_A');
    await act(async()=>button('Pause').click());
    const progress=(container.querySelector('progress') as HTMLProgressElement).value;
    await advance(300);
    expect((container.querySelector('progress') as HTMLProgressElement).value).toBe(progress);
    await act(async()=>button('Resume').click());await advance(800);
    expect(container.querySelector('.current-sign strong')?.textContent).toBe('TEST_CALIBRATION_B');
    expect(container.querySelector('.matched-words .current-word')?.textContent).toBe('test-b');
    await advance(2000);
    expect((button('Play') as HTMLButtonElement).disabled).toBe(true);
    await act(async()=>button('Replay').click());await advance(100);
    expect(container.querySelector('.current-sign strong')?.textContent).toBe('TEST_CALIBRATION_A');
    await act(async()=>button('Restart').click());
    expect((container.querySelector('progress') as HTMLProgressElement).value).toBe(0);
  });
  it('shows empty/missing sequences and aborts pending asset loads on unmount',async()=>{
    const manifest=parseManifest(fixtureManifest);
    await act(async()=>root.render(<SignSequencePlayer signs={[]} manifest={manifest}/>));
    expect(container.textContent).toContain('No sign sequence selected');
    await act(async()=>root.render(<SignSequencePlayer signs={['MISSING']} manifest={manifest}/>));
    expect(container.textContent).toContain('No saved animation for MISSING');
    let signal:AbortSignal|undefined;
    vi.stubGlobal('fetch',vi.fn().mockImplementation((_url,options)=>{signal=options.signal;return new Promise(()=>{});}));
    await act(async()=>root.render(<SignSequencePlayer signs={['TEST_CALIBRATION_A']} manifest={manifest}/>));
    await act(async()=>root.unmount());
    expect(signal?.aborted).toBe(true);
    expect(frames.size).toBe(0);
    root=createRoot(container);
  });
  it('renders video-driven seek positions without restarting an independent clock',async()=>{
    const manifest=parseManifest(fixtureManifest);
    const segments=[{startMs:1000,endMs:4000,signs:['TEST_CALIBRATION_A','TEST_CALIBRATION_B']}];
    async function render(time:number,playing:boolean){await act(async()=>root.render(<SignSequencePlayer signs={[]} manifest={manifest} segments={segments} videoClock={{currentTimeMs:time,playing}}/>));}
    await render(1100,true);
    expect(container.querySelector('.current-sign strong')?.textContent).toBe('TEST_CALIBRATION_A');
    await render(2300,false);
    expect(container.querySelector('.current-sign strong')?.textContent).toBe('TEST_CALIBRATION_B');
    const progress=(container.querySelector('progress') as HTMLProgressElement).value;
    await advance(500);
    expect((container.querySelector('progress') as HTMLProgressElement).value).toBe(progress);
    await render(1050,false);
    expect(container.querySelector('.current-sign strong')?.textContent).toBe('TEST_CALIBRATION_A');
    expect(frames.size).toBe(0);
  });
});
