import { useEffect, useState } from 'react';
import { Play, Pause, RotateCcw, SkipBack } from 'lucide-react';
import type { AnimationManifest, SignSegment, VideoClock } from '../../types/hands';
import { loadSequence, sequenceAt, sequenceDuration, type SequenceItem } from '../../utils/signSequence';
import { videoSignPosition } from '../../utils/videoSignSync';
import { frameAt } from '../../services/animationSchema';
import { useAnimationClock } from '../../hooks/useAnimationClock';
import { useAnimationLibrary } from '../../hooks/useAnimationLibrary';
import { HandSkeletonCanvas } from './HandSkeletonCanvas';

export interface SequencePlayerProps {
  signs: string[];
  visible?: boolean;
  size?: 'small'|'medium'|'large';
  manifest?: AnimationManifest | null;
  speed?: number;
  onSpeedChange?: (speed: number) => void;
  videoClock?: VideoClock;
  segments?: SignSegment[];
  onCurrentSignChange?: (id: string | null, index: number) => void;
  autoPlay?: boolean;
}
export function SignSequencePlayer({signs,manifest:providedManifest,visible=true,size='medium',speed=1,onSpeedChange,videoClock,segments=[],onCurrentSignChange,autoPlay=false}: SequencePlayerProps) {
  const defaultLibrary=useAnimationLibrary(false,providedManifest===undefined);
  const manifest=providedManifest===undefined ? defaultLibrary.manifest : providedManifest;
  const [items,setItems]=useState<SequenceItem[]>([]);
  const [loading,setLoading]=useState(false);
  const external=!!videoClock && segments.length>0;
  const requested=external ? segments.flatMap(segment=>segment.signs) : signs;
  const key=JSON.stringify({requested,external,fixture:manifest?.fixture});
  useEffect(() => {
    const controller=new AbortController(); let active=true;
    setItems([]); setLoading(!!manifest && requested.length>0);
    if(manifest) loadSequence(requested,manifest,controller.signal).then(result=>{
      if(active){setItems(result);setLoading(false);}
    }).catch(()=>{if(active)setLoading(false);});
    return ()=>{active=false;controller.abort();};
  },[key,manifest]);
  const clock=useAnimationClock(sequenceDuration(items),speed,!loading && !external,key);
  useEffect(()=>{if(autoPlay && !loading && !external && items.length && clock.durationMs===sequenceDuration(items) && clock.status==='idle')clock.play();},[autoPlay,loading,external,items,clock.durationMs,clock.status,clock.play]);
  const video=external ? videoSignPosition(segments,items,videoClock!.currentTimeMs,videoClock!.playing,speed) : null;
  const current=external ? video?.current || null : sequenceAt(items,clock.elapsedMs);
  const animation=current?.item.animation;
  const frame=animation ? frameAt(animation,current!.localTimeMs) : null;
  const progress=external ? video?.progress || 0 : clock.durationMs ? clock.elapsedMs/clock.durationMs : 0;
  const visibleSigns=external ? video?.signs || [] : signs;
  const elapsed=external ? video?.elapsedMs || 0 : clock.elapsedMs;
  const duration=external ? video?.durationMs || 0 : clock.durationMs;
  const status=loading ? 'Loading' : external ? video?.playing ? 'Video playing' : 'Video paused / between signs' : clock.status;
  const currentOrdinal = current ? external && video ? segments.slice(0,video.segmentIndex).reduce((count,segment)=>count+segment.signs.length,0)+current.index : current.index : -1;
  useEffect(()=>{onCurrentSignChange?.(current?.item.signId||null,currentOrdinal);},[current?.item.signId,currentOrdinal,onCurrentSignChange]);

  return <section className="sign-player">
    <div className="player-status"><span className="eyebrow">C · SAVED 2D HAND LANDMARKS</span><span className="badge">{status}</span></div>
    {manifest?.fixture && <p className="fixture-banner">Coordinate diagnostics only · synthetic test data · not SLSL signs</p>}
    <div className={`hand-preview ${size}`}>{visible ? <HandSkeletonCanvas frame={frame} metadata={animation?.metadata} label={current ? `Hand landmark playback for ${current.item.signId}` : 'Hand landmark player, no sign selected'}/> : <p className="hand-preview-hidden">Hand preview is hidden in Settings. Playback timing remains active.</p>}</div>
    <div className="hand-legend"><span><i className="left-hand-dot"/> Left hand</span><span><i className="right-hand-dot"/> Right hand</span><span>Full-frame positions · no mirroring</span></div>
    <div className="current-sign" aria-live="polite"><strong>{loading ? 'Loading saved animations…' : current?.item.signId || (external ? 'No active sign at this video time' : 'No sign sequence selected')}</strong><p>{current?.item.error || (!requested.length ? 'Process text or provide agent sign identifiers to begin.' : 'Only saved landmark coordinates are replayed.')}</p></div>
    <div className="sign-chips" aria-label="Sign sequence">{visibleSigns.map((id,index)=><span key={index} className={current?.index===index?'active':''} aria-current={current?.index===index?'step':undefined}>{id}</span>)}</div>
    <progress aria-label="Sign sequence progress" max={1} value={progress}/>
    <div className="sequence-controls">
      <button className="button primary" disabled={!items.length||loading||external||clock.status==='ended'} onClick={clock.status==='playing'?clock.pause:clock.play}>{clock.status==='playing'?<Pause size={16}/>:<Play size={16}/>}{clock.status==='playing'?'Pause':clock.status==='paused'?'Resume':'Play'}</button>
      <button className="button secondary" disabled={!items.length||loading||external} onClick={clock.restart}><SkipBack size={16}/> Restart</button>
      <button className="button secondary" disabled={!items.length||loading||external} onClick={clock.replay}><RotateCcw size={16}/> Replay</button>
      {onSpeedChange && <label>Speed <select value={speed} onChange={e=>onSpeedChange(Number(e.target.value))}>{[0.5,0.75,1,1.25,1.5].map(rate=><option key={rate} value={rate}>{rate}×</option>)}</select></label>}
    </div>
    <p className="small muted">{(elapsed/1000).toFixed(2)} / {(duration/1000).toFixed(2)} s · {external?'Use the video controls for play, pause, seek and replay.':'Missing signs use a labelled 0.8 s blank slot. No substitutes.'}</p>
    {video?.clipped && <p className="fixture-banner" role="status">This segment is shorter than its saved sequence at the selected speed. Motion is clipped at the segment end, never accelerated automatically. Adjust the timestamps before evaluation.</p>}
    {items.some(item=>item.error) && <ul className="missing-list">{items.filter(item=>item.error).map((item,index)=><li key={index}>{item.error}</li>)}</ul>}
    {defaultLibrary.error && providedManifest===undefined && <p role="alert" className="error">{defaultLibrary.error}</p>}
  </section>;
}
