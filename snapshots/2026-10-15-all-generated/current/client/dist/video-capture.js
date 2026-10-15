/* Original camera/microphone capture. One stream and one recorder share the clock. */
(function(root,factory){'use strict';const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.SVVideoCapture=api;})(typeof globalThis==='object'?globalThis:this,function(){
  'use strict';
  class VideoCaptureError extends Error{constructor(code,message,cause){super(message);this.name='VideoCaptureError';this.code=code;this.causeName=cause?.name||null;}}
  function createVideoCapture(options={}){
    const env=options.environment||globalThis,devices=options.mediaDevices||env.navigator?.mediaDevices,Recorder=options.MediaRecorder||env.MediaRecorder,BlobType=options.Blob||env.Blob,now=options.now||(()=>env.performance?.now?.()??Date.now()),setTimer=options.setTimeout||env.setTimeout?.bind(env),clearTimer=options.clearTimeout||env.clearTimeout?.bind(env);let generation=0,pending=false,current=null,disposed=false,lastError=null;
    const stoppedTracks=new WeakSet();const error=(code,message,cause)=>new VideoCaptureError(code,message,cause),stopTracks=stream=>stream?.getTracks?.().forEach(track=>{if(stoppedTracks.has(track))return;stoppedTracks.add(track);try{track.stop();}catch{}}),report=()=>{try{options.onStatus?.(status());}catch{}};
    function status(){return {pending,recording:!!current,disposed,error:lastError?{code:lastError.code,message:lastError.message}:null};}
    async function start(settings={}){
      if(disposed)throw error('DISPOSED','Video recorder is closed');if(pending||current)throw error('BUSY','A recording is already pending or running');if(!devices?.getUserMedia||!Recorder||!BlobType)throw error('UNSUPPORTED','Camera recording is not supported by this browser');
      const at=++generation;pending=true;lastError=null;report();let stream,recorder,preview=settings.preview,run=null;
      const detachPreview=()=>{if(preview&&preview.srcObject===stream){try{preview.pause?.();}catch{}preview.srcObject=null;preview.hidden=true;}};
      try{
        stream=await devices.getUserMedia({video:{facingMode:{ideal:'user'},width:{ideal:1280,max:1280},height:{ideal:720,max:720},frameRate:{ideal:24,max:30}},audio:{echoCancellation:false,noiseSuppression:false,autoGainControl:false}});
        if(at!==generation||disposed){stopTracks(stream);throw error('CANCELLED','Video permission request was cancelled');}
        if(!stream.getVideoTracks?.().length||!stream.getAudioTracks?.().length){stopTracks(stream);throw error('MISSING_TRACK','Camera and microphone tracks are both required');}
        const mime=['video/webm;codecs=vp8,opus','video/webm;codecs=vp9,opus','video/mp4;codecs=avc1.42E01E,mp4a.40.2','video/mp4','video/webm'].find(type=>{try{return Recorder.isTypeSupported?.(type)===true;}catch{return false;}});
        recorder=mime?new Recorder(stream,{mimeType:mime,videoBitsPerSecond:2500000,audioBitsPerSecond:128000}):new Recorder(stream);
        const chunks=[];let settled=false,stoppedAt=null,startedAt=0,bytes=0,timer=null,stopTimeout=null,resolve,reject;
        const completed=new Promise((yes,no)=>{resolve=yes;reject=no;});completed.catch(()=>{});
        const cleanup=()=>{if(timer!==null)clearTimer?.(timer);if(stopTimeout!==null)clearTimer?.(stopTimeout);stopTracks(stream);detachPreview();if(current===run)current=null;report();};
        const failure=cause=>{if(settled)return;settled=true;lastError=cause instanceof VideoCaptureError?cause:error('RECORD_FAILED','Video recording did not complete',cause);try{if(recorder.state!=='inactive')recorder.stop();}catch{}cleanup();reject(lastError);};
        const requestStop=()=>{if(settled)return completed;if(stoppedAt===null){stoppedAt=now();try{if(recorder.state!=='inactive'){recorder.stop();if(!settled)stopTimeout=setTimer?.(()=>failure(error('STOP_TIMEOUT','Video recorder did not finish')),5000);}else failure(error('EMPTY_CAPTURE','Video recorder stopped without data'));}catch(cause){failure(cause);}}return completed;};
        run={source:'microphone',stream,stop:requestStop,cancel(){if(!settled)failure(error('CANCELLED','Video recording cancelled'));return {cancelled:true};}};
        recorder.ondataavailable=event=>{if(settled||!event.data?.size)return;bytes+=event.data.size;if(bytes>200*1024*1024){failure(error('SIZE_LIMIT','Video exceeded the 200 MB capture limit'));return;}chunks.push(event.data);};
        recorder.onerror=event=>failure(event.error||error('RECORD_FAILED','Video recording failed'));
        recorder.onstop=()=>{if(settled)return;settled=true;stoppedAt??=now();const blob=new BlobType(chunks,{type:recorder.mimeType||chunks[0]?.type||''}),duration=Math.max(0,(stoppedAt-startedAt)/1000);let size={};try{size=stream.getVideoTracks?.()[0]?.getSettings?.()||{};}catch{}if(!blob.size)lastError=error('EMPTY_CAPTURE','Video contains no recorded media');cleanup();if(!blob.size)reject(lastError);else resolve({blob,mime:blob.type,duration,source:'microphone',synchronization:'single-media-stream',width:size.width||null,height:size.height||null});};
        startedAt=now();current=run;try{recorder.start(1000);}catch(cause){failure(cause);throw lastError;}
        if(at!==generation||disposed){run.cancel();throw error('CANCELLED','Video recording cancelled');}
        if(preview){preview.muted=true;preview.playsInline=true;preview.hidden=false;preview.srcObject=stream;try{preview.play?.()?.catch?.(()=>{});}catch{}}
        timer=setTimer?.(()=>requestStop().catch(()=>{}),Math.min(Math.max(1000,options.maxDurationMs??600000),1800000));pending=false;report();return run;
      }catch(cause){stopTracks(stream);detachPreview();if(run&&current===run)run.cancel();const failure=cause instanceof VideoCaptureError?cause:error(cause?.name==='NotAllowedError'?'PERMISSION_DENIED':'START_FAILED','Video recording could not start',cause);if(at===generation)lastError=failure;throw failure;}
      finally{if(at===generation){pending=false;report();}}
    }
    function cancel(){generation++;pending=false;if(current)current.cancel();report();return {cancelled:true};}
    function dispose(){if(disposed)return;disposed=true;cancel();env.removeEventListener?.('pagehide',onHide);}
    function onHide(){cancel();}
    env.addEventListener?.('pagehide',onHide);
    return {start,cancel,dispose,status};
  }
  return {createVideoCapture,VideoCaptureError};
});
