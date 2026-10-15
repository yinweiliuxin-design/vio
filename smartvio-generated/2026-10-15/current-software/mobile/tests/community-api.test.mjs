import assert from 'node:assert/strict';
import { readFileSync, existsSync, unlinkSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { randomUUID } from 'node:crypto';
import { handleAPI } from '../worker/community.mjs';
import { createD1, applyMigrations } from './d1-sqlite.mjs';

const project=fileURLToPath(new URL('../',import.meta.url)),migrations=join(project,'drizzle'),origin='https://community.test';
let checks=0;const cases=[];
function check(value,message){assert(value,message);checks++;}
class Bucket{
  constructor(){this.objects=new Map();this.puts=0;this.deletes=0;}
  async put(key,bytes,metadata){this.puts++;this.objects.set(key,{bytes:new Uint8Array(bytes),metadata});}
  async get(key){const value=this.objects.get(key);return value?{body:value.bytes}:null;}
  async delete(key){this.deletes++;this.objects.delete(key);}
}
function environment(file=':memory:'){const DB=createD1(file);applyMigrations(DB,migrations);return {DB,BUCKET:new Bucket(),ADMIN_USER_IDS:JSON.stringify(['test-admin']),CATALOG_SOURCE:[{id:'S001',title:'候选曲目',titles:{zh:'候选曲目',en:'Candidate'},category:'beginner',regions:['cn'],rightsStatus:'pending',published:false}]};}
async function call(env,user,path='/api/community/state',body,extra={}){
  const headers={'oai-authenticated-user-id':user||'','oai-authenticated-user-email':'PRIVATE-EMAIL@example.test','oai-authenticated-user-full-name':'PRIVATE-FULL-NAME','Content-Type':'application/json','Origin':origin,...extra.headers};
  if(!user)delete headers['oai-authenticated-user-id'];const request=new Request(origin+path,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body),...extra.options});const response=await handleAPI(request,env);return {status:response.status,data:await response.json()};
}
const userAction=(env,user,body,extra)=>call(env,user,'/api/community/action',body,extra);
const adminAction=(env,body)=>call(env,'test-admin','/api/admin/action',body);
async function draft(env,user='alice',extra={}){const response=await userAction(env,user,{type:'post-save',clientRequestId:randomUUID(),title:'练习记录',text:'本人练习验收内容，仅测试数据库。',topic:'practice',...extra});check(response.status===200,'draft saved');return response.data.result;}
async function publish(env,row,user='alice'){const submitted=await userAction(env,user,{type:'post-submit',id:row.id,version:row.version});check(submitted.status===200,'explicit submit');const approved=await adminAction(env,{type:'moderate',targetType:'post',id:row.id,version:submitted.data.result.version,action:'approve'});check(approved.status===200,'explicit admin approval in isolated test DB');return approved.data.result;}
async function test(name,fn){await fn();cases.push(name);}

await test('schema migrations preserve existing pre-topic post and immutable migration journal',async()=>{
  const db=createD1(),journal=JSON.parse(readFileSync(join(migrations,'meta','_journal.json'),'utf8'));
  db.exec(readFileSync(join(migrations,journal.entries[0].tag+'.sql'),'utf8'));
  const postId=randomUUID(),requestId=randomUUID(),at=new Date().toISOString();
  db.sqlite.prepare("INSERT INTO community_users (id,created_at,updated_at) VALUES ('legacy',?,?)").run(at,at);
  db.sqlite.prepare("INSERT INTO community_posts (id,user_id,client_request_id,request_hash,title,text,created_at,updated_at,mutation_token) VALUES (?,'legacy',?,'hash','保留标题','保留文字',?,?,'token')").run(postId,requestId,at,at);
  for(const entry of journal.entries.slice(1))db.exec(readFileSync(join(migrations,entry.tag+'.sql'),'utf8'));
  const row=db.sqlite.prepare('SELECT * FROM community_posts WHERE id=?').get(postId);check(row.title==='保留标题'&&row.text==='保留文字'&&row.topic==='practice','existing post preserved default topic');
  assert.throws(()=>db.sqlite.prepare("UPDATE community_posts SET topic='invalid' WHERE id=?").run(postId));checks++;
  check(db.sqlite.prepare('PRAGMA foreign_key_check').all().length===0,'foreign keys intact');db.close();
  const again=createD1();check(applyMigrations(again,migrations).length===journal.entries.length,'journal order applied');check(applyMigrations(again,migrations).length===0,'startup does not replay migrations');again.close();
});

await test('identity is database independent; auth and owner whitelist fail closed',async()=>{
  const signed=await call({ADMIN_USER_IDS:'["test-admin"]'},'alice','/api/identity');check(signed.status===200&&signed.data.viewer.id==='alice'&&!signed.data.viewer.isAdmin,'identity independent of DB');check(!JSON.stringify(signed.data).includes('PRIVATE-'),'platform contact information not used as public nickname');
  const missing=await call({},null,'/api/identity');check(missing.status===401&&missing.data.signInPath.startsWith('/signin-with-chatgpt?return_to='),'anonymous rejected with supported sign-in path');
  const env=environment();const nonAdmin=await call(env,'alice','/api/admin/state');check(nonAdmin.status===403&&nonAdmin.data.error.code==='ADMIN_REQUIRED','nonowner admin denied');env.ADMIN_USER_IDS='[]';check((await call(env,'test-admin','/api/admin/state')).status===503,'empty whitelist cannot grant first visitor admin');
  check((await call({ADMIN_USER_IDS:'["test-admin"]'},'alice')).status===503,'missing DB not a fake local success');env.DB.close();
});

await test('private drafts/pending; author isolation; profile nickname is explicit; no automatic publishing',async()=>{
  const env=environment();let row=await draft(env);const own=await call(env,'alice'),other=await call(env,'bob');check(own.data.mine.length===1&&own.data.posts.length===0&&other.data.mine.length===0&&other.data.posts.length===0,'draft private by actor');
  check(own.data.viewer.name==='琴友'&&!JSON.stringify(own.data).includes('PRIVATE-'),'default nickname never platform contact');check((await adminAction(env,{type:'moderate',targetType:'post',id:row.id,version:row.version,action:'approve'})).status===409,'draft cannot be directly approved');
  check((await userAction(env,'bob',{type:'post-save',id:row.id,version:row.version,title:'越权',text:'攻击'})).status===403,'other user edit denied');
  check((await userAction(env,'alice',{type:'post-save',clientRequestId:randomUUID(),text:'x',role:'admin'})).status===422,'body role is rejected');
  check((await userAction(env,'alice',{type:'profile-save',name:'自选琴友'})).status===200,'explicit nickname save');row=await publish(env,row);const feed=(await call(env,'bob')).data.posts[0];check(feed.authorName==='自选琴友'&&!Object.hasOwn(feed,'userId'),'public feed uses chosen name, not actor/contact ID');
  const admin=(await call(env,'test-admin','/api/admin/state')).data;check(admin.ok&&admin.catalog.length===1&&admin.counts.postsPublished===1&&admin.counts.users>=3,'admin state full actual counts/catalog');check(admin.audit.some(item=>item.action==='moderate-approve'),'approval audited');env.DB.close();
});

await test('post/comment request idempotency and same-key different-content conflicts',async()=>{
  const env=environment(),clientRequestId=randomUUID(),body={type:'post-save',clientRequestId,text:'幂等测试',topic:'help'};
  const [a,b]=await Promise.all([userAction(env,'alice',body),userAction(env,'alice',body)]);check(a.status===200&&b.status===200&&a.data.result.id===b.data.result.id,'concurrent identical create returns same post');check(env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_posts').get().n===1,'one physical post');check(env.DB.sqlite.prepare("SELECT COUNT(*) AS n FROM community_audit WHERE action='post-save'").get().n===1,'one successful creation audit');
  check((await userAction(env,'alice',{...body,text:'不同内容'})).data.error.code==='IDEMPOTENCY_CONFLICT','different content same request ID conflict');let row=await publish(env,a.data.result);
  const commentBody={type:'comment-create',postId:row.id,text:'幂等评论',clientRequestId:randomUUID()},[c,d]=await Promise.all([userAction(env,'bob',commentBody),userAction(env,'bob',commentBody)]);check(c.status===200&&d.status===200&&c.data.result.id===d.data.result.id,'one concurrent comment');check(env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_comments').get().n===1,'comment unique owner/request constraint');check((await userAction(env,'bob',{...commentBody,text:'改内容'})).status===409,'comment same request ID conflict');env.DB.close();
});

await test('pending comment visibility, moderation, unique likes, and report workflow',async()=>{
  const env=environment(),post=await publish(env,await draft(env));const comment=(await userAction(env,'bob',{type:'comment-create',postId:post.id,text:'待审核评论',clientRequestId:randomUUID()})).data.result;
  check(comment.status==='pending','comments always start pending');check((await call(env,'alice')).data.posts[0].comments.length===0,'post author cannot see someone else pending comment');check((await call(env,'bob')).data.myComments[0].status==='pending','comment author sees own pending');
  check((await adminAction(env,{type:'moderate',targetType:'comment',id:comment.id,version:comment.version,action:'approve'})).status===200,'comment moderation');check((await call(env,'alice')).data.posts[0].comments[0].text==='待审核评论','approved comment visible');
  for(let i=0;i<3;i++)check((await userAction(env,'bob',{type:'like-set',postId:post.id,liked:true})).data.result.likeCount===1,'unique repeated like');check(env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_likes').get().n===1,'actual likes uniqueness');check((await userAction(env,'bob',{type:'like-set',postId:post.id,liked:false})).data.result.likeCount===0,'unlike persisted');
  const reportBody={type:'report-create',targetType:'post',targetId:post.id,reason:'测试反馈'},r1=await userAction(env,'bob',reportBody),r2=await userAction(env,'bob',reportBody);check(r1.data.result.id===r2.data.result.id&&env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_reports').get().n===1,'open report deduplicated');
  const resolved=await adminAction(env,{type:'report-resolve',id:r1.data.result.id,version:r1.data.result.version,status:'resolved',resolution:'隔离测试已处理'});check(resolved.status===200&&resolved.data.state.counts.reportsOpen===0,'report actual resolution');check((await userAction(env,'bob',reportBody)).data.result.id!==r1.data.result.id,'new report allowed after prior closed');env.DB.close();
});

await test('published edits withdraw to draft; rejection/hide/restore/delete states remain bounded',async()=>{
  const env=environment();let post=await publish(env,await draft(env));post=(await adminAction(env,{type:'moderate',targetType:'post',id:post.id,version:post.version,action:'hide',reason:'暂时隐藏'})).data.result;check(post.status==='hidden'&&(await call(env,'bob')).data.posts.length===0,'hide removes public visibility');check((await userAction(env,'alice',{type:'post-save',id:post.id,version:post.version,text:'绕过隐藏'})).status===409,'author cannot bypass hidden moderation');
  post=(await adminAction(env,{type:'moderate',targetType:'post',id:post.id,version:post.version,action:'restore'})).data.result;check(post.status==='published','hidden previously-approved content restored');post=(await userAction(env,'alice',{type:'post-save',id:post.id,version:post.version,text:'编辑后重新审核',topic:'work'})).data.result;check(post.status==='draft'&&post.topic==='work'&&(await call(env,'bob')).data.posts.length===0,'published edit withdraws to draft');
  post=(await userAction(env,'alice',{type:'post-submit',id:post.id,version:post.version})).data.result;post=(await adminAction(env,{type:'moderate',targetType:'post',id:post.id,version:post.version,action:'reject',reason:'请补充内容'})).data.result;check(post.status==='rejected'&&(await call(env,'alice')).data.mine.some(item=>item.id===post.id),'own rejection visible');post=(await userAction(env,'alice',{type:'post-delete',id:post.id,version:post.version})).data.result;check(post.status==='deleted','soft deletion');post=(await adminAction(env,{type:'moderate',targetType:'post',id:post.id,version:post.version,action:'restore'})).data.result;check(post.status==='draft'&&(await call(env,'bob')).data.posts.length===0,'deleted restore never publishes');env.DB.close();
});

await test('real SQL compare-and-swap race and forced audit failure roll back all content',async()=>{
  const env=environment(),post=await draft(env),before=env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n;
  const edits=await Promise.all(['A','B'].map(text=>userAction(env,'alice',{type:'post-save',id:post.id,version:post.version,title:'竞态',text})));check(edits.filter(item=>item.status===200).length===1&&edits.filter(item=>item.status===409).length===1,'exactly one CAS succeeds');const saved=env.DB.sqlite.prepare('SELECT * FROM community_posts WHERE id=?').get(post.id);check(saved.version===post.version+1&&['A','B'].includes(saved.text),'one physical version increment');check(env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n===before+1,'failed race leaves no success audit');
  const priorBatch=env.DB.batch.bind(env.DB);env.DB.batch=async statements=>{if(statements[1]?.sql.startsWith('INSERT INTO community_audit'))statements[1]=env.DB.prepare("INSERT INTO community_audit (id,actor_id,action,target_type,target_id,detail_json,at) VALUES (?,'alice','__cas_failed__','post',?,'{}','test')").bind(randomUUID(),post.id);return priorBatch(statements);};
  const failed=await userAction(env,'alice',{type:'post-save',id:post.id,version:saved.version,title:'不应持久化',text:'失败写入'});check(failed.status===409,'storage/audit guard causes failed API response');const after=env.DB.sqlite.prepare('SELECT * FROM community_posts WHERE id=?').get(post.id);check(after.title===saved.title&&after.text===saved.text&&after.version===saved.version,'actual SQLite rolled back content written before audit failure');check(env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n===before+1,'failure writes no audit');env.DB.close();
});

await test('settings four-language partial patch, catalog ID whitelist, conflict, and account suspension',async()=>{
  const env=environment();await call(env,'bob');let state=(await call(env,'test-admin','/api/admin/state')).data;
  const first=await adminAction(env,{type:'settings-save',version:state.settings.version,announcement:{zh:'公告',en:'Notice',ja:'お知らせ',de:'Hinweis'}});check(first.status===200&&first.data.state.settings.announcement.ja==='お知らせ','four language announcement persisted');
  const second=await adminAction(env,{type:'catalog-set',id:'S001',visible:false,version:first.data.result.version});check(second.status===200&&second.data.state.catalog[0].visible===false&&second.data.state.settings.catalogHiddenIds[0]==='S001','real shipped catalog hide state');check(second.data.state.catalog[0].rightsStatus==='pending'&&!second.data.state.catalog[0].published,'hide does not assert music rights');
  check((await adminAction(env,{type:'catalog-set',id:'unshipped',visible:false,version:second.data.result.version})).status===422,'unknown catalog ID refused');check((await adminAction(env,{type:'settings-save',version:first.data.result.version,postingEnabled:false})).status===409,'stale settings conflict');
  const patched=await adminAction(env,{type:'settings-save',version:second.data.result.version,postingEnabled:false});check(patched.status===200&&patched.data.result.announcement.en==='Notice'&&patched.data.result.catalogHiddenIds[0]==='S001','partial settings patch preserves unrelated values');check((await userAction(env,'bob',{type:'post-save',clientRequestId:randomUUID(),text:'关闭发帖后不应成功'})).status===403,'posting switch enforced server-side');
  state=(await call(env,'test-admin','/api/admin/state')).data;const bob=state.users.find(item=>item.id==='bob');check((await adminAction(env,{type:'user-set',id:bob.id,version:bob.version,disabled:true})).status===200,'user suspension stored');check((await userAction(env,'bob',{type:'profile-save',name:'不应成功'})).status===403,'disabled account cannot mutate');check((await call(env,'bob')).data.viewer.disabled===true,'disabled viewer still sees truthful state');const admin=state.users.find(item=>item.id==='test-admin');check((await adminAction(env,{type:'user-set',id:admin.id,version:admin.version,disabled:true})).data.error.code==='ADMIN_PROTECTED','cannot disable configured admin');env.DB.close();
});

await test('cross-site JSON writes, oversized input, prototype role fields and HTTPS links are rejected',async()=>{
  const env=environment();const body={type:'post-save',clientRequestId:randomUUID(),text:'安全边界'};
  check((await userAction(env,'alice',body,{headers:{Origin:'https://other.test'}})).status===403,'cross origin mutation denied');check((await userAction(env,'alice',body,{headers:{'Sec-Fetch-Site':'cross-site'}})).status===403,'cross site request denied');check((await userAction(env,'alice',body,{headers:{'Content-Type':'text/plain'}})).status===415,'JSON type enforced');check((await userAction(env,'alice',{...body,text:'a'.repeat(40000)})).status===413,'actual byte cap enforced');
  for(const url of ['javascript:alert(1)','http://example.test','https://name:password@example.test/'])check((await userAction(env,'alice',{...body,attachments:[{kind:'url',url,title:'链接'}],rightsConfirmed:true})).status===422,'unsafe link rejected');check((await userAction(env,'alice',{...body,attachments:[{kind:'url',url:'https://example.test/legal'}]})).data.error.code==='RIGHTS_REQUIRED','rights confirmation required');
  const local=await draft(env,'alice',{attachments:[{kind:'local',id:'local-recording',name:'本机录音',mime:'audio/webm',duration:2}],rightsConfirmed:true});check(local.attachments[0].kind==='local'&&env.BUCKET.puts===0,'local metadata never uploaded');env.DB.close();
});

await test('real image bytes, R2 permissions by publication, magic/size failure, and orphan cleanup',async()=>{
  const env=environment(),png=new Uint8Array(readFileSync(join(project,'dist','icons','icon-192.png')));
  async function upload(user,bytes=png,mime='image/png'){const response=await handleAPI(new Request(origin+'/api/community/media',{method:'POST',headers:{'oai-authenticated-user-id':user,Origin:origin,'Content-Type':mime},body:bytes}),env);return {status:response.status,data:await response.json()};}
  async function image(user,id){return handleAPI(new Request(origin+'/api/community/media/'+id,{headers:{'oai-authenticated-user-id':user}}),env);}
  const uploaded=await upload('alice');check(uploaded.status===201&&uploaded.data.media.size===png.length&&env.BUCKET.objects.size===1,'real bytes stored in R2 adapter and metadata DB');const media=uploaded.data.media;check((await image('alice',media.id)).status===200,'owner can read pending media');check((await image('bob',media.id)).status===403,'unpublished image private');check((await image('test-admin',media.id)).status===200,'admin can inspect for moderation');
  check((await userAction(env,'bob',{type:'post-save',clientRequestId:randomUUID(),text:'偷用图片',attachments:[{kind:'media',mediaId:media.id}],rightsConfirmed:true})).status===403,'cannot attach another uploader private media');
  let post=await publish(env,await draft(env,'alice',{attachments:[{kind:'media',mediaId:media.id}],rightsConfirmed:true}));const shared=await image('bob',media.id);check(shared.status===200&&shared.headers.get('Cache-Control').includes('no-store')&&shared.headers.get('Cross-Origin-Resource-Policy')==='same-origin','published reference grants same-site read with private cache policy');check(Buffer.from(await shared.arrayBuffer()).equals(Buffer.from(png)),'R2 response real binary bytes');
  post=(await adminAction(env,{type:'moderate',targetType:'post',id:post.id,version:post.version,action:'hide',reason:'测试隐藏'})).data.result;check((await image('bob',media.id)).status===403,'hiding final published reference revokes media sharing');
  const count=env.BUCKET.puts;check((await upload('alice',new Uint8Array([1,2,3]))).status===422&&env.BUCKET.puts===count,'bad magic never put');check((await upload('alice',png,'image/jpeg')).status===422&&env.BUCKET.puts===count,'MIME mismatch never put');check((await upload('alice',new Uint8Array(5242881))).status===413&&env.BUCKET.puts===count,'oversize never put');
  const originalBatch=env.DB.batch.bind(env.DB);env.DB.batch=async statements=>{if(statements[1]?.sql.startsWith('INSERT INTO community_audit'))throw Error('injected metadata failure');return originalBatch(statements);};const previousObjects=env.BUCKET.objects.size;check((await upload('alice')).status===500&&env.BUCKET.objects.size===previousObjects&&env.BUCKET.deletes===1,'DB failure deletes newly put object');env.DB.batch=originalBatch;delete env.BUCKET;check((await upload('alice')).status===503,'missing R2 truthful unavailable');env.DB.close();
});

await test('local D1 restart persistence uses real database file and skips applied migrations',async()=>{
  const file=join(tmpdir(),'smartvio-community-test-'+randomUUID()+'.sqlite');let env;
  try{env=environment(file);const post=await draft(env);check((await userAction(env,'alice',{type:'onboarding-save',guideVersion:2,status:'in_progress',step:4})).status===200,'guide progress committed before restart');env.DB.close();env=environment(file);const state=(await call(env,'alice')).data;check(state.mine.some(item=>item.id===post.id),'real restart preserves draft');check(state.viewer.onboarding.status==='in_progress'&&state.viewer.onboarding.step===4,'real restart preserves account guide progress');check(applyMigrations(env.DB,migrations).length===0,'restart does not replay schema');env.DB.close();env=null;}finally{try{env?.DB.close();}catch{}if(existsSync(file))unlinkSync(file);}
});

await test('guide migration preserves old users and referencing data; snapshot matches real columns and checks',async()=>{
  const db=createD1(),journal=JSON.parse(readFileSync(join(migrations,'meta','_journal.json'),'utf8'));
  for(const entry of journal.entries.slice(0,2))db.exec(readFileSync(join(migrations,entry.tag+'.sql'),'utf8'));
  const at='2026-01-02T03:04:05.000Z',postId=randomUUID(),commentId=randomUUID(),mediaId=randomUUID();
  db.sqlite.prepare("INSERT INTO community_users (id,name,disabled,version,created_at,updated_at,mutation_token) VALUES ('old-user','原昵称',0,7,?,?,'old-token')").run(at,at);
  db.sqlite.prepare("INSERT INTO community_posts (id,user_id,client_request_id,request_hash,title,text,created_at,updated_at,mutation_token) VALUES (?,'old-user',?,'hash','原帖','保留内容',?,?,'post-token')").run(postId,randomUUID(),at,at);
  db.sqlite.prepare("INSERT INTO community_comments (id,post_id,user_id,client_request_id,request_hash,text,created_at,updated_at,mutation_token) VALUES (?,?,'old-user',?,'hash','原评论',?,?,'comment-token')").run(commentId,postId,randomUUID(),at,at);
  db.sqlite.prepare("INSERT INTO community_likes (post_id,user_id,created_at) VALUES (?,'old-user',?)").run(postId,at);
  db.sqlite.prepare("INSERT INTO community_media (id,user_id,object_key,mime,size,created_at,mutation_token) VALUES (?,'old-user','old/image.png','image/png',100,?,'media-token')").run(mediaId,at);
  const before={...db.sqlite.prepare("SELECT * FROM community_users WHERE id='old-user'").get()};
  for(const entry of journal.entries.slice(2))db.exec(readFileSync(join(migrations,entry.tag+'.sql'),'utf8'));
  const after=db.sqlite.prepare("SELECT * FROM community_users WHERE id='old-user'").get();
  check(Object.entries(before).every(([key,value])=>after[key]===value),'migration leaves old nickname/version/times/token unchanged');
  check(after.learn_guide_version===2&&after.learn_guide_status==='legacy'&&after.learn_guide_step===0&&after.learn_guide_updated_at===null,'old user classified legacy, never a new pending user');
  check(db.sqlite.prepare('PRAGMA foreign_key_check').all().length===0,'all guide migration foreign keys preserved');
  for(const [table,idColumn,id] of [['community_posts','id',postId],['community_comments','id',commentId],['community_media','id',mediaId],['community_likes','post_id',postId]])check(db.sqlite.prepare('SELECT COUNT(*) AS n FROM '+table+' WHERE '+idColumn+'=?').get(id).n===1,'referencing '+table+' survives in-place user migration');
  const env={DB:db,ADMIN_USER_IDS:'["test-admin"]'};
  const state=await call(env,'old-user');check(state.status===200&&state.data.viewer.onboarding.status==='legacy','GET does not reset old user onboarding');
  check(JSON.stringify(db.sqlite.prepare("SELECT * FROM community_users WHERE id='old-user'").get())===JSON.stringify(after),'old user GET leaves complete stored row unchanged');
  const previous=JSON.parse(readFileSync(join(migrations,'meta','0001_snapshot.json'),'utf8')),latest=JSON.parse(readFileSync(join(migrations,'meta','0002_snapshot.json'),'utf8'));
  check(latest.prevId===previous.id&&journal.entries[2].tag==='0002_learn_onboarding'&&journal.entries[2].idx===2,'new journal and snapshot chain agree');
  const columns=db.sqlite.prepare('PRAGMA table_info(community_users)').all(),snapshotColumns=latest.tables.community_users.columns;
  check(columns.length===Object.keys(snapshotColumns).length,'actual user column count matches snapshot');
  for(const col of columns){const snapshot=snapshotColumns[col.name];check(!!snapshot&&col.type.toLowerCase()===snapshot.type&&Boolean(col.notnull)===snapshot.notNull&&(col.dflt_value===null?snapshot.default===undefined:String(col.dflt_value)===String(snapshot.default)),'actual default/type/not-null matches snapshot for '+col.name);}
  const ddl=db.sqlite.prepare("SELECT sql FROM sqlite_master WHERE name='community_users'").get().sql;
  for(const name of Object.keys(latest.tables.community_users.checkConstraints))check(ddl.includes(name),'actual DDL retains snapshot constraint '+name);
  for(const [column,value] of [['learn_guide_version',1],['learn_guide_status','unknown'],['learn_guide_step',7],['learn_guide_step',1.5]]){assert.throws(()=>db.sqlite.prepare('UPDATE community_users SET '+column+'=? WHERE id=?').run(value,'old-user'));checks++;}
  db.close();
});

await test('new guide state is account-owned, strictly validated, and separate from platform registration',async()=>{
  const env=environment(),first=await call(env,'alice'),again=await call(env,'alice'),bob=await call(env,'bob');
  check(first.status===200&&JSON.stringify(first.data.viewer.onboarding)===JSON.stringify(again.data.viewer.onboarding),'repeat identity reads keep persisted guide state');
  check(first.data.viewer.onboarding.guideVersion===2&&first.data.viewer.onboarding.status==='pending'&&first.data.viewer.onboarding.step===0&&typeof first.data.viewer.onboarding.updatedAt==='string','new Site user starts guide 2 pending at zero');
  check(!Object.hasOwn((await call(env,'identity-only','/api/identity')).data.viewer,'onboarding')&&!env.DB.sqlite.prepare("SELECT id FROM community_users WHERE id='identity-only'").get(),'identity endpoint does not fake registration or create profile');
  const action={type:'onboarding-save',guideVersion:2,step:2,status:'in_progress'},saved=await userAction(env,'alice',action);
  check(saved.status===200&&saved.data.result.status==='in_progress'&&saved.data.state.viewer.onboarding.step===2,'result and viewer contain committed account guide');
  check(JSON.stringify((await call(env,'bob')).data.viewer.onboarding)===JSON.stringify(bob.data.viewer.onboarding),'alice guide cannot alter bob');
  check((await userAction(env,null,action)).status===401,'unauthenticated guide mutation rejected');
  const before=JSON.stringify(env.DB.sqlite.prepare("SELECT * FROM community_users WHERE id='alice'").get()),auditBefore=env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n;
  const invalid=[...[-1,7,1.5,'1',null,true].map(step=>({...action,step})),...[1,'2',null,true].map(guideVersion=>({...action,guideVersion})),...['unknown','',null].map(status=>({...action,status})),{type:'onboarding-save',step:0,status:'in_progress'},{type:'onboarding-save',guideVersion:2,status:'in_progress'},{type:'onboarding-save',guideVersion:2,step:0},...['userId','role','name'].map(key=>({...action,[key]:'bob'}))];
  for(const body of invalid)check((await userAction(env,'alice',body)).status===422,'invalid guide payload rejected');
  check((await userAction(env,'alice',action,{headers:{Origin:'https://other.test'}})).status===403,'guide action keeps same-origin guard');
  check(JSON.stringify(env.DB.sqlite.prepare("SELECT * FROM community_users WHERE id='alice'").get())===before&&env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n===auditBefore,'invalid guide requests change neither user row nor audit');
  check((await userAction(env,'alice',{type:'profile-save',name:'自主昵称'})).data.state.viewer.onboarding.step===2,'nickname save leaves learning progress intact');
  env.DB.close();
});

await test('guide terminal outcomes win both concurrent orders and late progress is a committed no-op',async()=>{
  const env=environment();
  for(const terminal of ['completed','skipped'])for(const reversed of [false,true]){
    const user=terminal+'-'+Number(reversed);await call(env,user);
    const done={type:'onboarding-save',guideVersion:2,status:terminal,step:6},progress={type:'onboarding-save',guideVersion:2,status:'in_progress',step:1};
    const results=await Promise.all((reversed?[progress,done]:[done,progress]).map(body=>userAction(env,user,body)));
    check(results.every(result=>result.status===200),'concurrent guide saves are resolved without stale actor version errors');
    check((await call(env,user)).data.viewer.onboarding.status===terminal&&(await call(env,user)).data.viewer.onboarding.step===6,'terminal guide wins concurrent '+terminal+' order '+Number(reversed));
    const before=JSON.stringify(env.DB.sqlite.prepare('SELECT * FROM community_users WHERE id=?').get(user)),audit=env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n;
    for(const status of ['legacy','pending','in_progress']){const late=await userAction(env,user,{...progress,status});check(late.status===200&&late.data.result.status===terminal&&late.data.state.viewer.onboarding.step===6,'late nonterminal acknowledges stored terminal state');}
    check(JSON.stringify(env.DB.sqlite.prepare('SELECT * FROM community_users WHERE id=?').get(user))===before&&env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n===audit,'late request preserves step/time/version/token/audit');
    const changed=await userAction(env,user,{...done,status:terminal==='completed'?'skipped':'completed'});check(changed.status===200&&changed.data.result.status!==terminal,'explicit terminal outcome changes allowed');
  }
  env.DB.close();
});

await test('guide writes retain disabled-user guard and real SQL rollback on audit failure',async()=>{
  const env=environment();await call(env,'alice');const body={type:'onboarding-save',guideVersion:2,status:'in_progress',step:3},priorBatch=env.DB.batch.bind(env.DB);
  const before=JSON.stringify(env.DB.sqlite.prepare("SELECT * FROM community_users WHERE id='alice'").get());
  env.DB.batch=async statements=>{if(statements[0]?.sql.startsWith('UPDATE community_users SET learn_guide_version'))statements[1]=env.DB.prepare("INSERT INTO community_audit (id,actor_id,action,target_type,target_id,detail_json,at) VALUES (?,'alice','__cas_failed__','user','alice','{}','test')").bind(randomUUID());return priorBatch(statements);};
  check((await userAction(env,'alice',body)).status===409,'guide forced SQL audit failure returned');
  check(JSON.stringify(env.DB.sqlite.prepare("SELECT * FROM community_users WHERE id='alice'").get())===before&&env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n===0,'guide fields and audit both rolled back');
  env.DB.batch=async statements=>{if(statements[0]?.sql.startsWith('UPDATE community_users SET learn_guide_version'))env.DB.sqlite.prepare("UPDATE community_users SET disabled=1 WHERE id='alice'").run();return priorBatch(statements);};
  check((await userAction(env,'alice',body)).status===409,'disable between identity read and write blocks SQL mutation');
  const row=env.DB.sqlite.prepare("SELECT * FROM community_users WHERE id='alice'").get();check(row.learn_guide_status==='pending'&&row.learn_guide_step===0&&env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n===0,'raced suspension keeps guide and audit unchanged');
  env.DB.batch=priorBatch;check((await userAction(env,'alice',body)).status===403,'already disabled user rejected before guide write');env.DB.close();
});
console.log(JSON.stringify({result:'PASS',cases:cases.length,checks,caseNames:cases,engine:'Node24 builtin SQLite; real generated migrations; same Worker API; in-memory R2 harness; no production content seeded'},null,2));
