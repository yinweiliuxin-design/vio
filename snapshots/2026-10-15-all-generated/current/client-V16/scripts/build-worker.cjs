/* Deterministic Worker bundle; dist remains the editable frontend source. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),zlib=require('node:zlib'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..'),dist=path.join(root,'dist');
const metadata=JSON.parse(fs.readFileSync(path.join(root,'.openai/hosting.json'),'utf8'));
if(metadata.static||metadata.d1!=='DB'||metadata.r2!=='BUCKET')throw Error('Expected D1/R2 Worker hosting configuration');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.webmanifest':'application/manifest+json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.txt':'text/plain; charset=utf-8','.pdf':'application/pdf','.wav':'audio/wav'};
const assets={},hashes={};
for(const required of ['index.html','client.html','client.js','community.js','community.css','admin.html','admin.js','admin.css','sw.js']){
  if(!fs.existsSync(path.join(dist,required)))throw Error('Required release asset is missing: '+required);
}
function visit(directory,relative=''){
  for(const entry of fs.readdirSync(directory,{withFileTypes:true}).sort((a,b)=>a.name.localeCompare(b.name))){
    if(!relative&&['server','.openai'].includes(entry.name))continue;
    if(entry.isSymbolicLink())throw Error('Asset symlinks are not supported');
    const rel=relative+entry.name,abs=path.join(directory,entry.name);
    if(entry.isDirectory())visit(abs,rel+'/');
    else if(entry.isFile()){
      const bytes=fs.readFileSync(abs),hash=crypto.createHash('sha256').update(bytes).digest('hex');
      assets['/'+rel]={data:zlib.gzipSync(bytes,{level:9,mtime:0}).toString('base64'),mime:mime[path.extname(rel)]||'application/octet-stream',hash};hashes[rel]=hash;
    }
  }
}
visit(dist);
const sandbox={window:{}};vm.runInNewContext(fs.readFileSync(path.join(dist,'seed.js'),'utf8'),sandbox,{timeout:1000});
const seed=Object.values(sandbox.window).find(value=>value&&Array.isArray(value.songs));
if(!seed)throw Error('Song catalog source was not found');
const catalog=seed.songs.map(s=>({id:s.id,title:s.title,titles:s.titles,author:s.author,category:s.category,regions:s.regions,rightsStatus:s.rights?.status||'pending'}));
let api=fs.readFileSync(path.join(root,'worker/community.mjs'),'utf8');
if(api.includes("from './video-inspection.mjs'")){const inspection=fs.readFileSync(path.join(root,'worker/video-inspection.mjs'),'utf8').replace(/^export\s+(?=(?:async\s+)?function|const|class)/gm,'');api=inspection+'\n'+api.replace(/^import\s+\{[^}]+\}\s+from\s+'\.\/video-inspection\.mjs';?\s*$/m,'');}
if(/^\s*import\s/m.test(api))throw Error('Community Worker must be standalone');
const code=api+'\nconst STATIC_ASSETS='+JSON.stringify(assets)+';\nconst CATALOG_SOURCE='+JSON.stringify(catalog)+';\n'+`
export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(url.pathname.startsWith('/api/'))return (await handleAPI(request,{...env,CATALOG_SOURCE}))||new Response('Not found',{status:404});
    if(!['GET','HEAD'].includes(request.method))return new Response('Method not allowed',{status:405,headers:{Allow:'GET, HEAD'}});
    let pathname=url.pathname;
    if(pathname==='/')pathname='/index.html';
    if(pathname==='/admin'||pathname==='/admin/')pathname='/admin.html';
    const asset=STATIC_ASSETS[pathname];
    if(!asset)return new Response('Not found',{status:404});
    const headers={'Content-Type':asset.mime,'Content-Encoding':'gzip','X-Content-Type-Options':'nosniff','Referrer-Policy':'same-origin','Cache-Control':'no-store','ETag':'"'+asset.hash+'"','Permissions-Policy':'camera=(self), microphone=(self), geolocation=()'};
    if(pathname==='/sw.js')headers['Service-Worker-Allowed']='/';
    const body=request.method==='HEAD'?null:Uint8Array.from(atob(asset.data),c=>c.charCodeAt(0));
    return new Response(body,{headers,encodeBody:'manual'});
  }
};
`;
fs.mkdirSync(path.join(dist,'server'),{recursive:true});fs.writeFileSync(path.join(dist,'server/index.js'),code);
fs.mkdirSync(path.join(dist,'.openai'),{recursive:true});fs.writeFileSync(path.join(dist,'.openai/hosting.json'),JSON.stringify(metadata,null,2)+'\n');
fs.cpSync(path.join(root,'drizzle'),path.join(dist,'.openai/drizzle'),{recursive:true});
fs.writeFileSync(path.join(dist,'.openai/build-provenance.json'),JSON.stringify({assets:hashes,catalogCount:catalog.length,workerSha256:crypto.createHash('sha256').update(code).digest('hex')},null,2)+'\n');
console.log(JSON.stringify({assets:Object.keys(assets).length,catalog:catalog.length,workerBytes:Buffer.byteLength(code)}));
