import { Hand, ScreenShare, ArrowLeft, ShieldCheck, BookOpen } from 'lucide-react';
import { useCallback,useEffect,useRef,useState } from 'react';
import { SharedAudioCapture,SpeechSegmenter } from '../../services/audioCapture';
import { LiveAudioClient,type LiveSelection } from '../../services/liveAudio';
import { ContinuousAvatar } from '../../components/avatar/ContinuousAvatar';
import '../../styles/live.css';

export default function LiveTranslation(){
  const [listening,setListening]=useState(false),[starting,setStarting]=useState(false),[busy,setBusy]=useState(false),[signing,setSigning]=useState(false);
  const [error,setError]=useState(''),[session,setSession]=useState(0),[selection,setSelection]=useState<LiveSelection|null>(null);
  const capture=useRef<SharedAudioCapture|null>(null),client=useRef<LiveAudioClient|null>(null),generation=useRef(0);
  const stop=useCallback(()=>{generation.current++;capture.current?.stop();client.current?.stop();setListening(false);setStarting(false);setBusy(false);setSigning(false);setSelection(null);setSession(v=>v+1);},[]);
  useEffect(()=>()=>{generation.current++;capture.current?.stop();client.current?.stop();},[]);
  const fail=useCallback((message:string)=>{stop();setError(message);},[stop]);
  async function listen(){
    setError('');setStarting(true);const token=++generation.current;
    const connection=new LiveAudioClient(setSelection,(message,fatal=true)=>{if(fatal)fail(message);else setError(message);},setBusy);client.current=connection;
    const segmenter=new SpeechSegmenter((pcm,start)=>connection.enqueue(pcm,start));
    const audio=new SharedAudioCapture();capture.current=audio;
    try{
      // getDisplayMedia is invoked in this user click, before network awaits.
      await audio.start(frame=>segmenter.push(frame),stop);
      if(token!==generation.current){audio.stop();return;}
      connection.connect();setListening(true);setStarting(false);
    }catch(e){if(token===generation.current)fail(e instanceof Error?e.message:'Audio sharing was not started. Please try again.');}
  }
  return <main className="live-page" id="main-content">
    <header className="studio-nav"><a href="/" className="live-brand"><span className="brand-icon"><Hand size={25}/></span><span>LankaSigns<small>AVATAR STUDIO</small></span></a><a className="text-link" href="/"><ArrowLeft size={16}/> Back to Home</a></header>
    <div className="live-heading"><span className="eyebrow">YOUR CONTENT. A MORE VISUAL EXPERIENCE.</span><h1>Your Sign Language Studio</h1><p>Share your browser tab, bring its audio into the studio, and watch the avatar sign.</p></div>
    <div className="studio-grid"><section className="share-controls" aria-labelledby="share-heading"><span className="step-icon"><ScreenShare size={26}/></span><h2 id="share-heading">Share Your Browser Tab</h2><p>Choose a browser tab containing audio. LankaSigns will process supported spoken content and display matching sign animations.</p>
      <div className="live-actions"><button aria-pressed={listening||starting} className={'listen-button '+(listening?'active':'')} onClick={listening||starting?stop:()=>void listen()}><ScreenShare size={20}/>{listening||starting?'Stop Listening':'Share Tab & See Signs'}</button>
      <p className="audio-status" role="status" aria-live="polite"><span className="status-dot"/>{starting?'Choose a tab and enable Share tab audio.':signing?'Avatar Signing':listening?busy?'Listening - Processing Speech':'Listening to Shared Audio':'Ready to Share'}</p></div>
      <ol className="studio-guide"><li>Open the video or lesson in a browser tab.</li><li>Choose that tab and enable <strong>Share tab audio</strong> when prompted.</li><li>Keep the audio playing and follow the matching signs here.</li></ol><p className="sharing-permission"><ShieldCheck size={18}/> Sharing starts with your permission. Stop Listening ends the capture.</p>
      <div className="studio-coverage"><BookOpen size={20}/><h3>Start with supported vocabulary</h3><p>Some spoken content may have no matching sign. Pause between short phrases to give the avatar time to respond.</p><a className="text-link" href="/vocabulary">Explore Sign Library &rarr;</a></div>
    </section><section className="avatar-display" aria-label="Sign language avatar"><div className="avatar-panel-heading"><div><span className="eyebrow">YOUR SIGNING COMPANION</span><h2>Your Signing Avatar</h2></div><span className="badge">{signing?'Signing':'Avatar ready'}</span></div><div className="live-avatar"><ContinuousAvatar selection={selection} session={session} onSigning={setSigning} onError={fail}/></div><p className="avatar-display-caption">Watch supported spoken content come to life through Sri Lankan Sign Language.</p></section></div>
    {error&&<p className="live-error" role="alert">{error}</p>}
    <p className="studio-bottom-note">Best experienced in desktop Chrome or Edge. Shared audio availability depends on your browser and the tab you choose.</p>
    <a href="/research" className="text-link studio-more">More playback options &rarr;</a>
  </main>;
}
