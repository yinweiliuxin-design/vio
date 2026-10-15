/* Actual frontend functions run in VM with a small, explicit DOM/network protocol substitute.
 * This verifies state transitions and listener lifecycle; it is not real-browser layout/video decoding QA.
 * Private seams exist only in this instrumented test source, never in the shipped frontend API.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import { readFileSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
const communitySource=readFileSync(new URL('../dist/community.js',import.meta.url),'utf8');
const adminSource=readFileSync(new URL('../dist/admin.js',import.meta.url),'utf8');
const origin='https://community-ui.test',VIDEO_KEY='smartvio-community-video-operations-v1';
const unescape=s=>String(s||'').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
function deferred(){let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};}
class Node{
  constructor(document,tag='div'){this.document=document;this.tagName=tag.toUpperCase();this.dataset={};this.listeners=new Map();this.children=[];this.videos=[];this.fields=new Map();this.attributes={};this.isConnected=false;this.disabled=false;this.hidden=false;this._html='';this.classList={add(){}};}
  addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,[]);if(!this.listeners.get(type).includes(fn))this.listeners.get(type).push(fn);}
  removeEventListener(type,fn){this.listeners.set(type,(this.listeners.get(type)||[]).filter(x=>x!==fn));}
  emit(type,extra={}){const event={target:this,preventDefault(){},stopPropagation(){},...extra};for(const fn of this.listeners.get(type)||[])fn(event);if(this.tagName==='VIDEO')this.document.emit(type,event);}
  appendChild(node){this.children.push(node);node.parentElement=this;node.isConnected=this.isConnected;for(const video of node.videos)video.isConnected=node.isConnected;}
  remove(){this.isConnected=false;for(const video of this.videos)video.isConnected=false;if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(n=>n!==this);}
  setAttribute(name,value){this.attributes[name]=String(value);}
  removeAttribute(name){delete this.attributes[name];if(name==='src')this.src='';}
  focus(){this.document.activeElement=this;}
  setSelectionRange(){}
  getClientRects(){return this.isConnected?[{}]:[];}
  contains(node){return this===node||node?.parentElement===this||this.videos.includes(node);}
  closest(){return null;}
  showModal(){this.open=true;}
  close(){this.open=false;this.emit('close');}
  set innerHTML(html){
    for(const video of this.videos)video.isConnected=false;this._html=html;this.fields=new Map();this.videos=[];
    for(const match of html.matchAll(/<(input|textarea|select)\b([^>]*data-svc-field="([^"]+)"[^>]*)>([\s\S]*?)(?:<\/\1>|(?=<)|$)/g)){
      const field=new Node(this.document,match[1]);field.parentElement=this;field.isConnected=this.isConnected;field.dataset.svcField=match[3];field.disabled=/\sdisabled(?:\s|$)/.test(match[2]);field.checked=/\schecked(?:\s|$)/.test(match[2]);field.value=unescape(/value="([^"]*)"/.exec(match[2])?.[1]||'');if(match[1]==='textarea')field.value=unescape(match[4]);if(match[1]==='select')field.value=/value="([^"]*)" selected/.exec(match[4])?.[1]||'practice';this.fields.set(match[3],field);
    }
    // Input is a void element and does not need a closing tag.
    for(const match of html.matchAll(/<input\b([^>]*data-svc-field="([^"]+)"[^>]*)>/g)){if(this.fields.has(match[2]))continue;const field=new Node(this.document,'input');field.parentElement=this;field.isConnected=this.isConnected;field.dataset.svcField=match[2];field.disabled=/\sdisabled(?:\s|$)/.test(match[1]);field.checked=/\schecked(?:\s|$)/.test(match[1]);field.value=unescape(/value="([^"]*)"/.exec(match[1])?.[1]||'');this.fields.set(match[2],field);}
    for(const match of html.matchAll(/<video\b([^>]*)>/g)){const video=new Node(this.document,'video');video.src=unescape(/src="([^"]*)"/.exec(match[1])?.[1]||'');video.isConnected=this.isConnected;video.parentElement={querySelector:()=>video.note};video.paused=true;video.pauseCount=0;video.loads=0;video.note={hidden:true};video.pause=()=>{video.paused=true;video.pauseCount++;};video.load=()=>{video.loads++;};video.play=()=>{video.paused=false;video.emit('play');return Promise.resolve();};video.matches=selector=>selector.includes('video')||selector.includes('.svc-video');video.isCommunity=/class="svc-video"/.test(match[1]);this.videos.push(video);}
  }
  get innerHTML(){return this._html;}
  querySelector(selector){if(selector.startsWith('[data-svc-field="'))return this.fields.get(/"([^"]+)"/.exec(selector)[1])||null;if(selector==='[data-svc-field]:not([disabled])')return [...this.fields.values()].find(f=>!f.disabled)||null;if(selector==='.svc-dialog-head')return {outerHTML:'<div class="svc-dialog-head"><h2>Editor</h2></div>'};if(selector==='[data-svc-dialog-message]')return this.messageNode??=(new Node(this.document));if(selector==='[data-svc-local-notice]')return null;return null;}
  querySelectorAll(selector){if(selector.includes('video'))return this.videos.filter(v=>selector.includes('.svc-video')?v.isCommunity:true);return [...this.fields.values()];}
}
class Document{
  constructor(admin=false){this.listeners=new Map();this.hidden=false;this.documentElement={lang:'en'};this.body=new Node(this,'body');this.body.isConnected=true;this.nodes=new Map();this.activeElement=new Node(this,'button');this.activeElement.isConnected=true;this.communityNode=new Node(this);this.communityNode.isConnected=true;this.admin=admin;for(const id of ['admin-modal','admin-modal-body','admin-main']){const node=new Node(this,id==='admin-modal'?'dialog':'div');node.isConnected=true;this.nodes.set('#'+id,node);}}
  createElement(tag){return new Node(this,tag);}
  addEventListener(type,fn){if(!this.listeners.has(type))this.listeners.set(type,[]);this.listeners.get(type).push(fn);}
  removeEventListener(type,fn){this.listeners.set(type,(this.listeners.get(type)||[]).filter(x=>x!==fn));}
  emit(type,event={}){for(const fn of this.listeners.get(type)||[])fn(event);}
  querySelector(selector){if(selector==='[data-sv-community]')return this.communityNode.isConnected?this.communityNode:null;return this.nodes.get(selector)||null;}
  querySelectorAll(selector){const scopes=[this.communityNode,...this.body.children,...this.nodes.values()];return scopes.flatMap(s=>s.videos).filter(v=>v.isConnected&&(selector.includes('.svc-video')?v.isCommunity:selector.includes('video')?!v.isCommunity:true));}
}
function response(data,status=200){return new Response(JSON.stringify(data),{status,headers:{'Content-Type':'application/json'}});}
function media(id,state='ready',version=3,extra={}){return {id,mediaId:id,kind:'video',url:'/api/community/videos/'+id,mime:'video/mp4',size:100,duration:1,width:64,height:64,state,version,cleanupPending:false,uploadActive:false,...extra};}
function cloud(actor='alice'){return {ok:true,viewer:{id:actor,name:actor,isAdmin:false},settings:{postingEnabled:true,allowExternalLinks:true},posts:[],mine:[],myComments:[]};}
function harness({fetch,storage={},admin=false}={}){
  const document=new Document(admin),values=new Map(Object.entries(storage)),timers=new Map(),observers=[],windowEvents=new Map();let tick=0;
  const root={document,location:{origin,href:origin+'/client.html#community'},crypto:{randomUUID},localStorage:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v)},fetch:fetch||(()=>{throw Error('Unexpected network request');}),addEventListener:(type,fn)=>windowEvents.set(type,fn)};
  root.IntersectionObserver=class{constructor(callback){this.callback=callback;this.observed=new Set();observers.push(this);}observe(v){this.observed.add(v);}disconnect(){this.observed.clear();}fire(video,ratio){this.callback([{target:video,intersectionRatio:ratio}]);}};
  const sandbox={window:root,document,location:root.location,localStorage:root.localStorage,URL,AbortController,Response,Blob,console,setTimeout:(fn,ms)=>{const id=++tick;timers.set(id,{fn,ms});return id;},clearTimeout:id=>timers.delete(id)};vm.createContext(sandbox);
  if(!admin){const source=communitySource.replace('root.SVCommunity=Object.freeze',`root.__ui={normalizeAttachment,payloadAttachments,videoURL,mediaURL,attachmentHTML,makeDraft,openEditor,closeDialog,refreshEditor,onDialogChange,uploadVideo,videoAction,applyVideoStatus,videoOperationHTML,attachUploadedVideo,acceptState,errorText,bindVideoPlayers,stopVideoPlayers,activate,deactivate,setContext,snapshot:()=>({drafts,dialog,editorId,videoOperations,message,uploadBusy,cloud}),setOperations:rows=>{videoOperations=rows;}};root.SVCommunity=Object.freeze`);vm.runInContext(source,sandbox);root.__ui.acceptState(cloud());root.__ui.setContext({lang:'en'});}
  else{const source=adminSource.replace('render();void load();',`global.__ui={dialog,closeDialog,safeVideo,safeMedia,attachmentMarkup,stopAdminVideos,bindAdminVideos};`);vm.runInContext(source,sandbox);}
  return {root,document,api:root.__ui,values,timers,observers,windowEvents};
}
function readyDraft(h,extra={}){const d=h.api.makeDraft({title:'My practice',text:'Original recording',rightsConfirmed:true,...extra});h.api.openEditor(d);return d;}

await test('video and image URLs reject credentials, foreign origin, query/hash and mismatched media IDs',()=>{
  const h=harness(),id=randomUUID(),url='/api/community/videos/'+id;assert(h.api.normalizeAttachment({kind:'video',mediaId:id,url}));for(const bad of ['https://attacker.test'+url,'[REDACTED_SECRET]community-ui.test'+url,url+'?x=1',url+'#fragment','/api/community/videos/'+randomUUID()])assert.equal(h.api.normalizeAttachment({kind:'video',mediaId:id,url:bad}),null);assert.equal(h.api.normalizeAttachment({kind:'video',mediaId:'invalid'}),null);assert.equal(h.api.mediaURL('/api/community/media/test/nested'),null);assert.equal(h.api.mediaURL('/api/community/media/test?x=1'),null);assert.equal(h.api.mediaURL('[REDACTED_SECRET]community-ui.test/api/community/media/test'),null);const payload=h.api.payloadAttachments({attachments:[{kind:'video',mediaId:id,url,duration:99}]});assert.equal(JSON.stringify(payload),JSON.stringify([{kind:'video',mediaId:id}]));
});

await test('rights checkbox enables video selection and unconfirmed upload makes no request',async()=>{
  let requests=0;const h=harness({fetch:()=>{requests++;throw Error('Must not upload');}}),d=readyDraft(h,{rightsConfirmed:false});assert.equal(h.api.snapshot().dialog.fields.get('video').disabled,true);await assert.rejects(h.api.uploadVideo(new Blob(['x'],{type:'video/mp4'})),e=>e.code==='INPUT');assert.equal(requests,0);const check=h.api.snapshot().dialog.fields.get('rights');check.checked=true;h.api.onDialogChange({target:check});assert.equal(d.rightsConfirmed,true);assert.equal(h.api.snapshot().dialog.fields.get('video').disabled,false);
});

await test('ready upload attaches only to its original session, binds owner and resets rights',async()=>{
  const requests=[];const h=harness({fetch:async(path,options)=>{requests.push({path,options});return response({ok:true,media:media(options.headers['X-Client-Request-Id'])},201);}}),d=readyDraft(h);await h.api.uploadVideo(new Blob(['x'],{type:'video/mp4'}));assert.equal(d.attachments.length,1);assert.equal(d.cloudOwnerId,'alice');assert.equal(d.rightsConfirmed,false);assert.equal(requests[0].options.headers['X-Account-Id'],'alice');assert.equal(requests[0].options.cache,'no-store');assert.match(h.api.snapshot().message,/added to the draft/);assert.equal(h.timers.size,0);
});

await test('late upload after another draft opens is cleaned and cannot attach to either draft',async()=>{
  const gate=deferred(),calls=[];let id;const h=harness({fetch:async(path,options)=>{calls.push(path);if(path==='/api/community/videos'){id=options.headers['X-Client-Request-Id'];return gate.promise;}return response({ok:true,media:media(id,'cancelled',5)});}}),d1=readyDraft(h),pending=h.api.uploadVideo(new Blob(['x'],{type:'video/mp4'}));const d2=readyDraft(h);gate.resolve(response({ok:true,media:media(id)},201));await pending;assert.equal(d1.attachments.length,0);assert.equal(d2.attachments.length,0);assert(calls.includes('/api/community/videos/'+id+'/cancel'));assert.equal(h.api.snapshot().videoOperations.length,0);assert.match(h.api.snapshot().message,/confirmed video cleanup/);
});

await test('late upload after identity change cannot attach Alice media or send cleanup as Bob',async()=>{
  const gate=deferred(),calls=[];let id;const h=harness({fetch:async(path,options)=>{calls.push(path);id=options.headers['X-Client-Request-Id'];return gate.promise;}}),d=readyDraft(h),pending=h.api.uploadVideo(new Blob(['x'],{type:'video/mp4'}));h.api.acceptState(cloud('bob'));assert.equal(h.api.snapshot().dialog,null);const bob=readyDraft(h);gate.resolve(response({ok:true,media:media(id)},201));await pending;assert.equal(d.attachments.length,0);assert.equal(bob.attachments.length,0);assert.equal(calls.length,1);assert.equal(h.api.snapshot().videoOperations[0].owner,'alice');
});

await test('newer cancelled status wins over an older late ready response and no false cleanup is shown',async()=>{
  const gate=deferred();let id,finished=false;const h=harness({fetch:async(path,options)=>{if(path==='/api/community/videos'){id=options.headers['X-Client-Request-Id'];return gate.promise;}return response({ok:true,media:media(id,'cancelled',finished?6:5,{cleanupPending:!finished,uploadActive:!finished})});}}),d=readyDraft(h),pending=h.api.uploadVideo(new Blob(['x'],{type:'video/mp4'}));await h.api.videoAction('cancel-video',id);assert.equal(h.api.snapshot().videoOperations[0].version,5);assert.match(h.api.snapshot().message,/still cleaning/);gate.resolve(response({ok:true,media:media(id,'ready',3)},201));await pending;assert.equal(d.attachments.length,0);assert.equal(h.api.snapshot().videoOperations[0].state,'cancelled');assert.equal(h.api.snapshot().videoOperations[0].cleanupPending,true);assert.doesNotMatch(h.api.snapshot().message,/confirmed video cleanup/);finished=true;await h.api.videoAction('check-video',id);assert.equal(h.api.snapshot().videoOperations.length,0);
});

await test('AbortError with unavailable cancellation leaves a recoverable uncertain operation',async()=>{
  let id;const h=harness({fetch:(path,options)=>{if(path!=='/api/community/videos')return Promise.reject(Error('Network down'));id=options.headers['X-Client-Request-Id'];return new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Aborted','AbortError'))));}});readyDraft(h);const pending=h.api.uploadVideo(new Blob(['x'],{type:'video/mp4'}));await assert.rejects(h.api.videoAction('cancel-video',id));await pending;const op=h.api.snapshot().videoOperations[0];assert.equal(op.cleared,undefined);assert.equal(op.uncertain,true);assert.equal(op.cancelRequested,true);assert.match(h.api.videoOperationHTML(),/data-svc-action="cancel-video"/);assert.doesNotMatch(h.api.snapshot().message,/confirmed video cleanup/);
});

await test('MEDIA_IN_USE is a known failure, preserves ready state and does not invent pending cleanup',async()=>{
  const id=randomUUID(),h=harness({fetch:async()=>response({ok:false,error:{code:'MEDIA_IN_USE',message:'used'}},409)}),op={id,owner:'alice',state:'ready',version:3,cleanupPending:false,media:media(id)};h.api.setOperations([op]);await assert.rejects(h.api.videoAction('delete-video',id),e=>e.code==='MEDIA_IN_USE');assert.equal(op.state,'ready');assert.equal(op.cleanupPending,false);assert.equal(op.uncertain,undefined);assert.match(h.api.errorText({code:'MEDIA_IN_USE'}),/has not been deleted/);assert.equal(h.api.snapshot().videoOperations.length,1);
});

await test('failed or cancelled pending cleanup has an explicit repeat-cancel action',async()=>{
  for(const state of ['failed','unknown','cancelled','deleting']){const id=randomUUID(),h=harness({fetch:async()=>response({ok:true,media:media(id,'cancelled',9)})});h.api.setOperations([{id,owner:'alice',state,version:4,cleanupPending:true}]);assert.match(h.api.videoOperationHTML(),/data-svc-action="cancel-video"/);await h.api.videoAction('cancel-video',id);assert.equal(h.api.snapshot().videoOperations.length,0);}
});

await test('cancel intent remains retryable when a status read still reports the object ready',()=>{
  const h=harness(),id=randomUUID(),op={id,owner:'alice',state:'ready',version:3,cancelRequested:true,cleanupPending:false,media:media(id)};h.api.setOperations([op]);assert.match(h.api.videoOperationHTML(),/data-svc-action="cancel-video"/);assert.doesNotMatch(h.api.videoOperationHTML(),/data-svc-action="attach-video"/);
});

await test('manual add from the main history verifies status and opens a usable editor',async()=>{
  const id=randomUUID(),h=harness({fetch:async()=>response({ok:true,media:media(id)})});h.api.setOperations([{id,owner:'alice',state:'ready',version:3,cleanupPending:false,media:media(id)}]);await h.api.videoAction('attach-video',id);const snap=h.api.snapshot();assert(snap.dialog);assert.equal(snap.drafts[0].attachments[0].mediaId,id);assert.equal(snap.drafts[0].cloudOwnerId,'alice');assert.equal(snap.drafts[0].rightsConfirmed,false);
});

await test('old video status cannot overwrite newer server version and malformed IDs cannot attach',()=>{
  const h=harness(),id=randomUUID(),op={id,owner:'alice',version:5,state:'cancelled',cleanupPending:true};assert.equal(h.api.applyVideoStatus(op,{media:media(id,'ready',3)}),false);assert.equal(op.state,'cancelled');assert.throws(()=>h.api.applyVideoStatus(op,{media:media(randomUUID(),'ready',6)}),e=>e.code==='BAD_RESPONSE');assert.throws(()=>h.api.applyVideoStatus(op,{media:media(id,'ready',6,{url:'https://attacker.test/video'})}),e=>e.code==='BAD_RESPONSE');
});

await test('confirmed cloud deletion removes local references only after the server acknowledgement',async()=>{
  const id=randomUUID(),gate=deferred(),h=harness({fetch:()=>gate.promise}),d=readyDraft(h,{cloudOwnerId:'alice',attachments:[{kind:'video',mediaId:id,url:'/api/community/videos/'+id,mime:'video/mp4',duration:1,size:100}]});h.api.setOperations([{id,owner:'alice',state:'ready',version:3,media:media(id)}]);const pending=h.api.videoAction('delete-video',id);assert.equal(d.attachments.length,1);gate.resolve(response({ok:true,media:media(id,'deleted',5)}));await pending;assert.equal(d.attachments.length,0);assert.equal(d.rightsConfirmed,false);assert.equal(h.api.snapshot().videoOperations.length,0);
});

await test('editor creation and refresh bind single-player, offscreen pause and playback-error UI',async()=>{
  const h=harness(),id=randomUUID(),d=readyDraft(h,{attachments:[{kind:'video',mediaId:id,url:'/api/community/videos/'+id,mime:'video/mp4',duration:1,size:100}]});const old=h.api.snapshot().dialog.videos[0];assert(old);assert(h.observers.at(-1).observed.has(old));await old.play();h.observers.at(-1).fire(old,0);assert.equal(old.paused,true);old.emit('error');assert.equal(old.note.hidden,false);h.api.refreshEditor();assert.equal(old.src,'');assert(old.loads>0);const fresh=h.api.snapshot().dialog.videos[0];assert(h.observers.at(-1).observed.has(fresh));const feed=new Node(h.document,'video');feed.isConnected=true;feed.isCommunity=true;feed.paused=false;feed.pause=()=>{feed.paused=true;};h.document.communityNode.videos.push(feed);await fresh.play();assert.equal(feed.paused,true);h.document.hidden=true;h.document.emit('visibilitychange');assert.equal(fresh.paused,true);h.api.closeDialog();assert.equal(fresh.src,'');assert.equal(h.api.snapshot().dialog,null);assert.equal(d.attachments.length,1);
});

await test('deactivate/activate reusing a root does not accumulate click handlers or keep media playing',()=>{
  const h=harness();h.api.activate();assert.equal(h.document.communityNode.listeners.get('click').length,1);h.api.deactivate();h.api.activate();h.api.deactivate();h.api.activate();assert.equal(h.document.communityNode.listeners.get('click').length,1);const previous=h.document.communityNode;previous.isConnected=false;h.document.communityNode=new Node(h.document);h.document.communityNode.isConnected=true;h.api.activate();assert.equal(h.document.communityNode.listeners.get('click').length,1);
});

await test('unresolved operations beyond the previous twenty-record cap survive persistence',()=>{
  const records=Array.from({length:25},()=>({id:randomUUID(),owner:'alice',state:'unknown',cleanupPending:true}));const h=harness({storage:{[VIDEO_KEY]:JSON.stringify(records)}});assert.equal(h.api.snapshot().videoOperations.length,25);assert.equal(h.api.snapshot().videoOperations.at(-1).id,records.at(-1).id);
});

await test('offline rendering never creates a network video/image source and forbids uploads',async()=>{
  let requests=0;const h=harness({fetch:()=>{requests++;throw Error('Offline');}}),id=randomUUID();readyDraft(h);h.api.setContext({mode:'offline'});assert.doesNotMatch(h.api.attachmentHTML({kind:'video',mediaId:id,mime:'video/mp4',size:100,duration:1}),/<video|src=/);assert.doesNotMatch(h.api.attachmentHTML({kind:'media',mediaId:id,url:'/api/community/media/'+id}),/<img|src=/);await assert.rejects(h.api.uploadVideo(new Blob(['x'],{type:'video/mp4'})),e=>e.code==='AUTH_REQUIRED');assert.equal(requests,0);
});

await test('admin video preview closes with pause and src release, including native Escape-close event',async()=>{
  const h=harness({admin:true}),id=randomUUID();h.api.dialog('Review',h.api.attachmentMarkup([media(id)]));const first=h.document.nodes.get('#admin-modal-body').videos[0];assert(first);assert(h.observers.at(-1).observed.has(first));await first.play();h.api.closeDialog();assert.equal(first.paused,true);assert.equal(first.src,'');assert(first.loads>0);h.api.dialog('Review',h.api.attachmentMarkup([media(id)]));const second=h.document.nodes.get('#admin-modal-body').videos[0];await second.play();h.document.nodes.get('#admin-modal').close();assert.equal(second.paused,true);assert.equal(second.src,'');
});

await test('admin errors reveal a translated actionable message, background/offscreen pauses and URLs stay strict',async()=>{
  const h=harness({admin:true}),id=randomUUID(),url='/api/community/videos/'+id;for(const bad of ['https://attacker.test'+url,'[REDACTED_SECRET]community-ui.test'+url,url+'?x=1',url+'#x'])assert.equal(h.api.safeVideo(bad),null);assert.equal(h.api.safeMedia('/api/community/media/id/nested'),null);h.api.dialog('Review',h.api.attachmentMarkup([media(id)]));const video=h.document.nodes.get('#admin-modal-body').videos[0];video.emit('error');assert.equal(video.note.hidden,false);assert.equal(video.hidden,true);await video.play();h.observers.at(-1).fire(video,0);assert.equal(video.paused,true);await video.play();h.document.hidden=true;h.document.emit('visibilitychange');assert.equal(video.paused,true);assert.match(h.document.nodes.get('#admin-modal-body').innerHTML,/访问权限失效/);assert.match(h.document.nodes.get('#admin-modal-body').innerHTML,/role="status"/);
});
