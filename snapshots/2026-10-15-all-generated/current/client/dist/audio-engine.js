/* SmartVio V12: original browser synthesis, local capture and playback.
 * No device connection, cloud upload, automatic permission request or UI. */
(function(root,factory){
  'use strict';
  const api=factory();
  if(typeof module==='object'&&module.exports)module.exports=api;
  else root.SVAudioEngine=api.createAudioEngine({environment:root});
})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  const PRESETS={
    Acoustic:{type:'triangle',filter:3200,attack:.008,level:.06},
    Warm:{type:'triangle',filter:1300,attack:.025,level:.06},
    Bright:{type:'triangle',filter:6800,attack:.004,level:.055},
    Electric:{type:'sawtooth',filter:2400,attack:.005,level:.04},
    Bass:{type:'sine',filter:600,attack:.01,level:.09},
    Piano:{type:'sine',filter:5200,attack:.002,level:.07},
    Organ:{type:'square',filter:900,attack:.09,level:.028},
    Strings:{type:'sawtooth',filter:1800,attack:.06,level:.05},
    Pad:{type:'triangle',filter:1700,attack:.12,level:.045}
  };
  class AudioEngineError extends Error{
    constructor(code,message,cause){super(message);this.name='AudioEngineError';this.code=code;this.causeName=cause?.name||null;}
  }
  const error=(code,message,cause)=>new AudioEngineError(code,message+(cause?.message?'：'+cause.message:''),cause);
  function createAudioEngine(options={}){
    const env=options.environment||(typeof globalThis==='object'?globalThis:{});
    const interval=options.setInterval||((fn,ms)=>env.setInterval(fn,ms));
    const cancel=options.clearInterval||(id=>env.clearInterval(id));
    const delay=options.setTimeout||((fn,ms)=>(env.setTimeout||setTimeout)(fn,ms)),clearDelay=options.clearTimeout||(id=>(env.clearTimeout||clearTimeout)(id));
    const clock=options.now||(()=>env.performance?.now?.()??Date.now());
    let context=null,graph=null,readyPromise=null,disposed=false,preset='Acoustic';
    let effects={volume:.65,reverb:.12,delay:0,compression:.2},inputGain=1;
    let sequence=null,playGeneration=0,metro=null,metroGeneration=0,chordRun=null,chordGeneration=0;
    let loopGeneration=0,loopNodes=[],tuner=null,tunerGeneration=0,captureGeneration=0,referenceGeneration=0,lastError=null;
    const voices=new Set(),captures=new Set();
    const unit=(v,name)=>{if(typeof v!=='number'||!Number.isFinite(v)||v<0||v>1)throw error('INVALID_VALUE',name+'必须为0至1');return v;};
    const tempo=bpm=>{if(!Number.isFinite(bpm)||bpm<30||bpm>240)throw error('INVALID_VALUE','速度必须为30至240 BPM');return bpm;};
    const disconnect=node=>{try{node?.disconnect();}catch{}};
    const stopTracks=stream=>stream?.getTracks?.().forEach(track=>track.stop());
    const param=(p,value)=>{if(p.setTargetAtTime)p.setTargetAtTime(value,context.currentTime,.02);else p.value=value;};
    function applyEffects(){
      if(!graph)return;
      param(graph.output.gain,effects.volume);param(graph.reverbWet.gain,effects.reverb*.6);
      param(graph.delayWet.gain,effects.delay*.45);param(graph.feedback.gain,effects.delay*.4);
      param(graph.compressor.threshold,-6-30*effects.compression);param(graph.compressor.ratio,1+11*effects.compression);
    }
    function makeGraph(ctx){
      const mix=ctx.createGain(),compressor=ctx.createDynamicsCompressor(),output=ctx.createGain(),analyser=ctx.createAnalyser();
      const reverb=ctx.createConvolver(),reverbWet=ctx.createGain(),delay=ctx.createDelay(1),delayWet=ctx.createGain(),feedback=ctx.createGain();
      analyser.fftSize=1024;delay.delayTime.value=.28;compressor.attack.value=.006;compressor.release.value=.2;
      const length=Math.round(ctx.sampleRate*1.6),impulse=ctx.createBuffer(2,length,ctx.sampleRate);
      for(let ch=0;ch<2;ch++){const data=impulse.getChannelData(ch);for(let i=0;i<length;i++)data[i]=(Math.random()*2-1)*Math.pow(1-i/length,2.4);}
      reverb.buffer=impulse;mix.connect(compressor);compressor.connect(output);
      compressor.connect(reverb);reverb.connect(reverbWet);reverbWet.connect(output);
      compressor.connect(delay);delay.connect(delayWet);delayWet.connect(output);delay.connect(feedback);feedback.connect(delay);
      output.connect(analyser);analyser.connect(ctx.destination);
      return {mix,compressor,output,analyser,reverb,reverbWet,delay,delayWet,feedback};
    }
    async function ready(){
      if(disposed)throw error('DISPOSED','音频引擎已关闭');
      if(context?.state==='closed'){Object.values(graph||{}).forEach(disconnect);graph=null;context=null;readyPromise=null;}
      if(!readyPromise)readyPromise=(async()=>{
        const Constructor=options.AudioContext||env.AudioContext||env.webkitAudioContext;
        if(!Constructor)throw error('UNSUPPORTED','当前浏览器不支持Web Audio');
        const ctx=new Constructor({latencyHint:'interactive'});context=ctx;
        try{graph=makeGraph(ctx);applyEffects();await ctx.resume();if(disposed)throw error('DISPOSED','音频引擎已关闭');if(ctx.state!=='running')throw error('AUDIO_NOT_RUNNING','浏览器音频尚未运行，请再次点击启动');return ctx;}
        catch(cause){Object.values(graph||{}).forEach(disconnect);graph=null;context=null;await ctx.close().catch(()=>{});throw error('AUDIO_START_FAILED','音频未启动',cause);}
      })();
      try{const ctx=await readyPromise;if(ctx.state!=='running')await ctx.resume();if(disposed)throw error('DISPOSED','音频引擎已关闭');if(ctx.state!=='running')throw error('AUDIO_NOT_RUNNING','浏览器音频尚未运行，请再次点击启动');applyEffects();lastError=null;return ctx;}
      catch(cause){if(!context)readyPromise=null;lastError=cause;throw cause;}
    }
    function setPreset(name){if(!Object.prototype.hasOwnProperty.call(PRESETS,name))throw error('INVALID_PRESET','未知浏览器合成音色');preset=name;return {name,source:'browser-synthesis'};}
    function setEffects(update){
      if(!update||typeof update!=='object'||Array.isArray(update))throw error('INVALID_VALUE','音效参数必须为对象');
      const next={...effects};for(const key of Object.keys(update)){if(!(key in next))throw error('INVALID_VALUE','未知音效参数');next[key]=unit(update[key],key);}
      effects=next;applyEffects();return {...effects};
    }
    function setInputGain(value){
      if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>2)throw error('INVALID_VALUE','麦克风输入增益必须为0至2');
      inputGain=value;for(const capture of captures)if(capture.inputGain&&context)param(capture.inputGain.gain,value);return value;
    }
    function stringTone(hz,start,length,style,velocity){
      if(voices.size>=24)throw error('VOICE_LIMIT','请先停止声音再添加新音符');
      const osc=context.createOscillator(),filter=context.createBiquadFilter(),gain=context.createGain();
      if(context.createPeriodicWave&&osc.setPeriodicWave){const real=new Float32Array(17),imag=new Float32Array(17);for(let h=1;h<17;h++)imag[h]=1/Math.pow(h,style==='pluck'?1.6:1.05);osc.setPeriodicWave(context.createPeriodicWave(real,imag));}else osc.type='triangle';
      osc.frequency.value=hz;filter.type='lowpass';filter.frequency.value=style==='pluck'?1900:3200;filter.Q.value=.5;
      const attack=style==='sustain'?.08:.006,peak=.08*Math.pow(velocity,.8);gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(peak,start+attack);
      if(style==='pluck')gain.gain.exponentialRampToValueAtTime(.0001,start+length);else{gain.gain.setValueAtTime(peak,start+length*.7);gain.gain.linearRampToValueAtTime(0,start+length);}
      osc.connect(filter);filter.connect(gain);gain.connect(graph.mix);const voice={osc,nodes:[osc,filter,gain],category:'strings'};voices.add(voice);osc.onended=()=>{voice.nodes.forEach(disconnect);voices.delete(voice);};
      try{osc.start(start);osc.stop(start+length+.01);}catch(cause){voice.nodes.forEach(disconnect);voices.delete(voice);throw cause;}
    }
    const stringParameters=(style,velocity)=>{if(!['sustain','short','pluck'].includes(style)||typeof velocity!=='number'||!Number.isFinite(velocity)||velocity<.1||velocity>1)throw error('INVALID_VALUE','弦乐奏法或力度无效');};
    async function playStringNote(note,style='sustain',velocity=.65){
      stringParameters(style,velocity);const match=/^([A-G])([#b]?)([3-7])$/.exec(note||'');if(!match)throw error('INVALID_VALUE','弦乐音高无效');const midi=12*(Number(match[3])+1)+{C:0,D:2,E:4,F:5,G:7,A:9,B:11}[match[1]]+(match[2]==='#'?1:match[2]==='b'?-1:0);if(midi<55||midi>100)throw error('INVALID_VALUE','弦乐音域无效');
      const generation=referenceGeneration,ctx=await ready();if(disposed||generation!==referenceGeneration)return {started:false,cancelled:true};stringTone(440*2**((midi-69)/12),ctx.currentTime+.02,style==='short'?.22:style==='pluck'?.8:1.3,style,velocity);return {started:true,source:'original-string-synthesis'};
    }
    async function stringChord(name,style='sustain',bpm=80,velocity=.65){
      stringParameters(style,velocity);const frequencies=chordFrequencies(name);tempo(bpm);stopChord();const generation=chordGeneration,ctx=await ready();if(disposed||generation!==chordGeneration)return {started:false,cancelled:true};
      const beat=60/bpm,run={next:ctx.currentTime+.03,step:0,timer:null};chordRun=run;
      const tick=()=>{try{if(run.next<ctx.currentTime-.5)run.next=ctx.currentTime+.02;while(run.next<ctx.currentTime+.12){if(style==='pluck')stringTone(frequencies[run.step%frequencies.length]*2,run.next,beat*.8,style,velocity);else frequencies.forEach(hz=>stringTone(hz*2,run.next,style==='short'?beat*.3:beat*1.8,style,velocity*.7));run.next+=style==='sustain'?beat*2:beat;run.step++;}}
        catch(cause){lastError=error('STRINGS_FAILED','弦乐伴奏未能继续播放',cause);stopChord();stopVoices('strings');return lastError;}};
      const failure=tick();if(failure)throw failure;run.timer=interval(tick,30);return {started:true,source:'original-string-synthesis'};
    }
    function tone(hz,start,length,category,level){
      if(hz===0)return;
      if(voices.size>=64)throw error('VOICE_LIMIT','合成声音超过64个，请先停止播放或缩短片段');
      const p=PRESETS[preset],osc=context.createOscillator(),filter=context.createBiquadFilter(),gain=context.createGain();
      osc.type=p.type;osc.frequency.value=hz;filter.type='lowpass';filter.frequency.value=p.filter;filter.Q.value=.7;
      const attack=Math.min(p.attack,length*.3),amount=level??p.level;
      gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(amount,start+attack);
      gain.gain.setValueAtTime(amount,Math.max(start+attack,start+length-.03));gain.gain.linearRampToValueAtTime(0,start+length);
      osc.connect(filter);filter.connect(gain);gain.connect(graph.mix);
      const voice={osc,nodes:[osc,filter,gain],category};voices.add(voice);
      osc.onended=()=>{voice.nodes.forEach(disconnect);voices.delete(voice);};
      try{osc.start(start);osc.stop(start+length+.01);}catch(cause){voice.nodes.forEach(disconnect);voices.delete(voice);throw cause;}
    }
    function stopVoices(category){for(const voice of [...voices])if(!category||voice.category===category){try{voice.osc.stop();}catch{}voice.nodes.forEach(disconnect);voices.delete(voice);}}
    function stopSequence(){playGeneration++;if(sequence){cancel(sequence.timer);sequence=null;}stopVoices('score');}
    async function play(plan,settings={}){
      if(!Array.isArray(plan)||!plan.length||plan.length>4096)throw error('INVALID_PLAN','曲谱计划为空或过长');
      const notes=plan.map((note,index)=>{
        if(!Number.isFinite(note.start)||!Number.isFinite(note.end)||note.start<0||note.end-note.start<.01||!Number.isFinite(note.freq)||note.freq<0||note.freq>20000)throw error('INVALID_PLAN','曲谱音符时间或频率无效');
        return {...note,i:note.i??index};
      }).sort((a,b)=>a.start-b.start);
      const duration=Math.max(...notes.map(n=>n.end));if(duration>7200)throw error('INVALID_PLAN','片段超过两小时');
      stopSequence();const generation=playGeneration,ctx=await ready();if(generation!==playGeneration)return {started:false,cancelled:true};
      const run={base:ctx.currentTime+.04,cursor:0,cycle:0,duration,loop:!!settings.loop,timer:null};sequence=run;
      const frame=()=>{
        if(sequence!==run)return;
        try{
          const elapsed=Math.max(0,ctx.currentTime-run.base);
          if(!run.loop&&ctx.currentTime>=run.base+duration){settings.onPosition?.(-1,duration,duration);stopSequence();settings.onEnd?.();return;}
          if(run.loop&&elapsed>(run.cycle+1)*duration){run.cycle=Math.floor(elapsed/duration);run.cursor=0;}
          const time=run.loop?elapsed%duration:Math.min(duration,elapsed);
          const active=notes.find(note=>note.start<=time&&note.end>time);
          settings.onPosition?.(active?.i??-1,time,duration);
          const horizon=ctx.currentTime+.18;let count=0;
          while(run.cursor<notes.length&&run.base+run.cycle*duration+notes[run.cursor].start<horizon){
            const note=notes[run.cursor],start=run.base+run.cycle*duration+note.start,end=run.base+run.cycle*duration+note.end;
            if(end>ctx.currentTime)tone(note.freq,Math.max(start,ctx.currentTime),end-Math.max(start,ctx.currentTime),'score');
            run.cursor++;
            if(run.cursor===notes.length){if(!run.loop)break;run.cursor=0;run.cycle++;}
            if(++count>4096)throw error('INVALID_PLAN','曲谱调度密度过高');
          }
        }catch(cause){const failure=cause instanceof AudioEngineError?cause:error('PLAYBACK_FAILED','合成播放失败',cause);lastError=failure;stopSequence();settings.onError?.(failure);settings.onEnd?.({error:failure});return failure;}
      };
      run.timer=interval(frame,25);const failure=frame();if(failure)throw failure;
      return {started:true,duration,source:'browser-synthesis'};
    }
    function stopMetronome(){metroGeneration++;if(metro){cancel(metro.timer);metro=null;}stopVoices('metro');}
    async function metronome(bpm,beats=4,denominator=4){
      tempo(bpm);if(!Number.isInteger(beats)||beats<1||beats>12)throw error('INVALID_VALUE','拍号必须为1至12');
      if(![2,4,8,16].includes(denominator))throw error('INVALID_VALUE','拍号分母须为2、4、8或16');
      stopMetronome();const generation=metroGeneration,ctx=await ready();if(generation!==metroGeneration)return {started:false,cancelled:true};
      const run={next:ctx.currentTime+.04,beat:0,timer:null};metro=run;
      const tick=()=>{try{const beat=60/bpm*4/denominator;if(run.next<ctx.currentTime-.5){const skipped=Math.floor((ctx.currentTime-run.next)/beat);run.beat+=skipped;run.next+=skipped*beat;}while(run.next<ctx.currentTime+.12){if(run.next>=ctx.currentTime)tone(run.beat%beats?900:1400,run.next,.04,'metro',.08);run.beat++;run.next+=beat;}}
        catch(cause){lastError=error('METRONOME_FAILED','节拍器未能继续播放',cause);stopMetronome();return lastError;}};
      const failure=tick();if(failure)throw failure;run.timer=interval(tick,30);return {started:true,bpm,beats,denominator,source:'browser-synthesis'};
    }
    function chordFrequencies(name){
      const match=/^([A-G])([#b]?)(maj7|m7|m|7|sus2|sus4|dim)?$/.exec(name);
      if(!match)throw error('INVALID_CHORD','不支持的和弦名称');
      const chromatic={C:0,D:2,E:4,F:5,G:7,A:9,B:11},key=chromatic[match[1]]+(match[2]==='#'?1:match[2]==='b'?-1:0);
      const steps={m:[0,3,7],m7:[0,3,7,10],maj7:[0,4,7,11],'7':[0,4,7,10],sus2:[0,2,7],sus4:[0,5,7],dim:[0,3,6]}[match[3]]||[0,4,7];
      return steps.map(step=>440*Math.pow(2,(48+key+step-69)/12));
    }
    function stopChord(){chordGeneration++;if(chordRun){cancel(chordRun.timer);chordRun=null;}stopVoices('chord');stopVoices('strings');}
    async function chord(name,style='arp',bpm=80){
      const frequencies=chordFrequencies(name);tempo(bpm);if(!['strum','arp','pad'].includes(style))throw error('INVALID_VALUE','伴奏方式须为strum、arp或pad');
      stopChord();const generation=chordGeneration,ctx=await ready();if(generation!==chordGeneration)return {started:false,cancelled:true};
      const beat=60/bpm,run={next:ctx.currentTime+.04,step:0,timer:null};chordRun=run;
      const tick=()=>{try{if(run.next<ctx.currentTime-.5)run.next=ctx.currentTime+.02;while(run.next<ctx.currentTime+.12){
        if(style==='arp')tone(frequencies[run.step%frequencies.length],run.next,beat*.45,'chord',.04);
        else frequencies.forEach((hz,i)=>tone(hz,run.next+(style==='strum'?i*.016:0),style==='pad'?beat*1.9:beat*.45,'chord',.03));
        run.next+=style==='pad'?beat*2:beat/2;run.step++;
      }}catch(cause){lastError=error('CHORD_FAILED','和弦伴奏未能继续播放',cause);stopChord();return lastError;}};
      const failure=tick();if(failure)throw failure;run.timer=interval(tick,30);return {started:true,name,style,source:'browser-synthesis'};
    }
    async function reference(hz){if(!Number.isFinite(hz)||hz<20||hz>12000)throw error('INVALID_VALUE','参考频率无效');const generation=++referenceGeneration;await ready();if(generation!==referenceGeneration)return {started:false,cancelled:true};stopVoices('reference');tone(hz,context.currentTime+.02,1.5,'reference',.07);return {started:true,frequency:hz,source:'browser-synthesis'};}
    function releaseLoopRows(rows){for(const item of rows){try{item.source.stop();}catch{}disconnect(item.source);disconnect(item.gain);}}
    function stopLoops(){loopGeneration++;releaseLoopRows(loopNodes);loopNodes=[];}
    function setLoopLevels(levels=[],mutes=[]){for(const item of loopNodes){const level=levels[item.slot]??.7;unit(level,'轨道音量');if(mutes[item.slot]!==undefined&&typeof mutes[item.slot]!=='boolean')throw error('INVALID_VALUE','静音状态必须为布尔值');param(item.gain.gain,mutes[item.slot]?0:level);}return loopNodes.length;}
    async function playLoops(records,levels=[],mutes=[],settings={}){
      if(!Array.isArray(records)||records.length>4)throw error('INVALID_LOOP','最多播放四轨');
      if(!settings||typeof settings!=='object'||Array.isArray(settings))throw error('INVALID_VALUE','循环设置无效');
      const slots=new Set();for(const row of records){if(!row||row.completed!==true||row.kind!=='loop'||!Number.isInteger(row.trackIndex)||row.trackIndex<0||row.trackIndex>3||slots.has(row.trackIndex)||!row.blob?.size||typeof row.blob.arrayBuffer!=='function')throw error('INVALID_LOOP','循环轨未完成、无音频或轨号重复');if(row.blob.size>16*1024*1024)throw error('LOOP_RESOURCE_LIMIT','单条循环音频最多16MB，请缩短录音');if(row.duration!==undefined&&(!Number.isFinite(row.duration)||row.duration<0))throw error('INVALID_LOOP','循环录音时长信息无效');if(Number.isFinite(row.duration)&&row.duration>120)throw error('LOOP_RESOURCE_LIMIT','循环录音最多120秒，请缩短录音');slots.add(row.trackIndex);unit(levels[row.trackIndex]??.7,'轨道音量');if(mutes[row.trackIndex]!==undefined&&typeof mutes[row.trackIndex]!=='boolean')throw error('INVALID_VALUE','静音状态必须为布尔值');}
      const generation=++loopGeneration,ctx=await ready(),decoded=[];let decodedSamples=0;
      try{for(const row of records){
        if(generation!==loopGeneration)return {started:false,cancelled:true,count:0};
        const bytes=await row.blob.arrayBuffer();if(generation!==loopGeneration)return {started:false,cancelled:true,count:0};if(!Number.isFinite(bytes?.byteLength)||!bytes.byteLength||bytes.byteLength>16*1024*1024)throw error('LOOP_RESOURCE_LIMIT','循环音频内容超过16MB上限');
        const buffer=await ctx.decodeAudioData(bytes.slice(0));if(generation!==loopGeneration)return {started:false,cancelled:true,count:0};
        if(!Number.isFinite(buffer.duration)||buffer.duration<=0||!Number.isInteger(buffer.length)||buffer.length<1||!Number.isInteger(buffer.numberOfChannels)||buffer.numberOfChannels<1)throw error('DECODE_FAILED','循环音频时长或格式无效');
        if(buffer.duration>120)throw error('LOOP_RESOURCE_LIMIT','解码后的循环录音最多120秒，请缩短录音');
        decodedSamples+=buffer.length*buffer.numberOfChannels;if(decodedSamples>12000000)throw error('LOOP_RESOURCE_LIMIT','循环音频解码样本超过预算，请缩短录音');decoded.push({row,buffer});
      }}catch(cause){lastError=cause instanceof AudioEngineError?cause:error('DECODE_FAILED','循环音频解码失败，旧循环保留',cause);throw lastError;}
      let playback=decoded,alignedDuration=null;
      if(settings.alignLength){
        const bpm=tempo(settings.bpm),meter=/^(\d{1,2})\/(2|4|8|16)$/.exec(settings.meter||''),bars=settings.barCount;
        if(!meter||Number(meter[1])<1||Number(meter[1])>12||!Number.isInteger(bars)||bars<1||bars>128)throw error('INVALID_VALUE','循环工程长度无效');
        alignedDuration=60/bpm*Number(meter[1])*4/Number(meter[2])*bars;
        if(alignedDuration>120)throw error('LOOP_RESOURCE_LIMIT','按工程长度循环最多120秒，请缩短工程');
        const frames=Math.round(alignedDuration*ctx.sampleRate),samples=decoded.reduce((total,item)=>total+frames*Math.min(2,item.buffer.numberOfChannels),0);
        if(samples>12000000)throw error('LOOP_RESOURCE_LIMIT','循环缓冲区过大，请缩短工程');
        playback=decoded.map(item=>{const channels=Math.min(2,item.buffer.numberOfChannels),buffer=ctx.createBuffer(channels,frames,ctx.sampleRate);for(let ch=0;ch<channels;ch++)buffer.getChannelData(ch).set(item.buffer.getChannelData(ch).subarray(0,frames));return {...item,buffer};});
      }
      const start=ctx.currentTime+.05,nextNodes=[];
      try{for(const {row,buffer} of playback){const source=ctx.createBufferSource(),gain=ctx.createGain();nextNodes.push({source,gain,slot:row.trackIndex});source.buffer=buffer;source.loop=true;source.loopStart=0;source.loopEnd=buffer.duration;gain.gain.value=mutes[row.trackIndex]?0:(levels[row.trackIndex]??.7);source.connect(gain);gain.connect(graph.mix);source.start(start);}}
      catch(cause){releaseLoopRows(nextNodes);throw error('LOOP_START_FAILED','新循环未启动，旧循环保留',cause);}
      releaseLoopRows(loopNodes);loopNodes=nextNodes;
      return {started:!!decoded.length,count:decoded.length,startTime:start,alignedDuration,source:'recorded-blobs'};
    }
    async function startCapture(source,limits={}){
      if(!['microphone','synth'].includes(source))throw error('INVALID_SOURCE','录音来源须为microphone或synth');
      if(!limits||typeof limits!=='object'||Array.isArray(limits)||Object.keys(limits).some(key=>key!=='maxDurationMs'))throw error('INVALID_VALUE','录音设置无效');
      const globalDuration=options.maxCaptureDurationMs??600000,maxBytes=options.maxCaptureBytes??200*1024*1024,stopDeadline=options.captureStopTimeoutMs??5000,maxDuration=limits.maxDurationMs??globalDuration;
      if(!Number.isFinite(globalDuration)||globalDuration<1||globalDuration>1800000||!Number.isFinite(maxDuration)||maxDuration<1||maxDuration>globalDuration||!Number.isFinite(maxBytes)||maxBytes<1||maxBytes>200*1024*1024||!Number.isFinite(stopDeadline)||stopDeadline<1||stopDeadline>10000)throw error('INVALID_VALUE','录音资源上限无效');
      const Recorder=options.MediaRecorder||env.MediaRecorder,BlobType=options.Blob||env.Blob;
      if(!Recorder||!BlobType)throw error('UNSUPPORTED','当前浏览器不支持录音');
      const generation=captureGeneration,ctx=await ready();let stream,rawStream,destination,meterSource,meter,recorder,captureGain;
      try{
        if(generation!==captureGeneration||disposed)throw error('CANCELLED','录音请求已取消');
        if(source==='microphone'){
          const devices=options.mediaDevices||env.navigator?.mediaDevices;if(!devices?.getUserMedia)throw error('UNSUPPORTED','当前浏览器不支持麦克风');
          stream=await devices.getUserMedia({audio:true});
          if(generation!==captureGeneration||disposed){stopTracks(stream);throw error('CANCELLED','录音请求已取消');}
          rawStream=stream;meterSource=ctx.createMediaStreamSource(stream);meter=ctx.createAnalyser();meter.fftSize=1024;captureGain=ctx.createGain();captureGain.gain.value=inputGain;destination=ctx.createMediaStreamDestination();meterSource.connect(captureGain);captureGain.connect(meter);captureGain.connect(destination);stream=destination.stream;
        }else{destination=ctx.createMediaStreamDestination();graph.output.connect(destination);stream=destination.stream;}
        const mime=['audio/webm;codecs=opus','audio/ogg;codecs=opus','audio/mp4'].find(type=>Recorder.isTypeSupported?.(type));
        recorder=mime?new Recorder(stream,{mimeType:mime}):new Recorder(stream);
        let resolve,reject,finished=false,requestedAt=null,limitTimer=null,stopTimer=null,totalBytes=0;const chunks=[],startedAt=clock();
        const finishedPromise=new Promise((yes,no)=>{resolve=yes;reject=no;});finishedPromise.catch(()=>{});
        const capture={source,recorder,meter,inputGain:captureGain,finished:finishedPromise,stop(){if(!finished&&requestedAt===null){requestedAt=clock();stopTimer=delay(()=>fail(error('CAPTURE_TIMEOUT','录音收尾超时，未保存不完整文件')),stopDeadline);try{if(recorder.state!=='inactive')recorder.stop();}catch(cause){fail(cause);}}return finishedPromise;}};
        const cleanup=()=>{clearDelay(limitTimer);clearDelay(stopTimer);limitTimer=stopTimer=null;stopTracks(stream);stopTracks(rawStream);disconnect(meterSource);disconnect(meter);disconnect(captureGain);if(destination){try{graph?.output.disconnect(destination);}catch{}disconnect(destination);}captures.delete(capture);};
        const fail=cause=>{if(finished)return;finished=true;lastError=error('CAPTURE_FAILED','录音未完成',cause);cleanup();try{if(recorder.state!=='inactive')recorder.stop();}catch{}reject(lastError);};
        recorder.ondataavailable=event=>{if(finished||!event.data?.size)return;totalBytes+=event.data.size;if(totalBytes>maxBytes){fail(error('CAPTURE_LIMIT','录音超过文件大小上限，未保存不完整文件'));return;}chunks.push(event.data);};
        recorder.onerror=event=>fail(event.error||event);
        recorder.onstop=()=>{if(finished)return;finished=true;const mimeType=recorder.mimeType||chunks[0]?.type||'';const blob=new BlobType(chunks,{type:mimeType});const duration=Math.max(0,((requestedAt??clock())-startedAt)/1000);cleanup();if(!blob.size){const cause=error('EMPTY_CAPTURE','录音没有可用音频数据');lastError=cause;reject(cause);}else resolve({blob,mime:blob.type,duration,source});};
        captures.add(capture);try{recorder.start(1000);limitTimer=delay(()=>capture.stop(),maxDuration);}catch(cause){fail(cause);throw lastError;}return capture;
      }catch(cause){stopTracks(stream);stopTracks(rawStream);disconnect(meterSource);disconnect(meter);disconnect(captureGain);if(destination){try{graph?.output.disconnect(destination);}catch{}disconnect(destination);}if(cause instanceof AudioEngineError)throw cause;lastError=error('CAPTURE_START_FAILED','未开始录音',cause);throw lastError;}
    }
    function stopTuner(){tunerGeneration++;if(tuner){tuner.alive=false;try{tuner.monitor?.stop();}catch{}stopTracks(tuner.stream);tuner=null;}}
    async function startTuner(callback){
      if(typeof callback!=='function')throw error('INVALID_VALUE','调音需要回调函数');
      const pitch=options.pitch||(typeof SVPitch!=='undefined'?SVPitch:env.SVPitch),devices=options.mediaDevices||env.navigator?.mediaDevices;
      if(!pitch?.monitor||!devices?.getUserMedia)throw error('UNSUPPORTED','当前环境不支持麦克风调音');
      stopTuner();const generation=tunerGeneration;let stream,monitor;
      try{stream=await devices.getUserMedia({audio:true});if(generation!==tunerGeneration||disposed){stopTracks(stream);throw error('CANCELLED','调音请求已取消');}
        const run={stream,monitor:null,alive:true};tuner=run;
        monitor=pitch.monitor(stream,(hz,meta)=>{if(run.alive&&tuner===run)callback(hz,meta);});run.monitor=monitor;
        if(monitor.context?.state==='suspended')await monitor.context.resume();
        if(generation!==tunerGeneration||disposed){run.alive=false;monitor.stop();stopTracks(stream);throw error('CANCELLED','调音请求已取消');}
        return {source:'microphone',stop:stopTuner};
      }catch(cause){try{monitor?.stop();}catch{}stopTracks(stream);if(tuner?.stream===stream)tuner=null;lastError=cause instanceof AudioEngineError?cause:error('TUNER_START_FAILED','麦克风调音未启动',cause);throw lastError;}
    }
    function getLevel(){
      const analysers=[graph?.analyser,...[...captures].map(capture=>capture.meter)].filter(Boolean);let rms=0;
      for(const analyser of analysers){const data=new Float32Array(analyser.fftSize);analyser.getFloatTimeDomainData(data);let sum=0;for(const value of data)sum+=value*value;rms=Math.max(rms,Math.sqrt(sum/data.length));}
      return Math.min(1,Number.isFinite(rms)?rms:0);
    }
    function stop(){referenceGeneration++;stopSequence();stopMetronome();stopChord();stopLoops();stopVoices();if(graph&&context){graph.output.gain.cancelScheduledValues?.(context.currentTime);graph.output.gain.setValueAtTime(0,context.currentTime);}}
    async function dispose(){if(disposed)return;disposed=true;captureGeneration++;stop();stopTuner();await Promise.allSettled([...captures].map(capture=>capture.stop()));Object.values(graph||{}).forEach(disconnect);graph=null;if(context)await context.close();context=null;}
    function status(){return {ready:!!context,state:context?.state||'not-started',preset,effects:{...effects},inputGain,playing:!!sequence,metronome:!!metro,chord:!!chordRun,loops:loopNodes.length,captures:captures.size,tuning:!!tuner,source:'browser-synthesis',baseLatency:Number.isFinite(context?.baseLatency)?context.baseLatency:null,outputLatency:Number.isFinite(context?.outputLatency)?context.outputLatency:null,error:lastError?{code:lastError.code,message:lastError.message}:null};}
    return {ready,setPreset,setEffects,setInputGain,playStringNote,stringChord,play,stop,reference,metronome,stopMetronome,chord,stopChord,startCapture,startTuner,stopTuner,playLoops,stopLoops,setLoopLevels,getLevel,status,dispose,presets:Object.keys(PRESETS)};
  }
  return {createAudioEngine,AudioEngineError,PRESETS};
});
