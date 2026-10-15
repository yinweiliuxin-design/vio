"""Read-only sources, filtered content-addressed project snapshot."""
from pathlib import Path, PurePosixPath
from collections import Counter
import json, os, re, hashlib, zipfile, tarfile, io
OUT=Path(__file__).resolve().parent
PROJECT=Path('<LOCAL_ENGINEERING>')
APPS=Path('<LOCAL_PROJECTS>')
DENY_DIRS=set('.git .aws .ssh .codex .agents .openai .preview .state node_modules __pycache__ .venv venv .cache esp-tools esp-idf-v5.4.3 toolchain toolchains java25 parser-tools router-data restored-project filtered-project repository-files downloads uploads sessions eb cmakefiles logs tmp tools sdk vendor build'.split())
DENY_NAME=re.compile(r'(?i)(^\.env($|\.)|^\.dev\.vars|credentials|cookies|private[-_]?key|id_rsa|id_ed25519|\.(pem|p12|pfx|key|sqlite|sqlite3|db|log|pyc|exe|dll|msi|lck|bak|kicad_prl)$|sdkconfig\.old$|test-record\.actual)')
TEXT_EXT=set('.py .ps1 .cmd .bat .c .h .cpp .hpp .s .ld .cmake .cjs .mjs .js .ts .tsx .jsx .html .css .json .xml .yaml .yml .toml .ini .csv .tsv .txt .md .svg .dxf .scad .step .stp .kicad_pcb .kicad_sch .kicad_pro .kicad_dru .kicad_mod .kicad_sym .dsn .ses .sql .sh .map .gbr .gbrjob .drl .g1 .g2 .g3 .g4 .gtl .gbl .gto .gbo .gtp .gbp .gts .gbs .gm1 .hex .net .asc .cir .spice .patch .pos .rpt .cfg .wrl'.split())
BINARY_EXT=set('.png .jpg .jpeg .webp .gif .bmp .ico .pdf .docx .xlsx .pptx .stl .glb .gltf .bin .elf .wav .mp3 .ogg .m4a .mp4 .webm .woff .woff2 .ttf .otf'.split())
EXACT={'CMakeLists.txt','Makefile','LICENSE','NOTICE','COPYING','fp-lib-table','sym-lib-table','sdkconfig','sdkconfig.defaults','flash_args','.gitignore','.gitattributes','.npmrc'}
PATTERNS={k:re.compile(v) for k,v in {
 'private-key':r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
 'github-token':r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b',
 'cloud-key':r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
 'api-key':r'\b(?:sk-(?:proj-)?[A-Za-z0-9_-]{24,}|AIza[A-Za-z0-9_-]{30,})\b',
 'jwt':r'\beyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
 'url-credential':r'https?://[^\s/<>:"\']+:[^\s/<>"\']+@',
}.items()}
LITERAL=re.compile(r'''(?ix)(?:password|api[_-]?key|access[_-]?token|client[_-]?secret|webhook[_-]?secret|account[_-]?id)\s*["']?\s*[:=]\s*["']([^"'\n]{6,})["']''')
MAIL=re.compile(r'(?i)\b[A-Z0-9._%+-]{1,64}@(?:gmail|qq|163|126|outlook|hotmail|yahoo)\.[A-Z.]{2,16}\b')
records=[]; excluded=[]; flags=[]; roots=[]; objects={}; cache={}
def digest(data): return hashlib.sha256(data).hexdigest()
def dump(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def scrub(s):
    s=re.sub(r'(?i)[A-Z]:[/\\]+Users[/\\]+[^/\\\s"<>]+','<LOCAL_USER_HOME>',s)
    s=re.sub(r'(?i)Tencent\s+Files[/\\]+\d+','PRIVATE_IMAGE_SOURCE',s)
    s=MAIL.sub('[REDACTED_EMAIL]',s)
    for v in ('[PRIVATE_ACCOUNT_INFORMATION]','[PRIVATE_ACCOUNT_INFORMATION]','[PRIVATE_ACCOUNT_INFORMATION]','[PRIVATE_ACCOUNT_INFORMATION]'): s=s.replace(v,'[PRIVATE_ACCOUNT_INFORMATION]')
    return s
def scrub_json(v):
    if isinstance(v,str): return scrub(v)
    if isinstance(v,list): return [scrub_json(x) for x in v]
    if isinstance(v,dict): return {scrub(k):scrub_json(x) for k,x in v.items()}
    return v
def allowed(name):
    parts=PurePosixPath(name.replace('\\','/')).parts
    if '..' in parts or any(p.lower() in DENY_DIRS or p.endswith('-backups') for p in parts): return 'cache-toolchain-runtime'
    if DENY_NAME.search(parts[-1]): return 'sensitive-or-runtime-name'
    if parts[-1].lower() in {'data.json','users.json','orders.json','admin-credentials.json','secrets.json','hosting.json'}: return 'runtime-account-data'
    return None
def add(name,data):
    reason=allowed(name)
    if reason: excluded.append({'path':name,'reason':reason}); return
    ext=PurePosixPath(name).suffix.lower()
    if ext=='.zip':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                for item in z.infolist():
                    if item.is_dir(): continue
                    member=item.filename.replace('\\','/')
                    if PurePosixPath(member).is_absolute() or '..' in PurePosixPath(member).parts: raise ValueError('unsafe path')
                    if item.file_size>200_000_000: excluded.append({'path':name+'!/'+member,'reason':'oversized-member'}); continue
                    add(name+'__contents/'+member,z.read(item))
        except Exception as e: excluded.append({'path':name,'reason':'unreadable-archive:'+type(e).__name__})
        return
    if name.endswith(('.tar.gz','.tgz')):
        try:
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as tar:
                for item in tar.getmembers():
                    if not item.isfile(): continue
                    member=item.name.replace('\\','/')
                    if PurePosixPath(member).is_absolute() or '..' in PurePosixPath(member).parts: raise ValueError('unsafe path')
                    add(name+'__contents/'+member,tar.extractfile(item).read())
        except Exception as e: excluded.append({'path':name,'reason':'unreadable-archive:'+type(e).__name__})
        return
    if ext not in TEXT_EXT|BINARY_EXT and PurePosixPath(name).name not in EXACT: excluded.append({'path':name,'reason':'unapproved-extension'}); return
    original_hash=digest(data); transformed=False
    cache_key=(original_hash,ext,PurePosixPath(name).name=='seed.json')
    if cache_key in cache:
        old,cached_flags=cache[cache_key]
        records.append(dict(old,path=name))
        flags.extend(dict(f,path=name) for f in cached_flags)
        return
    flag_start=len(flags)
    if ext in TEXT_EXT or PurePosixPath(name).name in EXACT:
        try: original_text=data.decode('utf-8-sig')
        except UnicodeDecodeError:
            try: original_text=data.decode('gb18030')
            except UnicodeDecodeError: excluded.append({'path':name,'reason':'unreadable-text'}); return
        s=original_text
        if ext=='.json':
            try:
                original=json.loads(s); clean=scrub_json(original)
                if PurePosixPath(name).name=='seed.json' and isinstance(clean,dict):
                    for key in ('users','orders','messages','notifications','practice','media','reports','tickets','deletions','audit'):
                        if key in clean: clean[key]=[]
                    if 'adminCredentials' in clean: clean['adminCredentials']=None
                if clean!=original: s=json.dumps(clean,ensure_ascii=False,indent=2)+'\n'
            except json.JSONDecodeError: s=scrub(s)
        else: s=scrub(s)
        for rule,rx in PATTERNS.items():
            for m in rx.finditer(s): flags.append({'path':name,'rule':rule,'line':s.count('\n',0,m.start())+1})
        for m in LITERAL.finditer(s):
            val=m.group(1)
            if val in {'current-password','new-password','Password confirmation required','Sign in required','password','Password','not-a-real-password','REPLACE_ME','CHANGE_ME'}: continue
            flags.append({'path':name,'rule':'literal-review','line':s.count('\n',0,m.start())+1,'valueSha256':digest(val.encode())})
        if s!=original_text: data=s.encode('utf-8'); transformed=True
    sha=digest(data)
    if sha not in objects: (OUT/'objects'/sha).write_bytes(data); objects[sha]=len(data)
    record={'path':name,'sha256':sha,'bytes':len(data),'sourceSha256':original_hash,'privacyFiltered':transformed}
    records.append(record)
    cache[cache_key]=(record,flags[flag_start:])
    if len(objects)%500==0: print('objects='+str(len(objects))+' path='+name[:160],flush=True)
def walk(root,prefix):
    if not root.exists(): return
    roots.append({'label':prefix,'source':str(root)})
    print('START '+prefix,flush=True)
    if root.is_file(): add(prefix+'/'+root.name,root.read_bytes()); return
    for folder,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=[d for d in dirs if d.lower() not in DENY_DIRS and not d.endswith('-backups') and not (Path(folder)/d).is_symlink()]
        for file in sorted(files):
            p=Path(folder)/file
            if p.is_symlink(): continue
            name=prefix+'/'+p.relative_to(root).as_posix(); reason=allowed(name)
            if reason: excluded.append({'path':name,'reason':reason}); continue
            if p.stat().st_size>300_000_000: excluded.append({'path':name,'reason':'oversized-file-review'}); continue
            add(name,p.read_bytes())
def main():
    (OUT/'objects').mkdir(parents=True,exist_ok=True)
    for sub in ('outputs','work','V26'): walk(PROJECT/sub,'engineering-history/'+sub)
    walk(Path('E:/codex/Documents/Codex/2026-10-01/99/work'),'engineering-post-migration/work')
    for p in sorted(APPS.iterdir()):
        if p.name.startswith('SmartVio') or 'smartvio_r3' in p.name: walk(p,'deliveries/'+p.name if p.is_dir() else 'deliveries')
    walk(APPS/'sites/smartvio-mobile','client-current')
    walk(APPS/'sites/artifacts','client-reports-history')
    walk(Path('E:/codex/.codex/generated_images/01a0f78d-43b1-7f10-b141-bd0e3c8c2ee6'),'generated-images')
    walk(Path('E:/codex/.codex/visualizations/2026/10/01/01a0f78d-43b1-7f10-b141-bd0e3c8c2ee6'),'visualizations')
    walk(Path('E:/codex/SmartVio-loop-fa438b40.webm'),'media')
    dump(OUT/'inventory.local.json',{'roots':roots,'files':records,'objects':objects,'exclusions':excluded,'flags':flags})
    print(json.dumps({'files':len(records),'uniqueObjects':len(objects),'uniqueBytes':sum(objects.values()),'exclusions':len(excluded),'flags':len(flags),'byRoot':dict(Counter(x['path'].split('/')[0] for x in records))},ensure_ascii=False))
if __name__=='__main__': main()
