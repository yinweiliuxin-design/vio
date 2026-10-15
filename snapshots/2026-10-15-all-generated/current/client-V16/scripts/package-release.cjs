'use strict';
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process'),crypto=require('node:crypto'),zlib=require('node:zlib');
const root=path.resolve(__dirname,'..'),git=process.env.SITES_GIT_BIN||'E:\\codex\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\native\\git\\cmd\\git.exe';
function gitRead(args){return cp.execFileSync(git,args,{cwd:root,maxBuffer:32*1024*1024});}
const commit=gitRead(['rev-parse','HEAD']).toString().trim();
if(gitRead(['status','--porcelain']).toString().trim())throw Error('Package only the exact committed source');
const tracked=gitRead(['ls-files','-z']).toString().split('\0').filter(Boolean);
for(const file of tracked){if(!fs.readFileSync(path.join(root,file)).equals(gitRead(['show',commit+':'+file])))throw Error('Source differs from commit: '+file);}
cp.execFileSync(process.execPath,[path.join(root,'scripts/build-worker.cjs')],{cwd:root,stdio:'inherit'});
const worker=fs.readFileSync(path.join(root,'dist/server/index.js'),'utf8'),match=worker.match(/\nconst STATIC_ASSETS=(.+);\nconst CATALOG_SOURCE=/);
if(!match)throw Error('Missing embedded asset map');
const assets=JSON.parse(match[1]);for(const [key,asset] of Object.entries(assets)){if(!zlib.gunzipSync(Buffer.from(asset.data,'base64')).equals(fs.readFileSync(path.join(root,'dist',key.slice(1)))))throw Error('Embedded asset mismatch: '+key);}
const artifacts=path.resolve(root,'../artifacts/v16-20261015');fs.mkdirSync(artifacts,{recursive:true});
const stage=fs.mkdtempSync(path.join(artifacts,'package-'));
const stageRelative=path.relative(fs.realpathSync(artifacts),fs.realpathSync(stage));
if(!stageRelative.startsWith('package-')||stageRelative.includes(path.sep)||path.isAbsolute(stageRelative))throw Error('Packaging target must be a new directory inside release artifacts');
const destination=path.join(fs.realpathSync(stage),'dist');
if(path.dirname(destination)!==fs.realpathSync(stage))throw Error('Unsafe packaging destination');
const helper=process.env.SITES_PREPARE_BUILD||'E:\\codex\\.codex\\plugins\\cache\\openai-curated-remote\\sites\\1.0.0\\skills\\sites\\scripts\\prepare-site-build.cjs';
cp.execFileSync(process.execPath,[helper,root,destination,root],{cwd:root,stdio:'inherit'});
const archive=path.join(artifacts,'smartvio-community-'+commit.slice(0,10)+'.tar.gz');
cp.execFileSync('C:\\Windows\\System32\\tar.exe',['-czf',archive,'-C',stage,'dist'],{cwd:root});
const members=cp.execFileSync('C:\\Windows\\System32\\tar.exe',['-tzf',archive],{encoding:'utf8'}).split(/\r?\n/).filter(Boolean);
if(members.some(name=>/node_modules|\.preview|\.git\/|\.env|community\.sqlite/.test(name))||!members.includes('dist/server/index.js')||!members.includes('dist/.openai/drizzle/0001_furry_zarek.sql')||!members.includes('dist/.openai/drizzle/0002_learn_onboarding.sql')||!members.includes('dist/.openai/drizzle/0003_private_preset_backup.sql'))throw Error('Archive inventory is invalid');
const proof={commit,archive,archiveSha256:crypto.createHash('sha256').update(fs.readFileSync(archive)).digest('hex'),files:members.length,assets:Object.keys(assets).length,workerSha256:crypto.createHash('sha256').update(worker).digest('hex'),stage};
fs.writeFileSync(path.join(artifacts,'release-provenance.json'),JSON.stringify(proof,null,2)+'\n');console.log(JSON.stringify(proof));
