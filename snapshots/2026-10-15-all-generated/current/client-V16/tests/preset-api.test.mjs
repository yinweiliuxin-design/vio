import assert from 'node:assert/strict';
import { readFileSync, existsSync, unlinkSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { randomUUID } from 'node:crypto';
import vm from 'node:vm';
import { handleAPI } from '../worker/community.mjs';
import { createD1, applyMigrations } from './d1-sqlite.mjs';
const project=fileURLToPath(new URL('../',import.meta.url)),migrations=join(project,'drizzle'),origin='https://preset.test';
let checks=0;const cases=[];function check(value,message){assert(value,message);checks++;}
function environment(file=':memory:'){const DB=createD1(file);applyMigrations(DB,migrations);return {DB,ADMIN_USER_IDS:'["admin"]',CATALOG_SOURCE:[]};}
function preset(extra={}){return {id:randomUUID(),name:'PRIVATE_PRESET_NAME',group:'PRIVATE_GROUP',preset:'Warm',effects:{volume:0.7,reverb:0.2,delay:0.1,compression:0.3},...extra};}
async function call(env,user='alice',body,path='/api/presets',extra={}){
  const headers={'oai-authenticated-user-id':user,'Origin':origin,'Content-Type':'application/json',...extra.headers};if(!user)delete headers['oai-authenticated-user-id'];
  const response=await handleAPI(new Request(origin+path,{method:body===undefined?'GET':'POST',headers,body:body===undefined?undefined:JSON.stringify(body),...extra.options}),env);
  return {status:response.status,data:await response.json(),headers:response.headers};
}
const save=(env,user,version,presets,extra={})=>call(env,user,{type:'save',accountId:user,version,presets,...extra});
const clear=(env,user,version)=>call(env,user,{type:'clear',accountId:user,version});
async function test(name,fn){await fn();cases.push(name);}
await test('additive preset migration preserves existing settings, user and post; generated snapshot matches columns',async()=>{
  const db=createD1(),journal=JSON.parse(readFileSync(join(migrations,'meta/_journal.json'),'utf8'));
  for(const entry of journal.entries.slice(0,3))db.exec(readFileSync(join(migrations,entry.tag+'.sql'),'utf8'));
  db.sqlite.prepare("INSERT INTO community_users (id,name,created_at,updated_at) VALUES ('alice','Preserved','now','now')").run();
  const id=randomUUID();db.sqlite.prepare("INSERT INTO community_posts (id,user_id,client_request_id,request_hash,title,text,created_at,updated_at,mutation_token) VALUES (?,'alice',?,'hash','Preserved post','Old text','now','now','token')").run(id,randomUUID());
  db.sqlite.prepare("INSERT INTO community_settings(id,posting_enabled,announcement_json,catalog_hidden_ids_json,version,updated_at,mutation_token) VALUES ('global',0,'{\"zh\":\"preserved\",\"en\":\"\",\"ja\":\"\",\"de\":\"\"}','[\"S001\"]',9,'now','token')").run();
  const existingUser=JSON.stringify(db.sqlite.prepare("SELECT * FROM community_users WHERE id='alice'").get()),existingPost=JSON.stringify(db.sqlite.prepare('SELECT * FROM community_posts WHERE id=?').get(id));
  db.exec(readFileSync(join(migrations,'0003_private_preset_backup.sql'),'utf8'));
  check(JSON.stringify(db.sqlite.prepare("SELECT * FROM community_users WHERE id='alice'").get())===existingUser,'user unchanged');check(JSON.stringify(db.sqlite.prepare('SELECT * FROM community_posts WHERE id=?').get(id))===existingPost,'post unchanged');
  const settings=db.sqlite.prepare("SELECT * FROM community_settings WHERE id='global'").get();check(settings.version===9&&!settings.posting_enabled&&settings.cloud_preset_backup_enabled===1&&JSON.parse(settings.announcement_json).zh==='preserved'&&settings.catalog_hidden_ids_json==='["S001"]','old settings and new default preserved');
  const snapshot=JSON.parse(readFileSync(join(migrations,'meta/0003_snapshot.json'),'utf8'));
  for(const name of ['community_settings','user_preset_backups'])check(JSON.stringify(db.sqlite.prepare('PRAGMA table_info('+name+')').all().map(row=>row.name).sort())===JSON.stringify(Object.keys(snapshot.tables[name].columns).sort()),'snapshot matches '+name);
  check(db.sqlite.prepare('PRAGMA foreign_key_check').all().length===0,'foreign keys intact');db.close();
});
await test('private backup authenticates ownership, legacy defaults and anonymous admin counts without leaking payload',async()=>{
  const env=environment();check((await call(env,null)).status===401,'anonymous needs cloud identity');
  const initial=await call(env);check(initial.status===200&&initial.data.viewer.id==='alice'&&initial.data.backup.version===0&&initial.data.backup.presets.length===0,'empty account state');check(initial.headers.get('Cache-Control')==='private, no-store','not cached');
  check((await save(env,'alice',5,[preset()])).status===409,'nonexistent row cannot accept nonzero expected version');
  const value=preset({name:'  PRIVATE_PRESET_NAME  ',group:' PRIVATE_GROUP '});const stored=await save(env,'alice',0,[value]);check(stored.status===200&&stored.data.backup.version===1&&stored.data.backup.presets[0].name==='PRIVATE_PRESET_NAME'&&stored.data.backup.presets[0].group==='PRIVATE_GROUP'&&stored.data.backup.presets[0].inputGain===1,'strict canonical record and old gain default');
  check((await call(env,'bob')).data.backup.presets.length===0,'second user cannot read first user presets');check((await call(env,'admin')).data.backup.presets.length===0,'admin cannot read private user presets');
  const admin=await call(env,'admin',undefined,'/api/admin/state');check(admin.data.counts.presetOwners===1&&admin.data.counts.presetCount===1,'only aggregate counts');check(!JSON.stringify(admin.data).includes('PRIVATE_PRESET_NAME')&&!JSON.stringify(admin.data).includes('PRIVATE_GROUP')&&!JSON.stringify(admin.data).includes('presets_json'),'admin state and audit do not leak private contents');
  check(admin.data.audit.every(row=>row.targetType!=='preset-backup'),'individual private backup metadata excluded from admin audit');check(env.DB.sqlite.prepare("SELECT COUNT(*) AS n FROM community_audit WHERE target_type='preset-backup'").get().n===1,'private CAS audit retained inside transaction database');
  check((await save(env,'alice',1,[value],{accountId:'bob'})).status===409,'account switch is rejected');check((await save(env,'alice',1,[value],{userId:'bob'})).status===422,'cannot choose target owner');
  check((await save(env,'bob',0,[value])).status===200,'same local preset ID is scoped per account');env.DB.close();
});
await test('CAS races allow one winner; clear preserves monotonic versions and local records are outside API',async()=>{
  const env=environment(),value=preset();await save(env,'alice',0,[value]);
  const answers=await Promise.all([save(env,'alice',1,[{...value,name:'First'}]),save(env,'alice',1,[{...value,name:'Second'}])]);check(answers.filter(row=>row.status===200).length===1&&answers.filter(row=>row.status===409).length===1,'one concurrent winner');
  const current=(await call(env)).data.backup;check(current.version===2&&current.presets.length===1,'single committed new version');
  const cleared=await clear(env,'alice',2);check(cleared.status===200&&cleared.data.backup.version===3&&cleared.data.backup.presets.length===0,'clear is a tombstone, not deletion to zero');check((await save(env,'alice',0,[value])).status===409,'ABA cannot replay version zero');
  check((await save(env,'alice',3,[value])).data.backup.version===4,'backup can resume after clear');env.DB.close();
});
await test('preset input is constrained to browser-synthesis controls and bounded owner records',async()=>{
  const env=environment(),value=preset();
  const bad=[{name:''},{group:'a'.repeat(61)},{id:'bad/id'},{preset:'Unknown'},{inputGain:-1},{inputGain:2.01},{inputGain:'1'},{effects:{...value.effects,reverb:2}},{effects:{...value.effects,hardwareSensitivity:0.5}},{effects:[]},{name:'control\u0001name'},{hardwareSync:true}];
  for(const fields of bad)check((await save(env,'alice',0,[{...value,...fields}])).status===422,'invalid field '+Object.keys(fields)[0]);
  check((await save(env,'alice',0,[value,value])).status===422,'duplicate IDs rejected');check((await save(env,'alice',0,Array.from({length:101},()=>preset()))).status===422,'count bounded');
  check((await save(env,'alice',0,[{...value,inputGain:2}])).status===200,'software input gain upper bound accepted');
  check((await save(env,'alice',1,[value],{version:Number.MAX_SAFE_INTEGER})).status===422,'version overflow rejected');
  const payload={type:'save',accountId:'alice',version:1,presets:Array.from({length:100},()=>preset({name:'音'.repeat(80),group:'组'.repeat(60)}))};check((await call(env,'alice',payload)).status===413,'UTF8 body bytes bounded');
  check((await call(env,'alice',{type:'clear',accountId:'alice',version:1,presets:[]})).status===422,'clear ignores no unexpected payload');env.DB.close();
});
await test('same-origin checks, authenticated account consistency, feature management and suspension remain enforced',async()=>{
  const env=environment(),value=preset();
  check((await call(env,'alice',{type:'save',accountId:'alice',version:0,presets:[value]},'/api/presets',{headers:{Origin:'https://evil.test'}})).status===403,'cross origin rejected');
  check((await call(env,'alice',{type:'save',accountId:'alice',version:0,presets:[value]},'/api/presets',{headers:{'Sec-Fetch-Site':'cross-site'}})).status===403,'cross-site context rejected');
  check((await call(env,'alice',{type:'save',version:0,presets:[value]})).status===422,'explicit read account required');
  check((await call(env,'bob',{type:'settings-save',version:0,cloudPresetBackupEnabled:false},'/api/admin/action')).status===403,'ordinary user cannot manage feature');
  await save(env,'alice',0,[value]);const disabled=await call(env,'admin',{type:'settings-save',version:0,cloudPresetBackupEnabled:false},'/api/admin/action');check(disabled.status===200&&!disabled.data.state.settings.cloudPresetBackupEnabled,'admin feature switch saved');
  check((await save(env,'alice',1,[value])).status===403,'disabled feature blocks new backup');check((await call(env)).data.backup.presets.length===1,'existing backup readable when feature disabled');check((await clear(env,'alice',1)).status===200,'owner can clear when feature disabled');
  check((await call(env,'admin',{type:'settings-save',version:1,cloudPresetBackupEnabled:true},'/api/admin/action')).status===200,'admin can reenable feature');
  env.DB.sqlite.prepare("UPDATE community_users SET disabled=1 WHERE id='alice'").run();check((await save(env,'alice',2,[value])).status===403&&(await clear(env,'alice',2)).status===403,'suspended user cannot mutate');check((await call(env)).status===200,'suspended account retains own read access');env.DB.close();
});
await test('failed SQL audit and raced feature/suspension guards roll back backup atomically',async()=>{
  const env=environment(),value=preset();await save(env,'alice',0,[value]);const before=JSON.stringify((await call(env)).data.backup),batch=env.DB.batch.bind(env.DB),auditBefore=env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n;
  env.DB.batch=async statements=>{if(statements[0]?.sql.startsWith('INSERT INTO user_preset_backups'))statements[1]=env.DB.prepare("INSERT INTO community_audit (id,actor_id,action,target_type,target_id,detail_json,at) VALUES (?,'alice','__cas_failed__','preset-backup','alice','{}','now')").bind(randomUUID());return batch(statements);};
  check((await save(env,'alice',1,[{...value,name:'MUST_NOT_APPEAR'}])).status===409,'audit failure rejects mutation');check(JSON.stringify((await call(env)).data.backup)===before&&env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM community_audit').get().n===auditBefore,'content and audit rolled back together');
  env.DB.batch=async statements=>{if(statements[0]?.sql.startsWith('INSERT INTO user_preset_backups'))env.DB.sqlite.prepare("UPDATE community_users SET disabled=1 WHERE id='alice'").run();return batch(statements);};
  check((await save(env,'alice',1,[{...value,name:'DISABLED_RACE'}])).status===409,'in-transaction live guard blocks raced suspension');check(JSON.stringify((await call(env)).data.backup)===before,'raced suspension retained snapshot');
  env.DB.sqlite.prepare("UPDATE community_users SET disabled=0 WHERE id='alice'").run();env.DB.batch=batch;await call(env,'admin',{type:'settings-save',version:0,cloudPresetBackupEnabled:true},'/api/admin/action');
  env.DB.batch=async statements=>{if(statements[0]?.sql.startsWith('INSERT INTO user_preset_backups'))env.DB.sqlite.prepare("UPDATE community_settings SET cloud_preset_backup_enabled=0 WHERE id='global'").run();return batch(statements);};
  check((await save(env,'alice',1,[{...value,name:'FEATURE_RACE'}])).status===409,'in-transaction flag guard blocks raced feature disable');check(JSON.stringify((await call(env)).data.backup)===before,'raced feature retained snapshot');env.DB.batch=batch;env.DB.close();
});
await test('private backup restart persists and no default names/parameters are automatically seeded',async()=>{
  const file=join(tmpdir(),'smartvio-presets-'+randomUUID()+'.sqlite');let env=environment(file),value=preset({inputGain:0.7});
  try{check(env.DB.sqlite.prepare('SELECT COUNT(*) AS n FROM user_preset_backups').get().n===0,'no private presets seeded');await save(env,'alice',0,[value]);env.DB.close();env=environment(file);const restored=await call(env);check(restored.data.backup.version===1&&restored.data.backup.presets[0].inputGain===0.7&&restored.data.backup.presets[0].id===value.id,'actual disk database survives restart');check(applyMigrations(env.DB,migrations).length===0,'applied migrations not repeated');}
  finally{env.DB.close();for(const suffix of ['','-wal','-shm'])if(existsSync(file+suffix))unlinkSync(file+suffix);}
});
await test('client serializer excludes local timestamps/hardware fields and preserves independent digital input gain',async()=>{
  const context={window:{}};vm.createContext(context);vm.runInContext(readFileSync(join(project,'dist/preset-cloud.js'),'utf8'),context);const value=preset({at:'local',hardwareSecret:'discard',inputGain:0.8}),normalized=context.window.SVPresetCloud.normalize([value])[0];
  check(normalized.inputGain===0.8&&normalized.effects.volume===value.effects.volume,'digital gain and effects preserved');check(!('hardwareSecret'in normalized)&&!('at'in normalized),'unsupported local fields not uploaded');assert.throws(()=>context.window.SVPresetCloud.normalize([{...value,inputGain:Infinity}]));checks++;
});
await test('cloud UI is opt-in, confirms replacing backups, and rechecks account before local restore',async()=>{
  let listener,requests=[],restores=0,actor='alice',version=1,records=[preset()],rejectWrites=false;
  const container={isConnected:true,innerHTML:'',addEventListener(type,fn){if(type==='click')listener=fn;},removeEventListener(){},contains(){return true;}};
  const context={window:{fetch:async(url,options)=>{
    requests.push({url,options});if(options.method==='POST'&&rejectWrites)throw Error('network lost after dispatch');
    if(options.method==='POST'){const body=JSON.parse(options.body);version++;records=body.presets??[];}
    return {ok:true,status:200,json:async()=>({ok:true,viewer:{id:actor},backup:{version,updatedAt:'2026-10-14T00:00:00Z',presets:records},features:{cloudPresetBackupEnabled:true}})};
  }},AbortController,TextEncoder,structuredClone,setTimeout,clearTimeout};vm.createContext(context);vm.runInContext(readFileSync(join(project,'dist/preset-cloud.js'),'utf8'),context);
  const api=context.window.SVPresetCloud,options={lang:'en',mode:'full',getPresets:()=>[preset({at:'local-only'})],onRestore:async()=>{restores++;return true;}};
  let mounted=api.mount(container,options);check(requests.length===0,'mount makes no automatic cloud request');
  async function click(action){listener({target:{closest(){return {dataset:{presetCloud:action},disabled:false};}}});await new Promise(resolve=>setImmediate(resolve));}
  await click('refresh');check(requests.length===1&&container.innerHTML.includes('version 1'),'explicit load displays current version');
  await click('save');check(requests.length===1&&container.innerHTML.includes('Replace this cloud backup'),'replacement requires visible confirmation');
  await click('confirm');check(requests.length===2&&JSON.parse(requests[1].options.body).accountId==='alice'&&!JSON.stringify(JSON.parse(requests[1].options.body)).includes('local-only'),'save is account-bound and strips timestamps');
  actor='bob';await click('restore');check(restores===0&&container.innerHTML.includes('signed-in account changed'),'restore reread blocks stale account');
  actor='alice';await click('refresh');rejectWrites=true;await click('save');await click('confirm');check(container.innerHTML.includes('save result is unconfirmed'),'lost save response requires refresh instead of unsafe retry');
  mounted.dispose();requests=[];mounted=api.mount(container,{...options,mode:'offline'});await click('refresh');check(requests.length===0&&container.innerHTML.includes('Local presets work offline'),'offline keeps cloud silent');mounted.dispose();
});
await test('cloud UI timeout includes a stalled JSON body and clears busy state without an automatic retry',async()=>{
  let listener,sequence=0,requests=0;const timers=new Map();const container={isConnected:true,innerHTML:'',addEventListener(type,fn){if(type==='click')listener=fn;},removeEventListener(){},contains(){return true;}};
  const context={window:{fetch:async(url,options)=>{requests++;return {ok:true,status:200,json:()=>new Promise((resolve,reject)=>{options.signal.addEventListener('abort',()=>reject(Error('body stream aborted')),{once:true});})};}},AbortController,TextEncoder,structuredClone,setTimeout(fn,delay){const id=++sequence;timers.set(id,{fn,delay});return id;},clearTimeout(id){timers.delete(id);}};
  vm.createContext(context);vm.runInContext(readFileSync(join(project,'dist/preset-cloud.js'),'utf8'),context);const mounted=context.window.SVPresetCloud.mount(container,{lang:'en',mode:'full',getPresets:()=>[]});
  listener({target:{closest(){return {dataset:{presetCloud:'refresh'},disabled:false};}}});await new Promise(resolve=>setImmediate(resolve));check(timers.size===1&&[...timers.values()][0].delay===15000,'body read remains inside timeout window');
  [...timers.values()][0].fn();await new Promise(resolve=>setImmediate(resolve));check(timers.size===0&&container.innerHTML.includes('unavailable'),'body abort releases timer and shows readable failure');check(requests===1&&!container.innerHTML.includes('Working…'),'no retry loop and busy message cleared');mounted.dispose();
});
console.log(JSON.stringify({result:'PASS',cases:cases.length,checks,caseNames:cases,engine:'Node24 SQLite, additive generated migration, actual Worker, and mocked account-switch/lost-response/JSON-body-timeout UI; no production account or preset changed'},null,2));
