// @vitest-environment jsdom
// Opt-in: real HTTP + Qwen + downloaded JSON + real-timer React/SVG playback.
// This is a DOM test environment, not a visible-browser or screenshot test.
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { webcrypto } from 'node:crypto';
import { Buffer } from 'node:buffer';
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, it, vi } from 'vitest';
import { processTranscript } from '../../services/semanticAgent';
import { parseAnimation } from '../../services/animationSchema';
import type { HandAnimation } from '../../types/hands';
import { SignSequencePlayer } from './SignSequencePlayer';

const live = process.env.LANKASIGNS_LIVE_TEST === '1';
const pause = (ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));

it.skipIf(!live)('verifies real Qwen selection through the live frontend proxy and replays stored landmarks',async()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
  const base='http://127.0.0.1:5173';
  const actualFetch=globalThis.fetch;
  const requests:{url:string;status:number}[]=[];
  let saved:HandAnimation|undefined;
  // Only resolve relative development URLs; every response comes from real HTTP.
  vi.stubGlobal('fetch',async(input:RequestInfo|URL,init?:RequestInit)=>{
    const url=new URL(String(input),base);
    const response=await actualFetch(url,init);
    requests.push({url:url.href,status:response.status});
    if(url.pathname.endsWith('/recorded/nurse.json'))saved=parseAnimation(await response.clone().json(),'NURSE');
    return response;
  });
  // jsdom lacks subtle and uses a different ArrayBuffer realm. Copy the actual
  // downloaded bytes into a Node Buffer, then run real WebCrypto SHA-256.
  vi.stubGlobal('crypto',{subtle:{digest:(algorithm:AlgorithmIdentifier,bytes:ArrayBuffer)=>
    webcrypto.subtle.digest(algorithm,Buffer.from(new Uint8Array(bytes)))}});
  const container=document.createElement('div');document.body.append(container);
  const root=createRoot(container);
  let report:Record<string,unknown>={verificationType:'jsdom React/SVG with real HTTP and real timers; visible browser not verified',testedAtUtc:new Date().toISOString()};
  const started=performance.now();
  try {
    const result=await processTranscript('nursing professional',true);
    expect(result.signs).toEqual(['NURSE']);
    expect(result.inference?.performed).toBe(true);
    expect(result.inference?.model).toBe('qwen3:1.7b');
    report={...report,inferenceLatencySeconds:(performance.now()-started)/1000,inference:result.inference,signs:result.signs};
    await act(async()=>root.render(<SignSequencePlayer signs={result.signs} manifest={result.manifest} autoPlay/>));
    async function until(condition:()=>boolean,timeoutMs=8000){
      const deadline=performance.now()+timeoutMs;
      while(performance.now()<deadline){
        await act(async()=>{await pause(70);});
        if(condition())return;
      }
      throw new Error('Live player did not reach the expected state: '+container.textContent);
    }
    const signature=()=>JSON.stringify([...container.querySelectorAll('g[data-hand]')].map(g=>({hand:g.getAttribute('data-hand'),points:[...g.querySelectorAll('circle')].map(p=>[Number(p.getAttribute('cx')),Number(p.getAttribute('cy'))])})));
    function savedFrameIndex(){
      expect(saved).toBeDefined();
      const groups=JSON.parse(signature()) as {hand:'leftHand'|'rightHand';points:number[][]}[];
      return saved!.frames.findIndex(frame=>groups.every(g=>JSON.stringify(frame[g.hand]?.map(p=>[p.x*saved!.metadata.sourceWidth,p.y*saved!.metadata.sourceHeight]))===JSON.stringify(g.points)));
    }
    await until(()=>container.querySelectorAll('circle').length>0);
    expect(container.textContent).toContain('Pause');
    const first=signature();const firstFrame=savedFrameIndex();
    expect(firstFrame).toBeGreaterThanOrEqual(0);
    await until(()=>container.querySelectorAll('circle').length>0&&signature()!==first);
    const secondFrame=savedFrameIndex();
    expect(secondFrame).toBeGreaterThan(firstFrame);
    const landmarkCount=container.querySelectorAll('circle').length;
    await until(()=>container.querySelector('.badge')?.textContent==='ended');
    expect(container.querySelector('progress')!.value).toBe(1);
    report={...report,status:'passed',animationSha256:result.manifest.signs[0].sha256,
      savedFrameCount:saved!.frames.length,durationMs:saved!.durationMs,
      observedStoredFrameIndices:[firstFrame,secondFrame],observedLandmarkCount:landmarkCount,
      automaticPlaybackCompleted:true,requests};
  }catch(error){report={...report,status:'failed',error:String(error),requests};throw error;}
  finally{
    writeFileSync(resolve(process.cwd(),'../research/evaluation/live-playback-results.json'),JSON.stringify(report,null,2));
    await act(async()=>root.unmount());container.remove();vi.unstubAllGlobals();
  }
},180000);
