'use strict';
/* Browser-local monophonic pitch monitor. Confidence is periodicity, not a
 * probability of correct violin fundamental detection. Physical instruments,
 * vibrato, double stops and input latency still require separate validation. */
const SVPitch=(()=>{
  const NOTE_NAMES=['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'];
  const MIN_HZ=80,MAX_HZ=3000;
  let gate=0.008;
  function rms(buf){let sum=0;for(let i=0;i<buf.length;i++)sum+=buf[i]*buf[i];return Math.sqrt(sum/buf.length);}
  function estimatePitch(buf,sampleRate){
    const level=rms(buf),invalid=reason=>({frequency:0,confidence:0,rms:Number.isFinite(level)?level:0,valid:false,reason,minFrequency:MIN_HZ,maxFrequency:MAX_HZ,method:'yin-periodicity'});
    if(!Number.isFinite(sampleRate)||sampleRate<=0||buf.length<128||!Number.isFinite(level))return invalid('invalid-input');
    if(level<gate)return invalid('below-noise-gate');
    const minLag=Math.max(2,Math.ceil(sampleRate/MAX_HZ));
    const maxLag=Math.min(Math.floor(sampleRate/MIN_HZ),Math.floor(buf.length/2)-1);
    if(minLag>=maxLag)return invalid('insufficient-window');
    const length=buf.length-maxLag,values=new Float64Array(maxLag+1);
    let running=0;
    for(let lag=1;lag<=maxLag;lag++){
      let difference=0;
      for(let i=0;i<length;i++){const d=buf[i]-buf[i+lag];difference+=d*d;}
      running+=difference;
      values[lag]=running>0?difference*lag/running:1;
    }
    let candidate=-1;
    for(let lag=minLag;lag<maxLag;lag++){
      if(values[lag]<0.1){while(lag+1<maxLag&&values[lag+1]<values[lag])lag++;candidate=lag;break;}
    }
    if(candidate<0)return invalid('low-periodicity');
    // A very weak fundamental can produce an early octave minimum. Prefer a
    // substantially stronger doubled-period minimum, but do not infer certainty.
    let ambiguous=false;
    const twice=candidate*2;
    if(values[candidate]>0.015&&twice+2<maxLag){
      let alternate=twice;
      for(let lag=twice-2;lag<=twice+2;lag++)if(values[lag]<values[alternate])alternate=lag;
      if(values[alternate]<values[candidate]*0.25){candidate=alternate;ambiguous=true;}
    }
    let lag=candidate;
    if(candidate>minLag&&candidate<maxLag){
      const a=values[candidate-1],b=values[candidate],c=values[candidate+1],denom=a-2*b+c;
      if(denom!==0)lag=candidate+Math.max(-0.5,Math.min(0.5,0.5*(a-c)/denom));
    }
    const frequency=sampleRate/lag;
    const confidence=Math.max(0,Math.min(1,1-values[candidate]));
    const valid=Number.isFinite(frequency)&&frequency>=MIN_HZ&&frequency<=MAX_HZ&&confidence>=0.85&&!ambiguous;
    return {frequency:valid?frequency:0,candidateFrequency:frequency,confidence:ambiguous?Math.min(confidence,0.5):confidence,rms:level,valid,reason:ambiguous?'ambiguous-period':valid?'periodic':'out-of-range',minFrequency:MIN_HZ,maxFrequency:MAX_HZ,method:'yin-periodicity'};
  }
  function detectPitch(buf,sampleRate){return estimatePitch(buf,sampleRate).frequency;}
  function freqToNote(freq,a4=440){
    if(!Number.isFinite(freq)||freq<=0||!Number.isFinite(a4)||a4<=0)return null;
    const n=Math.round(12*Math.log2(freq/a4))+69;
    const cents=Math.round(1200*Math.log2(freq/(a4*Math.pow(2,(n-69)/12))));
    return {name:NOTE_NAMES[((n%12)+12)%12]+(Math.floor(n/12)-1),cents,midi:n};
  }
  function monitor(stream,cb){
    const Ctx=window.AudioContext||window.webkitAudioContext,context=new Ctx();
    const source=context.createMediaStreamSource(stream),analyser=context.createAnalyser();
    analyser.fftSize=4096;source.connect(analyser);
    const buf=new Float32Array(analyser.fftSize);let alive=true;
    if(context.state==='suspended')context.resume().catch(()=>{});
    const timer=setInterval(()=>{
      if(!alive)return;
      analyser.getFloatTimeDomainData(buf);
      const result=estimatePitch(buf,context.sampleRate);
      cb(result.frequency,{...result,audioTime:context.currentTime,analysisWindowMs:buf.length/context.sampleRate*1000});
    },40);
    return {context,stop(){alive=false;clearInterval(timer);try{source.disconnect();}catch{}context.close().catch(()=>{});}};
  }
  function setGate(v){gate=Math.min(0.05,Math.max(0.001,Number(v)||0.008));}
  return {rms,estimatePitch,detectPitch,freqToNote,monitor,setGate,MIN_HZ,MAX_HZ};
})();
if(typeof module==='object'&&module.exports)module.exports=SVPitch;
