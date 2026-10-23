// @vitest-environment jsdom
import { act,useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { expect,it,vi } from 'vitest';
const state=vi.hoisted(()=>({captureStops:0,socketStops:0,select:null as null|((s:any)=>void)}));
vi.mock('../../services/audioCapture',()=>({SharedAudioCapture:class{async start(){}stop(){state.captureStops++;}},SpeechSegmenter:class{push(){}}}));
vi.mock('../../services/liveAudio',()=>({LiveAudioClient:class{constructor(select:any){state.select=select;}connect(){}stop(){state.socketStops++;}}}));
vi.mock('../../components/avatar/ContinuousAvatar',()=>({ContinuousAvatar:({selection,onSigning}:any)=>{useEffect(()=>onSigning(!!selection),[selection,onSigning]);return <div role="img" aria-label="Avatar"/>;}}));
import LiveTranslation from './LiveTranslation';

it('preserves the sharing controls and moves through idle, listening, signing and stopped states',async()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});const container=document.createElement('div');const root=createRoot(container);
  await act(async()=>root.render(<LiveTranslation/>));
  expect(container.querySelectorAll('textarea,input,select,video')).toHaveLength(0);
  expect(container.textContent).not.toContain('Research preview');expect(container.textContent).not.toContain('Transcript');
  const button=container.querySelector('button')!;expect(button.textContent).toBe('Share Tab & See Signs');
  await act(async()=>button.click());expect(button.textContent).toBe('Stop Listening');expect(container.textContent).toContain('Listening');
  await act(async()=>state.select?.({signs:['CRY'],manifest:{}}));expect(container.textContent).toContain('Signing');
  await act(async()=>button.click());expect(button.textContent).toBe('Share Tab & See Signs');expect(state.captureStops).toBeGreaterThan(0);expect(state.socketStops).toBeGreaterThan(0);
  await act(async()=>root.unmount());
});
