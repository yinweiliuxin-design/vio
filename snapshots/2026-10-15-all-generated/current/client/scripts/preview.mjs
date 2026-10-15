// Development only: loopback server with an isolated SQLite DB and explicit fixture identity.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createD1,applyMigrations} from '../tests/d1-sqlite.mjs';
import worker from '../dist/server/index.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const instance=process.env.SV_PREVIEW_INSTANCE;
if(instance!==undefined&&!/^[a-zA-Z0-9_-]{1,64}$/.test(instance))throw Error('SV_PREVIEW_INSTANCE must contain 1-64 letters, digits, underscores or hyphens.');
const dir=instance===undefined?path.join(root,'.preview'):path.join(root,'.preview',instance);fs.mkdirSync(dir,{recursive:true});
const db=createD1(path.join(dir,'community.sqlite'));await applyMigrations(db,path.join(root,'drizzle'));
const bucketDir=path.join(dir,'media');fs.mkdirSync(bucketDir,{recursive:true});
function objectPath(key){if(!/^[a-zA-Z0-9/_\-.]+$/.test(key)||key.includes('..'))throw Error('Invalid object key');return path.join(bucketDir,key);}
const BUCKET={async put(key,value){const filename=objectPath(key);fs.mkdirSync(path.dirname(filename),{recursive:true});fs.writeFileSync(filename,new Uint8Array(value));return {key};},async get(key){const filename=objectPath(key);return fs.existsSync(filename)?{body:fs.readFileSync(filename)}:null;},async delete(key){const filename=objectPath(key);if(fs.existsSync(filename))fs.unlinkSync(filename);}};
const port=Number(process.env.SV_PREVIEW_PORT||18912),env={DB:db,BUCKET,ADMIN_USER_IDS:JSON.stringify(['preview-owner'])};
const server=http.createServer(async(req,res)=>{
  try{
    if(req.headers.host!==`127.0.0.1:${port}`&&req.headers.host!==`localhost:${port}`){res.writeHead(403);res.end();return;}
    const chunks=[];let length=0;for await(const chunk of req){length+=chunk.length;if(length>21000000){res.writeHead(413);res.end();return;}chunks.push(chunk);}
    const headers=new Headers(req.headers);headers.delete('oai-authenticated-user-id');headers.delete('oai-authenticated-user-email');headers.delete('oai-authenticated-user-name');
    // Only this development server injects the documented test identity; never bundled into production.
    headers.set('oai-authenticated-user-id','preview-owner');
    const request=new Request(`http://127.0.0.1:${port}${req.url}`,{method:req.method,headers,...(['GET','HEAD'].includes(req.method)?{}:{body:Buffer.concat(chunks)})});
    const response=await worker.fetch(request,env,{waitUntil(promise){promise.catch(()=>{});}});
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(req.method==='HEAD'?undefined:Buffer.from(await response.arrayBuffer()));
  }catch(error){console.error(error.message);res.writeHead(500,{'Content-Type':'text/plain'});res.end('Preview failure');}
});
server.listen(port,'127.0.0.1',()=>console.log(JSON.stringify({preview:`http://127.0.0.1:${port}`,fixture:'preview-owner',instance:instance??null,storageDir:dir,root,pid:process.pid})));
process.on('SIGTERM',()=>server.close(()=>process.exit(0)));
