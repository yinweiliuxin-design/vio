/* Same-origin app assets only. User records, media, accounts and API traffic are never cached. */
'use strict';
const VERSION='20261015-v16-1',PREFIX='smartvio-static-v1-',FINAL=PREFIX+VERSION;
const BASE=new URL('./',self.location.href);
const FILES=Object.freeze([
  'index.html','client.html','style.css','lucide.min.js','seed.js','i18n.js','common.js',
  'pitch.js','score-model.js','media-store.js','audio-engine.js','client.js','offline.js','sw.js',
  'midi.js','video-capture.js','device-bridge.js','performance.js','preset-cloud.js','preset-cloud.css','community.js','community.css','tutorial.js','tutorial.css','learning-path.js','learning-path.css','favicon.svg','violin.png','module.png',
  ...['A3','E4','A4','E5','A5','E6','A6'].map(note=>'assets/audio/violin/'+note+'.wav'),'assets/audio/violin/manifest.json','assets/audio/violin/LICENSE.txt',
  'brands/silvio-wordmark.png','brands/vellen-wordmark.png','icons/icon-192.png','icons/icon-512.png','icons/apple-touch-icon.png',
  'manifest.webmanifest','manifest-en.webmanifest','manifest-ja.webmanifest','manifest-zh.webmanifest','manifest-de.webmanifest',
  'manifest-vellen-en.webmanifest','manifest-vellen-ja.webmanifest','manifest-vellen-zh.webmanifest','manifest-vellen-de.webmanifest',
  ...Array.from({length:35},(_,i)=>'covers/s'+String(i+1).padStart(3,'0')+'.jpg'),
  ...['welcome','tuner','listen','phrase','record','confidence'].map(name=>'learning/'+name+'.jpg')
]);
const allowed=new Set(FILES.map(file=>new URL(file,BASE).pathname));
const marker=version=>new URL('__sv_offline_complete__?v='+encodeURIComponent(version),BASE).href;
let preparation=null;
const progressPorts=new Set();
function send(port,message){try{port?.postMessage(message);}catch{}}
function isAsset(value){const url=new URL(value,BASE);return url.origin===BASE.origin&&allowed.has(url.pathname)&&[...url.searchParams.keys()].every(key=>key==='v')&&(!url.search||/^[A-Za-z0-9._-]{1,80}$/.test(url.searchParams.get('v')||''));}
async function completeCache(name){
  if(!name.startsWith(PREFIX)||name.includes('-staging-'))return null;
  const version=name.slice(PREFIX.length).split('-generation-')[0],cache=await caches.open(name),response=await cache.match(marker(version));
  if(!response)return null;
  try{
    const data=await response.json();
    if(data.version!==version||data.schema!==1||!Array.isArray(data.files)||!data.files.length||data.files.some(value=>!isAsset(value)))return null;
    if(version===VERSION&&FILES.some(file=>!data.files.includes(new URL(file,BASE).href)))return null;
    for(const file of data.files)if(!await cache.match(file))return null;
    return {cache,data};
  }catch{return null;}
}
async function bestCache(){
  const candidates=[];
  for(const name of await caches.keys()){const value=await completeCache(name);if(value)candidates.push(value);}
  return candidates.sort((a,b)=>Number(b.data.version===VERSION)-Number(a.data.version===VERSION)||String(b.data.completedAt).localeCompare(String(a.data.completedAt)))[0]||null;
}
async function status(){
  try{
    const best=await bestCache(),data=best?.data;
    return {version:VERSION,ready:data?.version===VERSION,available:Boolean(best),cachedVersion:data?.version||null,completed:data?.files.length||0,total:data?.files.length||0,completedAt:data?.completedAt||null};
  }catch(error){return {version:VERSION,ready:false,available:false,cachedVersion:null,error:error?.message||'浏览器未允许读取离线缓存。'};}
}
async function checkedFetch(url){
  const response=await fetch(url,{cache:'reload',credentials:'same-origin',redirect:'follow'});
  if(!response.ok||response.type==='opaque'||new URL(response.url||url).origin!==BASE.origin)throw Error('静态资源下载失败：'+new URL(url).pathname.split('/').pop());
  const pathname=new URL(url).pathname,type=response.headers.get('content-type')||'';
  if(/\.html$/.test(pathname)){
    const html=await response.clone().text();
    if(!/text\/html/i.test(type)||!/(?:id=["']main["'])/.test(html)||!/\bclient\.js\b/.test(html))throw Error('入口未返回琴房页面，请先联网打开入口并完成站点访问。');
  }else if(/\.(?:js|css)$/.test(pathname)){
    const text=await response.clone().text();
    if(!(/\.js$/.test(pathname)?/(?:java|ecma)script/i.test(type):/text\/css/i.test(type))||/^\s*</.test(text))throw Error('脚本或样式未下载完整：'+pathname.split('/').pop());
  }else if(/\.webmanifest$/.test(pathname)){
    const data=await response.clone().json();if(typeof data.start_url!=='string')throw Error('应用清单未下载完整。');
  }else if(/\.png$/.test(pathname)){
    const bytes=new Uint8Array(await response.clone().arrayBuffer());if(bytes.length<8||![137,80,78,71,13,10,26,10].every((byte,i)=>bytes[i]===byte))throw Error('图片未下载完整：'+pathname.split('/').pop());
  }else if(/\.jpg$/.test(pathname)){
    const bytes=new Uint8Array(await response.clone().arrayBuffer());if(!/image\/jpeg/i.test(type)||bytes.length<4||bytes[0]!==255||bytes[1]!==216||bytes[2]!==255)throw Error('图片未下载完整：'+pathname.split('/').pop());
  }else if(/\.svg$/.test(pathname)&&!/<svg\b/i.test(await response.clone().text()))throw Error('图标未下载完整。');
  return response;
}
async function build(force){
  const existing=await bestCache();if(existing?.data.version===VERSION&&!force)return status();
  const previous=[];
  for(const name of await caches.keys())if((name===FINAL||name.startsWith(FINAL+'-generation-'))&&await completeCache(name))previous.push(name);
  const staging=FINAL+'-generation-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2),stage=await caches.open(staging);let committed=false;
  try{
    const documents=new Map(),references=new Map(FILES.map(file=>[new URL(file,BASE).pathname,new Set()]));
    for(const file of ['index.html','client.html']){
      const url=new URL(file,BASE).href,response=await checkedFetch(url),html=await response.clone().text();documents.set(url,response);
      for(const match of html.matchAll(/\b(?:src|href)\s*=\s*["']([^"']+)["']/g)){
        const asset=new URL(match[1],BASE);if(isAsset(asset.href)){asset.hash='';references.get(asset.pathname).add(asset.href);}
      }
    }
    const urls=[];
    for(const file of FILES){const canonical=new URL(file,BASE),refs=references.get(canonical.pathname);refs.add(canonical.href);if(/\.(?:js|css)$/.test(file))refs.add(new URL(file+'?v='+VERSION,BASE).href);urls.push(...refs);}
    let completed=0;
    const report=()=>{for(const [port,id] of progressPorts)send(port,{type:'SV_OFFLINE_PROGRESS',id,completed,total:urls.length});};report();
    for(const file of FILES){
      const canonical=new URL(file,BASE),refs=references.get(canonical.pathname),source=[...refs].find(value=>new URL(value).search)||canonical.href;
      const response=documents.get(canonical.href)||await checkedFetch(source);
      for(const url of refs){await stage.put(url,response.clone());completed++;report();}
    }
    // A complete marker publishes this independent generation atomically; existing caches stay intact.
    for(const url of urls)if(!await stage.match(url))throw Error('离线缓存校验失败，请重试。');
    const data={schema:1,version:VERSION,completedAt:new Date().toISOString(),files:urls};
    await stage.put(marker(VERSION),new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}}));
    const verified=await completeCache(staging);if(!verified)throw Error('离线缓存校验失败，请重试。');committed=true;
    // Prune only completed generations of this same version seen before the download began.
    // A failed update keeps them; other versions and all user storage remain untouched.
    for(const name of previous)try{await caches.delete(name);}catch{}
    return status();
  }finally{if(!committed)try{await caches.delete(staging);}catch{}}
}
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('message',event=>{
  const data=event.data,port=event.ports?.[0];if(!port||!data||!['SV_OFFLINE_PREPARE','SV_OFFLINE_STATUS'].includes(data.type))return;
  const task=(async()=>{
    if(data.version!==VERSION){send(port,{type:'SV_OFFLINE_RESULT',id:data.id,...await status(),ready:false,error:'离线模块版本已更新，请联网刷新页面后重试。'});return;}
    const entry=[port,data.id];
    try{
      if(data.type==='SV_OFFLINE_PREPARE'){progressPorts.add(entry);if(!preparation)preparation=build(data.force===true).finally(()=>{preparation=null;});await preparation;}
      send(port,{type:'SV_OFFLINE_RESULT',id:data.id,...await status()});
    }catch(error){send(port,{type:'SV_OFFLINE_RESULT',id:data.id,...await status(),ready:false,error:error?.message||'离线缓存未完成，请联网后重试。'});}
    finally{progressPorts.delete(entry);}
  })();event.waitUntil(task);
});
self.addEventListener('fetch',event=>{
  const request=event.request,url=new URL(request.url);if(request.method!=='GET'||url.origin!==BASE.origin)return;
  if(request.mode==='navigate'&&[BASE.pathname,new URL('index.html',BASE).pathname,new URL('client.html',BASE).pathname].includes(url.pathname)){
    event.respondWith((async()=>{try{return await fetch(request);}catch{let response;try{const best=await bestCache();response=best&&await best.cache.match(new URL('index.html',BASE).href);}catch{}return response||new Response('离线入口尚未准备。请联网打开琴房并下载离线资源。',{status:503,headers:{'Content-Type':'text/plain;charset=utf-8'}});}})());return;
  }
  if(!isAsset(url.href))return;
  event.respondWith((async()=>{let cached;try{const best=await bestCache();cached=best&&await best.cache.match(request);}catch{}return cached||fetch(request);})());
});
