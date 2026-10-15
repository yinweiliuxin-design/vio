from pathlib import Path
import json
O=Path(r'E:/codex/.codex/visualizations/2026/10/09/01a120af-077d-7860-a708-5b0048a16888/github-vio-upload-20261015/inventory')
allrows=json.loads((O/'inventory-files.json').read_text(encoding='utf-8'))
inv=json.loads((O/'inventory.json').read_text(encoding='utf-8'))
included=[];excluded=[]
for r in allrows:
    if '/firmware/eb/' in r['relativePath'] or '/firmware/build/' in r['relativePath']:
        excluded.append({'path':r['absolutePath'],'relativePath':r['relativePath'],'size':r['size'],'reason':'ESP-IDF or host-test rebuild cache; deliverable firmware/artifacts and source retained'})
        continue
    included.append({'absolutePath':r['absolutePath'],'relativePath':r['relativePath'],'sha256':r['sha256'],'size':r['size'],'category':r['scope'].replace('history/user-reorganized-r3','history/reorganized-r3-copy'),'risks':r['risks']})
unique={r['sha256']:r['size'] for r in included}
inv['fileCount']=len(included);inv['bytes']=sum(r['size'] for r in included)
inv['uniqueContentFiles']=len(unique);inv['uniqueContentBytes']=sum(unique.values())
inv['excluded']+=excluded
inv['scanNote']='Files were observed at scan time; active mobile project changed by two files during inventory, so packing must revalidate source hashes and record the snapshot rather than assume source quiescence.'
for root in inv['roots']:
    rr=root['relativeRoot'];chosen=[r for r in included if r['relativePath']==rr or r['relativePath'].startswith(rr+'/')]
    root['files']=len(chosen);root['bytes']=sum(r['size'] for r in chosen)
    root['largestFiles']=sorted(chosen,key=lambda r:r['size'],reverse=True)[:5]
    root['recommendedCategory']=root['recommendedCategory'].replace('history/user-reorganized-r3','history/reorganized-r3-copy')
(O/'included-files.json').write_text(json.dumps(included,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'inventory.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2),encoding='utf-8')
(O/'excluded-build-cache-files.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:inv[k] for k in ['fileCount','bytes','uniqueContentFiles','uniqueContentBytes','scanNote']},ensure_ascii=False,indent=2))
