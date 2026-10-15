import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { randomUUID } from 'node:crypto';
const seedSandbox={window:{}};vm.runInNewContext(readFileSync(new URL('../dist/seed.js',import.meta.url),'utf8'),seedSandbox);const seed=seedSandbox.window.SV_SEED,source=readFileSync(new URL('../dist/common.js',import.meta.url),'utf8');
const plain=value=>JSON.parse(JSON.stringify(value));
function preset(id=randomUUID(),extra={}){return {id,name:'My warm sound',preset:'Warm',effects:{volume:.7,reverb:.2,delay:.1,compression:.3},...extra};}
function harness(saved=null,options={}){
  let raw=saved===null?null:JSON.stringify(saved),writes=0;
  const context={window:{SV_SEED:plain(seed)},crypto:{randomUUID},structuredClone,document:{querySelector(){return null;}},localStorage:{getItem(){if(options.readError)throw Error('denied');return raw;},setItem(key,value){if(options.writeError)throw Error('readonly');writes++;raw=value;}},setTimeout,clearTimeout};vm.createContext(context);vm.runInContext(source,context);vm.runInContext('svOnline=true;svState=loadMobileState();',context);
  return {context,raw:()=>raw,writes:()=>writes,state:()=>plain(vm.runInContext('svState',context)),load:()=>plain(vm.runInContext('loadMobileState()',context)),normalize(value){context.testPayload=value;return plain(vm.runInContext('mobilePreset(testPayload)',context));},async action(value){context.testPayload=value;return await vm.runInContext('action(testPayload)',context);}};
}
function baseline(presets=[]){return {schema:11,revision:7,songs:plain(seed.songs.slice(0,35)),sessions:[{id:'old-session',songId:'S001',duration:60}],projects:[{id:'old-project',name:'Old project',trackIds:['existing-recording']}],presets,posts:[{id:'old-note',text:'Keep private'}],reports:[{id:'old-report'}],audit:[{id:'old-audit'}],userPractice:{dailyGoal:35,completedLessons:['hold']}};}
test('local preset defaults and strict browser gain ranges preserve independent four effects',()=>{
  const h=harness(),record=h.normalize(preset());assert.equal(record.group,'');assert.equal(record.inputGain,1);assert.deepEqual(Object.keys(record.effects).sort(),['compression','delay','reverb','volume']);
  assert.equal(h.normalize(preset('p',{inputGain:0,group:' Beginners '})).inputGain,0);assert.equal(h.normalize(preset('p',{inputGain:2})).inputGain,2);assert.equal(h.normalize(preset('p',{name:' Name ',group:' Group '})).group,'Group');
  for(const fields of [{name:''},{name:'n'.repeat(81)},{group:'g'.repeat(61)},{preset:'UnlicensedApplePatch'},{inputGain:-.1},{inputGain:2.1},{inputGain:NaN},{inputGain:Infinity},{inputGain:'1'},{effects:{volume:1,reverb:-1,delay:0,compression:0}},{effects:{volume:1,reverb:0,delay:0}}])assert.throws(()=>h.normalize(preset('p',fields)));
  assert.equal(h.writes(),0,'normalizing does not persist');
});
test('same-ID same-content import is idempotent and conflicting content becomes a new ID without replacing history',async()=>{
  const original=preset('one',{group:'Private',inputGain:.8}),saved=baseline([original]),h=harness(saved);
  assert.equal(await h.action({type:'presets-import',presets:[plain(original)]}),true);assert.equal(h.state().presets.length,1,'duplicate identical record is not added');assert.deepEqual(h.state().presets[0],original,'identical old record retains its metadata');
  assert.equal(await h.action({type:'presets-import',presets:[{...plain(original),name:'New sound',inputGain:1.5}]}),true);const state=h.state();assert.equal(state.presets.length,2);assert.deepEqual(state.presets[0],original);assert.notEqual(state.presets[1].id,'one');assert.equal(state.presets[1].name,'New sound');assert.equal(state.presets[1].inputGain,1.5);
  for(const key of ['sessions','projects','posts','reports','userPractice'])assert.deepEqual(state[key],saved[key],key+' preserved');assert.equal(state.songs.length,68);assert.equal(h.writes(),2);
});
test('bad file records, duplicate IDs and oversized merged preset count never commit partially applied changes',async()=>{
  const saved=baseline(Array.from({length:99},(_,i)=>preset('preset_'+i))),h=harness(saved),before=h.raw(),stateBefore=h.state();
  assert.equal(await h.action({type:'presets-import',presets:[preset('new1'),preset('new2')]}),false);assert.equal(h.raw(),before);assert.deepEqual(h.state(),stateBefore);assert.equal(h.writes(),0,'overflow has no partial save');
  for(const incoming of [[preset('valid'),preset('bad',{name:''})],[preset('repeat'),preset('repeat')],[preset('unsafe/id')],Array.from({length:101},(_,i)=>preset('too_'+i)),null]){assert.equal(await h.action({type:'presets-import',presets:incoming}),false);assert.equal(h.raw(),before);assert.equal(h.writes(),0);}
  assert.equal(await h.action({type:'presets-import',presets:[preset('new1')]}),true);assert.equal(h.state().presets.length,100);assert.equal(await h.action({type:'preset-save',...preset(undefined)}),false);assert.equal(h.state().presets.length,100);
});
test('readonly local persistence rejects save/import and keeps both committed bytes and displayed state',async()=>{
  const saved=baseline([preset('keep')]),h=harness(saved,{writeError:true}),before=h.raw(),stateBefore=h.state();
  assert.equal(await h.action({type:'presets-import',presets:[preset('incoming')]}),false);assert.equal(await h.action({type:'preset-save',...preset('keep',{name:'Changed'})}),false);assert.equal(h.raw(),before);assert.equal(h.writes(),0);assert.deepEqual(h.state(),stateBefore);
});
test('personal scale tunes retain safe note syntax and user-provided rights, cannot overwrite stock or claim publication',async()=>{
  const h=harness(baseline()),song={id:'EXERCISE_G_fixture',title:'G major scale',author:'Original first-position exercise',category:'custom',melody:'G3:1 A3:1 B3:1 C4:1 D4:1 E4:1 F#4:1 G4:1',rights:{status:'reviewed',territories:['global']},published:true};
  assert.equal(await h.action({type:'personal-song',song}),true);const stored=h.state().songs.find(row=>row.id===song.id);assert.equal(stored.rights.status,'user-provided');assert.equal(stored.published,false);assert.deepEqual(stored.rights.territories,[]);assert.equal(stored.melody,song.melody);assert.equal(h.state().songs.length,69);
  const before=h.raw(),writes=h.writes();assert.equal(await h.action({type:'personal-song',song:{...song,id:'S001'}}),false);assert.equal(h.raw(),before);assert.equal(h.writes(),writes);assert.equal(h.state().songs.find(row=>row.id==='S001').title,seed.songs[0].title);
  for(const melody of ['G4:0','Unknown:1','G4:-1','G4:Infinity','G4:1:extra','G4:65','']){assert.equal(await h.action({type:'personal-song',song:{...song,id:'EXERCISE_invalid',melody}}),false);assert.equal(h.raw(),before);}
});
test('old stock catalog migration restores all 68 shipped songs while retaining personal collisions and record references',async()=>{
  const saved=baseline([preset('old')]);saved.songs.push({id:'S036',title:'Old private tune',author:'Owner',category:'custom',melody:'G4:1 A4:1 B4:2',rights:{status:'reviewed'},published:true});saved.sessions.push({id:'private-history',songId:'S036',song:'Old private tune',duration:70});const h=harness(saved),state=h.state();
  assert.equal(state.songs.length,69);const own=state.songs.find(row=>row.category==='custom');assert.equal(own.id,'USER_S036');assert.equal(state.sessions.at(-1).songId,own.id);assert.equal(state.songs.find(row=>row.id==='S036').title,seed.songs.find(row=>row.id==='S036').title);assert.deepEqual(state.presets,saved.presets);assert.equal(h.writes(),0,'migration read keeps stored file bytes unchanged');
  assert.equal(await h.action({type:'presets-import',presets:[preset('new')]}),true);assert.deepEqual(h.load(),h.state(),'actual committed migration reload is stable');
});
