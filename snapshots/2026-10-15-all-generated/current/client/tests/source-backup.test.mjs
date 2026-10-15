import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { mkdtempSync, readFileSync, writeFileSync, existsSync, realpathSync, rmSync } from 'node:fs';
import { join, relative, isAbsolute } from 'node:path';
import { tmpdir } from 'node:os';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
const require=createRequire(import.meta.url),api=require('../scripts/prepare-source-backup.cjs'),sha=bytes=>createHash('sha256').update(bytes).digest('hex');
test('source backup path and privacy filters reject runtime data while retaining approved app assets',()=>{
  for(const name of ['../outside.js','/absolute.js','C:/outside.js','a//b','a/../b','a\\b','a\0b'])assert.throws(()=>api.safeName(name));assert.equal(api.safeName('dist/client.js'),'dist/client.js');
  for(const name of ['.git/config','.preview/community.sqlite','node_modules/pkg/index.js','.env.local','nested/.env','account.p12','database.db','credentials.json','key.json','private.mp4','private.wav','private.zip','bearer-token.txt','private-user-photos/selfie.jpg','dist/server/index.js','dist/.openai/build-provenance.json'])assert.equal(api.denied(name),true,name);
  for(const name of ['worker/community.mjs','.openai/hosting.json','db/schema.ts','dist/brands/silvio-wordmark.png'])assert.equal(api.denied(name),false,name);
  for(const name of ['dist/covers/s001.jpg','dist/covers/s035.jpg','dist/learning/welcome.jpg','dist/brands/vellen-wordmark.png','dist/icons/icon-192.png','dist/violin.png'])assert.doesNotThrow(()=>api.inspectImage(name));assert.throws(()=>api.inspectImage('photos/customer.jpg'));
  assert.throws(()=>api.inspectText('secret.js',Buffer.from('ghp_'+'a'.repeat(36))));assert.throws(()=>api.inspectText('key.txt',Buffer.from(['-----BEGIN','PRIVATE KEY-----'].join(' '))));assert.throws(()=>api.inspectText('auth.json',Buffer.from('{"Authorization":"Bearer '+ 'a'.repeat(32)+'"}')));
  assert.doesNotThrow(()=>api.inspectText('normal.js',Buffer.from('const token = options.token;')));
});
test('ZIP checksum validation round-trips exact UTF8 names and rejects corrupt data',()=>{
  const entries=[{name:'smartvio-mobile/app.js',bytes:Buffer.from('const answer=42;\n')},{name:'smartvio-mobile/报告.txt',bytes:Buffer.from('正式报告\n')}],zip=api.makeZip(entries),decoded=api.readZip(zip);assert.equal(decoded.size,2);for(const entry of entries)assert(decoded.get(entry.name).equals(entry.bytes));assert.equal(api.crc32(Buffer.from('123456789')),0xcbf43926,'standard CRC32 test vector');
  const broken=Buffer.from(zip);broken[31+Buffer.byteLength(entries[0].name)]^=16;assert.throws(()=>api.readZip(broken));assert.throws(()=>api.makeZip([{name:'../unsafe',bytes:Buffer.from('x')}]));
});
test('generated restore tool verifies pieces, archive CRC and each source SHA before safe extraction',()=>{
  const folder=mkdtempSync(join(tmpdir(),'smartvio-backup-test-'));
  try{
    const files=[{path:'app.js',data:Buffer.from('console.log("fixture");\n')},{path:'docs/报告.txt',data:Buffer.from('原始文件\n')}],commit='a'.repeat(40),source={schemaVersion:1,project:'smartvio-mobile',commit,files:files.map(item=>({path:item.path,bytes:item.data.length,sha256:sha(item.data)}))};
    const zip=api.makeZip([...files.map(item=>({name:'smartvio-mobile/'+item.path,bytes:item.data})),{name:'smartvio-source-manifest.json',bytes:Buffer.from(JSON.stringify(source))}]),parts=[];
    for(let offset=0,index=1;offset<zip.length;offset+=100,index++){const path='source.zip.part-'+String(index).padStart(4,'0')+'.b64',bytes=zip.subarray(offset,offset+100),encoded=bytes.toString('base64')+'\n';writeFileSync(join(folder,path),encoded,'ascii');parts.push({path,bytes:bytes.length,encodedBytes:Buffer.byteLength(encoded,'ascii'),sha256:sha(bytes)});}
    const manifest={...source,archive:{bytes:zip.length,sha256:sha(zip)},partEncoding:'base64-ascii',parts};writeFileSync(join(folder,'FILE-MANIFEST.json'),JSON.stringify(manifest));writeFileSync(join(folder,'RESTORE-VERIFY.cjs'),api.restoreSource());
    const result=JSON.parse(execFileSync(process.execPath,[join(folder,'RESTORE-VERIFY.cjs'),'--verify-only'],{encoding:'utf8'}));assert.equal(result.result,'PASS');assert.equal(result.files,2);assert.equal(result.crcVerified,true);
    const destination=join(folder,'restored');execFileSync(process.execPath,[join(folder,'RESTORE-VERIFY.cjs'),destination],{encoding:'utf8'});for(const file of files)assert(readFileSync(join(destination,'smartvio-mobile',file.path)).equals(file.data));assert.equal(readFileSync(join(destination,'SOURCE-COMMIT.txt'),'utf8'),commit+'\n');
    assert.throws(()=>execFileSync(process.execPath,[join(folder,'RESTORE-VERIFY.cjs'),destination],{stdio:'pipe'}),'never overwrite an existing destination');
    const originalPart=readFileSync(join(folder,parts[0].path),'ascii');writeFileSync(join(folder,parts[0].path),'!'+originalPart);assert.throws(()=>execFileSync(process.execPath,[join(folder,'RESTORE-VERIFY.cjs'),'--verify-only'],{stdio:'pipe'}),'reject invalid Base64 before extracting');
    const corrupt=Buffer.from(originalPart.trim(),'base64');corrupt[0]^=1;writeFileSync(join(folder,parts[0].path),corrupt.toString('base64')+'\n','ascii');assert.throws(()=>execFileSync(process.execPath,[join(folder,'RESTORE-VERIFY.cjs'),'--verify-only'],{stdio:'pipe'}),'valid Base64 with changed decoded bytes still fails SHA');
  }finally{
    const base=realpathSync(tmpdir()),target=realpathSync(folder),rel=relative(base,target);assert(!isAbsolute(rel)&&/^smartvio-backup-test-[A-Za-z0-9]+$/.test(rel),'bounded task-owned cleanup target');rmSync(target,{recursive:true,force:true});
  }
});
