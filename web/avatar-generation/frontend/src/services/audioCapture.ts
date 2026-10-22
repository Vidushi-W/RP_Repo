export class SharedAudioCapture {
  private stream:MediaStream|null=null;
  private context:AudioContext|null=null;
  private node:AudioWorkletNode|null=null;
  private generation=0;
  async start(onFrame:(samples:Float32Array)=>void,onEnded:()=>void){
    if(!navigator.mediaDevices?.getDisplayMedia)throw new Error('Tab audio sharing is unavailable. Open LankaSigns in a supported desktop browser.');
    const token=++this.generation;
    const stream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:true});
    if(token!==this.generation){stream.getTracks().forEach(t=>t.stop());return;}
    this.stream=stream;
    if(!stream.getAudioTracks().length){this.stop();throw new Error('No shared audio was received. Choose a browser tab and enable Share tab audio.');}
    try{
      const context=new AudioContext({sampleRate:16000});this.context=context;
      if(context.sampleRate!==16000)throw new Error('This browser cannot capture the required audio format. Try a current desktop Chrome or Edge.');
      await context.audioWorklet.addModule(import.meta.env.BASE_URL+'audio-capture-worklet.js');
      if(token!==this.generation){this.stop();return;}
      const node=new AudioWorkletNode(context,'pcm-capture');this.node=node;
      node.port.onmessage=event=>{if(token===this.generation&&event.data instanceof Float32Array)onFrame(event.data);};
      context.createMediaStreamSource(new MediaStream(stream.getAudioTracks())).connect(node);
      node.connect(context.destination);
      stream.getTracks().forEach(track=>track.addEventListener('ended',onEnded,{once:true}));
      await context.resume();
    }catch(error){this.stop();throw error;}
  }
  stop(){
    this.generation++;this.node?.disconnect();if(this.node)this.node.port.onmessage=null;this.node=null;
    this.stream?.getTracks().forEach(track=>track.stop());this.stream=null;
    void this.context?.close().catch(()=>{});this.context=null;
  }
}

/** Non-overlapping utterances: 200 ms pre-roll, 600 ms silence, max 6 s. */
export class SpeechSegmenter {
  private position=0;private start=0;private active:number[]=[];private pre:number[]=[];private silent=0;
  constructor(private emit:(pcm:Int16Array,startMs:number)=>void){}
  push(frame:Float32Array){
    const rms=Math.sqrt(frame.reduce((sum,v)=>sum+v*v,0)/frame.length);
    if(!this.active.length){
      if(rms<0.012){this.pre.push(...frame);this.pre=this.pre.slice(-3200);this.position+=frame.length;return;}
      this.start=this.position-this.pre.length;this.active=this.pre;this.pre=[];
    }
    this.active.push(...frame);this.position+=frame.length;
    this.silent=rms<0.012?this.silent+frame.length:0;
    if(this.silent>=9600||this.active.length>=96000){
      if(this.active.length-this.silent>=6400){
        const pcm=Int16Array.from(this.active,v=>Math.round(Math.max(-1,Math.min(1,v))*32767));
        this.emit(pcm,Math.round(this.start/16));
      }
      this.active=[];this.silent=0;
    }
  }
}

export function pcmBase64(pcm:Int16Array){
  const buffer=new ArrayBuffer(pcm.length*2);const view=new DataView(buffer);
  pcm.forEach((value,index)=>view.setInt16(index*2,value,true));
  let binary='';for(const byte of new Uint8Array(buffer))binary+=String.fromCharCode(byte);
  return btoa(binary);
}
