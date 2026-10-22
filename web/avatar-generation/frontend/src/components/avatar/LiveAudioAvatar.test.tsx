// @vitest-environment jsdom
// @vitest-environment-options {"url":"http://127.0.0.1:5173"}
// Real-paced PCM at the capture seam; actual socket, Whisper, Qwen, files and player.
// Does not verify a visible browser, permission picker or shared-tab audio tracks.
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { existsSync,readFileSync,writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { webcrypto,createHash } from 'node:crypto';
import { Buffer } from 'node:buffer';
import { expect,it,vi } from 'vitest';
const capture=vi.hoisted(()=>({frame:null as null|((f:Float32Array)=>void),stops:0}));
vi.mock('../../services/audioCapture',async original=>{
  const real=await original<typeof import('../../services/audioCapture')>();
  return {...real,SharedAudioCapture:class{async start(frame:(f:Float32Array)=>void){capture.frame=frame;}stop(){capture.stops++;capture.frame=null;}}};
});
import LiveTranslation from '../../pages/VideoTranslation/LiveTranslation';
const wait=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));

it.skipIf(process.env.LANKASIGNS_LIVE_AUDIO_TEST!=='1')('streams actual English PCM through local ASR and Qwen to sequential body/hand playback',async()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
  const raw=readFileSync(resolve(process.cwd(),process.env.LANKASIGNS_AUDIO_PCM||'../.cache/english-sample-16k.pcm'));
  const expected=(process.env.LANKASIGNS_AUDIO_EXPECTED||'CRY,WALK,LOOK').split(',');
  const reference=process.env.LANKASIGNS_AUDIO_REFERENCE||'Someone is crying. The child is walking and looking.';
  const output=resolve(process.cwd(),process.env.LANKASIGNS_AUDIO_REPORT||'../research/evaluation/live-audio-avatar-results.json');
  if(process.env.LANKASIGNS_AUDIO_REPORT&&existsSync(output))throw new Error('Preserve existing audio evaluation evidence; choose a new report path');
  const pcm=new Int16Array(raw.length/2);for(let i=0;i<pcm.length;i++)pcm[i]=raw.readInt16LE(i*2);
  const base='http://127.0.0.1:5173',actualFetch=globalThis.fetch;
  const metrics:any[]=[],selections:any[]=[];const assets:string[]=[];
  vi.stubGlobal('fetch',async(input:RequestInfo|URL,init?:RequestInit)=>{
    const url=new URL(String(input),base);const response=await actualFetch(url,init);
    if(url.pathname==='/api/audio/metrics'&&response.ok)metrics.push(JSON.parse(String(init?.body)));
    if(url.pathname.includes('/recorded/batch/'))assets.push(url.pathname);
    return response;
  });
  vi.stubGlobal('crypto',{subtle:{digest:(algorithm:AlgorithmIdentifier,bytes:ArrayBuffer)=>webcrypto.subtle.digest(algorithm,Buffer.from(new Uint8Array(bytes)))}});
  const ActualSocket=globalThis.WebSocket;
  vi.stubGlobal('WebSocket',class extends ActualSocket{constructor(url:string){super(url);this.addEventListener('message',event=>{const value=JSON.parse(String(event.data));if(value.type==='selection')selections.push(value);});}});
  const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
  const report:any={atUtc:new Date().toISOString(),referenceTranscript:reference,expectedConceptIds:expected,pcmSha256:createHash('sha256').update(raw).digest('hex'),captureSeam:'real-paced generated English PCM; browser capture mocked',browserCaptureVerified:false,visiblePlaybackVerified:false};
  try{
    await act(async()=>root.render(<LiveTranslation/>));
    const button=container.querySelector('button')!;
    await act(async()=>button.click());expect(button.textContent).toBe('Stop Listening');
    for(let offset=0;offset<pcm.length;offset+=320){
      const samples=Float32Array.from(pcm.subarray(offset,offset+320),v=>v/32768);
      await act(async()=>{capture.frame?.(samples);await wait(20);});
    }
    for(let i=0;i<40;i++)await act(async()=>{capture.frame?.(new Float32Array(320));await wait(20);});
    const deadline=performance.now()+240000;let sawBody=false,sawHands=false;
    while(performance.now()<deadline){
      await act(async()=>{await wait(80);});
      sawHands ||= !!container.querySelector('[data-hand]');
      sawBody ||= !!container.querySelector('[data-face]');
      const resting=container.querySelector('[aria-label="Avatar resting"]');
      if(metrics.length>=expected.length&&resting)break;
      if(container.querySelector('[role="alert"]'))throw new Error(container.querySelector('[role="alert"]')!.textContent||'Live error');
    }
    expect(selections.flatMap(s=>s.signs)).toEqual(expected);
    expect(metrics.map(m=>m.signId)).toEqual(expected);
    expect(sawBody&&sawHands).toBe(true);
    for(let index=1;index<metrics.length;index++){
      // Different source windows have different timing origins. Compare delay
      // only within one window; the observed metrics list checks global order.
      if(metrics[index].seq===metrics[index-1].seq)expect(metrics[index].firstRecordedHandMs).toBeGreaterThan(metrics[index-1].firstRecordedHandMs);
    }
    expect(container.querySelector('[aria-label="Avatar resting"]')).not.toBeNull();
    await act(async()=>button.click());expect(button.textContent).toBe('Listen');expect(capture.stops).toBeGreaterThan(0);
    expect(container.querySelectorAll('textarea,input,select,video')).toHaveLength(0);
    Object.assign(report,{status:'passed',playbackOrder:selections.flatMap(s=>s.signs),serverResponses:selections,metrics,assets,bodyAndHandsRendered:true,captureCleanupCalled:true});
  }catch(error){Object.assign(report,{status:'failed',error:String(error),serverResponses:selections,metrics,assets});throw error;}
  finally{
    const log=resolve(process.cwd(),'../research/evaluation/live-sessions/events.jsonl');
    if(existsSync(log)){
      const sessions=new Set(selections.map(selection=>selection.session));
      report.speechAndSelection=readFileSync(log,'utf8').split('\n').filter(Boolean).map(line=>JSON.parse(line)).filter(event=>sessions.has(event.session)&&['speech-recognition','speech-selection'].includes(event.type));
    }
    writeFileSync(output,JSON.stringify(report,null,2));await act(async()=>root.unmount());container.remove();vi.unstubAllGlobals();
  }
},300000);
