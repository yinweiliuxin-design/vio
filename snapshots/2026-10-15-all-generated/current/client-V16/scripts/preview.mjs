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
function objectPath(key){if(typeof key!=='string'||!/^[a-zA-Z0-9/_\-.]+$/.test(key)||key.includes('..')||key.startsWith('/'))throw Error('Invalid object key');const filename=path.resolve(bucketDir,key);if(!filename.startsWith(path.resolve(bucketDir)+path.sep))throw Error('Invalid object key');return filename;}
const BUCKET={
  async put(key,value){const filename=objectPath(key);fs.mkdirSync(path.dirname(filename),{recursive:true});const bytes=new Uint8Array(value);fs.writeFileSync(filename,bytes);return {key,size:bytes.byteLength};},
  async head(key){const filename=objectPath(key);try{const stat=fs.statSync(filename);return stat.isFile()?{size:stat.size}:null;}catch(cause){if(cause.code==='ENOENT')return null;throw cause;}},
  async get(key,options){const filename=objectPath(key);let stat;try{stat=fs.statSync(filename);}catch(cause){if(cause.code==='ENOENT')return null;throw cause;}if(!stat.isFile())return null;
    if(options?.range){const {offset,length}=options.range;if(!Number.isSafeInteger(offset)||offset<0||!Number.isSafeInteger(length)||length<1)throw Error('Invalid object range');const actual=Math.min(length,Math.max(0,stat.size-offset)),body=Buffer.alloc(actual),handle=fs.openSync(filename,'r');try{let read=0;while(read<actual){const count=fs.readSync(handle,body,read,actual-read,offset+read);if(!count)throw Error('Truncated local object');read+=count;}}finally{fs.closeSync(handle);}return {body,size:stat.size,range:{offset,length:actual}};}
    return {body:fs.readFileSync(filename),size:stat.size};
  },
  async delete(key){const filename=objectPath(key);if(fs.existsSync(filename))fs.unlinkSync(filename);}
};
const qaEnabled=process.env.SV_PREVIEW_QA==='true';let qaFixture=null;
function fixtureVideo(){if(qaFixture)return qaFixture;const source=fs.readFileSync(path.join(root,'tests','community-video.test.mjs'),'utf8'),match=/const MP4=Buffer\.from\('([A-Za-z0-9+/=]+)','base64'\)/.exec(source);if(!match)throw Error('Generated video fixture not found');const bytes=Buffer.from(match[1],'base64');if(bytes.length<32||bytes.length>20000000||bytes.toString('ascii',4,8)!=='ftyp')throw Error('Generated video fixture is invalid');qaFixture=bytes;return qaFixture;}
function qaResponse(req,res,bytes,type,frameable=false){const headers={'Content-Type':type,'Content-Length':String(bytes.length),'Cache-Control':'no-store','X-Content-Type-Options':'nosniff','Cross-Origin-Resource-Policy':'same-origin'};
  if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{...headers,Allow:'GET, HEAD','Content-Length':'0'});res.end();return;}
  if(type.startsWith('text/html')){headers['Content-Security-Policy']="default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; frame-src 'self'; connect-src 'self'; media-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors "+(frameable?"'self'":"'none'");headers['X-Frame-Options']=frameable?'SAMEORIGIN':'DENY';}
  if(type==='video/mp4'){headers['Accept-Ranges']='bytes';const range=req.method==='GET'&&req.headers.range;if(range&&/^bytes=(\d*)-(\d*)$/.test(range)){const [,left,right]=/^bytes=(\d*)-(\d*)$/.exec(range);let start,end;if(!left){const count=Number(right);start=Math.max(0,bytes.length-count);end=bytes.length-1;}else{start=Number(left);end=right?Math.min(Number(right),bytes.length-1):bytes.length-1;}if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||start>=bytes.length||end<start||(!left&&Number(right)<1)){res.writeHead(416,{...headers,'Content-Range':'bytes */'+bytes.length,'Content-Length':'0'});res.end();return;}res.writeHead(206,{...headers,'Content-Range':'bytes '+start+'-'+end+'/'+bytes.length,'Content-Length':String(end-start+1)});res.end(bytes.subarray(start,end+1));return;}}
  res.writeHead(200,headers);res.end(req.method==='HEAD'?undefined:bytes);
}
const port=Number(process.env.SV_PREVIEW_PORT||18912),env={DB:db,BUCKET,ADMIN_USER_IDS:JSON.stringify(['preview-owner'])};
const server=http.createServer(async(req,res)=>{
  try{
    if(req.headers.host!==`127.0.0.1:${port}`&&req.headers.host!==`localhost:${port}`){res.writeHead(403);res.end();return;}
    const pathname=new URL(req.url,`http://127.0.0.1:${port}`).pathname;
    if(pathname.startsWith('/__qa/')){
      if(!qaEnabled){res.writeHead(404);res.end();return;}
      if(pathname==='/__qa/blank'){qaResponse(req,res,Buffer.from('<!doctype html><meta charset="utf-8"><title>等待载入应用</title><p style="font:16px system-ui;color:#52655a;padding:30px">点击左侧“载入 390px 应用”开始验收。</p>'),'text/html; charset=utf-8',true);return;}
      if(pathname==='/__qa/v16'){qaResponse(req,res,fs.readFileSync(path.join(root,'scripts','qa-v16.html')),'text/html; charset=utf-8');return;}
      if(pathname==='/__qa/fixture.mp4'){qaResponse(req,res,fixtureVideo(),'video/mp4');return;}
      res.writeHead(404);res.end();return;
    }
    const chunks=[];let length=0;for await(const chunk of req){length+=chunk.length;if(length>21000000){res.writeHead(413);res.end();return;}chunks.push(chunk);}
    const headers=new Headers(req.headers);headers.delete('oai-authenticated-user-id');headers.delete('oai-authenticated-user-email');headers.delete('oai-authenticated-user-name');
    // Only this development server injects the documented test identity; never bundled into production.
    headers.set('oai-authenticated-user-id','preview-owner');
    const request=new Request(`http://127.0.0.1:${port}${req.url}`,{method:req.method,headers,...(['GET','HEAD'].includes(req.method)?{}:{body:Buffer.concat(chunks)})});
    const response=await worker.fetch(request,env,{waitUntil(promise){promise.catch(()=>{});}});
    res.writeHead(response.status,Object.fromEntries(response.headers));res.end(req.method==='HEAD'?undefined:Buffer.from(await response.arrayBuffer()));
  }catch(error){console.error(error.message);res.writeHead(500,{'Content-Type':'text/plain'});res.end('Preview failure');}
});
server.listen(port,'127.0.0.1',()=>console.log(JSON.stringify({preview:`http://127.0.0.1:${port}`,fixture:'preview-owner',instance:instance??null,storageDir:dir,root,pid:process.pid,qa:qaEnabled?`http://127.0.0.1:${port}/__qa/v16`:null})));
process.on('SIGTERM',()=>server.close(()=>process.exit(0)));
