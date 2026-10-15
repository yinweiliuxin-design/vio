/* Explicit offline preparation. This module never registers or downloads on load. */
'use strict';
(() => {
  const VERSION='20261014-integration3';
  const base=new URL('./',document.currentScript?.src||location.href);
  const supported=Boolean(navigator.serviceWorker&&typeof MessageChannel==='function'&&window.isSecureContext!==false);
  const listeners=new Set();
  let state={ready:false,supported,available:false,version:VERSION,cachedVersion:null,phase:'idle',completed:0,total:0,error:null,scope:base.href},pending=null,generation=0;
  const snapshot=()=>({...state});
  function update(values){
    state={...state,...values};const value=snapshot();
    for(const callback of listeners){try{callback(value);}catch(error){console.error(error);}}
    window.dispatchEvent(new CustomEvent('sv-offline-status',{detail:value}));
  }
  function subscribe(callback){if(typeof callback!=='function')throw TypeError('callback must be a function');listeners.add(callback);callback(snapshot());return ()=>listeners.delete(callback);}
  function ask(worker,type,timeout,options={}){
    return new Promise((resolve,reject)=>{
      const channel=new MessageChannel(),id=Date.now().toString(36)+'-'+Math.random().toString(36).slice(2);
      let settled=false;
      const timer=setTimeout(()=>finish(Error('离线准备超时，请联网后重试。')),timeout);
      function finish(error,value){if(settled)return;settled=true;clearTimeout(timer);channel.port1.close();if(error)reject(error);else resolve(value);}
      channel.port1.onmessage=event=>{
        const value=event.data;if(!value||value.id!==id)return;
        if(value.type==='SV_OFFLINE_PROGRESS'){update({phase:'downloading',completed:value.completed,total:value.total});return;}
        if(value.type==='SV_OFFLINE_RESULT')finish(null,value);
      };
      channel.port1.onmessageerror=()=>finish(Error('离线缓存状态读取失败。'));
      try{worker.postMessage({type,id,version:VERSION,...options},[channel.port2]);}catch(error){finish(error);}
    });
  }
  function activated(registration){
    const worker=registration.installing||registration.waiting||registration.active;
    if(!worker)return Promise.reject(Error('离线模块没有启动，请重试。'));
    if(worker.state==='activated')return Promise.resolve(worker);
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>finish(Error('离线模块启动超时，请重试。')),20000);
      function finish(error){clearTimeout(timer);worker.removeEventListener('statechange',changed);if(error)reject(error);else resolve(worker);}
      function changed(){if(worker.state==='activated')finish();else if(worker.state==='redundant')finish(Error('离线模块更新失败，请重试。'));}
      worker.addEventListener('statechange',changed);changed();
    });
  }
  function accept(result){
    const ready=result.ready===true&&result.version===VERSION;
    update({ready,available:result.available===true,cachedVersion:result.cachedVersion||null,phase:ready?'ready':result.error?'error':'idle',completed:result.completed||0,total:result.total||0,lastPreparedAt:result.completedAt||null,error:result.error||null});
    return ready?{ready:true}:{ready:false,...(result.error?{error:result.error}:{})};
  }
  function prepare(options={}){
    if(pending)return pending;
    generation++;
    pending=(async()=>{
      if(!supported){const error='当前浏览器不支持离线缓存。请使用 HTTPS 或本机 localhost 的完整浏览器。';update({ready:false,phase:'error',error});return {ready:false,error};}
      update({phase:'checking',error:null});
      try{
        // Re-entering offline mode must work without even fetching the worker script.
        if(options?.force!==true){
          const existing=await navigator.serviceWorker.getRegistration(base.href);
          if(existing?.active){const cached=await ask(existing.active,'SV_OFFLINE_STATUS',5000);if(cached.ready===true&&cached.version===VERSION)return accept(cached);}
        }
        update({phase:'registering',completed:0,total:0});
        const registration=await navigator.serviceWorker.register(new URL('sw.js?v='+VERSION,base).href,{scope:base.href,updateViaCache:'none'});
        const worker=await activated(registration);
        const result=await ask(worker,'SV_OFFLINE_PREPARE',180000,{force:options?.force===true});
        return accept(result);
      }catch(error){const message=error?.message||'离线缓存没有完成，请联网后重试。';update({ready:false,phase:'error',error:message});return {ready:false,error:message};}
    })().finally(()=>{pending=null;});
    return pending;
  }
  window.SVOffline=Object.freeze({prepare,status:snapshot,subscribe,version:VERSION});
  // Reading an existing registration/cache is local; it does not register, update or fetch.
  const probeGeneration=generation;
  if(supported)navigator.serviceWorker.getRegistration(base.href).then(async registration=>{
    if(!registration?.active||pending||generation!==probeGeneration)return;
    const result=await ask(registration.active,'SV_OFFLINE_STATUS',5000);
    if(!pending&&generation===probeGeneration)accept(result);
  }).catch(()=>{});
})();
