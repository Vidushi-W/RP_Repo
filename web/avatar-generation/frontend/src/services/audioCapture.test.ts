import { afterEach,describe,expect,it,vi } from 'vitest';
import { SharedAudioCapture,SpeechSegmenter,pcmBase64 } from './audioCapture';
import { parseLiveSelection,LiveAudioClient } from './liveAudio';
import { PlaybackQueue } from '../components/avatar/ContinuousAvatar';
import type { HandAnimation } from '../types/hands';
afterEach(()=>vi.unstubAllGlobals());
describe('shared audio lifecycle and bounded speech windows',()=>{
  it('does not request capture until start, and stops all tracks if audio is missing',async()=>{
    const stop=vi.fn(),request=vi.fn().mockResolvedValue({getTracks:()=>[{stop}],getAudioTracks:()=>[]});
    vi.stubGlobal('navigator',{mediaDevices:{getDisplayMedia:request}});
    const capture=new SharedAudioCapture();expect(request).not.toHaveBeenCalled();
    await expect(capture.start(()=>{},()=>{})).rejects.toThrow('Share tab audio');
    expect(stop).toHaveBeenCalled();expect(request).toHaveBeenCalledWith({video:true,audio:true});
  });
  it('stops a stream that arrives after cancellation while the permission picker is open',async()=>{
    const stop=vi.fn();let resolve!:(v:unknown)=>void;
    vi.stubGlobal('navigator',{mediaDevices:{getDisplayMedia:()=>new Promise(r=>resolve=r)}});
    const capture=new SharedAudioCapture();const pending=capture.start(()=>{},()=>{});capture.stop();
    resolve({getTracks:()=>[{stop}]});await pending;expect(stop).toHaveBeenCalled();
  });
  it('handles unsupported capture without requesting a microphone',async()=>{
    vi.stubGlobal('navigator',{mediaDevices:{}});
    await expect(new SharedAudioCapture().start(()=>{},()=>{})).rejects.toThrow('unavailable');
  });
  it('releases shared audio, shared video, worklet and audio context on stop',async()=>{
    const stopAudio=vi.fn(),stopVideo=vi.fn(),close=vi.fn().mockResolvedValue(undefined),disconnect=vi.fn();
    const audio={stop:stopAudio,addEventListener:vi.fn()},video={stop:stopVideo,addEventListener:vi.fn()};
    vi.stubGlobal('navigator',{mediaDevices:{getDisplayMedia:vi.fn().mockResolvedValue({getTracks:()=>[audio,video],getAudioTracks:()=>[audio]})}});
    vi.stubGlobal('AudioContext',class{sampleRate=16000;audioWorklet={addModule:async()=>{}};destination={};close=close;resume=async()=>{};createMediaStreamSource(){return{connect:vi.fn()};}});
    vi.stubGlobal('AudioWorkletNode',class{port={onmessage:null};connect=vi.fn();disconnect=disconnect;});
    vi.stubGlobal('MediaStream',class{});
    const capture=new SharedAudioCapture();await capture.start(()=>{},()=>{});capture.stop();
    expect(stopAudio).toHaveBeenCalled();expect(stopVideo).toHaveBeenCalled();expect(disconnect).toHaveBeenCalled();expect(close).toHaveBeenCalled();
  });
  it('ignores silence and creates non-overlapping ordered windows, retaining repeated speech',()=>{
    const windows:{pcm:Int16Array;start:number}[]=[];const segmenter=new SpeechSegmenter((pcm,start)=>windows.push({pcm,start}));
    const silence=new Float32Array(320),voice=new Float32Array(320).fill(.1);
    for(let i=0;i<100;i++)segmenter.push(silence);expect(windows).toHaveLength(0);
    for(let repeat=0;repeat<2;repeat++){for(let i=0;i<40;i++)segmenter.push(voice);for(let i=0;i<40;i++)segmenter.push(silence);}
    expect(windows).toHaveLength(2);expect(windows[1].start).toBeGreaterThanOrEqual(windows[0].start+windows[0].pcm.length/16);
  });
  it('splits sustained speech into bounded windows and encodes signed little-endian PCM',()=>{
    const durations:number[]=[];const segmenter=new SpeechSegmenter(pcm=>durations.push(pcm.length));
    for(let i=0;i<700;i++)segmenter.push(new Float32Array(320).fill(.2));
    expect(durations).toEqual([96000,96000]);
    expect([...atob(pcmBase64(new Int16Array([1,-1])))].map(c=>c.charCodeAt(0))).toEqual([1,0,255,255]);
  });
  it('rejects pending manifests and unknown sign IDs at the live boundary',()=>{
    expect(()=>parseLiveSelection({type:'selection',signs:['NURSE'],manifest:{schemaVersion:1,fixture:false,signs:[]}})).toThrow('unavailable');
    expect(()=>parseLiveSelection({type:'selection',signs:[],manifest:{schemaVersion:1,fixture:false,signs:[{signId:'NURSE',label:'nurse',aliases:[],animationUrl:'hand-animations/recorded/nurse.json',datasetReference:'test',reviewed:false}]}})).toThrow('reviewed');
  });
  it('bounds playback duration and supports immediate queue cancellation',()=>{
    const queue=new PlaybackQueue(1000,2);const animation={durationMs:600} as HandAnimation;
    expect(queue.push(animation)).toBe(true);expect(queue.push(animation)).toBe(false);
    queue.clear();expect(queue.shift()).toBeNull();expect(queue.push(animation)).toBe(true);
  });
  it('closes the socket and clears pending audio on stop',()=>{
    const close=vi.fn(),send=vi.fn();let socket:any;
    class FakeSocket{static OPEN=1;readyState=1;close=close;send=send;onmessage:any;onerror:any;onclose:any;constructor(){socket=this;}}
    vi.stubGlobal('WebSocket',FakeSocket);vi.stubGlobal('location',{protocol:'http:',host:'localhost:5173'});
    const selection=vi.fn(),client=new LiveAudioClient(selection,vi.fn(),vi.fn());client.connect();
    client.enqueue(new Int16Array(16000),0);client.enqueue(new Int16Array(16000),1000);expect(send).toHaveBeenCalledTimes(1);
    client.stop();socket.onmessage({data:JSON.stringify({type:'selection'})});expect(close).toHaveBeenCalled();expect(selection).not.toHaveBeenCalled();
  });
});
