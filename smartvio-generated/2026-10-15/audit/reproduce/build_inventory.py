from pathlib import Path
import os, json, stat, hashlib

BASE = Path(r'E:/codex/Documents/亚马逊图片')
OUT = Path(r'E:/codex/.codex/visualizations/2026/10/09/01a120af-077d-7860-a708-5b0048a16888/github-vio-upload-20261015/inventory')
SKIP_DIRS = {'.git','node_modules','__pycache__','.pytest_cache','.mypy_cache','.venv','venv','.cache','cadquery_pkgs','.openai','.preview'}
SKIP_EXTS = {'.pyc','.pyo','.sqlite','.sqlite3','.db','.key','.pem','.p12','.pfx','.jks','.keystore'}

def classify(p):
    s=p.relative_to(BASE).as_posix()
    if s.startswith('sites/smartvio-mobile'):
        return 'active-software/mobile', 'Independent current Web software branch; preserve separately from R3 hardware snapshot.'
    if s.startswith('sites/artifacts'):
        return 'active-software/artifacts-history', 'Software evidence, render assets, prior packages and staging snapshots; distinguish from active mobile source.'
    if s == 'SmartVio-R3-最新方案与工程资料-20261013' and p.is_dir():
        return 'history/user-reorganized-r3', 'Live delivery directory has been reorganized into numbered 1/1.1/2/3/4/5/5.1/6/7 folders and archives; preserve as user-reorganized material, not the original 1418-file delivery layout.'
    if s.startswith('SmartVio-R3-最新方案与工程资料-20261013'):
        return 'current/r3-delivery', 'Latest consolidated R3 engineering delivery; production release remains HOLD.'
    if s.startswith('SmartVio-工程整改-20261012-R3'):
        return 'current/r3-working', 'Working R3 sources include historical failed candidates and stale reports; selected-board manifest determines current design.'
    if s.startswith('SmartVio-V12'):
        return 'history/software-v12', 'Separate later UI/redesign branch, not replacement for native R3 hardware.'
    if s.startswith('SmartVio-V11'):
        return 'history/software-v11', 'Historical V11 software branch.'
    if s.startswith('SmartVio-最终效果图'):
        return 'history/concept-renders', 'Historical concept renders, not validated production geometry.'
    if s.startswith('SmartVio-'):
        return 'history/engineering', 'Preserved older engineering or delivery version.'
    return 'current/reproduction-scripts', 'Delivery/reproduction helper source.'

roots=[]
for p in sorted(BASE.iterdir(), key=lambda x:x.name.casefold()):
    if p.name.startswith('SmartVio') or p.name.startswith('.r3-workbook-build') or p.name in {'build_smartvio_r3_delivery.py','create_smartvio_r3_index.py','create_smartvio_r3_overview.py'}:
        roots.append(p)
roots += [BASE/'sites'/'smartvio-mobile',BASE/'sites'/'artifacts']
records=[]; summaries=[]; omitted=[]

def reparse(p):
    s=p.lstat()
    return bool(getattr(s, 'st_file_attributes',0) & stat.FILE_ATTRIBUTE_REPARSE_POINT)

def add_file(p, root_records, scope):
    try:
        if reparse(p):
            omitted.append({'path':str(p),'reason':'reparse-point; not followed'});return
        n=p.name.lower()
        if p.suffix.lower() in SKIP_EXTS or (n=='.env' or (n.startswith('.env.') and n not in {'.env.example','.env.sample','.env.template'})) or n in {'credentials','credentials.json','secrets.json','id_rsa','id_ed25519'}:
            omitted.append({'path':str(p),'reason':'credential or local data/cache filename; content not accessed'});return
        size=p.stat().st_size
        rel=p.relative_to(BASE).as_posix()
        risks=[]
        if size>=100*1024*1024:risks.append('exceeds GitHub 100 MiB ordinary blob threshold')
        elif size>=50*1024*1024:risks.append('large file over 50 MiB; prefer release asset or LFS')
        if p.suffix.lower() in {'.zip','.gz','.tgz','.7z','.tar'}:risks.append('archive requires recursive contents review before publication')
        if p.suffix.lower() in {'.exe','.dll','.pyd','.lib','.a'}:risks.append('runtime/tool/library binary; scope review required')
        if any(w in n for w in ('session','cookie','auth','token','account','login','user')):risks.append('name-only privacy review candidate; may be source/test fixture')
        h=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        r={'relativePath':rel,'absolutePath':str(p),'size':size,'sha256':h.hexdigest(),'scope':scope,'risks':risks}
        root_records.append(r);records.append(r)
    except OSError as e:omitted.append({'path':str(p),'reason':type(e).__name__})

for root in roots:
    category,note=classify(root);items=[];start=len(omitted)
    if root.is_file():add_file(root,items,category)
    else:
        for current, dirs, files in os.walk(root, followlinks=False):
            here=Path(current);keep=[]
            for d in dirs:
                p=here/d
                if d in SKIP_DIRS:
                    omitted.append({'path':str(p),'reason':'dependency/runtime/cache/local deployment state directory'})
                elif reparse(p):
                    omitted.append({'path':str(p),'reason':'reparse-point; not followed'})
                else:keep.append(d)
            dirs[:]=keep
            for f in files:add_file(here/f,items,category)
    summaries.append({'root':str(root),'relativeRoot':root.relative_to(BASE).as_posix(),'recommendedCategory':category,'note':note,'files':len(items),'bytes':sum(i['size'] for i in items),'largestFiles':sorted(items,key=lambda x:x['size'],reverse=True)[:5],'riskFileCount':sum(bool(i['risks']) for i in items),'excludedEntries':len(omitted)-start})

inventory={'schema':'smartvio.github-upload.inventory.v1','inventoryDate':'2026-10-15','sourceBase':str(BASE),'scope':'All SmartVio-named workspace outputs, R3 generation helper scripts, current independent mobile web branch and its artifacts. Not unrelated Amazon images/research or installed runtimes.','scan':'os.walk followlinks=False and Windows reparse-point rejection; no original mutations; no credential contents read.','fileCount':len(records),'bytes':sum(i['size'] for i in records),'roots':summaries,'excluded':omitted,'criticalNotes':['Current R3 delivery claims require selected-board and audit manifests; preserve production HOLD.','Current mobile Web branch is independent and newer than bundled R3 Web copy; classify separately.','Working R3 folders contain failed candidates; do not infer latest from filename timestamp.','Archive contents need recursively screened; filenames alone cannot prove no private data.','Full file list is inventory-files.json; metadata not an authorization or production qualification.']}
unique={i['sha256']:i['size'] for i in records}
inventory['uniqueContentFiles']=len(unique)
inventory['uniqueContentBytes']=sum(unique.values())
inventory['criticalNotes'].append('Original R3 ZIP remains available. Live R3 delivery directory is now user-reorganized, 2847 files, distinct from original 1418-file ZIP.')
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'inventory.json').write_text(json.dumps(inventory,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'inventory-files.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'files':inventory['fileCount'],'bytes':inventory['bytes'],'roots':[{k:s[k] for k in ('relativeRoot','files','bytes','riskFileCount','excludedEntries')} for s in summaries],'excluded':len(omitted)},ensure_ascii=False,indent=2))
