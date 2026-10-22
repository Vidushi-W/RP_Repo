// @vitest-environment jsdom
// Actual HTTP, SHA checks, saved samples, renderer and real-time animation clock.
// This checks DOM/SVG playback, not visible browser pixels or capture permissions.
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { renderToStaticMarkup } from 'react-dom/server';
import { webcrypto } from 'node:crypto';
import { Buffer } from 'node:buffer';
import { existsSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, it, vi } from 'vitest';
import { ContinuousAvatar } from './ContinuousAvatar';
import { HandSkeletonCanvas } from './HandSkeletonCanvas';
import { loadAnimation, parseManifest } from '../../services/animationLoader';
import type { HandAnimation } from '../../types/hands';

const pause = (ms:number) => new Promise(resolve=>setTimeout(resolve,ms));
it.skipIf(process.env.LANKASIGNS_EXPANSION_PLAYBACK_TEST!=='1')('plays all ten reviewed recordings and requested sequences using saved motion',async()=>{
  Object.assign(globalThis,{IS_REACT_ACT_ENVIRONMENT:true});
  const output=resolve(process.cwd(),'../research/evaluation/vocabulary-expansion/playback-results.json');
  if(existsSync(output))throw new Error('Preserve the existing playback evidence before a new run');
  const actualFetch=globalThis.fetch,base='http://127.0.0.1:5173';
  const metrics:any[]=[],errors:string[]=[];
  vi.stubGlobal('fetch',async(input:RequestInfo|URL,init?:RequestInit)=>{
    const url=new URL(String(input),base);const response=await actualFetch(url,init);
    if(url.pathname==='/api/audio/metrics'&&response.ok)metrics.push(JSON.parse(String(init?.body)));
    return response;
  });
  vi.stubGlobal('crypto',{subtle:{digest:(algorithm:AlgorithmIdentifier,bytes:ArrayBuffer)=>webcrypto.subtle.digest(algorithm,Buffer.from(new Uint8Array(bytes)))}});
  const container=document.createElement('div');document.body.append(container);const root=createRoot(container);
  const report:any={atUtc:new Date().toISOString(),method:'actual HTTP/SHA/saved-frame DOM rendering with real timers',visibleBrowserPlaybackVerified:false,sequences:[]};
  try{
    const vocabulary=await (await fetch('/api/agent/vocabulary')).json();
    const manifest=parseManifest({schemaVersion:1,fixture:false,signs:vocabulary.signs.map((e:any)=>({signId:e.signId,label:e.canonicalLabel,aliases:[e.canonicalLabel,...e.verifiedSynonyms],animationUrl:e.animationFile,sha256:e.sha256,datasetReference:e.provenance,reviewed:e.reviewStatus==='approved'}))});
    expect(manifest.signs).toHaveLength(10);
    expect(manifest.signs.some(e=>e.signId==='ASK'||e.signId==='NURSE')).toBe(false);
    const animations=new Map<string,HandAnimation>();
    for(const entry of manifest.signs)animations.set(entry.signId,await loadAnimation(entry.signId,manifest));
    const sequences=[['CRY','WALK','LOOK'],['DRINK','RUN'],['GIVE','TAKE'],['LOOK'],['DRAW','SEE'],['EAT']];
    for(let seq=0;seq<sequences.length;seq++){
      const signs=sequences[seq],before=metrics.length,signingStates:boolean[]=[];
      const movement=new Map(signs.map(sid=>[sid,new Set<string>()]));
      const frameMatches=new Map(signs.map(sid=>[sid,new Set<number>()]));
      const startedAt=performance.now();
      const selection={signs,manifest,session:'eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee',seq,startedAt,captureWindowMs:0};
      const signing=(value:boolean)=>signingStates.push(value);
      await act(async()=>root.render(<ContinuousAvatar selection={selection} session={seq} onSigning={signing} onError={message=>errors.push(message)}/>));
      const deadline=performance.now()+signs.reduce((n,sid)=>n+animations.get(sid)!.durationMs,0)+12000;
      while(performance.now()<deadline){
        await act(async()=>{await pause(50);});
        expect(errors).toEqual([]);
        const groups=[...container.querySelectorAll('g[data-hand]')].map(g=>({side:g.getAttribute('data-hand') as 'leftHand'|'rightHand',points:[...g.querySelectorAll('circle')].map(p=>[Number(p.getAttribute('cx')),Number(p.getAttribute('cy'))])}));
        if(groups.length){
          for(const sid of signs){
            const animation=animations.get(sid)!;
            const index=animation.frames.findIndex(frame=>groups.every(g=>JSON.stringify(frame[g.side]?.map(p=>[p.x*animation.metadata.sourceWidth,p.y*animation.metadata.sourceHeight]))===JSON.stringify(g.points)));
            if(index>=0){
              movement.get(sid)!.add(JSON.stringify(groups));frameMatches.get(sid)!.add(index);
              if(frameMatches.get(sid)!.size===1){
                const svg=renderToStaticMarkup(<HandSkeletonCanvas frame={animation.frames[index]} metadata={animation.metadata}/>);
                writeFileSync(resolve(process.cwd(),`../research/evaluation/vocabulary-expansion/rendered-${sid.toLowerCase()}.svg`),svg);
              }
            }
          }
        }
        if(metrics.length-before===signs.length&&container.querySelector('[aria-label="Avatar resting"]'))break;
      }
      expect(metrics.slice(before).map(m=>m.signId)).toEqual(signs);
      expect(container.querySelector('[aria-label="Avatar resting"]')).not.toBeNull();
      for(const sid of signs){expect(movement.get(sid)!.size).toBeGreaterThan(1);expect(frameMatches.get(sid)!.size).toBeGreaterThan(1);}
      report.sequences.push({requested:signs,played:metrics.slice(before).map(m=>m.signId),completed:true,elapsedMs:performance.now()-startedAt,observedDistinctStoredFrames:Object.fromEntries([...frameMatches].map(([sid,indices])=>[sid,[...indices]])),signingStates});
    }
    Object.assign(report,{status:'passed',metrics,approvedIds:[...animations.keys()],allTenAnimationsMovedAndCompleted:true});
  }catch(error){Object.assign(report,{status:'failed',error:String(error),metrics,errors});throw error;}
  finally{writeFileSync(output,JSON.stringify(report,null,2));await act(async()=>root.unmount());container.remove();vi.unstubAllGlobals();}
},150000);
