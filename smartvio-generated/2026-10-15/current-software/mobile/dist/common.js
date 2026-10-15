'use strict';
/* Static HTTPS edition: state belongs to this browser/origin, never a cloud API.
 * Only user actions are allowed. Audio/video remain in SVMediaStore/IndexedDB. */
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $=s=>document.querySelector(s);
const icon=n=>'<i data-lucide="'+E(n)+'"></i>';
const icons=()=>window.lucide?.createIcons();
let svState=structuredClone(window.SV_SEED),svToken=null,svOnline=false;
let noticeTimer;
function notify(message){const el=$('#notice');if(!el)return;el.textContent=window.SVLocale?.text(message)||message;el.style.display='block';clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>{el.style.display='none';},4200);}
function modal(html){$('#modal-body').innerHTML=html;if(!$('#modal').open)$('#modal').showModal();icons();window.SVLocale?.translate($('#modal'));}
function fmtMoney(n,code){try{return new Intl.NumberFormat(undefined,{style:'currency',currency:code}).format(n);}catch{return code+' '+Number(n).toFixed(2);}}
function download(name,value,type='application/json'){name=name.replace(/^SmartVio(?=[- ])/,(window.SVLocale?.brand()||'Silvio'));const b=value instanceof Blob?value:new Blob([typeof value==='string'?value:JSON.stringify(value,null,2)],{type});const u=URL.createObjectURL(b),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);}
const MOBILE_STATE_KEY='smartvio-mobile-state-v12-v1';
const MOBILE_PRESETS=new Set(['Acoustic','Warm','Bright','Electric','Bass','Piano','Organ','Strings','Pad']);
const MOBILE_USER_ACTIONS=new Set(['session','preset-save','preset-delete','presets-import','personal-song','project-save','project-delete','practice-settings','lesson-toggle','post','like','report','clear-user']);
function mobileConnection(message){const el=$('#connection');if(el)el.textContent=window.SVLocale?.text(message)||message;}
function mobileText(value,max=300){if(typeof value!=='string'||value.length>max)throw Error('文字格式或长度不正确。');return value.trim();}
function mobileObject(value){return value!==null&&typeof value==='object'&&!Array.isArray(value);}
function mobileId(){return crypto.randomUUID();}
function initialMobileState(){
  const next=structuredClone(window.SV_SEED);
  if(next.schema!==11)throw Error('此页面的数据版本不兼容，请保留已有浏览器数据。');
  for(const key of ['sessions','posts','reports','presets','projects','audit','orders','codes'])next[key]=[];
  next.revision=0;next.binding=null;
  next.userPractice={dailyGoal:20,completedLessons:[]};
  next.device={status:'disconnected',kind:'not-connected',latencyMs:null,firmware:null,updatedAt:null};
  next.ota=null;
  return next;
}
function preservedCustomSong(value){
  if(!mobileObject(value)||typeof value.id!=='string'||!/^[a-zA-Z0-9_-]{1,160}$/.test(value.id)||value.category!=='custom')throw Error('自建曲目格式异常，原浏览器数据已保留。');
  const title=mobileText(value.title,200),author=mobileText(value.author||'我的曲目',120),melody=mobileText(value.melody,16000);
  if(!title||!melody||melody.split(/\s+/).some(token=>{const [pitch,beats,...extra]=token.split(':');return extra.length||!(/^(?:R|[A-G][#b]?-?\d)$/.test(pitch))||!Number.isFinite(Number(beats))||Number(beats)<=0||Number(beats)>64;}))throw Error('自建曲目音符格式异常，原浏览器数据已保留。');
  const titles={};for(const lang of ['zh','en','ja','de'])if(typeof value.titles?.[lang]==='string')titles[lang]=mobileText(value.titles[lang],200);
  const song={id:value.id,title,author,category:'custom',regions:['us','uk','de','jp','fr','cn'],melody,titles,rights:{status:'user-provided',evidence:'',territories:[]},published:false};
  for(const key of ['legacyCatalogId','originalId'])if(value[key]!==undefined){
    if(typeof value[key]!=='string'||!/^[a-zA-Z0-9_-]{1,160}$/.test(value[key]))throw Error('自建曲目原编号格式异常，原浏览器数据已保留。');
    song[key]=value[key];
  }
  return song;
}
function mergePersonalSongs(next,savedSongs){
  const personal=savedSongs.filter(song=>song?.category==='custom').map(preservedCustomSong);
  if(personal.length>1000)throw Error('浏览器自建曲目数量异常，原数据已保留。');
  // Reserve every old personal ID before allocating, so an earlier stock collision
  // cannot steal the ID of an existing USER_ tune later in the saved array.
  const used=new Set(next.songs.map(song=>song.id)),reserved=new Set(personal.map(song=>song.id)),references=new Map();
  for(const song of personal){
    const oldId=song.id;
    if(used.has(oldId)){
      const base=(oldId.startsWith('USER_')?oldId:'USER_'+oldId).slice(0,160);
      let id=base,suffix=1;
      while(used.has(id)||reserved.has(id)){
        const tail='_'+(++suffix);id=base.slice(0,160-tail.length)+tail;
      }
      song.id=id;song.legacyCatalogId??=oldId;song.originalId??=oldId;
    }
    used.add(song.id);next.songs.push(song);
    if(!references.has(oldId))references.set(oldId,[]);
    references.get(oldId).push(song);
  }
  return references;
}
function restorePersonalSongReference(row,references,stockSongs){
  const candidates=references.get(row.songId);
  if(!candidates||candidates.every(song=>song.id===row.songId))return;
  const named=typeof row.song==='string'?row.song:typeof row.songTitle==='string'?row.songTitle:null;
  const sameTitle=(song,name)=>song.title===name||Object.values(song.titles||{}).includes(name);
  const matches=named===null?[]:candidates.filter(song=>sameTitle(song,named));
  // A stock practice record with the same ID and its own title remains stock.
  // Historical duplicates are distinguishable only when their saved title is present;
  // otherwise the first saved personal tune is the stable canonical reference.
  if(!matches.length&&named!==null&&stockSongs.some(song=>song.id===row.songId&&sameTitle(song,named)))return;
  const target=matches[0]||candidates[0];
  if(target.id!==row.songId)row.songId=target.id;
}
function loadMobileState(){
  let raw;
  try{raw=localStorage.getItem(MOBILE_STATE_KEY);}
  catch{throw Error('当前浏览器不允许读取本地记录；可试听，保存功能暂不可用。');}
  const next=initialMobileState();
  if(raw===null)return next;
  let saved;
  try{saved=JSON.parse(raw);}catch{throw Error('当前浏览器记录无法解析，原数据已保留；请勿清理网站数据。');}
  if(!mobileObject(saved)||saved.schema!==11)throw Error('当前浏览器记录版本不兼容，原数据已保留。');
  // Shipped catalog/rights/products update with the seed; retain only validated personal tunes.
  let personalReferences=new Map();
  const stockSongs=next.songs.slice();
  if(saved.songs!==undefined){
    if(!Array.isArray(saved.songs)||saved.songs.length>1000+next.songs.length)throw Error('浏览器曲目记录格式异常，原数据已保留。');
    personalReferences=mergePersonalSongs(next,saved.songs);
  }
  for(const key of ['sessions','posts','reports','presets','projects','audit']){
    if(saved[key]!==undefined){
      if(!Array.isArray(saved[key])||saved[key].some(row=>!mobileObject(row)))throw Error('当前浏览器记录格式异常，原数据已保留。');
      next[key]=structuredClone(saved[key]);
    }
  }
  for(const key of ['sessions','projects'])for(const row of next[key])restorePersonalSongReference(row,personalReferences,stockSongs);
  if(saved.revision!==undefined){
    if(!Number.isSafeInteger(saved.revision)||saved.revision<0)throw Error('当前浏览器记录版本号异常，原数据已保留。');
    next.revision=saved.revision;
  }
  if(saved.userPractice!==undefined){
    const practice=saved.userPractice;
    if(!mobileObject(practice)||!Number.isInteger(practice.dailyGoal)||practice.dailyGoal<1||practice.dailyGoal>240||!Array.isArray(practice.completedLessons)||practice.completedLessons.length>200||practice.completedLessons.some(id=>typeof id!=='string'||!/^[a-zA-Z0-9_-]{1,80}$/.test(id)))throw Error('当前浏览器练习设置异常，原数据已保留。');
    next.userPractice={dailyGoal:practice.dailyGoal,completedLessons:[...new Set(practice.completedLessons)]};
  }
  return next;
}
function commitMobileState(next){
  try{localStorage.setItem(MOBILE_STATE_KEY,JSON.stringify(next));}
  catch{throw Error('当前浏览器保存失败，变更未提交；请检查存储空间或浏览器权限后重试。');}
}
async function connectApi(){
  try{svToken=(await readApi('/api/session')).token;await refreshState();}
  catch(error){svOnline=false;mobileConnection('当前浏览器记录未就绪 · 仅预览');notify(error.message);}
}
async function readApi(url){
  const path=String(url).split('?')[0];
  if(path==='/api/session')return {token:svToken||(svToken='browser-local-'+mobileId()),mode:'mobile-browser-local'};
  if(path==='/api/state')return loadMobileState();
  if(path==='/api/export'){
    const state=loadMobileState();let rows=[];
    if(typeof SVMediaStore!=='undefined'){
      rows=await SVMediaStore.list();
      if(SVMediaStore.status().error?.code==='READ_FAILED')throw Error('浏览器媒体列表读取失败，未生成不完整导出。');
    }
    return {exportedAt:new Date().toISOString(),scope:'mobile-browser-local',sessions:state.sessions,projects:state.projects,presets:state.presets,userPractice:state.userPractice,media:rows.map(({blob,...row})=>({...row,bytes:blob.size,mime:blob.type,audioIncluded:false}))};
  }
  throw Error('手机浏览器版本不提供此管理接口。');
}
async function refreshState(){
  const next=await readApi('/api/state');
  // Keep readable history visible if the browser has become read-only.
  svState=next;
  try{commitMobileState(next);}
  catch(error){svOnline=false;mobileConnection('当前浏览器记录可读 · 保存不可用');throw error;}
  svOnline=true;mobileConnection('当前手机浏览器数据已就绪');return svState;
}
function mobileEffects(value){
  if(!mobileObject(value))throw Error('请提供完整效果参数。');
  const effects={};
  for(const key of ['volume','reverb','delay','compression']){
    if(typeof value[key]!=='number'||!Number.isFinite(value[key])||value[key]<0||value[key]>1)throw Error('效果参数须为0到1。');
    effects[key]=value[key];
  }
  return effects;
}
function mobileInputGain(value=1){if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>2)throw Error('麦克风输入增益必须为0至2。');return value;}
function mobilePreset(value){
  if(!mobileObject(value))throw Error('预设格式不正确。');const name=mobileText(value.name,80),group=mobileText(value.group??'',60);
  if(!name||!MOBILE_PRESETS.has(value.preset))throw Error('请填写名称并选择有效音色。');
  return {name,group,preset:value.preset,effects:mobileEffects(value.effects),inputGain:mobileInputGain(value.inputGain??1)};
}
function mobileSaveItem(items,item,id){
  const at=new Date().toISOString();
  if(id!==undefined){
    const key=mobileText(id,160),index=items.findIndex(row=>row.id===key);
    if(index<0)throw Error('没有找到要更新的浏览器记录。');
    items[index]={...item,id:key,at};
  }else{
    if(items.length>=100)throw Error('最多保存100条，请先导出或删除不再使用的记录。');
    items.unshift({...item,id:mobileId(),at});
  }
}
function mobileDeleteItem(items,id){
  const key=mobileText(id,160),index=items.findIndex(row=>row.id===key);
  if(index<0)throw Error('没有找到要删除的浏览器记录。');
  items.splice(index,1);
}
function mutateMobileState(next,a){
  if(!mobileObject(a)||!MOBILE_USER_ACTIONS.has(a.type))throw Error('手机浏览器版本不提供后台、权利或设备管理操作。');
  switch(a.type){
    case 'session':{
      const target=next.songs.find(song=>song.id===a.song);
      if(!target)throw Error('没有找到练习曲目。');
      if(typeof a.duration!=='number'||!Number.isFinite(a.duration)||a.duration<0)throw Error('练习时长不正确。');
      const score=a.score===null||a.score===undefined?null:a.score;
      if(score!==null&&(typeof score!=='number'||!Number.isFinite(score)))throw Error('参考成绩不正确。');
      const scoringVersion=mobileText(a.scoringVersion,64);
      if(!scoringVersion)throw Error('缺少评分版本。');
      if(!['microphone','synth','unknown'].includes(a.inputRoute))throw Error('练习来源不正确。');
      if(score!==null&&a.inputRoute!=='microphone')throw Error('合成聆听不能保存演奏成绩。');
      const range=a.rangeTicks;
      if(!mobileObject(range)||!Number.isSafeInteger(range.start)||!Number.isSafeInteger(range.end)||range.start<0||range.end<=range.start)throw Error('练习段落不正确。');
      if(a.metrics!==undefined&&!mobileObject(a.metrics))throw Error('练习指标格式不正确。');
      const metrics={};
      for(const key of ['pitchCoverage','validInputFraction']){
        const value=a.metrics?.[key]??null;
        if(value!==null&&(typeof value!=='number'||!Number.isFinite(value)||value<0||value>1))throw Error('练习指标须为0到1。');
        metrics[key]=value;
      }
      next.sessions.unshift({id:mobileId(),at:new Date().toISOString(),kind:score!==null?'mic-scored':'simulation',song:target.title,songId:target.id,duration:Math.min(3600,a.duration),score:score===null?null:Math.min(100,Math.max(0,Math.round(score))),scoringVersion,inputRoute:a.inputRoute,rangeTicks:{start:range.start,end:range.end},metrics});
      next.sessions=next.sessions.slice(0,200);break;
    }
    case 'preset-save':{
      mobileSaveItem(next.presets,mobilePreset(a),a.id);break;
    }
    case 'presets-import':{
      if(!Array.isArray(a.presets)||a.presets.length>100)throw Error('最多导入100套预设。');
      const incoming=a.presets.map(value=>{const id=mobileText(value.id,160);if(!/^[a-zA-Z0-9_-]{1,160}$/.test(id))throw Error('预设编号格式不正确。');return {id,...mobilePreset(value)};});
      if(new Set(incoming.map(p=>p.id)).size!==incoming.length)throw Error('导入预设编号重复。');
      const fingerprint=value=>JSON.stringify(mobilePreset(value));
      for(const value of incoming){const existing=next.presets.find(p=>p.id===value.id);if(existing&&fingerprint(existing)===fingerprint(value))continue;if(next.presets.length>=100)throw Error('合并后超过100套预设，请先导出并整理。');next.presets.push({...value,id:existing?mobileId():value.id,at:new Date().toISOString()});}
      break;
    }
    case 'personal-song':{
      const value=preservedCustomSong(a.song);if(next.songs.some(s=>s.id===value.id))throw Error('练习曲编号已存在。');if(next.songs.filter(s=>s.category==='custom').length>=1000)throw Error('自建曲目数量达到上限。');next.songs.push(value);break;
    }
    case 'preset-delete':mobileDeleteItem(next.presets,a.id);break;
    case 'project-save':{
      const name=mobileText(a.name,80);
      if(!name||typeof a.bpm!=='number'||!Number.isFinite(a.bpm)||a.bpm<30||a.bpm>240||!Number.isInteger(a.barCount)||a.barCount<1||a.barCount>128)throw Error('工程名称、速度或小节数不正确。');
      if(!Array.isArray(a.trackIds)||a.trackIds.length>4)throw Error('工程最多引用4条轨道。');
      const trackIds=a.trackIds.map(id=>mobileText(id,160));
      if(trackIds.some(id=>!id)||new Set(trackIds).size!==trackIds.length)throw Error('轨道引用不能为空或重复。');
      mobileSaveItem(next.projects,{name,bpm:a.bpm,barCount:a.barCount,trackIds,kind:'local-browser-project'},a.id);break;
    }
    case 'project-delete':mobileDeleteItem(next.projects,a.id);break;
    case 'practice-settings':
      if(!Number.isInteger(a.dailyGoal)||a.dailyGoal<1||a.dailyGoal>240)throw Error('每日目标须为1到240分钟。');
      next.userPractice.dailyGoal=a.dailyGoal;break;
    case 'lesson-toggle':{
      if(typeof a.id!=='string'||!/^[a-zA-Z0-9_-]{1,80}$/.test(a.id)||typeof a.done!=='boolean')throw Error('学习进度格式不正确。');
      const done=new Set(next.userPractice.completedLessons);
      if(a.done)done.add(a.id);else done.delete(a.id);
      if(done.size>200)throw Error('学习进度超过本机保存上限。');
      next.userPractice.completedLessons=[...done];break;
    }
    case 'post':{
      const text=mobileText(a.text,600);
      if(!text)throw Error('练习笔记不能为空。');
      next.posts.unshift({id:mobileId(),author:'我的琴房',text,status:'pending',likes:0,createdAt:new Date().toISOString()});
      next.posts=next.posts.slice(0,200);break;
    }
    case 'like':{
      const post=next.posts.find(row=>row.id===a.id&&row.status==='published');
      if(!post)throw Error('没有找到可标记的本机内容。');
      post.likes++;break;
    }
    case 'report':
      if(!next.posts.some(row=>row.id===a.id))throw Error('没有找到反馈对应的本机内容。');
      next.reports.unshift({id:mobileId(),postId:a.id,reason:mobileText(a.reason,200),status:'open'});
      next.reports=next.reports.slice(0,200);break;
    case 'clear-user':
      next.sessions=[];next.posts=[];next.reports=[];next.binding=null;next.orders=[];
      next.presets=[];next.projects=[];next.userPractice={dailyGoal:20,completedLessons:[]};break;
  }
  if(next.revision>=Number.MAX_SAFE_INTEGER)throw Error('记录版本已到上限，请导出后清理。');
  next.revision++;
  next.audit.unshift({at:new Date().toISOString(),action:a.type,mode:'mobile-browser-local',id:mobileId()});
  next.audit=next.audit.slice(0,300);
  return next;
}
async function action(value){
  if(!svOnline){notify('当前浏览器保存未就绪；请检查存储权限后刷新，音频试听仍可使用。');return false;}
  try{
    // Read the latest committed state, then mutate a private clone.
    const next=mutateMobileState(loadMobileState(),value);
    commitMobileState(next);
    svState=next;mobileConnection('当前手机浏览器数据已就绪');return true;
  }catch(error){mobileConnection('当前浏览器变更未提交');notify(error.message||'浏览器保存失败，原记录未变。');return false;}
}
function table(headers,rows){return '<div class="table-wrap"><table><thead><tr>'+headers.map(h=>'<th>'+E(h)+'</th>').join('')+'</tr></thead><tbody>'+ (rows.join('')||'<tr><td colspan="'+headers.length+'" class="empty">暂无记录</td></tr>')+'</tbody></table></div>';}
const regions={us:'美国',uk:'英国',de:'德国',jp:'日本',fr:'法国',cn:'中国'};
function rightsBadge(s){return '<span class="badge '+(s.rights.status==='reviewed'?'':'pending')+'">'+(s.rights.status==='reviewed'?'演示审核已登记':'权利待核验')+'</span>';}

