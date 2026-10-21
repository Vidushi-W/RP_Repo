import { useEffect, useState } from 'react';
import { Eye, EyeOff, Upload, RotateCcw, Play, Pause, Film } from 'lucide-react';
import { AvatarRenderer } from '../avatar/AvatarRenderer';
import { useVideoSync } from '../../hooks/useVideoSync';
import { usePreferences } from '../../hooks/usePreferences';
import { findVocabulary, isPlayable } from '../../services/vocabulary';
import { formatTime, validateCues } from '../../utils/synchronization';
import demo from '../../data/demo.json';
const cues = validateCues(demo.cues);
export function VideoWorkspace() {
  const { preferences, update } = usePreferences();
  const { videoRef, time, duration, playing, sync } = useVideoSync(cues, preferences.signingSpeed);
  const [source, setSource] = useState<string | null>(demo.videoUrl);
  const [filename, setFilename] = useState('No video selected');
  const [error, setError] = useState('');
  const [testTime, setTestTime] = useState(0);
  // Test markers are deliberately independent of the user's uploaded video's speech.
  const entry = sync.cue ? findVocabulary(sync.cue.wordId) : undefined;
  useEffect(() => () => { if (source?.startsWith('blob:')) URL.revokeObjectURL(source); }, [source]);
  async function toggle() {
    const video = videoRef.current;
    if (!video || !source) return;
    try { if (video.paused) await video.play(); else video.pause(); } catch { setError('This browser could not play the video. Try a browser-compatible MP4 or WebM file.'); }
  }
  function seek(value: number) { if (videoRef.current && source && duration > 0) videoRef.current.currentTime = Math.max(0, Math.min(duration, value)); }
  return <div className="translation-grid"><section className="panel player-panel">
    <div className="panel-heading"><div><span className="eyebrow">VIDEO WORKSPACE</span><h2>Your video, with a signing companion.</h2></div><span className="badge">Prepared timestamps</span></div>
    <div className="video-stage">
      <video ref={videoRef} src={source || undefined} controls={!!source} playsInline preload="metadata" aria-label="Educational video" onError={() => setError('Video playback failed. Select a browser-compatible MP4 or WebM file.')}/>
      {!source && <div className="video-empty"><span className="large-icon"><Film size={32}/></span><h3>Bring your learning into view</h3><p>Choose a local educational video to test playback.<br/>Your file stays in this browser.</p><label className="button light"> <Upload size={17}/> Choose video<input className="sr-only" type="file" accept="video/*" onChange={event => { const file = event.target.files?.[0]; if (!file) return; if (!file.type.startsWith('video/')) { setError('Select a video file.'); return; } setSource(URL.createObjectURL(file)); setFilename(file.name); setError(''); }}/></label></div>}
      {preferences.avatarVisible && <div className={`avatar-overlay ${preferences.avatarSize}`}><AvatarRenderer avatarUrl={demo.avatarUrl} entry={entry} sync={sync}/><span>Placeholder · no SLSL motion</span></div>}
    </div>
    <div className="playback-controls"><button className="icon-button" aria-label={playing ? 'Pause video' : 'Play video'} disabled={!source} onClick={toggle}>{playing ? <Pause size={19}/> : <Play size={19}/>}</button><button className="icon-button" aria-label="Replay video" disabled={!source} onClick={() => { seek(0); videoRef.current?.play().catch(() => setError('Playback was blocked. Press Play to try again.')); }}><RotateCcw size={18}/></button><input type="range" aria-label="Video playback position" min={0} max={duration || 1} step={0.05} value={Math.min(time, duration || 1)} onChange={event => seek(Number(event.target.value))} disabled={!source || !duration}/><span className="time">{formatTime(time)} / {formatTime(duration)}</span><button className="icon-button" aria-label={preferences.avatarVisible ? 'Hide avatar' : 'Show avatar'} aria-pressed={preferences.avatarVisible} onClick={() => update({ avatarVisible: !preferences.avatarVisible })}>{preferences.avatarVisible ? <Eye size={19}/> : <EyeOff size={19}/>}</button></div>
    <div className="video-file"><span>{filename}</span>{source && <button className="text-button" onClick={() => { videoRef.current?.pause(); setSource(null); setFilename('No video selected'); setError(''); }}>Remove video</button>}</div>
    {error && <p role="alert" className="error">{error}</p>}
    <div className="notice"><strong>Timing demonstration only.</strong> Markers A–C are synthetic test cues, not spoken-word detections or SLSL translations. No sign model or validated animation is connected.</div>
  </section>
  <aside className="translation-aside"><section className="panel"><span className="eyebrow">LIVE PLAYBACK STATE</span><h3>Synchronization monitor</h3><dl className="state-list"><div><dt>Current detected word</dt><dd>Detection not configured</dd></div><div><dt>Prepared timing marker</dt><dd>{sync.cue?.label || 'Between markers'}</dd></div><div><dt>Animation status</dt><dd>{isPlayable(entry) ? 'Asset available' : 'No validated animation'}</dd></div><div><dt>Video time</dt><dd>{time.toFixed(2)} s</dd></div><div><dt>Cue-local animation time</dt><dd>{sync.animationTime.toFixed(2)} s</dd></div><div><dt>Playback</dt><dd>{playing ? 'Playing' : 'Paused / waiting'}</dd></div></dl></section>
    <section className="panel"><span className="eyebrow">PREPARED TIMELINE</span><h3>Three test markers</h3><p className="muted small">Click a cue to seek your video. No automatic transcription runs.</p><div className="cue-list">{cues.map(cue => <button key={cue.id} disabled={!source || duration <= cue.start} className={sync.cue?.id === cue.id ? 'active' : ''} onClick={() => seek(cue.start)}><span>{cue.label}</span><small>{formatTime(cue.start)}–{formatTime(cue.end)}</small></button>)}</div></section>
    <section className="panel"><span className="eyebrow">NO VIDEO REQUIRED</span><h3>Inspect a timestamp</h3><p className="muted small">A manual test of cue boundaries, independent of video playback.</p><input aria-label="Test timeline position" type="range" min="0" max="10" step="0.1" value={testTime} onChange={e => setTestTime(Number(e.target.value))}/><p className="small">{testTime.toFixed(1)} s · {cues.find(c => c.start <= testTime && testTime < c.end)?.label || 'No active marker'}</p></section>
  </aside></div>;
}
