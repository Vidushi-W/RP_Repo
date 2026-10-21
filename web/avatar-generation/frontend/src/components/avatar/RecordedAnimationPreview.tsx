import { useEffect, useRef, useState } from 'react';
import type { HandAnimation } from '../../types/hands';
import { parseAnimation, frameAt } from '../../services/animationSchema';
import { useAnimationClock } from '../../hooks/useAnimationClock';
import { HandSkeletonCanvas } from './HandSkeletonCanvas';

// Local inspection is separate from the reviewed vocabulary manifest.
export function RecordedAnimationPreview() {
  const [animation,setAnimation]=useState<HandAnimation|null>(null);
  const [error,setError]=useState('');
  const [speed,setSpeed]=useState(1);
  const [version,setVersion]=useState(0);
  const generation=useRef(0);
  const mounted=useRef(true);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;generation.current++;};},[]);
  const clock=useAnimationClock(animation?.durationMs||0,speed,true,String(version));
  async function open(file?:File) {
    if(!file)return;
    const token=++generation.current;
    setAnimation(null);setError('');
    try {
      if(file.size>64*1024*1024)throw new Error('Choose an extracted animation JSON smaller than 64 MB.');
      const parsed=parseAnimation(JSON.parse(await file.text()));
      if(!mounted.current||token!==generation.current)return;
      setAnimation(parsed);setVersion(value=>value+1);
    } catch(error) {
      if(mounted.current&&token===generation.current)setError(error instanceof Error?error.message:'Could not read the animation.');
    }
  }
  return <details className="panel local-video-panel">
    <summary>Preview an extracted recording before review</summary>
    <p className="small muted mt-4">Choose saved landmark JSON from the extractor. This local preview does not add it to the reviewed SLSL vocabulary.</p>
    <label className="field-label" htmlFor="recorded-json">Extracted animation JSON</label>
    <input id="recorded-json" type="file" accept=".json,application/json" onChange={event=>{const file=event.target.files?.[0];event.target.value='';void open(file);}}/>
    {error&&<p role="alert" className="error">{error}</p>}
    {animation&&<>
      <p className="fixture-banner"><strong>{animation.signId} · {animation.metadata.fixture?'synthetic diagnostic, not a sign':'unreviewed source recording'}.</strong> Verify tracking, predicted handedness and sign correctness against the original video. Extraction is not linguistic validation.</p>
      <HandSkeletonCanvas frame={frameAt(animation,clock.elapsedMs)} metadata={animation.metadata} label={`Local unreviewed landmark preview: ${animation.signId}`}/>
      <div className="hand-legend"><span><i className="left-hand-dot"/> Predicted left hand</span><span><i className="right-hand-dot"/> Predicted right hand</span></div>
      <progress aria-label="Recording preview progress" max={animation.durationMs} value={clock.elapsedMs}/>
      <div className="sequence-controls">
        <button className="button primary" disabled={clock.status==='ended'} onClick={clock.status==='playing'?clock.pause:clock.play}>{clock.status==='playing'?'Pause preview':clock.status==='paused'?'Resume preview':'Play preview'}</button>
        <button className="button secondary" onClick={clock.restart}>Restart preview</button>
        <button className="button secondary" onClick={clock.replay}>Replay preview</button>
        <label>Preview speed <select value={speed} onChange={event=>setSpeed(Number(event.target.value))}>{[0.5,0.75,1,1.25,1.5].map(value=><option key={value} value={value}>{value}×</option>)}</select></label>
        <button className="text-button" onClick={()=>{generation.current++;setAnimation(null);setVersion(value=>value+1);}}>Clear preview</button>
      </div>
      <p className="small muted">{(clock.elapsedMs/1000).toFixed(2)} / {(animation.durationMs/1000).toFixed(2)} s · {animation.frames.length} saved samples · {clock.status}</p>
    </>}
  </details>;
}
