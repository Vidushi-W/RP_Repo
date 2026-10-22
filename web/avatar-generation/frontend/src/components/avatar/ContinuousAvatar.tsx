import { useEffect,useRef,useState } from 'react';
import { loadAnimation } from '../../services/animationLoader';
import { frameAt } from '../../services/animationSchema';
import { useAnimationClock } from '../../hooks/useAnimationClock';
import type { HandAnimation } from '../../types/hands';
import type { LiveSelection } from '../../services/liveAudio';
import { HandSkeletonCanvas } from './HandSkeletonCanvas';

export class PlaybackQueue {
  private items:HandAnimation[]=[];
  constructor(private maxMs=20000,private maxSigns=8){}
  push(animation:HandAnimation){if(this.items.length>=this.maxSigns||this.items.reduce((n,a)=>n+a.durationMs,0)+animation.durationMs>this.maxMs)return false;this.items.push(animation);return true;}
  shift(){return this.items.shift()||null;}
  clear(){this.items=[];}
}
export function ContinuousAvatar({selection,session,onSigning,onError}:{selection:LiveSelection|null;session:number;onSigning:(s:boolean)=>void;onError:(e:string)=>void}){
  const queue=useRef(new PlaybackQueue());const [current,setCurrent]=useState<HandAnimation|null>(null);const [version,setVersion]=useState(0);
  const generation=useRef(0);const chain=useRef(Promise.resolve());const currentRef=useRef<HandAnimation|null>(null);
  const metrics=useRef(new WeakMap<HandAnimation,{selection:LiveSelection;preparationMs:number;reported:boolean}>());
  const clock=useAnimationClock(current?.durationMs||0,1,!!current,String(version));
  useEffect(()=>{generation.current++;queue.current.clear();currentRef.current=null;setCurrent(null);setVersion(v=>v+1);onSigning(false);return()=>{generation.current++;queue.current.clear();};},[session]);
  useEffect(()=>{
    if(!selection?.signs.length)return;
    const token=generation.current;
    chain.current=chain.current.catch(()=>{}).then(async()=>{
      for(const sid of selection.signs){
        if(token!==generation.current)return;
        const prepared=performance.now();
        const animation=await loadAnimation(sid,selection.manifest);
        if(token!==generation.current)return;
        metrics.current.set(animation,{selection,preparationMs:performance.now()-prepared,reported:false});
        // Prepare independently of active playback; never reset its clock on append.
        if(!queue.current.push(animation))throw new Error('The avatar is catching up. Please pause before speaking again.');
        if(!currentRef.current){const next=queue.current.shift();currentRef.current=next;setCurrent(next);setVersion(v=>v+1);}
      }
    }).catch(error=>{if(token===generation.current)onError(error instanceof Error&&error.message.startsWith('The avatar is catching up')?error.message:'A sign could not be loaded. Please try listening again.');});
  },[selection]);
  useEffect(()=>{if(current&&clock.durationMs===current.durationMs&&clock.status==='idle'){clock.play();onSigning(true);}},[current,clock.durationMs,clock.status,clock.play]);
  useEffect(()=>{
    if(clock.status!=='ended'||!current)return;
    onSigning(false);
    const timer=setTimeout(()=>{const next=queue.current.shift();currentRef.current=next;setCurrent(next);setVersion(v=>v+1);},150);
    return()=>clearTimeout(timer);
  },[clock.status,current,onSigning]);
  const frame=current?frameAt(current,clock.elapsedMs):null;
  useEffect(()=>{
    if(!current||!frame||(frame.leftHand===null&&frame.rightHand===null))return;
    const metric=metrics.current.get(current);
    if(!metric||metric.reported||!metric.selection.session||metric.selection.startedAt===undefined)return;
    metric.reported=true;
    void fetch('/api/audio/metrics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      session:metric.selection.session,seq:metric.selection.seq,signId:current.signId,captureWindowMs:metric.selection.captureWindowMs,
      preparationMs:metric.preparationMs,firstRecordedHandMs:performance.now()-metric.selection.startedAt,
      animationDurationMs:current.durationMs})}).catch(()=>{});
  },[current,frame]);
  if(!current||clock.status==='ended')return <svg className="neutral-avatar" viewBox="0 0 640 480" role="img" aria-label="Avatar resting"><circle cx="320" cy="115" r="55"/><path d="M255 190 Q320 165 385 190 L415 375 Q320 405 225 375 Z"/><path d="M255 205 Q200 245 205 355 M385 205 Q440 245 435 355"/></svg>;
  return <HandSkeletonCanvas frame={frame} metadata={current.metadata} label="Avatar signing from a saved recording" showMissing={false}/>;
}
