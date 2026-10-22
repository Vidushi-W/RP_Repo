// Audio stays in memory. The connected output is silent (no audio feedback).
class PcmCapture extends AudioWorkletProcessor {
  constructor(){super();this.buffer=new Float32Array(320);this.index=0;}
  process(inputs,outputs){
    for(const channel of outputs[0]||[])channel.fill(0);
    const input=inputs[0];if(!input?.length)return true;
    for(let i=0;i<input[0].length;i++){
      let sample=0;for(const channel of input)sample+=channel[i]/input.length;
      this.buffer[this.index++]=sample;
      if(this.index===320){this.port.postMessage(this.buffer,[this.buffer.buffer]);this.buffer=new Float32Array(320);this.index=0;}
    }
    return true;
  }
}
registerProcessor('pcm-capture',PcmCapture);
