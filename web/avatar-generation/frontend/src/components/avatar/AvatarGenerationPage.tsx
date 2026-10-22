import { useCallback, useEffect, useState } from 'react';
import { Upload, Play } from 'lucide-react';
import { useAnimationLibrary } from '../../hooks/useAnimationLibrary';
import { usePreferences } from '../../hooks/usePreferences';
import { useVideoSync } from '../../hooks/useVideoSync';
import { matchWords, type WordMatch } from '../../services/signMatcher';
import { parseAgentResult } from '../../services/agentAdapter';
import type { AgentResult } from '../../types/hands';
import { TranslationPanel } from './TranslationPanel';
import { SignSequencePlayer } from './SignSequencePlayer';
import { RecordedAnimationPreview } from './RecordedAnimationPreview';
import { SemanticAgentPanel } from './SemanticAgentPanel';

export function AvatarGenerationPage() {
  const [fixtureMode,setFixtureMode]=useState(false);
  const [currentWord,setCurrentWord]=useState(-1);
  const onCurrentSign=useCallback((_id:string|null,index:number)=>setCurrentWord(index),[]);
  const {manifest,error:libraryError}=useAnimationLibrary(fixtureMode);
  const {preferences,update}=usePreferences();
  const [english,setEnglish]=useState('');
  const [result,setResult]=useState<AgentResult|null>(null);
  const [words,setWords]=useState<WordMatch[]>([]);
  const [missing,setMissing]=useState<string[]>([]);
  const [resultSource,setResultSource]=useState<'resolver'|'agent'|'fixture'>('resolver');
  const [agentJson,setAgentJson]=useState('');
  const [error,setError]=useState('');
  const [videoUrl,setVideoUrl]=useState<string|null>(null);
  const [videoName,setVideoName]=useState('');
  const [syncEnabled,setSyncEnabled]=useState(false);
  const {videoRef,time,duration,playing}=useVideoSync([],1);
  useEffect(()=>()=>{if(videoUrl)URL.revokeObjectURL(videoUrl);},[videoUrl]);
  const clearResult=()=>{setResult(null);setWords([]);setMissing([]);setSyncEnabled(false);setError('');};
  function processText() {
    if(!manifest)return;
    const match=matchWords(english,manifest);
    setResult({englishText:english,signs:match.signs});
    setWords(match.words);setMissing(match.missing);setResultSource('resolver');setSyncEnabled(false);setError('');
  }
  function importAgent() {
    try {
      const parsed=parseAgentResult(JSON.parse(agentJson));
      setResult(parsed);setEnglish(parsed.englishText);setResultSource('agent');
      setWords([]);setMissing([]);setError('');setSyncEnabled(false);
    } catch(error) {setError(error instanceof Error?error.message:'Agent JSON could not be read.');}
  }
  function timingFixture() {
    if(!fixtureMode)return;
    const englishText='test-a test-b test-a';
    setResult({englishText,signs:['TEST_CALIBRATION_A','TEST_CALIBRATION_B','TEST_CALIBRATION_A'],segments:[{startMs:1000,endMs:4000,signs:['TEST_CALIBRATION_A','TEST_CALIBRATION_B']},{startMs:5000,endMs:5500,signs:['TEST_CALIBRATION_A']}]});
    setEnglish(englishText);setResultSource('fixture');setWords(manifest?matchWords(englishText,manifest).words:[]);setMissing([]);setError('');setSyncEnabled(false);
  }
  return <><div className="notice hand-research-note"><strong>Hand-only research prototype.</strong> Saved hand landmarks do not represent complete SLSL: facial expressions, body position and other nonmanual features are absent. No new gestures, speech recognition or AI translation are generated here.</div>
    <div className="hand-workspace"><div className="input-column">
      <section className="panel"><span className="eyebrow">A · INPUT</span><h2>Start with English text</h2><p className="small muted mt-4">The development resolver matches only exact aliases in the selected library. It preserves English order and does not determine SLSL grammar.</p>
        <label className="field-label" htmlFor="english-input">English text or transcript</label><textarea id="english-input" rows={4} maxLength={20000} value={english} onChange={e=>setEnglish(e.target.value)} placeholder={fixtureMode?'test-a test-b':'Enter English words from your reviewed vocabulary…'}/>
        <div className="input-actions"><button className="button primary" disabled={!manifest||!english.trim()} onClick={processText}><Play size={16}/> Process input</button><span className="small muted">{manifest?manifest.signs.length+' '+(fixtureMode?'test fixtures':'reviewed signs'):'Loading library…'}</span></div>
        <label className="fixture-toggle"><input type="checkbox" checked={fixtureMode} onChange={e=>{const enabled=e.target.checked;setFixtureMode(enabled);setEnglish(enabled?'test-a test-b':'');clearResult();}}/> Use coordinate test fixtures (not SLSL)</label>
        {fixtureMode && <div className="fixture-banner"><strong>Development diagnostics.</strong> TEST_CALIBRATION_A and B are saved synthetic coordinate samples, not human recordings or sign-language words. Process “test-a test-b” to exercise the player.<button className="text-button" disabled={!manifest} onClick={timingFixture}>Load timestamped coordinate test</button></div>}
        {!fixtureMode && manifest?.signs.length===0 && <p className="small muted mt-4">No dataset signs have been registered. Add reviewed recordings using the extraction guide, or enable coordinate diagnostics to test the player.</p>}
        {libraryError && <p className="error" role="alert">{libraryError}</p>}
      </section>
      <TranslationPanel result={result} words={words} missing={missing} manifest={manifest} source={resultSource} activeIndex={currentWord}/>
      <details className="panel agent-import"><summary>Connect existing agent output</summary><p className="small muted mt-4">Paste the real agent's JSON with englishText, optional sinhalaText, explicit signs and optional timestamped segments. This validates structure, not translation or SLSL grammar. No agent service is configured.</p><label className="field-label" htmlFor="agent-json">External agent JSON</label><textarea id="agent-json" rows={6} maxLength={100000} value={agentJson} onChange={e=>setAgentJson(e.target.value)} placeholder={'{"englishText":"…","sinhalaText":"…","signs":["SIGN_ID"]}'}/><button className="button secondary mt-4" onClick={importAgent} disabled={!agentJson.trim()}>Use supplied agent result</button></details>
    </div>
    <div className="animation-column"><section className="panel"><SignSequencePlayer signs={result?.signs||[]} manifest={manifest} visible={preferences.avatarVisible} size={preferences.avatarSize} speed={preferences.signingSpeed} onSpeedChange={value=>update({signingSpeed:value})} segments={result?.segments} onCurrentSignChange={onCurrentSign} videoClock={syncEnabled&&videoUrl ? {currentTimeMs:time*1000,playing} : undefined}/></section><p className="small muted mt-4">Coordinates retain the recording's full-frame positions and aspect ratio. Green = predicted left; amber = predicted right. Handedness requires source-video review.</p></div></div>
    <section className="panel local-video-panel"><div><span className="eyebrow">OPTIONAL · VIDEO SYNCHRONIZATION</span><h2>Follow a local video's clock</h2><p className="small muted mt-4">Choose a video and supply timestamped segments from your agent or prepared annotations. This browser does not transcribe speech or infer sign timing.</p></div>
      <label className="button secondary video-picker"><Upload size={16}/> Choose local video<input className="sr-only" type="file" accept="video/mp4,video/webm" onChange={e=>{const file=e.target.files?.[0];if(!file)return;if(!['video/mp4','video/webm'].includes(file.type)){setError('Choose a browser-compatible MP4 or WebM video.');return;}setVideoUrl(URL.createObjectURL(file));setVideoName(file.name);setError('');}}/></label>
      <video ref={videoRef} className="local-video" src={videoUrl||undefined} controls={!!videoUrl} playsInline preload="metadata" aria-label="Local educational video for timestamp synchronization" hidden={!videoUrl} onError={()=>{if(videoUrl)setError('The selected video could not be decoded. Try a supported MP4 or WebM codec.');}}/>
      {videoUrl && <div className="video-meta"><span>{videoName} · {time.toFixed(2)} / {duration.toFixed(2)} s</span><button className="text-button" onClick={()=>{if(videoRef.current){videoRef.current.pause();videoRef.current.currentTime=0;void videoRef.current.play().catch(()=>setError('Playback was blocked. Use the video Play control.'));}}}>Replay video</button><button className="text-button" onClick={()=>{videoRef.current?.pause();setVideoUrl(null);setVideoName('');setSyncEnabled(false);}}>Remove video</button></div>}
      <label className="fixture-toggle"><input type="checkbox" checked={syncEnabled} disabled={!videoUrl||!result?.segments?.length} onChange={e=>setSyncEnabled(e.target.checked)}/> Synchronize hands to video timestamps</label>
      {!result?.segments?.length && <p className="small muted">No timestamped segments supplied. Standalone sequence playback remains available.</p>}
      {result?.segments && <div className="segment-list">{result.segments.map((segment,index)=><span key={index}>{(segment.startMs/1000).toFixed(2)}–{(segment.endMs/1000).toFixed(2)} s: {segment.signs.join(' → ')||'No signs'}</span>)}</div>}
      {resultSource==='fixture' && <p className="fixture-banner">Synthetic timing fixture only. These markers do not correspond to your video's speech. The second segment intentionally demonstrates clipping.</p>}
      <p className="small muted mt-4">Files stay in this browser. When synchronized, video time is authoritative; the player never loops a completed segment or automatically accelerates a sign.</p>
    </section>
    <SemanticAgentPanel/>
    <RecordedAnimationPreview/>
    {error && <p role="alert" className="error">{error}</p>}
  </>;
}
