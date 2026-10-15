"""Append only approved snapshot content to the separate sparse Git clone."""
from pathlib import Path
import json,hashlib,shutil
import collect
BASE=Path(__file__).resolve().parent
REPO=BASE/'repo'
REL='snapshots/2026-10-15-all-generated'
DEST=REPO/REL
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def main():
    if DEST.exists(): raise ValueError('Refusing to overwrite staged snapshot')
    DEST.mkdir(parents=True)
    m=json.loads((BASE/'filtered-manifest.local.json').read_text(encoding='utf-8'))
    s=json.loads((BASE/'publish/SNAPSHOT.json').read_text(encoding='utf-8'))
    names=['SNAPSHOT.json','FILE-MANIFEST.json.gz','PRIVACY-REPORT.json.gz','RESTORE.py','README.md']+[p['path'] for p in s['parts']]
    for name in names:
        dst=DEST/name; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(BASE/'publish'/name,dst)
    selections=[]
    def copy_record(rec,name):
        data=(BASE/'objects'/rec['sha256']).read_bytes()
        if sha(data)!=rec['sha256']: raise ValueError('Staged object corrupted')
        dst=DEST/name;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data)
        selections.append({'repoPath':REL+'/'+name,'sourcePath':rec['path'],'sha256':rec['sha256']})
    for r in m['files']:
        p=r['path']
        if p.startswith('client-current/'):
            copy_record(r,'current/client/'+p.removeprefix('client-current/'))
        prefix='deliveries/SmartVio-工程整改-20261012-R3/project/'
        if p.startswith(prefix): copy_record(r,'current/hardware-R3/'+p.removeprefix(prefix))
        if p=='deliveries/SmartVio-工程整改-20261012-R3/r3-work-state.json':copy_record(r,'current/hardware-R3/r3-work-state.json')
        if p=='deliveries/SmartVio-最终效果图-20261009/SmartVio-整机外观效果图-20261009.png':copy_record(r,'preview/violin-render-20261009.png')
        drawing='deliveries/SmartVio-R3-最新方案与工程资料-20261013/1.1/drawings/'
        if p==drawing+'M-R3-机械图与装配效果图.pdf':copy_record(r,'preview/R3-mechanical-review.pdf')
        if p==drawing+'E-R3-24页当前原理图.pdf':copy_record(r,'preview/R3-schematic-review.pdf')
        if p=='client-current/mobile-home-preview.jpg':copy_record(r,'preview/client-home.jpg')
    (DEST/'DIRECT-FILES.json').write_text(json.dumps(selections,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (DEST/'.gitattributes').write_text('* -text\n',encoding='ascii')
    readme=DEST/'README.md'
    with readme.open('a',encoding='utf-8') as f:
        f.write('\n## 可直接浏览\n\n- [当前客户端源码](current/client/)\n- [R3 原生EDA、PCB和元件资料](current/hardware-R3/)\n- [机械图与装配效果](preview/R3-mechanical-review.pdf)\n- [24页当前原理图](preview/R3-schematic-review.pdf)\n\n![已生成的整机效果图（外观参考，非生产放行）](preview/violin-render-20261009.png)\n\n当前客户端 Git 源提交：`2c7f0a7ce5ffd97372092a1cc4ccaafc36439fbd`。直接浏览的副本与归档内相同，若脱敏过，以清单记录为准。历史 V26 已有检查点保留在仓库 `checkpoints/`，不重写旧交接文档。\n')
    for name in ('collect.py','supplement.py','package_snapshot.py','restore.py','stage_repository.py'):
        # Reproduction utilities contain no account credentials. Remove local source roots.
        text=collect.scrub((BASE/name).read_text(encoding='utf-8'))
        text=text.replace('<LOCAL_PROJECTS>','<LOCAL_PROJECTS>').replace('<LOCAL_ENGINEERING>','<LOCAL_ENGINEERING>')
        dst=DEST/'backup-tools'/name;dst.parent.mkdir(exist_ok=True);dst.write_text(text,encoding='utf-8')
    index=REPO/'SMARTVIO_ARCHIVE_20261015.md'
    if index.exists():raise ValueError('Existing index must not be overwritten')
    index.write_text('# SmartVio 项目备份入口\n\n[打开 2026-10-15 完整安全归档](snapshots/2026-10-15-all-generated/README.md)\n\n包含当前客户端、R3硬件工程、历次设计、图纸、数据和效果图。历史检查点与 CLOUD_HANDOFF.md 原样保留。所有硬件资料仍为研发阶段，备份不等于投产批准。\n',encoding='utf-8')
    files=[]
    for p in sorted(DEST.rglob('*')):
        if p.is_file():
            data=p.read_bytes();files.append({'path':p.relative_to(REPO).as_posix(),'bytes':len(data),'sha256':sha(data),'gitBlobSha':blob(data)})
    b=index.read_bytes();files.append({'path':index.name,'bytes':len(b),'sha256':sha(b),'gitBlobSha':blob(b)})
    (BASE/'UPLOAD-MANIFEST.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'repoFiles':len(files),'bytes':sum(f['bytes'] for f in files),'directFiles':len(selections)}))
if __name__=='__main__':main()
