from pathlib import Path,PurePosixPath
import json,hashlib,io,os,zipfile,tarfile,shutil,re,collections,datetime
W=Path(__file__).resolve().parent
BASE=Path('E:/codex/Documents/亚马逊图片')
OUT=W/'publish'; OUT.mkdir(exist_ok=True)
OBJECTS=W/'objects';OBJECTS.mkdir(exist_ok=True)
PREFIX='smartvio-generated/2026-10-15'
REPO=OUT/PREFIX;REPO.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def digest_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
inventory=json.loads((W/'inventory/included-files.json').read_text('utf8'))
privacy=json.loads((W/'privacy/privacy-audit.json').read_text('utf8'))
assert not privacy['errors']
assert not any(x.get('kind')=='credential' for x in privacy['findings'])
SKIP={'.openai','.git','.state','.wrangler','.preview','.aws','.ssh','node_modules','__pycache__','.venv','venv','.cache','ccache'}
def bad(name):
 p=PurePosixPath(name.replace('\\','/'));low=[s.lower() for s in p.parts]
 return p.is_absolute() or '..' in low or any(s in SKIP for s in low) or bool(low and (low[0].endswith(':') or low[-1] in {'cookies.json','credentials.json','secrets.json','id_rsa','id_ed25519'} or low[-1]=='.env' or (low[-1].startswith('.env.') and low[-1] not in {'.env.example','.env.sample','.env.template'})))
removed=[];changed_archives=[];cache={}
def sanitize(data,name,source,depth=0):
 assert depth<10
 key=sha(data)
 if key in cache:
  result,reasons=cache[key]
  removed.extend({'source':source,'member':r} for r in reasons)
  return result
 reasons=[]; name=name.lower(); result=data
 if name.endswith('.zip') and zipfile.is_zipfile(io.BytesIO(data)):
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   entries=[];change=False
   for item in z.infolist():
    if bad(item.filename) or ((item.external_attr>>16)&0o170000)==0o120000:
     reasons.append(item.filename);change=True;continue
    value=z.read(item)
    n=sanitize(value,item.filename,source+'!'+item.filename,depth+1) if not item.is_dir() else value
    change|=n!=value;entries.append((item,n))
   if change:
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as oz:
     for item,n in entries:oz.writestr(item,n)
    result=buf.getvalue()
 elif name.endswith(('.tar.gz','.tgz','.tar')):
  with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as z:
   entries=[];change=False
   for item in z:
    if bad(item.name) or item.issym() or item.islnk():
     reasons.append(item.name);change=True;continue
    value=z.extractfile(item).read() if item.isfile() else b''
    n=sanitize(value,item.name,source+'!'+item.name,depth+1) if item.isfile() else value
    change|=n!=value;entries.append((item,n))
   if change:
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz' if name.endswith(('.tgz','.gz')) else 'w') as oz:
     for item,n in entries:
      if item.isfile():item.size=len(n)
      oz.addfile(item,io.BytesIO(n) if item.isfile() else None)
    result=buf.getvalue()
 if name.endswith(('.zip','.tar.gz','.tgz','.tar')):cache[key]=(result,reasons)
 removed.extend({'source':source,'member':r} for r in reasons)
 return result

# Re-enumerate active software to include files created since the read-only inventory.
known={r['relativePath'] for r in inventory}
for folder,category in [('sites/smartvio-mobile','active-software/mobile'),('sites/artifacts','active-software/artifacts-history')]:
 for root,dirs,fs in os.walk(BASE/folder,followlinks=False):
  dirs[:]=[d for d in dirs if d not in SKIP and not (Path(root)/d).is_junction() and not (Path(root)/d).is_symlink()]
  for n in fs:
   p=Path(root)/n;rel=p.relative_to(BASE).as_posix()
   if rel in known or bad(rel) or p.suffix.lower() in {'.pyc','.sqlite','.sqlite3','.db','.pem','.key','.p12','.pfx'}:continue
   inventory.append({'absolutePath':str(p),'relativePath':rel,'sha256':None,'category':category,'size':p.stat().st_size});known.add(rel)
records=[];drift=[];secret=[]
patterns=[re.compile(rb'github_pat_[A-Za-z0-9_]{40,}'),re.compile(rb'gh[pousr]_[A-Za-z0-9]{30,}'),re.compile(rb'AKIA[0-9A-Z]{16}'),re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
for i,row in enumerate(inventory):
 p=Path(row['absolutePath']); rel=row['relativePath'];assert not p.is_junction() and not p.is_symlink()
 data=p.read_bytes(); before=sha(data)
 assert p.stat().st_size==len(data),'Source changing during read '+rel
 if row.get('sha256')!=before:drift.append({'file':rel,'inventoried':row.get('sha256'),'captured':before})
 if len(data)<10*1024*1024 and p.suffix.lower() in {'.txt','.json','.py','.cjs','.mjs','.js','.ps1','.html','.md','.csv','.yml','.yaml','.log'}:
  if any(rx.search(data) for rx in patterns):secret.append(rel);continue
 clean=sanitize(data,p.name,rel);dig=sha(clean)
 obj=OBJECTS/dig
 if not obj.exists():obj.write_bytes(clean)
 if clean!=data:changed_archives.append({'source':rel,'sourceSHA256':before,'uploadedSHA256':dig})
 records.append({'file':rel,'category':row['category'],'restorePath':row['category']+'/'+rel,'sourceSHA256':before,'sha256':dig,'bytes':len(clean),'sanitized':clean!=data})
 if i%1000==0:print('Captured',i,flush=True)
assert not secret, 'Credential-pattern review required: '+str(secret)
assert next(r for r in records if r['file']=='SmartVio-R3-最新方案与工程资料-20261013.zip')['sha256']=='d0ec6331d4b88b9c7c2a80528609e6f0f7621eafb7953d97fb55bfcd11a7381a'
byhash={r['sha256']:r['bytes'] for r in records}
write(REPO/'FILE-MANIFEST.json',{'schema':'smartvio.organized-full-snapshot.v1','snapshotDate':'2026-10-15','capturedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'SmartVio generated project files in the named local workspace; current, active software and historical material kept separate',
 'fileCount':len(records),'uniqueObjects':len(byhash),'files':records})
write(REPO/'audit/SOURCE-CAPTURE.json',{'sourceBase':str(BASE),'changesSinceInventory':drift,'credentialPatternHits':0,'note':'Point-in-time file capture; no claim that ongoing software edits were product-qualified'})
write(REPO/'audit/ARCHIVE-SANITIZATION.json',{'changedArchives':changed_archives,'removedMembers':removed,'originalsRetainedLocally':True,'reason':'Remove local deployment/account/cache state from upload copies'})
shutil.copy2(W/'privacy/privacy-summary.json',REPO/'audit/PRIVACY-INITIAL-SCAN.json')
shutil.copy2(W/'inventory/excluded-build-cache-files.json',REPO/'audit/EXCLUDED-BUILD-CACHE.json')
write(REPO/'audit/SCOPE-EXCLUSIONS.json',{'excluded':'Unrelated Amazon assets, REA/tooling installations, credentials/account state, node_modules, runtime caches, .git, junction targets and temporary compilation objects.',
 'allProjectOriginalsPreserved':True,'classifications':dict(collections.Counter(x['category'] for x in records))})
pack=W/'all-unique-objects.zip'
with zipfile.ZipFile(pack,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
 for h in sorted(byhash):z.write(OBJECTS/h,'objects/'+h)
with zipfile.ZipFile(pack) as z:
 assert z.testzip() is None
 for h in byhash:assert sha(z.read('objects/'+h))==h
parts=[];chunk=4*1024*1024
with pack.open('rb') as f:
 i=0
 while b:=f.read(chunk):
  i+=1;rel=f'archive-parts/all-objects.zip.part-{i:04d}';p=REPO/rel;p.parent.mkdir(exist_ok=True);p.write_bytes(b)
  parts.append({'file':rel,'bytes':len(b),'sha256':sha(b)})
write(REPO/'ARCHIVES.json',{'format':'Concatenate binary parts in listed order to obtain a ZIP containing SHA256-named objects; restore.py maps objects back to classified paths.',
 'zipBytes':pack.stat().st_size,'zipSHA256':digest_file(pack),'parts':parts,'uniqueObjects':len(byhash),'restoredFiles':len(records)})

# Browsable current software and selected R3 documents retain original bytes.
for row in records:
 if row['category']=='active-software/mobile':
  rel=PurePosixPath(row['file']).relative_to('sites/smartvio-mobile')
  p=REPO/'current-software/mobile'/str(rel);p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(OBJECTS/row['sha256'],p)
r3=next(r for r in records if r['file']=='SmartVio-R3-最新方案与工程资料-20261013.zip')
direct=[]
with zipfile.ZipFile(OBJECTS/r3['sha256']) as z:
 for item in z.infolist():
  rel='/'.join(item.filename.split('/')[1:])
  if rel.startswith(('reports/','drawings/','visuals/')) and not rel.startswith(('visuals/qa/','visuals/concept-history/')) and not rel.endswith(('.py','.cjs','.json','.txt')):
   dest=REPO/'current-engineering/r3-view'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(item));direct.append(dest.relative_to(REPO).as_posix())
  if rel in {'review/current-snapshot.json','review/current-feature-gap-review.txt','engineering/project/selected-boards.json','先读我_当前版本.txt'}:
   dest=REPO/'current-engineering/r3-view'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(z.read(item));direct.append(dest.relative_to(REPO).as_posix())
write(REPO/'audit/BROWSABLE-R3-FILES.json',direct)
summary={'capturedFiles':len(records),'uniqueObjects':len(byhash),'sourceBytes':sum(r['bytes'] for r in records),'zipBytes':pack.stat().st_size,'parts':len(parts),'sanitizedArchives':len(changed_archives),'removedMembers':len(removed),'changedSinceInventory':len(drift),'publishRoot':str(OUT)}
write(W/'prepare-result.json',summary);print(json.dumps(summary,ensure_ascii=False),flush=True)
