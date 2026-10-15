"""Sanitize staged objects and create a restorable, deduplicated snapshot."""
from pathlib import Path, PurePosixPath
import json, hashlib, gzip, zipfile, io, re, shutil
from collections import Counter
import collect

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/'publish'
PRIVATE=('[PRIVATE_ACCOUNT_INFORMATION]','[PRIVATE_ACCOUNT_INFORMATION]','[PRIVATE_ACCOUNT_INFORMATION]')
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def jsonbytes(v): return (json.dumps(v,ensure_ascii=False,indent=2)+'\n').encode()
def main():
    PUBLIC.mkdir(exist_ok=True)
    inv=json.loads((ROOT/'inventory.local.json').read_text(encoding='utf-8'))
    result=[]; objects={}; excluded=list(inv['exclusions']); changes=[]; checked={}
    quarantine=[]; runtime=[]
    previous=ROOT/'filtered-manifest.local.json'
    if previous.exists() and (PUBLIC/'PRIVACY-REPORT.json.gz').exists():
        old_manifest=json.loads(previous.read_text(encoding='utf-8'))
        old_by_path={r['path']:r for r in old_manifest['files']}
        old_report=json.loads(gzip.decompress((PUBLIC/'PRIVACY-REPORT.json.gz').read_bytes()))
        old_exclusions={r['path']:r['reason'] for r in old_report['exclusions']}
        for r in inv['files']:
            old=old_by_path.get(r['path'])
            if old and old['sourceSha256']==r['sourceSha256']:
                checked[r['sha256']]=(old['sha256'],old['bytes'],None)
            elif old_exclusions.get(r['path'],'').startswith(('document-','binary-secret')):
                checked[r['sha256']]=(r['sha256'],r['bytes'],old_exclusions[r['path']])
    for record in inv['files']:
        name=record['path']; ext=PurePosixPath(name).suffix.lower()
        if any(x.lower() in {'pydeps','site-packages','venv','vendor-source'} for x in PurePosixPath(name).parts):
            excluded.append({'path':name,'reason':'reinstallable-third-party-dependency'}); continue
        old=record['sha256']
        if old not in checked:
            if len(checked)%200==0: print('SCANNED '+str(len(checked))+' '+name[:150],flush=True)
            data=(ROOT/'objects'/old).read_bytes(); binary=ext in collect.BINARY_EXT|{'.mid','.midi'}
            reason=None
            if not binary:
                try: text=data.decode('utf-8-sig')
                except UnicodeDecodeError: text=data.decode('gb18030')
                for rx in collect.PATTERNS.values(): text=rx.sub('[REDACTED_SECRET]',text)
                def replace_literal(m):
                    val=m.group(1)
                    if val in {'current-password','new-password','Password confirmation required','Sign in required','password','Password','not-a-real-password','REPLACE_ME','CHANGE_ME'}: return m.group(0)
                    start=m.start(1)-m.start(); end=m.end(1)-m.start()
                    return m.group(0)[:start]+'[CONFIGURE_AT_RUNTIME]'+m.group(0)[end:]
                text=collect.LITERAL.sub(replace_literal,text)
                clean=text.encode('utf-8')
                if clean!=data:
                    data=clean
            elif ext in {'.pdf','.docx','.xlsx','.pptx'}:
                try:
                    if ext=='.pdf':
                        from pypdf import PdfReader
                        reader=PdfReader(io.BytesIO(data))
                        text='\n'.join(page.extract_text() or '' for page in reader.pages)
                    else:
                        with zipfile.ZipFile(io.BytesIO(data)) as z:
                            text='\n'.join(z.read(n).decode('utf-8','replace') for n in z.namelist() if n.endswith('.xml'))
                    if collect.MAIL.search(text) or any(v in text for v in PRIVATE) or any(rx.search(text) for rx in collect.PATTERNS.values()):
                        reason='document-contains-private-information'
                except Exception as e:
                    reason='document-scan-incomplete:'+type(e).__name__
            else:
                text=data.decode('utf-8','ignore')
                if any(rx.search(text) for rx in collect.PATTERNS.values()): reason='binary-secret-pattern'
            digest=sha(data)
            if not reason:
                (ROOT/'objects'/digest).write_bytes(data)
            checked[old]=(digest,len(data),reason)
        digest,size,reason=checked[old]
        if reason:
            excluded.append({'path':name,'reason':reason}); quarantine.append(name); continue
        rec=dict(record,sha256=digest,bytes=size,privacyFiltered=record['privacyFiltered'] or digest!=old)
        if digest!=old: changes.append({'path':name,'reason':'redact-embedded-credential-or-normalize-text-encoding'})
        objects[digest]=size; result.append(rec)
    manifest={'schemaVersion':1,'files':result,'objects':objects,'privacyFiltered':True}
    manifest_bytes=jsonbytes(manifest)
    (PUBLIC/'FILE-MANIFEST.json.gz').write_bytes(gzip.compress(manifest_bytes,mtime=0))
    (ROOT/'filtered-manifest.local.json').write_bytes(manifest_bytes)
    print(json.dumps({'stage':'sanitized','files':len(result),'uniqueObjects':len(objects),'bytes':sum(objects.values()),'withheldDocuments':len(quarantine)},ensure_ascii=False),flush=True)
    archive_path=ROOT/'snapshot.zip'
    existing=set()
    if archive_path.exists():
        with zipfile.ZipFile(archive_path) as z: existing=set(z.namelist())
        if not existing <= {'objects/'+d for d in objects}: raise ValueError('Archive contains obsolete objects; do not reuse')
    with zipfile.ZipFile(archive_path,'a' if existing else 'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for digest in sorted(objects):
            if 'objects/'+digest not in existing: z.write(ROOT/'objects'/digest,'objects/'+digest)
    data=(ROOT/'snapshot.zip').read_bytes(); parts=[]
    (PUBLIC/'parts').mkdir(exist_ok=True)
    for i,start in enumerate(range(0,len(data),8*1024*1024),1):
        part=data[start:start+8*1024*1024]; path='parts/snapshot.zip.part-'+str(i).zfill(3)
        (PUBLIC/path).write_bytes(part)
        parts.append({'path':path,'bytes':len(part),'sha256':sha(part),'gitBlobSha':blob(part)})
    snapshot={'schemaVersion':1,'date':'2026-10-15','repository':'yinweiliuxin-design/vio','scope':'Generated SmartVio hardware, software, data, drawings, images and version history; security-filtered snapshot',
      'sourceFiles':len(result),'uniqueObjects':len(objects),'archiveBytes':len(data),'archiveSha256':sha(data),'manifestSha256':sha(manifest_bytes),'parts':parts,'manufacturingReleased':False,'sourceOriginalsModified':False,'excludedFiles':len(excluded),'withheldDocumentOccurrences':len(quarantine),
      'notes':['Paths ending __contents represent safely inspected archive contents, not byte-identical original ZIP containers.','Identical files across versions are stored once; restore recreates every indexed path.','Historical SHA reports describe their original files; use this snapshot manifest for filtered file integrity.','Credentials, live user databases, unrelated material and reinstallable dependency caches are not included.','Firmware binaries present in output deliveries are research artifacts, not authorization to charge a battery or manufacture.']}
    (PUBLIC/'SNAPSHOT.json').write_bytes(jsonbytes(snapshot))
    privacy={'schemaVersion':1,'checks':['File/path filtering','Recursive archive inspection','Text secret scanning and redaction','PDF/Office text scan','Binary key-pattern check'],
      'exclusions':excluded,'transformedFiles':changes,'sourceOriginalsModified':False,'allSourceRoots': [r['label'] for r in inv['roots']], 'limitations':['No OCR of image pixels; project-generated images only, no unrelated raw messenger photo folders.','Static checks do not certify hardware behavior.']}
    (PUBLIC/'PRIVACY-REPORT.json.gz').write_bytes(gzip.compress(jsonbytes(privacy),mtime=0))
    shutil.copyfile(ROOT/'restore.py',PUBLIC/'RESTORE.py')
    groups=Counter(r['path'].split('/')[0] for r in result)
    readme='''# SmartVio 项目全量安全归档 / 2026-10-15

本目录保存已定位的项目代码、数据、原生EDA、PCB、图纸、BOM、固件输出、效果图及历史版本。它是研发备份，不是生产放行包。

## 先看这些

- `SNAPSHOT.json`：范围、分片及 SHA256。
- `FILE-MANIFEST.json.gz`：每个恢复路径、原文件与过滤后文件的 SHA256。
- `PRIVACY-REPORT.json.gz`：排除与脱敏清单。
- `preview/`：可直接查看的近期效果图和资料。
- `RESTORE.py`：只使用 Python 标准库的校验恢复工具。

## 恢复

下载或克隆仓库后，在本目录执行：

```text
python RESTORE.py --verify-only
python RESTORE.py --target E:/codex/SmartVio-restored-20261015
```

目标目录必须全新或为空；不会覆盖现有工程。检查每个分片、完整归档、对象哈希和 ZIP CRC 后才开始恢复。文件较多，Windows 建议开启长路径支持。

恢复后的目录：

- `deliveries/`：R3 当前硬件资料及 R1/R2、首样准备包等历次交付。
- `client-current/`：本次读取的客户端、后台、测试、数据库迁移和资源文件。
- `client-reports-history/`：软件历次报告、界面截图和可用历史源文件。
- `engineering-history/`：V27 及更早原理图、PCB、脚本、设计资料。
- `generated-images/`：本研发对话已生成的效果图。
- `visualizations/`、`media/`：相关可视化与媒体。

## 版本说明

硬件存在后续 R3 资料，不能把旧 V27 状态当成最新整机状态；各原报告保留其历史版本含义。最新软件源码也与早期概念客户端不同。本次只备份，不修改功能、不复跑硬件验证，也不将 HOLD 改成 PASS。

原仓库 `CLOUD_HANDOFF.md` 和已存在的检查点保留不变。请以本目录了解此次备份范围；旧交接文档中的日期和工程状态仅代表历史。

## 安全与完整性

旧 ZIP/TAR 的内容先检查，再以 `__contents` 目录恢复，避免把密码或运行数据库藏在压缩包里上传。同一内容只存储一次，但清单保留所有版本路径。
存在敏感信息或无法检查的文件会列入排除清单，保留在本地原位置。脱敏源码中的凭据需要在目标环境自行配置；不会上传真实用户数据库或无关电商资料。
依赖工具链及第三方安装缓存不打包，依赖清单、项目脚本、锁文件按筛选结果保留。所有原件保持不变。
'''
    readme+='\n恢复文件数：'+str(len(result))+'；唯一内容数：'+str(len(objects))+'。\n'
    for k,v in groups.items(): readme+='- '+k+': '+str(v)+'\n'
    (PUBLIC/'README.md').write_text(readme,encoding='utf-8')
    print(json.dumps({k:v for k,v in snapshot.items() if k!='parts'},ensure_ascii=True),flush=True)
if __name__=='__main__': main()
