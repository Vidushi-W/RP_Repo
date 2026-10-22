import { parseManifest } from './animationLoader';
import { validSignId,record } from './animationSchema';
import type { AnimationManifest } from '../types/hands';
import { pcmBase64 } from './audioCapture';
export interface LiveSelection {signs:string[];manifest:AnimationManifest;session?:string;seq?:number;startedAt?:number;captureWindowMs?:number}
export function parseLiveSelection(value:unknown):LiveSelection{
  if(!record(value)||value.type!=='selection'||!Array.isArray(value.signs)||value.signs.length>40||!value.signs.every(validSignId))throw new Error('The sign response could not be verified.');
  const manifest=parseManifest(value.manifest);
  if(manifest.fixture||manifest.signs.some(entry=>!entry.sha256))throw new Error('The sign library could not be verified.');
  if(value.signs.some(id=>!manifest.signs.some(entry=>entry.signId===id)))throw new Error('An unavailable sign was returned.');
  return {signs:value.signs as string[],manifest};
}
export class LiveAudioClient {
  private socket:WebSocket|null=null;private seq=0;private pending:{type:string;seq:number;startMs:number;pcm16:string}[]=[];
  private busy=false;private stopped=true;
  private timing=new Map<number,{startedAt:number;captureWindowMs:number}>();
  constructor(private onSelection:(s:LiveSelection)=>void,private onError:(message:string,fatal?:boolean)=>void,private onBusy:(busy:boolean)=>void){}
  connect(){
    this.stopped=false;const socket=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/api/audio/live`);this.socket=socket;
    socket.onmessage=event=>{
      if(this.stopped)return;
      try{
        const message=JSON.parse(event.data);
        if(message.type==='ready'){this.sendNext();return;}
        if(message.type==='selection'){
          const selection=parseLiveSelection(message),timing=this.timing.get(message.seq);
          this.timing.delete(message.seq);
          this.onSelection({...selection,...timing,session:message.session,seq:message.seq});
        }
        if(message.type==='error'){
          this.onError(message.message||'Speech processing failed.',message.fatal!==false);
          if(message.fatal){this.stop();return;}
        }
        if(['selection','ack','error'].includes(message.type)){this.busy=false;this.onBusy(false);this.sendNext();}
      }catch{this.onError('The sign response could not be verified.');this.stop();}
    };
    socket.onerror=()=>{if(!this.stopped)this.onError('The local speech service is unavailable. Please try again.');};
    socket.onclose=()=>{if(!this.stopped){this.stopped=true;this.onError('Listening stopped because the local speech service disconnected.');}};
  }
  enqueue(pcm:Int16Array,startMs:number){
    if(this.stopped)return;
    if(this.pending.length>=3){this.onError('Please pause between shorter phrases so the avatar can keep up.');this.stop();return;}
    const seq=this.seq++;this.timing.set(seq,{startedAt:performance.now()-pcm.length/16,captureWindowMs:pcm.length/16});
    this.pending.push({type:'audio',seq,startMs,pcm16:pcmBase64(pcm)});this.sendNext();
  }
  private sendNext(){
    if(this.stopped||this.busy||this.socket?.readyState!==WebSocket.OPEN)return;
    const next=this.pending.shift();if(next){this.busy=true;this.onBusy(true);this.socket.send(JSON.stringify(next));}
  }
  stop(){this.stopped=true;this.pending=[];this.timing.clear();this.busy=false;this.socket?.close();this.socket=null;this.onBusy(false);}
}
