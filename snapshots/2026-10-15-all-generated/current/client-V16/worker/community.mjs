/* Native Sites API. Identity headers are injected by Sites dispatch, never by app roles. */
import { inspectVideo } from './video-inspection.mjs';
const COMMUNITY_LIMITS=Object.freeze({posts:50,mine:100,comments:200,admin:200,postTitle:120,postText:5000,commentText:1000,reportReason:500,attachments:4,imageBytes:5242880,videoBytes:20000000,videoSeconds:60,videosPerPost:1,videosPerUser:100});
const cLangs=['zh','en','ja','de'];
const cGuideVersion=2,cGuideStatuses=['legacy','pending','in_progress','completed','skipped'],cGuideTerminal=['completed','skipped'];
const cTables={post:'community_posts',comment:'community_comments',report:'community_reports',user:'community_users',settings:'community_settings',media:'community_media',video:'community_videos'};
const cNow=()=>new Date().toISOString(),cUuid=()=>crypto.randomUUID();
class CommunityError extends Error{constructor(status,code,message){super(message);this.status=status;this.code=code;}}
function cFail(status,code,message){throw new CommunityError(status,code,message);}
function cResponse(value,status=200){return new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json;charset=utf-8','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Vary':'Cookie, oai-authenticated-user-id'}});}
function cKeys(value,allowed){for(const key of Object.keys(value))if(!allowed.includes(key))cFail(422,'INVALID_INPUT','不支持的字段：'+key);}
function cText(value,max,min=0){if(typeof value!=='string'||value.length>max||/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(value))cFail(422,'INVALID_INPUT','文字格式或长度不正确。');const clean=value.trim();if(clean.length<min)cFail(422,'INVALID_INPUT','请填写需要的文字。');return clean;}
function cId(value){const clean=cText(value,80,1);if(!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(clean))cFail(422,'INVALID_INPUT','记录编号无效。');return clean.toLowerCase();}
function cVersion(value,zero=false){if(!Number.isSafeInteger(value)||value<(zero?0:1))cFail(422,'INVALID_INPUT','请提供有效版本，刷新后重试。');return value;}
function cBool(value){if(typeof value!=='boolean')cFail(422,'INVALID_INPUT','开关必须为 true 或 false。');return value;}
function cAdmins(env){try{const ids=JSON.parse(env.ADMIN_USER_IDS);if(!Array.isArray(ids)||!ids.length||ids.length>20||ids.some(id=>typeof id!=='string'||!id.trim()||id.length>256))return null;return new Set(ids);}catch{return null;}}
function cIdentity(request,env){
  const id=request.headers.get('oai-authenticated-user-id');
  if(!id||id.length>256||id.trim()!==id||/[\u0000-\u0020\u007f]/.test(id))cFail(401,'AUTH_REQUIRED','请先登录已授权的站点账号。');
  const admins=cAdmins(env);return {id,name:'琴友',isAdmin:Boolean(admins?.has(id)),admins};
}
function cOrigin(request){if(request.headers.get('Origin')!==new URL(request.url).origin||request.headers.get('Sec-Fetch-Site')==='cross-site')cFail(403,'FORBIDDEN_ORIGIN','请从当前站点提交操作。');}
async function cBytes(request,limit){
  const declared=request.headers.get('Content-Length');if(declared!==null&&(!/^\d+$/.test(declared)||Number(declared)>limit))cFail(413,'BODY_TOO_LARGE','提交内容超过大小限制。');
  if(!request.body)return new Uint8Array();const reader=request.body.getReader(),chunks=[];let length=0;
  try{while(true){const {done,value}=await reader.read();if(done)break;length+=value.byteLength;if(length>limit){await reader.cancel();cFail(413,'BODY_TOO_LARGE','提交内容超过大小限制。');}chunks.push(value);}}finally{reader.releaseLock();}
  const bytes=new Uint8Array(length);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}return bytes;
}
async function cBody(request){if((request.headers.get('Content-Type')||'').split(';')[0].trim().toLowerCase()!=='application/json')cFail(415,'JSON_REQUIRED','请以 JSON 提交。');let value;try{value=JSON.parse(new TextDecoder().decode(await cBytes(request,32768)));}catch(error){if(error instanceof CommunityError)throw error;cFail(422,'INVALID_INPUT','JSON 内容无效。');}if(!value||typeof value!=='object'||Array.isArray(value))cFail(422,'INVALID_INPUT','需要 JSON 对象。');return value;}
function cDatabase(env){if(!env.DB?.prepare||!env.DB?.batch)cFail(503,'DB_UNAVAILABLE','云社区数据库尚未接入。');return env.DB;}
function cOnboarding(row){return {guideVersion:row.learn_guide_version,status:row.learn_guide_status,step:row.learn_guide_step,updatedAt:row.learn_guide_updated_at};}
async function cEnsureUser(db,identity){const now=cNow();await db.prepare("INSERT OR IGNORE INTO community_users (id,name,disabled,version,created_at,updated_at,mutation_token,learn_guide_version,learn_guide_status,learn_guide_step,learn_guide_updated_at) VALUES (?,'琴友',0,1,?,?,'',2,'pending',0,?)").bind(identity.id,now,now,now).run();const row=await db.prepare('SELECT * FROM community_users WHERE id=?').bind(identity.id).first();return {...identity,name:row.name,disabled:Boolean(row.disabled),version:row.version,onboarding:cOnboarding(row)};}
function cUser(row,admins){return {id:row.id,name:row.name,disabled:Boolean(row.disabled),isAdmin:Boolean(admins?.has(row.id)),version:row.version,createdAt:row.created_at,updatedAt:row.updated_at,onboarding:cOnboarding(row)};}
function cDefaultSettings(){return {version:0,postingEnabled:true,commentsEnabled:true,likesEnabled:true,allowExternalLinks:true,cloudPresetBackupEnabled:true,announcement:{zh:'',en:'',ja:'',de:''},catalogHiddenIds:[]};}
function cSettings(row){if(!row)return cDefaultSettings();return {version:row.version,postingEnabled:Boolean(row.posting_enabled),commentsEnabled:Boolean(row.comments_enabled),likesEnabled:Boolean(row.likes_enabled),allowExternalLinks:Boolean(row.allow_external_links),cloudPresetBackupEnabled:Boolean(row.cloud_preset_backup_enabled),announcement:JSON.parse(row.announcement_json),catalogHiddenIds:JSON.parse(row.catalog_hidden_ids_json),updatedAt:row.updated_at};}
async function cGetSettings(db){return cSettings(await db.prepare("SELECT * FROM community_settings WHERE id='global'").first());}
function cPost(row,actor,admin=false){const own=row.user_id===actor.id;const item={id:row.id,title:row.title,text:row.text,topic:row.topic,attachments:JSON.parse(row.attachments_json),rightsConfirmed:Boolean(row.rights_confirmed),status:row.status,version:row.version,moderationReason:row.moderation_reason,authorName:row.author_name||'琴友',isOwn:own,likeCount:Number(row.like_count||0),likedByMe:Boolean(row.liked_by_me),createdAt:row.created_at,updatedAt:row.updated_at,comments:[]};if(own||admin)item.clientRequestId=row.client_request_id;if(admin)item.userId=row.user_id;return item;}
function cComment(row,actor,admin=false){const own=row.user_id===actor.id;const item={id:row.id,postId:row.post_id,text:row.text,status:row.status,version:row.version,moderationReason:row.moderation_reason,authorName:row.author_name||'琴友',isOwn:own,createdAt:row.created_at,updatedAt:row.updated_at};if(own||admin)item.clientRequestId=row.client_request_id;if(admin)item.userId=row.user_id;return item;}
function cReport(row){return {id:row.id,userId:row.user_id,reporterName:row.reporter_name||'琴友',targetType:row.target_type,targetId:row.target_id,reason:row.reason,status:row.status,resolution:row.resolution,version:row.version,createdAt:row.created_at,updatedAt:row.updated_at};}
const cPostSelect="SELECT p.*,u.name AS author_name,(SELECT COUNT(*) FROM community_likes l WHERE l.post_id=p.id) AS like_count,(SELECT COUNT(*) FROM community_likes l WHERE l.post_id=p.id AND l.user_id=?) AS liked_by_me FROM community_posts p JOIN community_users u ON u.id=p.user_id ";
const cCommentSelect='SELECT c.*,u.name AS author_name FROM community_comments c JOIN community_users u ON u.id=c.user_id ';
async function cFindPost(db,id,actor){return db.prepare(cPostSelect+'WHERE p.id=?').bind(actor.id,id).first();}
async function cFindComment(db,id){return db.prepare(cCommentSelect+'WHERE c.id=?').bind(id).first();}
function cCatalog(env,settings){return (Array.isArray(env.CATALOG_SOURCE)?env.CATALOG_SOURCE:[]).map(item=>({id:item.id,title:item.title||item.titles?.zh||'',titles:item.titles||{},category:item.category||'',regions:item.regions||[],author:item.author||'',rightsStatus:item.rightsStatus||item.rights?.status||'pending',published:Boolean(item.published),visible:!settings.catalogHiddenIds.includes(item.id)}));}
async function cState(db,actor,env,admin=false){
  const statements=[db.prepare("SELECT * FROM community_settings WHERE id='global'")];
  if(admin){
    statements.push(db.prepare(cPostSelect+'ORDER BY p.updated_at DESC,p.id DESC LIMIT 200').bind(actor.id),db.prepare(cCommentSelect+'ORDER BY c.updated_at DESC,c.id DESC LIMIT 200'),db.prepare('SELECT r.*,u.name AS reporter_name FROM community_reports r JOIN community_users u ON u.id=r.user_id ORDER BY r.updated_at DESC,r.id DESC LIMIT 200'),db.prepare('SELECT * FROM community_users ORDER BY updated_at DESC,id DESC LIMIT 200'),db.prepare("SELECT * FROM community_audit WHERE target_type <> 'preset-backup' ORDER BY at DESC,id DESC LIMIT 200"),db.prepare("SELECT (SELECT COUNT(*) FROM community_posts WHERE status='pending') AS postsPending,(SELECT COUNT(*) FROM community_comments WHERE status='pending') AS commentsPending,(SELECT COUNT(*) FROM community_reports WHERE status='open') AS reportsOpen,(SELECT COUNT(*) FROM community_posts WHERE status='published') AS postsPublished,(SELECT COUNT(*) FROM community_users) AS users,(SELECT COUNT(*) FROM user_preset_backups WHERE json_array_length(presets_json)>0) AS presetOwners,(SELECT COALESCE(SUM(json_array_length(presets_json)),0) FROM user_preset_backups) AS presetCount"));
    const result=await db.batch(statements),settings=cSettings(result[0].results[0]);
    return {ok:true,viewer:{id:actor.id,name:actor.name,isAdmin:true,disabled:actor.disabled,version:actor.version,onboarding:actor.onboarding},settings,counts:result[6].results[0],posts:result[1].results.map(row=>cPost(row,actor,true)),comments:result[2].results.map(row=>cComment(row,actor,true)),reports:result[3].results.map(cReport),users:result[4].results.map(row=>cUser(row,actor.admins)),audit:result[5].results.map(row=>({id:row.id,actorId:row.actor_id,action:row.action,targetType:row.target_type,targetId:row.target_id,at:row.at,detail:JSON.parse(row.detail_json)})),catalog:cCatalog(env,settings),limits:COMMUNITY_LIMITS};
  }
  statements.push(db.prepare(cPostSelect+"WHERE p.status='published' ORDER BY p.created_at DESC,p.id DESC LIMIT 50").bind(actor.id),db.prepare(cPostSelect+'WHERE p.user_id=? ORDER BY p.updated_at DESC,p.id DESC LIMIT 100').bind(actor.id,actor.id),db.prepare(cCommentSelect+"JOIN community_posts p ON p.id=c.post_id WHERE (p.status='published' OR p.user_id=?) AND (c.status='published' OR c.user_id=?) ORDER BY c.created_at DESC,c.id DESC LIMIT 200").bind(actor.id,actor.id),db.prepare(cCommentSelect+'WHERE c.user_id=? ORDER BY c.updated_at DESC,c.id DESC LIMIT 100').bind(actor.id));
  const result=await db.batch(statements),posts=result[1].results.map(row=>cPost(row,actor)),mine=result[2].results.map(row=>cPost(row,actor)),comments=result[3].results.map(row=>cComment(row,actor));
  for(const item of [...posts,...mine])item.comments=comments.filter(comment=>comment.postId===item.id);
  return {ok:true,viewer:{id:actor.id,name:actor.name,isAdmin:actor.isAdmin,disabled:actor.disabled,version:actor.version,onboarding:actor.onboarding},settings:cSettings(result[0].results[0]),posts,mine,myComments:result[4].results.map(row=>cComment(row,actor)),limits:COMMUNITY_LIMITS};
}
async function cMutation(db,statement,actor,table,id,token,action,detail={}){
  const guard=db.prepare(`INSERT INTO community_audit (id,actor_id,action,target_type,target_id,detail_json,at) VALUES (?,?,CASE WHEN EXISTS (SELECT 1 FROM ${cTables[table]} WHERE id=? AND mutation_token=?) THEN ? ELSE '__cas_failed__' END,?,?,?,?)`).bind(token,actor.id,id,token,action,table,id,JSON.stringify(detail),cNow());
  try{return await db.batch([statement,guard]);}catch(error){if(/community_cas_guard|__cas_failed__/i.test(error.message||''))cFail(409,'CONFLICT','记录或权限已变化，刷新后重试。');throw error;}
}
const cAlive="EXISTS (SELECT 1 FROM community_users WHERE id=? AND disabled=0)";
async function cHash(value){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(byte=>byte.toString(16).padStart(2,'0')).join('');}
async function cAttachments(db,input,actor,settings,rights){
  if(input===undefined)return [];if(!Array.isArray(input)||input.length>4)cFail(422,'INVALID_INPUT','最多添加 4 个附件。');if(input.length&&rights!==true)cFail(422,'RIGHTS_REQUIRED','请确认附件为本人有权使用的内容。');
  const clean=[];
  for(const item of input){
    if(!item||typeof item!=='object'||Array.isArray(item))cFail(422,'INVALID_INPUT','附件无效。');
    if(item.kind==='media'){
      cKeys(item,['kind','mediaId','url','mime','size']);const mediaId=cId(item.mediaId),media=await db.prepare('SELECT * FROM community_media WHERE id=? AND user_id=?').bind(mediaId,actor.id).first();if(!media)cFail(403,'MEDIA_NOT_OWNED','只能使用本人上传的图片。');clean.push({kind:'media',mediaId,url:'/api/community/media/'+mediaId,mime:media.mime,size:media.size});
    }else if(item.kind==='video'){
      cKeys(item,['kind','mediaId','url','mime','size','duration','width','height','videoCodec','audioCodec','container','verification']);
      if(clean.some(value=>value.kind==='video'))cFail(422,'VIDEO_LIMIT','每篇帖子最多添加一条视频。');
      const media=await db.prepare('SELECT * FROM community_videos WHERE id=? AND user_id=?').bind(cId(item.mediaId),actor.id).first();
      if(!media)cFail(403,'MEDIA_NOT_OWNED','只能使用本人上传的视频。');if(media.state!=='ready'||media.cleanup_pending||media.upload_active)cFail(409,'VIDEO_NOT_READY','视频尚未完成校验或已经撤回。');
      clean.push(cVideoAttachment(media));
    }else if(item.kind==='url'){
      cKeys(item,['kind','url','title']);if(!settings.allowExternalLinks)cFail(422,'LINKS_DISABLED','管理员暂时关闭了外链。');let url;try{url=new URL(cText(item.url,2048,1));}catch{cFail(422,'INVALID_INPUT','外链地址无效。');}if(url.protocol!=='https:'||url.username||url.password)cFail(422,'INVALID_INPUT','只支持不含账号口令的 HTTPS 外链。');clean.push({kind:'url',url:url.href,title:cText(item.title??'',120)});
    }else if(item.kind==='local'){
      cKeys(item,['kind','id','name','mime','duration']);const duration=item.duration??0;if(typeof duration!=='number'||!Number.isFinite(duration)||duration<0||duration>86400)cFail(422,'INVALID_INPUT','本机媒体时长无效。');clean.push({kind:'local',id:cText(item.id,160,1),name:cText(item.name??'',120),mime:cText(item.mime??'',100),duration});
    }else cFail(422,'INVALID_INPUT','不支持的附件类型。');
  }
  return clean;
}
function cVideoGuard(attachments,owner){
  if(!attachments.some(item=>item.kind==='video'))return {sql:'1',args:[]};
  return {sql:"NOT EXISTS (SELECT 1 FROM json_each(?) attachment LEFT JOIN community_videos video ON video.id=json_extract(attachment.value,'$.mediaId') WHERE json_extract(attachment.value,'$.kind')='video' AND (video.id IS NULL OR video.user_id<>? OR video.state<>'ready' OR video.cleanup_pending<>0 OR video.upload_active<>0))",args:[JSON.stringify(attachments),owner]};
}
async function cOwnedPost(db,id,actor){const row=await cFindPost(db,cId(id),actor);if(!row)cFail(404,'NOT_FOUND','帖子不存在。');if(row.user_id!==actor.id)cFail(403,'NOT_OWNER','不能修改他人的帖子。');return row;}
function cEnabled(settings,key){if(!settings[key])cFail(403,'FEATURE_DISABLED','管理员暂时关闭了此功能。');}
async function cCommunityAction(db,actor,env,body){
  const settings=await cGetSettings(db),now=cNow(),token=cUuid();
  if(body.type==='onboarding-save'){
    cKeys(body,['type','guideVersion','step','status']);
    if(body.guideVersion!==cGuideVersion||!Number.isInteger(body.step)||body.step<0||body.step>6||!cGuideStatuses.includes(body.status))cFail(422,'INVALID_INPUT','教学版本、步骤或状态无效。');
    // Check the latest stored status inside the transaction: a late progress request must never reopen a finished guide.
    const terminal=cGuideTerminal.includes(body.status);
    try{await cMutation(db,db.prepare("UPDATE community_users SET learn_guide_version=2,learn_guide_status=?,learn_guide_step=?,learn_guide_updated_at=?,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND disabled=0 AND (learn_guide_status NOT IN ('completed','skipped') OR ?=1)").bind(body.status,body.step,now,now,token,actor.id,Number(terminal)),actor,'user',actor.id,token,'onboarding-save',{guideVersion:2,status:body.status,step:body.step});}
    catch(error){
      if(error.code!=='CONFLICT'||terminal)throw error;
      const current=await db.prepare('SELECT * FROM community_users WHERE id=?').bind(actor.id).first();
      if(!current||current.disabled||!cGuideTerminal.includes(current.learn_guide_status))throw error;
      // A completed/skipped guide is an acknowledged no-op; the failed batch changed neither data nor audit.
    }
    const row=await db.prepare('SELECT * FROM community_users WHERE id=?').bind(actor.id).first();
    actor.version=row.version;actor.onboarding=cOnboarding(row);return actor.onboarding;
  }
  if(body.type==='profile-save'){
    cKeys(body,['type','name','version']);const name=cText(body.name,40,1),version=body.version===undefined?actor.version:cVersion(body.version);
    await cMutation(db,db.prepare('UPDATE community_users SET name=?,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND version=? AND disabled=0').bind(name,now,token,actor.id,version),actor,'user',actor.id,token,'profile-save',{nameChanged:true});actor.name=name;actor.version=version+1;return cUser(await db.prepare('SELECT * FROM community_users WHERE id=?').bind(actor.id).first(),actor.admins);
  }
  if(body.type==='post-save'){
    cKeys(body,['type','id','version','clientRequestId','title','text','topic','attachments','rightsConfirmed']);cEnabled(settings,'postingEnabled');const title=cText(body.title??'',120),text=cText(body.text??'',5000),topic=body.topic??'practice';if(!['practice','help','work'].includes(topic))cFail(422,'INVALID_INPUT','话题无效。');const rights=body.rightsConfirmed===undefined?false:cBool(body.rightsConfirmed),attachments=await cAttachments(db,body.attachments,actor,settings,rights);
    const videoGuard=cVideoGuard(attachments,actor.id);
    if(body.id!==undefined){
      const row=await cOwnedPost(db,body.id,actor),version=cVersion(body.version);if(['hidden','deleted'].includes(row.status))cFail(409,'CONFLICT','隐藏或删除的帖子不能由作者直接恢复。');
      await cMutation(db,db.prepare("UPDATE community_posts SET title=?,text=?,topic=?,attachments_json=?,rights_confirmed=?,status='draft',moderation_reason='',version=version+1,updated_at=?,mutation_token=? WHERE id=? AND user_id=? AND version=? AND "+cAlive+" AND COALESCE((SELECT posting_enabled FROM community_settings WHERE id='global'),1)=1 AND "+videoGuard.sql).bind(title,text,topic,JSON.stringify(attachments),Number(rights),now,token,row.id,actor.id,version,actor.id,...videoGuard.args),actor,'post',row.id,token,'post-save',{previousStatus:row.status,status:'draft'});return cPost(await cFindPost(db,row.id,actor),actor);
    }
    const requestId=cId(body.clientRequestId),hash=await cHash({title,text,topic,attachments,rights}),prior=await db.prepare('SELECT * FROM community_posts WHERE user_id=? AND client_request_id=?').bind(actor.id,requestId).first();
    if(prior){if(prior.request_hash!==hash)cFail(409,'IDEMPOTENCY_CONFLICT','同一提交编号已用于不同内容。');return cPost(await cFindPost(db,prior.id,actor),actor);}
    const id=cUuid(),statement=db.prepare("INSERT OR IGNORE INTO community_posts (id,user_id,client_request_id,request_hash,title,text,topic,attachments_json,rights_confirmed,status,version,moderation_reason,created_at,updated_at,mutation_token) SELECT ?,?,?,?,?,?,?,?,?,'draft',1,'',?,?,? WHERE "+cAlive+" AND COALESCE((SELECT posting_enabled FROM community_settings WHERE id='global'),1)=1 AND "+videoGuard.sql).bind(id,actor.id,requestId,hash,title,text,topic,JSON.stringify(attachments),Number(rights),now,now,token,actor.id,...videoGuard.args);
    try{await cMutation(db,statement,actor,'post',id,token,'post-save',{status:'draft'});}catch(error){const replay=await db.prepare('SELECT * FROM community_posts WHERE user_id=? AND client_request_id=?').bind(actor.id,requestId).first();if(error.code==='CONFLICT'&&replay?.request_hash===hash)return cPost(await cFindPost(db,replay.id,actor),actor);throw error;}
    return cPost(await cFindPost(db,id,actor),actor);
  }
  if(body.type==='post-submit'||body.type==='post-delete'){
    cKeys(body,['type','id','version']);const row=await cOwnedPost(db,body.id,actor),version=cVersion(body.version),submit=body.type==='post-submit';if(submit){cEnabled(settings,'postingEnabled');if(row.status!=='draft'||(!row.title.trim()&&!row.text.trim()&&!JSON.parse(row.attachments_json).length))cFail(409,'CONFLICT','请先保存有内容的草稿，再提交审核。');if(!settings.allowExternalLinks&&JSON.parse(row.attachments_json).some(item=>item.kind==='url'))cFail(422,'LINKS_DISABLED','请移除已关闭的外链后提交。');}
    if(!submit&&row.status==='deleted')return cPost(row,actor);const status=submit?'pending':'deleted',videoGuard=submit?cVideoGuard(JSON.parse(row.attachments_json),actor.id):{sql:'1',args:[]};
    await cMutation(db,db.prepare('UPDATE community_posts SET status=?,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND user_id=? AND version=? AND '+cAlive+(submit?" AND status='draft' AND COALESCE((SELECT posting_enabled FROM community_settings WHERE id='global'),1)=1":'')+' AND '+videoGuard.sql).bind(status,now,token,row.id,actor.id,version,actor.id,...videoGuard.args),actor,'post',row.id,token,body.type,{previousStatus:row.status,status});return cPost(await cFindPost(db,row.id,actor),actor);
  }
  if(body.type==='comment-create'){
    cKeys(body,['type','postId','text','clientRequestId']);cEnabled(settings,'commentsEnabled');const postId=cId(body.postId),text=cText(body.text,1000,1),requestId=cId(body.clientRequestId),hash=await cHash({postId,text});const prior=await db.prepare('SELECT * FROM community_comments WHERE user_id=? AND client_request_id=?').bind(actor.id,requestId).first();if(prior){if(prior.request_hash!==hash)cFail(409,'IDEMPOTENCY_CONFLICT','同一提交编号已用于不同评论。');return cComment(await cFindComment(db,prior.id),actor);}
    const post=await cFindPost(db,postId,actor);if(!post||post.status!=='published')cFail(404,'NOT_FOUND','只能评论已发布的帖子。');const id=cUuid(),statement=db.prepare("INSERT OR IGNORE INTO community_comments (id,post_id,user_id,client_request_id,request_hash,text,status,version,moderation_reason,created_at,updated_at,mutation_token) SELECT ?,?,?,?,?,?,'pending',1,'',?,?,? WHERE "+cAlive+" AND EXISTS (SELECT 1 FROM community_posts WHERE id=? AND status='published') AND COALESCE((SELECT comments_enabled FROM community_settings WHERE id='global'),1)=1").bind(id,postId,actor.id,requestId,hash,text,now,now,token,actor.id,postId);
    try{await cMutation(db,statement,actor,'comment',id,token,'comment-create',{status:'pending'});}catch(error){const replay=await db.prepare('SELECT * FROM community_comments WHERE user_id=? AND client_request_id=?').bind(actor.id,requestId).first();if(error.code==='CONFLICT'&&replay?.request_hash===hash)return cComment(await cFindComment(db,replay.id),actor);throw error;}return cComment(await cFindComment(db,id),actor);
  }
  if(body.type==='comment-delete'){
    cKeys(body,['type','id','version']);const row=await cFindComment(db,cId(body.id));if(!row)cFail(404,'NOT_FOUND','评论不存在。');if(row.user_id!==actor.id)cFail(403,'NOT_OWNER','不能删除他人的评论。');const version=cVersion(body.version);await cMutation(db,db.prepare("UPDATE community_comments SET status='deleted',version=version+1,updated_at=?,mutation_token=? WHERE id=? AND user_id=? AND version=? AND "+cAlive).bind(now,token,row.id,actor.id,version,actor.id),actor,'comment',row.id,token,'comment-delete',{status:'deleted'});return cComment(await cFindComment(db,row.id),actor);
  }
  if(body.type==='like-set'){
    cKeys(body,['type','postId','liked']);cEnabled(settings,'likesEnabled');const postId=cId(body.postId),liked=cBool(body.liked),post=await cFindPost(db,postId,actor);if(!post||post.status!=='published')cFail(404,'NOT_FOUND','帖子尚未发布。');
    if(liked)await db.prepare("INSERT OR IGNORE INTO community_likes (post_id,user_id,created_at) SELECT ?,?,? WHERE "+cAlive+" AND EXISTS (SELECT 1 FROM community_posts WHERE id=? AND status='published') AND COALESCE((SELECT likes_enabled FROM community_settings WHERE id='global'),1)=1").bind(postId,actor.id,now,actor.id,postId).run();else await db.prepare('DELETE FROM community_likes WHERE post_id=? AND user_id=? AND '+cAlive).bind(postId,actor.id,actor.id).run();const item=await cFindPost(db,postId,actor);if(Boolean(item.liked_by_me)!==liked)cFail(409,'CONFLICT','点赞状态或权限已变化，请刷新。');return cPost(item,actor);
  }
  if(body.type==='report-create'){
    cKeys(body,['type','targetType','targetId','reason']);if(!['post','comment'].includes(body.targetType))cFail(422,'INVALID_INPUT','举报对象无效。');const targetId=cId(body.targetId),reason=cText(body.reason,500,1),target=body.targetType==='post'?await cFindPost(db,targetId,actor):await cFindComment(db,targetId);if(!target||target.status!=='published')cFail(404,'NOT_FOUND','只能举报已发布内容。');if(body.targetType==='comment'){const parent=await cFindPost(db,target.post_id,actor);if(parent?.status!=='published')cFail(404,'NOT_FOUND','内容尚未发布。');}
    const existing=await db.prepare("SELECT * FROM community_reports WHERE user_id=? AND target_type=? AND target_id=? AND status='open'").bind(actor.id,body.targetType,targetId).first();if(existing)return cReport(existing);const id=cUuid(),statement=db.prepare("INSERT OR IGNORE INTO community_reports (id,user_id,target_type,target_id,reason,status,resolution,version,created_at,updated_at,mutation_token) SELECT ?,?,?,?,?,'open','',1,?,?,? WHERE "+cAlive).bind(id,actor.id,body.targetType,targetId,reason,now,now,token,actor.id);
    try{await cMutation(db,statement,actor,'report',id,token,'report-create',{targetType:body.targetType,targetId});}catch(error){const replay=await db.prepare("SELECT * FROM community_reports WHERE user_id=? AND target_type=? AND target_id=? AND status='open'").bind(actor.id,body.targetType,targetId).first();if(error.code==='CONFLICT'&&replay)return cReport(replay);throw error;}return cReport(await db.prepare('SELECT * FROM community_reports WHERE id=?').bind(id).first());
  }
  cFail(422,'INVALID_ACTION','不支持的社区操作。');
}
const cPresetTones=new Set(['Acoustic','Warm','Bright','Electric','Bass','Piano','Organ','Strings','Pad']);
function cPresetRecords(value){
  if(!Array.isArray(value)||value.length>100)cFail(422,'INVALID_INPUT','云备份最多保存 100 套预设。');
  const ids=new Set();
  return value.map(item=>{
    if(!item||typeof item!=='object'||Array.isArray(item))cFail(422,'INVALID_INPUT','预设格式无效。');
    cKeys(item,['id','name','group','preset','effects','inputGain']);
    const id=cText(item.id,160,1),name=cText(item.name,80,1),group=cText(item.group??'',60);
    if(!/^[a-zA-Z0-9_-]+$/.test(id)||ids.has(id)||!cPresetTones.has(item.preset))cFail(422,'INVALID_INPUT','预设编号、名称或音色无效。');ids.add(id);
    if(!item.effects||typeof item.effects!=='object'||Array.isArray(item.effects))cFail(422,'INVALID_INPUT','预设效果参数无效。');
    cKeys(item.effects,['volume','reverb','delay','compression']);const effects={};
    for(const key of ['volume','reverb','delay','compression']){
      const number=item.effects[key];if(typeof number!=='number'||!Number.isFinite(number)||number<0||number>1)cFail(422,'INVALID_INPUT','效果参数须为 0 到 1。');effects[key]=number;
    }
    // Digital microphone-recording gain only; this is never a claim of hardware pickup control.
    const inputGain=item.inputGain??1;if(typeof inputGain!=='number'||!Number.isFinite(inputGain)||inputGain<0||inputGain>2)cFail(422,'INVALID_INPUT','麦克风录音数字增益须为 0 到 2。');
    return {id,name,group,preset:item.preset,effects,inputGain};
  });
}
async function cPresetState(db,actor){
  const row=await db.prepare('SELECT presets_json,version,updated_at FROM user_preset_backups WHERE user_id=?').bind(actor.id).first();
  const settings=await cGetSettings(db);
  return {ok:true,viewer:{id:actor.id},backup:row?{version:row.version,updatedAt:row.updated_at,presets:JSON.parse(row.presets_json)}:{version:0,updatedAt:null,presets:[]},features:{cloudPresetBackupEnabled:settings.cloudPresetBackupEnabled}};
}
async function cPresetAction(db,actor,body){
  if(!['save','clear'].includes(body.type))cFail(422,'INVALID_ACTION','不支持的云预设操作。');
  cKeys(body,body.type==='save'?['type','version','presets','accountId']:['type','version','accountId']);
  if(cText(body.accountId,256,1)!==actor.id)cFail(409,'STALE_USER','登录账号已变化，请刷新当前账号的云备份后重试。');
  const version=cVersion(body.version,true);if(version===Number.MAX_SAFE_INTEGER)cFail(422,'INVALID_INPUT','云备份版本超出范围。');const presets=body.type==='save'?cPresetRecords(body.presets):[],clear=body.type==='clear',settings=await cGetSettings(db);
  if(!clear&&!settings.cloudPresetBackupEnabled)cFail(403,'FEATURE_DISABLED','管理员暂时关闭了新的云预设备份；本机功能、读取和清空仍可使用。');
  const now=cNow(),token=cUuid(),statement=db.prepare('INSERT INTO user_preset_backups (user_id,presets_json,version,updated_at,mutation_token) SELECT ?,?,?,?,? WHERE '+cAlive+' AND (?=0 OR EXISTS (SELECT 1 FROM user_preset_backups WHERE user_id=? AND version=?))'+(clear?'':" AND COALESCE((SELECT cloud_preset_backup_enabled FROM community_settings WHERE id='global'),1)=1")+' ON CONFLICT(user_id) DO UPDATE SET presets_json=excluded.presets_json,version=user_preset_backups.version+1,updated_at=excluded.updated_at,mutation_token=excluded.mutation_token WHERE user_preset_backups.version=?').bind(actor.id,JSON.stringify(presets),version+1,now,token,actor.id,version,actor.id,version,version);
  const guard=db.prepare("INSERT INTO community_audit (id,actor_id,action,target_type,target_id,detail_json,at) VALUES (?,?,CASE WHEN EXISTS (SELECT 1 FROM user_preset_backups WHERE user_id=? AND mutation_token=?) THEN ? ELSE '__cas_failed__' END,'preset-backup',?,?,?)").bind(token,actor.id,actor.id,token,clear?'preset-backup-clear':'preset-backup-save',actor.id,JSON.stringify({count:presets.length,version:version+1}),now);
  try{await db.batch([statement,guard]);}catch(error){if(/community_cas_guard|__cas_failed__/i.test(error.message||''))cFail(409,'CONFLICT','云备份版本或权限已变化，请刷新核对后重试。');throw error;}
  return cPresetState(db,actor);
}
async function cSaveSettings(db,actor,current,next,version,action,detail){
  const token=cUuid(),now=cNow(),statement=db.prepare("INSERT INTO community_settings (id,posting_enabled,comments_enabled,likes_enabled,allow_external_links,cloud_preset_backup_enabled,announcement_json,catalog_hidden_ids_json,version,updated_at,mutation_token) SELECT 'global',?,?,?,?,?,?,?,?,?,? WHERE "+cAlive+" ON CONFLICT(id) DO UPDATE SET posting_enabled=excluded.posting_enabled,comments_enabled=excluded.comments_enabled,likes_enabled=excluded.likes_enabled,allow_external_links=excluded.allow_external_links,cloud_preset_backup_enabled=excluded.cloud_preset_backup_enabled,announcement_json=excluded.announcement_json,catalog_hidden_ids_json=excluded.catalog_hidden_ids_json,version=community_settings.version+1,updated_at=excluded.updated_at,mutation_token=excluded.mutation_token WHERE community_settings.version=?").bind(Number(next.postingEnabled),Number(next.commentsEnabled),Number(next.likesEnabled),Number(next.allowExternalLinks),Number(next.cloudPresetBackupEnabled),JSON.stringify(next.announcement),JSON.stringify(next.catalogHiddenIds),version+1,now,token,actor.id,version);
  if(current.version!==version)cFail(409,'CONFLICT','内容设置已变化，请刷新后重试。');await cMutation(db,statement,actor,'settings','global',token,action,detail);return cGetSettings(db);
}
async function cAdminAction(db,actor,env,body){
  const now=cNow(),token=cUuid();
  if(body.type==='moderate'){
    cKeys(body,['type','targetType','id','version','action','reason']);if(!['post','comment'].includes(body.targetType)||!['approve','reject','hide','restore'].includes(body.action))cFail(422,'INVALID_INPUT','审核操作无效。');const table=cTables[body.targetType],id=cId(body.id),version=cVersion(body.version),row=await db.prepare(`SELECT * FROM ${table} WHERE id=?`).bind(id).first();if(!row)cFail(404,'NOT_FOUND','内容不存在。');let status;
    if(body.action==='approve'&&row.status==='pending')status='published';else if(body.action==='reject'&&row.status==='pending')status='rejected';else if(body.action==='hide'&&row.status==='published')status='hidden';else if(body.action==='restore'&&row.status==='hidden')status='published';else if(body.action==='restore'&&row.status==='deleted')status=body.targetType==='post'?'draft':'pending';else cFail(409,'CONFLICT','当前状态不允许此审核操作。');
    const videoGuard=body.targetType==='post'&&['published','draft'].includes(status)?cVideoGuard(JSON.parse(row.attachments_json),row.user_id):{sql:'1',args:[]};
    const reason=cText(body.reason??'',500,['reject','hide'].includes(body.action)?1:0);await cMutation(db,db.prepare(`UPDATE ${table} SET status=?,moderation_reason=?,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND version=? AND status=? AND ${cAlive} AND ${videoGuard.sql}`).bind(status,reason,now,token,id,version,row.status,actor.id,...videoGuard.args),actor,body.targetType,id,token,'moderate-'+body.action,{previousStatus:row.status,status,reason});return body.targetType==='post'?cPost(await cFindPost(db,id,actor),actor,true):cComment(await cFindComment(db,id),actor,true);
  }
  if(body.type==='report-resolve'){
    cKeys(body,['type','id','version','status','resolution']);const id=cId(body.id),version=cVersion(body.version);if(!['resolved','dismissed'].includes(body.status))cFail(422,'INVALID_INPUT','举报处理状态无效。');const resolution=cText(body.resolution,500,1),row=await db.prepare('SELECT * FROM community_reports WHERE id=?').bind(id).first();if(!row)cFail(404,'NOT_FOUND','举报不存在。');if(row.status!=='open')cFail(409,'CONFLICT','举报已处理。');await cMutation(db,db.prepare("UPDATE community_reports SET status=?,resolution=?,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND version=? AND status='open' AND "+cAlive).bind(body.status,resolution,now,token,id,version,actor.id),actor,'report',id,token,'report-resolve',{status:body.status,resolution});return cReport(await db.prepare('SELECT * FROM community_reports WHERE id=?').bind(id).first());
  }
  if(body.type==='user-set'){
    cKeys(body,['type','id','version','disabled']);const id=cText(body.id,256,1),version=cVersion(body.version),disabled=cBool(body.disabled);if(actor.admins.has(id)&&disabled)cFail(409,'ADMIN_PROTECTED','不能停用管理员身份。');const row=await db.prepare('SELECT * FROM community_users WHERE id=?').bind(id).first();if(!row)cFail(404,'NOT_FOUND','用户不存在。');await cMutation(db,db.prepare('UPDATE community_users SET disabled=?,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND version=? AND '+cAlive).bind(Number(disabled),now,token,id,version,actor.id),actor,'user',id,token,'user-set',{disabled});return cUser(await db.prepare('SELECT * FROM community_users WHERE id=?').bind(id).first(),actor.admins);
  }
  if(body.type==='settings-save'){
    cKeys(body,['type','version','postingEnabled','commentsEnabled','likesEnabled','allowExternalLinks','cloudPresetBackupEnabled','announcement']);const current=await cGetSettings(db),next={...current},version=cVersion(body.version,true);for(const key of ['postingEnabled','commentsEnabled','likesEnabled','allowExternalLinks','cloudPresetBackupEnabled'])if(body[key]!==undefined)next[key]=cBool(body[key]);if(body.announcement!==undefined){if(!body.announcement||typeof body.announcement!=='object'||Array.isArray(body.announcement))cFail(422,'INVALID_INPUT','公告需要四种语言。');cKeys(body.announcement,cLangs);next.announcement=Object.fromEntries(cLangs.map(lang=>[lang,cText(body.announcement[lang],1000)]));}return cSaveSettings(db,actor,current,next,version,'settings-save',{fields:Object.keys(body).filter(key=>!['type','version'].includes(key))});
  }
  if(body.type==='catalog-set'){
    cKeys(body,['type','id','visible','version']);const id=cText(body.id,160,1),visible=cBool(body.visible),version=cVersion(body.version,true),current=await cGetSettings(db);if(!cCatalog(env,current).some(item=>item.id===id))cFail(422,'UNKNOWN_CATALOG_ITEM','只能调整随站点提供的曲目。');const hidden=new Set(current.catalogHiddenIds);if(visible)hidden.delete(id);else hidden.add(id);return cSaveSettings(db,actor,current,{...current,catalogHiddenIds:[...hidden].sort()},version,'catalog-set',{id,visible,rightsAuthorization:false});
  }
  cFail(422,'INVALID_ACTION','不支持的后台操作。');
}
function cImage(bytes,mime){
  if(mime==='image/png'){if(bytes.length<33||![137,80,78,71,13,10,26,10].every((value,i)=>bytes[i]===value)||String.fromCharCode(...bytes.slice(12,16))!=='IHDR')return false;const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),w=view.getUint32(16),h=view.getUint32(20);return view.getUint32(8)===13&&w>0&&h>0&&w<=12000&&h<=12000&&w*h<=36000000;}
  if(mime==='image/jpeg')return bytes.length>=4&&bytes[0]===255&&bytes[1]===216&&bytes[2]===255&&bytes.at(-2)===255&&bytes.at(-1)===217;
  if(mime==='image/webp')return bytes.length>=16&&String.fromCharCode(...bytes.slice(0,4))==='RIFF'&&String.fromCharCode(...bytes.slice(8,12))==='WEBP'&&new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength).getUint32(4,true)+8===bytes.length;
  return false;
}
async function cUpload(request,db,actor,env){
  if(!env.BUCKET?.put||!env.BUCKET?.delete)cFail(503,'UPLOAD_UNAVAILABLE','图片云存储尚未接入。');const settings=await cGetSettings(db);cEnabled(settings,'postingEnabled');const mime=(request.headers.get('Content-Type')||'').split(';')[0].trim().toLowerCase();if(!['image/png','image/jpeg','image/webp'].includes(mime))cFail(415,'IMAGE_REQUIRED','只支持 PNG、JPEG 或 WebP 图片。');const bytes=await cBytes(request,COMMUNITY_LIMITS.imageBytes);if(!cImage(bytes,mime))cFail(422,'INVALID_IMAGE','图片格式与内容不匹配或尺寸过大。');const id=cUuid(),key='community-images/'+id,token=cUuid(),now=cNow();
  await env.BUCKET.put(key,bytes,{httpMetadata:{contentType:mime,cacheControl:'private, no-store'}});
  try{await cMutation(db,db.prepare('INSERT INTO community_media (id,user_id,object_key,mime,size,created_at,mutation_token) SELECT ?,?,?,?,?,?,? WHERE '+cAlive+" AND COALESCE((SELECT posting_enabled FROM community_settings WHERE id='global'),1)=1").bind(id,actor.id,key,mime,bytes.byteLength,now,token,actor.id),actor,'media',id,token,'media-upload',{mime,size:bytes.byteLength});}catch(error){try{await env.BUCKET.delete(key);}catch{}throw error;}
  return cResponse({ok:true,media:{id,url:'/api/community/media/'+id,mime,size:bytes.byteLength}},201);
}
async function cMedia(request,db,actor,env,id){
  const row=await db.prepare('SELECT * FROM community_media WHERE id=?').bind(cId(id)).first();if(!row)cFail(404,'NOT_FOUND','图片不存在。');if(row.user_id!==actor.id&&!actor.isAdmin){const published=await db.prepare("SELECT 1 AS allowed FROM community_posts p,json_each(p.attachments_json) a WHERE p.status='published' AND json_extract(a.value,'$.mediaId')=? LIMIT 1").bind(row.id).first();if(!published)cFail(403,'MEDIA_PRIVATE','这张图片尚未公开给站点访客。');}
  if(!env.BUCKET?.get)cFail(503,'UPLOAD_UNAVAILABLE','图片云存储尚未接入。');const object=await env.BUCKET.get(row.object_key);if(!object)cFail(404,'NOT_FOUND','图片文件不存在。');return new Response(request.method==='HEAD'?null:object.body,{headers:{'Content-Type':row.mime,'Content-Length':String(row.size),'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin','Content-Disposition':'inline; filename="image-'+row.id+'.'+({['image/png']:'png',['image/jpeg']:'jpg',['image/webp']:'webp'})[row.mime]+'"','Vary':'Cookie, oai-authenticated-user-id'}});
}

// At most one buffered video inspection per isolate. Other requests (including cancellation)
// remain available. The existing image endpoint keeps its original limits and behavior.
let cVideoUploads=0;
function cVideoAttachment(row){return {kind:'video',mediaId:row.id,url:'/api/community/videos/'+row.id,mime:row.mime,size:row.size,duration:row.duration_ms/1000,width:row.width,height:row.height,container:row.container,videoCodec:row.video_codec,audioCodec:row.audio_codec,verification:row.verification};}
function cVideoInfo(row){return {...cVideoAttachment(row),id:row.id,state:row.state,version:row.version,cleanupPending:Boolean(row.cleanup_pending),uploadActive:Boolean(row.upload_active),errorCode:row.error_code,createdAt:row.created_at,updatedAt:row.updated_at};}
async function cVideoRow(db,id){return db.prepare('SELECT * FROM community_videos WHERE id=?').bind(cId(id)).first();}
function cVideoOwner(row,actor){if(!row)cFail(404,'NOT_FOUND','视频记录不存在。');if(row.user_id!==actor.id&&!actor.isAdmin)cFail(403,'NOT_OWNER','不能操作他人的视频。');return row;}
function cVideoAccount(value,actor){if(cText(value??'',256,1)!==actor.id)cFail(409,'STALE_USER','账号已变化，请刷新后再操作视频。');}
const cVideoUnused="NOT EXISTS (SELECT 1 FROM community_posts post,json_each(post.attachments_json) attachment WHERE post.status<>'deleted' AND json_extract(attachment.value,'$.kind')='video' AND json_extract(attachment.value,'$.mediaId')=community_videos.id)";
async function cVideoCleanup(db,row,actor,env){
  if(row.upload_active||!row.cleanup_pending)return row;
  if(!env.BUCKET?.delete)cFail(503,'UPLOAD_UNAVAILABLE','视频云存储尚未接入。');
  try{await env.BUCKET.delete(row.object_key);}catch{
    await db.prepare("UPDATE community_videos SET error_code='VIDEO_CLEANUP_PENDING',updated_at=? WHERE id=? AND cleanup_pending=1").bind(cNow(),row.id).run();
    return cVideoRow(db,row.id);
  }
  const token=cUuid();try{await cMutation(db,db.prepare("UPDATE community_videos SET state=CASE WHEN state='deleting' THEN 'deleted' ELSE state END,cleanup_pending=0,error_code='',version=version+1,updated_at=?,mutation_token=? WHERE id=? AND upload_active=0 AND cleanup_pending=1 AND state IN ('cancelled','deleting','failed')").bind(cNow(),token,row.id),actor,'video',row.id,token,'video-cleanup',{objectDeleted:true});}
  catch(error){const current=await cVideoRow(db,row.id);if(error.code==='CONFLICT'&&current&&!current.cleanup_pending&&!current.upload_active)return current;throw error;}
  return cVideoRow(db,row.id);
}
async function cVideoWithdraw(request,db,actor,env,id,intent){
  const body=await cBody(request);cKeys(body,['accountId']);cVideoAccount(body.accountId,actor);id=cId(id);
  let row=await cVideoRow(db,id);if(row)cVideoOwner(row,actor);
  if(!row){
    if(intent!=='cancel')cFail(404,'NOT_FOUND','视频记录不存在。');
    // A cancellation may reach the service before the raw-body upload. Preserve that tombstone.
    const token=cUuid(),now=cNow();
    try{await cMutation(db,db.prepare("INSERT OR IGNORE INTO community_videos (id,user_id,object_key,state,upload_token,created_at,updated_at,mutation_token) SELECT ?,?,?,'cancelled',?,?,?,? WHERE "+cAlive).bind(id,actor.id,'community-videos/'+id+'/'+token,token,now,now,token,actor.id),actor,'video',id,token,'video-cancel',{beforeUpload:true});}catch(error){row=await cVideoRow(db,id);if(!row)throw error;cVideoOwner(row,actor);}
    row=await cVideoRow(db,id);
  }
  if(row.state==='deleted')return cResponse({ok:true,media:cVideoInfo(row)},200);
  if(row.state==='cancelled'&&intent==='cancel'){
    row=await cVideoCleanup(db,row,actor,env);return cResponse({ok:true,media:cVideoInfo(row)},row.cleanup_pending||row.upload_active?202:200);
  }
  if(row.state==='deleting'){
    row=await cVideoCleanup(db,row,actor,env);return cResponse({ok:true,media:cVideoInfo(row)},row.cleanup_pending||row.upload_active?202:200);
  }
  const token=cUuid(),target=intent==='cancel'?'cancelled':'deleting';
  try{await cMutation(db,db.prepare("UPDATE community_videos SET state=?,cleanup_pending=CASE WHEN upload_active=1 OR cleanup_pending=1 OR state='ready' THEN 1 ELSE 0 END,error_code='',version=version+1,updated_at=?,mutation_token=? WHERE id=? AND version=? AND "+cVideoUnused).bind(target,cNow(),token,id,row.version),actor,'video',id,token,'video-'+intent,{state:target});}
  catch(error){if(error.code==='CONFLICT'&&await db.prepare("SELECT 1 AS used FROM community_posts post,json_each(post.attachments_json) attachment WHERE post.status<>'deleted' AND json_extract(attachment.value,'$.kind')='video' AND json_extract(attachment.value,'$.mediaId')=? LIMIT 1").bind(id).first())cFail(409,'MEDIA_IN_USE','请先从所有未删除的帖子中移除此视频，再删除云文件。');throw error;}
  row=await cVideoCleanup(db,await cVideoRow(db,id),actor,env);
  // No object was ever written for an early/failed upload; deleting is immediately complete.
  if(row.state==='deleting'&&!row.cleanup_pending&&!row.upload_active){const finish=cUuid();await cMutation(db,db.prepare("UPDATE community_videos SET state='deleted',version=version+1,updated_at=?,mutation_token=? WHERE id=? AND state='deleting' AND upload_active=0 AND cleanup_pending=0").bind(cNow(),finish,id),actor,'video',id,finish,'video-delete',{objectDeleted:true});row=await cVideoRow(db,id);}
  return cResponse({ok:true,media:cVideoInfo(row)},row.cleanup_pending||row.upload_active?202:200);
}
async function cVideoUpload(request,db,actor,env){
  if(!env.BUCKET?.put||!env.BUCKET?.delete)cFail(503,'UPLOAD_UNAVAILABLE','视频云存储尚未接入。');
  cVideoAccount(request.headers.get('X-Account-Id'),actor);const id=cId(request.headers.get('X-Client-Request-Id'));
  const mime=(request.headers.get('Content-Type')||'').split(';')[0].trim().toLowerCase();if(!['video/mp4','video/webm'].includes(mime))cFail(415,'VIDEO_UNSUPPORTED','只支持经过校验的 MP4 或 WebM 视频。');
  cEnabled(await cGetSettings(db),'postingEnabled');let previous=await cVideoRow(db,id);
  if(previous&&previous.user_id!==actor.id)cFail(403,'NOT_OWNER','上传编号已属于其他账号。');
  if(previous&&previous.state!=='ready')cFail(409,previous.state==='uploading'?'VIDEO_UPLOAD_IN_PROGRESS':'VIDEO_UPLOAD_CLOSED','请核对原上传状态；失败或取消后使用新的上传编号。');
  if(cVideoUploads)cFail(429,'VIDEO_BUSY','当前视频正在处理，请稍后重试。');cVideoUploads++;
  const uploadToken=cUuid(),key='community-videos/'+id+'/'+uploadToken;let claimed=false,putStarted=false,hash='';
  try{
    if(!previous){const token=cUuid(),now=cNow();
      await cMutation(db,db.prepare("INSERT OR IGNORE INTO community_videos (id,user_id,object_key,mime,state,upload_active,upload_token,created_at,updated_at,mutation_token) SELECT ?,?,?,?,'uploading',1,?,?,?,? WHERE "+cAlive+" AND COALESCE((SELECT posting_enabled FROM community_settings WHERE id='global'),1)=1 AND (SELECT COUNT(*) FROM community_videos WHERE user_id=? AND state IN ('uploading','ready','deleting'))<?").bind(id,actor.id,key,mime,uploadToken,now,now,token,actor.id,actor.id,COMMUNITY_LIMITS.videosPerUser),actor,'video',id,token,'video-upload-start',{mime});claimed=true;
    }
    const bytes=await cBytes(request,COMMUNITY_LIMITS.videoBytes);let inspection;
    try{inspection=inspectVideo(bytes,mime);}catch(error){cFail(error.status||422,error.code||'VIDEO_INVALID',error.message||'视频格式无效。');}
    hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(byte=>byte.toString(16).padStart(2,'0')).join('');
    if(previous){if(previous.request_hash!==hash||previous.mime!==mime)cFail(409,'IDEMPOTENCY_CONFLICT','相同上传编号已用于不同视频。');previous=await cVideoRow(db,id);if(previous.state!=='ready'||previous.cleanup_pending||previous.upload_active)cFail(409,'VIDEO_UPLOAD_CLOSED','原视频已撤回，请核对当前状态。');return cResponse({ok:true,media:cVideoInfo(previous),replayed:true},200);}
    if(request.signal?.aborted)cFail(409,'VIDEO_UPLOAD_CANCELLED','上传已取消。');
    const durationMs=Math.ceil(inspection.duration*1000);if(!Number.isSafeInteger(durationMs)||durationMs<1||durationMs>60000)cFail(422,'VIDEO_DURATION','社区视频须在60秒以内。');
    const token=cUuid();await cMutation(db,db.prepare("UPDATE community_videos SET request_hash=?,size=?,duration_ms=?,width=?,height=?,container=?,video_codec=?,audio_codec=?,verification=?,cleanup_pending=1,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND state='uploading' AND upload_token=? AND upload_active=1 AND "+cAlive+" AND COALESCE((SELECT posting_enabled FROM community_settings WHERE id='global'),1)=1").bind(hash,bytes.byteLength,durationMs,inspection.width,inspection.height,inspection.container,inspection.videoCodec,inspection.audioCodec||'',inspection.durationVerification||'container-timeline',cNow(),token,id,uploadToken,actor.id),actor,'video',id,token,'video-validated',{size:bytes.byteLength,durationMs,container:inspection.container});
    // The key was persisted before PUT. A late completion can only touch this attempt's key.
    putStarted=true;await env.BUCKET.put(key,bytes,{httpMetadata:{contentType:mime,cacheControl:'private, no-store'}});
    if(request.signal?.aborted)cFail(409,'VIDEO_UPLOAD_CANCELLED','上传已取消。');
    const finish=cUuid();await cMutation(db,db.prepare("UPDATE community_videos SET state='ready',upload_active=0,cleanup_pending=0,error_code='',version=version+1,updated_at=?,mutation_token=? WHERE id=? AND state='uploading' AND upload_token=? AND upload_active=1 AND "+cAlive+" AND COALESCE((SELECT posting_enabled FROM community_settings WHERE id='global'),1)=1").bind(cNow(),finish,id,uploadToken,actor.id),actor,'video',id,finish,'video-upload-ready',{size:bytes.byteLength,durationMs});
    return cResponse({ok:true,media:cVideoInfo(await cVideoRow(db,id)),replayed:false},201);
  }catch(error){
    if(!claimed){
      // INSERT may have committed even if its acknowledgement was lost.
      const uncertain=await cVideoRow(db,id);if(uncertain?.upload_token===uploadToken)claimed=true;else throw error;
    }
    let row;try{row=await cVideoRow(db,id);}catch{}
    // A lost D1 response after a committed final transaction must not delete a ready object.
    if(row?.state==='ready'&&row.upload_token===uploadToken&&row.request_hash===hash)return cResponse({ok:true,media:cVideoInfo(row),replayed:true},200);
    let cleaned=!putStarted;
    if(putStarted){try{await env.BUCKET.delete(key);cleaned=true;}catch{cleaned=false;}}
    const code=error.code||'VIDEO_UPLOAD_FAILED';
    try{
      const token=cUuid();await cMutation(db,db.prepare("UPDATE community_videos SET state=CASE WHEN state='uploading' THEN 'failed' WHEN state='deleting' AND ?=0 THEN 'deleted' ELSE state END,upload_active=0,cleanup_pending=?,error_code=?,version=version+1,updated_at=?,mutation_token=? WHERE id=? AND upload_token=? AND state<>'ready'").bind(Number(!cleaned),Number(!cleaned),cleaned?code:'VIDEO_CLEANUP_PENDING',cNow(),token,id,uploadToken),actor,'video',id,token,'video-upload-stopped',{cleanupPending:!cleaned,errorCode:code});
      row=await cVideoRow(db,id);
    }catch{
      // Persisted uploading/cleanup state is deliberately not reported as successfully cleaned.
      cFail(503,'VIDEO_STATE_UNCONFIRMED','上传状态尚未确认，请核对原编号，勿重复提交。');
    }
    if(['cancelled','deleting','deleted'].includes(row.state))return cResponse({ok:true,media:cVideoInfo(row),replayed:false},row.cleanup_pending?202:200);
    if(row.cleanup_pending)cFail(503,'VIDEO_CLEANUP_PENDING','视频未完成，云端清理待确认；请重试取消并核对状态。');
    if(error instanceof CommunityError)throw error;cFail(503,'VIDEO_UPLOAD_FAILED','视频上传未完成，本机原文件仍可保留。');
  }finally{cVideoUploads--;}
}
function cVideoRange(value,size){
  if(!value||!value.startsWith('bytes='))return null;if(value.includes(','))return null;
  const match=/^bytes=(\d*)-(\d*)$/.exec(value);if(!match||!match[1]&&!match[2])return false;
  let start,end;if(!match[1]){const suffix=Number(match[2]);if(!Number.isSafeInteger(suffix)||suffix<1)return false;start=Math.max(0,size-suffix);end=size-1;}
  else{start=Number(match[1]);end=match[2]?Number(match[2]):size-1;if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start>=size||start>end)return false;end=Math.min(end,size-1);}
  return {offset:start,length:end-start+1};
}
async function cVideoRead(request,db,actor,env,id){
  const row=await cVideoRow(db,id);if(!row)cFail(404,'NOT_FOUND','视频不存在。');
  if(row.user_id!==actor.id&&!actor.isAdmin){const published=await db.prepare("SELECT 1 AS allowed FROM community_posts post,json_each(post.attachments_json) attachment WHERE post.status='published' AND json_extract(attachment.value,'$.kind')='video' AND json_extract(attachment.value,'$.mediaId')=? LIMIT 1").bind(row.id).first();if(!published)cFail(403,'MEDIA_PRIVATE','此视频尚未向站点访客公开。');}
  if(row.state!=='ready'||row.cleanup_pending||row.upload_active)cFail(410,'VIDEO_UNAVAILABLE','此视频已撤回或尚未准备好。');
  if(!env.BUCKET?.get)cFail(503,'UPLOAD_UNAVAILABLE','视频云存储尚未接入。');
  const etag='"sha256-'+row.request_hash+'"',headers={'Content-Type':row.mime,'Content-Length':String(row.size),'Accept-Ranges':'bytes','ETag':etag,'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin','Content-Disposition':'inline; filename="video-'+row.id+'.'+(row.mime==='video/mp4'?'mp4':'webm')+'"','Vary':'Cookie, oai-authenticated-user-id'};
  let range=request.method==='HEAD'?null:cVideoRange(request.headers.get('If-Range')&&request.headers.get('If-Range')!==etag?null:request.headers.get('Range'),row.size);
  if(range===false){delete headers['Content-Length'];headers['Content-Range']='bytes */'+row.size;return new Response(null,{status:416,headers});}
  if(request.method==='HEAD'){
    const object=env.BUCKET.head?await env.BUCKET.head(row.object_key):await env.BUCKET.get(row.object_key,{range:{offset:0,length:1}});if(!object)cFail(404,'NOT_FOUND','视频云文件不存在。');try{await object.body?.cancel?.();}catch{}return new Response(null,{headers});
  }
  const object=await env.BUCKET.get(row.object_key,range?{range}:undefined);if(!object)cFail(404,'NOT_FOUND','视频云文件不存在。');
  if(range){if(object.range?.offset!==range.offset||object.range?.length!==range.length){try{await object.body?.cancel?.();}catch{}cFail(503,'VIDEO_RANGE_UNAVAILABLE','云存储未返回请求的片段。');}headers['Content-Length']=String(range.length);headers['Content-Range']='bytes '+range.offset+'-'+(range.offset+range.length-1)+'/'+row.size;}
  return new Response(object.body,{status:range?206:200,headers});
}

export async function handleAPI(request,env){
  const path=new URL(request.url).pathname;if(path!=='/api/identity'&&path!=='/api/presets'&&!path.startsWith('/api/community')&&!path.startsWith('/api/admin'))return null;const requestId=cUuid();
  try{
    const identity=cIdentity(request,env);
    if(path==='/api/identity'){if(request.method!=='GET')cFail(405,'METHOD_NOT_ALLOWED','只支持 GET。');return cResponse({ok:true,viewer:{id:identity.id,name:'琴友',isAdmin:identity.isAdmin}});}
    const admin=path.startsWith('/api/admin');if(admin&&!identity.admins)cFail(503,'ADMIN_CONFIG_REQUIRED','管理员身份白名单尚未配置。');if(admin&&!identity.isAdmin)cFail(403,'ADMIN_REQUIRED','需要站点管理员权限。');
    const db=cDatabase(env),actor=await cEnsureUser(db,identity),isPost=request.method==='POST';if(isPost){cOrigin(request);if(actor.disabled)cFail(403,'USER_DISABLED','当前账号已暂停提交内容。');}
    if(path==='/api/presets'){if(request.method==='GET')return cResponse(await cPresetState(db,actor));if(isPost)return cResponse(await cPresetAction(db,actor,await cBody(request)));cFail(405,'METHOD_NOT_ALLOWED','只支持 GET 或 POST。');}
    if(path==='/api/community/media'&&isPost)return await cUpload(request,db,actor,env);
    if(path.startsWith('/api/community/media/')&&['GET','HEAD'].includes(request.method))return await cMedia(request,db,actor,env,path.slice('/api/community/media/'.length));
    if(path==='/api/community/videos'&&isPost)return await cVideoUpload(request,db,actor,env);
    const videoPath=/^\/api\/community\/videos\/([^/]+)(?:\/(status|cancel|delete))?$/.exec(path);
    if(videoPath){const id=cId(videoPath[1]);if(videoPath[2]==='status'&&request.method==='GET')return cResponse({ok:true,media:cVideoInfo(cVideoOwner(await cVideoRow(db,id),actor))});if(!videoPath[2]&&['GET','HEAD'].includes(request.method))return await cVideoRead(request,db,actor,env,id);if(isPost&&['cancel','delete'].includes(videoPath[2]))return await cVideoWithdraw(request,db,actor,env,id,videoPath[2]);}
    if((path==='/api/community/state'||path==='/api/admin/state')&&request.method==='GET')return cResponse(await cState(db,actor,env,admin));
    if((path==='/api/community/action'||path==='/api/admin/action')&&isPost){const body=await cBody(request),result=admin?await cAdminAction(db,actor,env,body):await cCommunityAction(db,actor,env,body);return cResponse({ok:true,result,state:await cState(db,actor,env,admin)});}
    cFail(404,'NOT_FOUND','API 路由不存在或方法不支持。');
  }catch(error){
    let status=error.status||500,code=error.code||'INTERNAL_ERROR',message=error instanceof CommunityError?error.message:'云服务未完成本次操作，请重试。';
    if(/no such table|no such column/i.test(error.message||'')){status=503;code='DB_SCHEMA_NOT_READY';message='数据库结构尚未就绪，请管理员完成部署迁移。';}
    return cResponse({ok:false,error:{code,message},requestId,...(status===401?{signInPath:'/signin-with-chatgpt?return_to=%2F%23community'}:{})},status);
  }
}
