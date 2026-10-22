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
  return <main className="live-page">
    <a href="/" className="live-brand">LankaSigns</a>
    <div className="live-heading"><h1>Listen. Understand. Connect.</h1><p>Share a tab’s audio and watch the available signs.</p></div>
    <section className="live-avatar" aria-label="Sign language avatar"><ContinuousAvatar selection={selection} session={session} onSigning={setSigning} onError={fail}/></section>
    <div className="live-actions"><button aria-pressed={listening||starting} className={'listen-button '+(listening?'active':'')} onClick={listening||starting?stop:()=>void listen()}>{listening||starting?'Stop Listening':'Listen'}</button>
    <p role="status" aria-live="polite">{starting?'Choose a tab and enable Share tab audio.':signing?'Signing':listening?busy?'Listening · processing speech':'Listening':'Choose a browser tab and enable Share tab audio when prompted.'}</p></div>
    {error&&<p className="live-error" role="alert">{error}</p>}
  </main>;
}
