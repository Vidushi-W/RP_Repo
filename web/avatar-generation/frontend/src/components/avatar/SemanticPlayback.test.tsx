// @vitest-environment jsdom
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { afterEach, expect, it, vi } from 'vitest';
import { SignSequencePlayer } from './SignSequencePlayer';
import fixture from '../../../public/hand-animations/fixtures/calibration-a.json';

afterEach(()=>{vi.restoreAllMocks();vi.unstubAllGlobals();});
it('automatically starts validated sequential playback and keeps manual pause available',async()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
  const request=vi.fn().mockReturnValue(7);vi.stubGlobal('requestAnimationFrame',request);vi.stubGlobal('cancelAnimationFrame',vi.fn());
  const animation={...fixture,signId:'NURSE',metadata:{...fixture.metadata,fixture:false}};
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:async()=>animation}));
  const manifest={schemaVersion:1 as const,fixture:false,signs:[{signId:'NURSE',label:'nurse',aliases:['nurse'],animationUrl:'hand-animations/recorded/nurse.json',datasetReference:'Pending research recording',reviewed:false}]};
  const container=document.createElement('div');const root=createRoot(container);
  await act(async()=>root.render(<SignSequencePlayer signs={['NURSE','NURSE']} manifest={manifest} autoPlay/>));
  expect(container.textContent).toContain('Pause');expect(request).toHaveBeenCalled();
  const pause=[...container.querySelectorAll('button')].find(b=>b.textContent==='Pause')!;
  await act(async()=>pause.click());
  expect(container.textContent).toContain('Resume');
  expect(container.querySelectorAll('.sign-chips span')).toHaveLength(2);
  await act(async()=>root.unmount());
});
