'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),seedContext={window:{}};vm.runInNewContext(fs.readFileSync(path.join(root,'dist/seed.js'),'utf8'),seedContext);
const seed=seedContext.window.SV_SEED,scoreContext={module:{exports:{}}};vm.runInNewContext(fs.readFileSync(path.join(root,'dist/score-model.js'),'utf8'),scoreContext);const model=scoreContext.module.exports;
const ids=new Set(),titles=new Set(),markets=['us','uk','de','jp','cn','fr'],newSongs=seed.songs.filter(s=>s.catalogVersion===2);
const checks=[];for(const song of seed.songs){
  assert(!ids.has(song.id),'Duplicate ID '+song.id);ids.add(song.id);assert(song.melody?.trim(),'Missing melody '+song.id);
  const meter=(song.practice?.meter||'4/4').split('/').map(Number),score=model.createScore(song,{numerator:meter[0],denominator:meter[1]});
  assert(score.events.some(n=>n.pitch!=='R'),'Silent score '+song.id);assert(score.totalTicks>0);assert(song.regions.every(r=>markets.includes(r)));
  if(song.catalogVersion!==2)continue;
  assert(['global','regional'].includes(song.collection));assert(['beginner','folk','classic'].includes(song.category));
  for(const lang of ['zh','en','ja','de'])assert(typeof song.titles[lang]==='string'&&song.titles[lang].length>0,'Missing title '+song.id+' '+lang);
  assert(!titles.has(song.titles.en),'Duplicate new title '+song.titles.en);titles.add(song.titles.en);
  assert(song.rights.status==='verified-source');assert(song.source.url.startsWith('https://'));assert(song.source.edition&&song.source.attribution&&song.source.license&&song.source.licenseUrl);
  assert(song.practice.kind==='excerpt');assert(score.events.length<=250);assert(/^S0(?:0[1-9]|[12]\d|3[0-5])$/.test(song.coverId));
  if(song.collection==='global')assert(markets.every(r=>song.regions.includes(r)));else assert(song.regions.includes(song.originCountry));
  for(const event of score.events.filter(n=>n.pitch!=='R')){const midi=model.midi(event.pitch);assert(midi>=55&&midi<=100,'Outside violin practice range '+song.id+' '+event.pitch);}
  checks.push({id:song.id,title:song.titles.zh,group:song.collection,country:song.originCountry,notes:score.events.length,bars:Math.ceil(score.totalTicks/score.ticksPerBar),meter:song.practice.meter,melodySha256:crypto.createHash('sha256').update(song.melody).digest('hex')});
}
assert(newSongs.length>0,'Catalog expansion has not been applied');
// Existing browser history/personal tunes must survive receiving the new stock catalog.
const commonSource=fs.readFileSync(path.join(root,'dist/common.js'),'utf8'),stateKey='smartvio-mobile-state-v12-v1';
const plain=value=>JSON.parse(JSON.stringify(value));
function stateHarness(saved){
  let raw=JSON.stringify(saved);const writes=[];
  const sandbox={window:{SV_SEED:plain(seed)},structuredClone,localStorage:{getItem(key){assert.equal(key,stateKey);return raw;},setItem(key,value){assert.equal(key,stateKey);writes.push(key);raw=value;}},crypto:{randomUUID(){return 'fixture';}},document:{querySelector(){return null;}},setTimeout,clearTimeout};
  vm.createContext(sandbox);vm.runInContext(commonSource,sandbox);
  return {load:()=>plain(vm.runInContext('loadMobileState()',sandbox)),commit(value){sandbox.testState=value;vm.runInContext('commitMobileState(testState)',sandbox);},writes,raw:()=>raw};
}
const custom=(id,title)=>({id,title,author:'Owner',category:'custom',melody:'G4:1 A4:1 B4:2',titles:{en:title,zh:'私人曲 '+title},published:true,rights:{status:'verified-source'}});
const baseline={schema:11,revision:7,songs:[seed.songs[0],custom('PERSONAL_001','My saved melody')],sessions:[{id:'keep-session',duration:60}],presets:[{id:'keep-preset',effects:{volume:0.6}}],projects:[{id:'keep-project',trackIds:['S036','USER_S036']}],userPractice:{dailyGoal:35,completedLessons:['hold']}};
const originalHarness=stateHarness(baseline),restored=originalHarness.load();
assert.equal(restored.songs.length,seed.songs.length+1);assert.deepEqual(restored.sessions,baseline.sessions);assert.deepEqual(restored.presets,baseline.presets);assert.deepEqual(restored.projects,baseline.projects);assert.equal(restored.userPractice.dailyGoal,35);assert.equal(restored.songs.at(-1).rights.status,'user-provided');assert.equal(restored.songs.at(-1).published,false);assert.equal(originalHarness.writes.length,0,'Reading must not mutate storage or prefs');
const stock=seed.songs.find(song=>song.id==='S036');assert(stock,'S036 stock must exist for the actual regression');
const oldCustoms=[custom('S036','Old collision'),custom('USER_S036','Existing personal namespace'),custom('S036','Duplicate collision'),custom('USER_S036','Duplicate namespace'),custom('USER_S036_2','Existing suffix')];
const conflictSaved={...plain(baseline),songs:[stock,...oldCustoms],sessions:[
  {id:'old-personal',songId:'S036',song:'Old collision',duration:65,metrics:{pitchCoverage:0.8}},
  {id:'duplicate-personal',songId:'S036',song:'Duplicate collision',duration:70},
  {id:'existing-user',songId:'USER_S036',song:'Existing personal namespace'},
  {id:'duplicate-user',songId:'USER_S036',song:'Duplicate namespace'},
  {id:'stock-history',songId:'S036',song:stock.title},
  {id:'ambiguous-first',songId:'S036'},
  {id:'legacy-text-only',song:'Old collision',duration:80}
],projects:[...plain(baseline.projects),{id:'song-reference-project',songId:'S036',song:'Old collision',trackIds:['S036','USER_S036']}],posts:[{id:'note',text:'Retain'}],reports:[{id:'feedback'}],audit:[{id:'prior'}]};
const migration=stateHarness(conflictSaved),migrated=migration.load(),personal=migrated.songs.filter(song=>song.category==='custom');
assert.equal(personal.length,oldCustoms.length,'Every duplicate custom tune survives');assert.equal(new Set(migrated.songs.map(song=>song.id)).size,migrated.songs.length);
assert.deepEqual(personal.map(song=>song.id),['USER_S036_3','USER_S036','USER_S036_4','USER_S036_5','USER_S036_2']);
assert.equal(personal[0].legacyCatalogId,'S036');assert.equal(personal[0].originalId,'S036');assert.equal(personal[2].legacyCatalogId,'S036');assert.equal(personal[3].legacyCatalogId,'USER_S036');assert.equal(personal[1].legacyCatalogId,undefined);
for(let i=0;i<oldCustoms.length;i++){assert.equal(personal[i].title,oldCustoms[i].title);assert.equal(personal[i].author,oldCustoms[i].author);assert.equal(personal[i].melody,oldCustoms[i].melody);assert.deepEqual(personal[i].titles,oldCustoms[i].titles);assert.equal(personal[i].rights.status,'user-provided');assert.equal(personal[i].published,false);}
assert.deepEqual(migrated.sessions.map(row=>row.songId),['USER_S036_3','USER_S036_4','USER_S036','USER_S036_5','S036','USER_S036_3',undefined]);
assert.equal(migrated.sessions[0].duration,65);assert.deepEqual(migrated.sessions[0].metrics,{pitchCoverage:0.8});assert.deepEqual(migrated.projects[0],conflictSaved.projects[0]);assert.equal(migrated.projects[1].songId,'USER_S036_3');assert.deepEqual(migrated.projects[1].trackIds,['S036','USER_S036']);
for(const key of ['presets','posts','reports','audit','userPractice','revision'])assert.deepEqual(migrated[key],conflictSaved[key],'Preserve '+key);
assert.equal(migration.raw(),JSON.stringify(conflictSaved));assert.equal(migration.writes.length,0);
// Commit and reload the actual returned state. Retained legacy evidence must not
// redirect newly chosen stock songs, or renumber personal tunes a second time.
migration.commit(migrated);assert.deepEqual(migration.load(),migrated);
const afterStockPractice=plain(migrated);afterStockPractice.sessions.unshift({id:'new-stock',songId:'S036',song:stock.title});migration.commit(afterStockPractice);assert.deepEqual(migration.load(),afterStockPractice);assert.equal(migration.load().sessions[0].songId,'S036');
const sameTitleSaved=plain(conflictSaved);sameTitleSaved.songs[3].title='Old collision';sameTitleSaved.sessions=[{id:'same-title',songId:'S036',song:'Old collision'}];const sameTitleRestored=stateHarness(sameTitleSaved).load();assert.equal(sameTitleRestored.sessions[0].songId,'USER_S036_3','Indistinguishable duplicates use first saved tune');
const longId='X'.repeat(160),longSaved={...plain(baseline),songs:[custom(longId,'Long first'),custom(longId,'Long duplicate')],sessions:[{songId:longId,song:'Long duplicate'}]},longHarness=stateHarness(longSaved),longState=longHarness.load(),longPersonal=longState.songs.filter(song=>song.category==='custom');
assert.equal(longPersonal.length,2);assert.notEqual(longPersonal[0].id,longPersonal[1].id);assert(longPersonal.every(song=>/^[a-zA-Z0-9_-]{1,160}$/.test(song.id)));assert.equal(longState.sessions[0].songId,longPersonal[1].id);longHarness.commit(longState);assert.deepEqual(longHarness.load(),longState);
// A previously legal near-limit saved catalog must remain legal after expansion.
const largeSaved={...plain(baseline),songs:[...seed.songs.slice(0,35),...Array.from({length:950},(_,i)=>custom('PERSONAL_'+i,'Personal tune '+i))]},largeHarness=stateHarness(largeSaved),largeState=largeHarness.load();
assert.equal(largeSaved.songs.length,985);assert.equal(largeState.songs.length,seed.songs.length+950);largeHarness.commit(largeState);assert.deepEqual(largeHarness.load(),largeState);
const excessivePersonal={...plain(baseline),songs:Array.from({length:1001},(_,i)=>custom('PERSONAL_'+i,'Personal tune '+i))};assert.throws(()=>stateHarness(excessivePersonal).load(),/自建曲目数量/,'The personal count remains bounded');
console.log(JSON.stringify({result:'PASS',total:seed.songs.length,added:newSongs.length,global:newSongs.filter(s=>s.collection==='global').length,regional:Object.fromEntries(markets.map(r=>[r,newSongs.filter(s=>s.collection==='regional'&&s.originCountry===r).length])),browserRecordsPreserved:true,personalMigration:{stockCollision:true,existingNamespaceReserved:true,duplicatesPreserved:true,titleMatchedReferences:true,stockHistoryRetained:true,mediaIdsUnchanged:true,repeatRestoreStable:true,maxLengthIdStable:true,nearLimitExpansionStable:true,readDoesNotWritePrefs:true},scores:checks},null,2));
