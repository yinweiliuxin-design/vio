'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),file=path.join(root,'dist/seed.js'),context={window:{}};vm.runInNewContext(fs.readFileSync(file,'utf8'),context);
const seed=context.window.SV_SEED,expansion=JSON.parse(fs.readFileSync(path.join(root,'catalog/expansion-20261014.json'),'utf8'));
if(seed.schema!==11||expansion.catalogVersion!==2||!Array.isArray(expansion.songs))throw Error('Unexpected catalog schema');
const stock=seed.songs.filter(song=>song.catalogVersion!==2),ids=new Set(stock.map(s=>s.id));
for(const song of stock){song.collection=song.regions.length===6?'global':'regional';if(song.regions.length===1)song.originCountry=song.regions[0];}
// The Neapolitan standard belongs with shared repertoire, rather than German/French/UK traditions.
// Classification only: its existing pending score-rights status stays unchanged.
const sharedStandard=stock.find(song=>song.id==='S035');
if(sharedStandard){sharedStandard.collection='global';sharedStandard.regions=['us','uk','de','jp','fr','cn'];delete sharedStandard.originCountry;}
for(const song of expansion.songs){if(ids.has(song.id))throw Error('Duplicate catalog ID');ids.add(song.id);}
seed.songs=[...stock,...expansion.songs];seed.catalogVersion=2;
fs.writeFileSync(file,'window.SV_SEED='+JSON.stringify(seed)+';\n');console.log(JSON.stringify({total:seed.songs.length,added:expansion.songs.length}));
