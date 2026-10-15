"""Include project-specific web, music and legacy EDA formats."""
import collect as c
from pathlib import Path, PurePosixPath
import json,zipfile,io

path=c.OUT/'inventory.local.json'
d=json.loads(path.read_text(encoding='utf-8'))
c.records=d['files']; c.flags=d['flags']; c.roots=d['roots']; c.objects=d['objects']
extra={'.webmanifest','.mid','.midi','.ly','.d356','.sch','.lib','.policy','.template','.properties'}
c.TEXT_EXT.update(extra-{'.mid','.midi'}); c.BINARY_EXT.update({'.mid','.midi'})
c.EXACT.add('svg')
roots=sorted(d['roots'],key=lambda x:len(x['label']),reverse=True)
def source_bytes(name):
    for r in roots:
        prefix=r['label']+'/'
        if not name.startswith(prefix): continue
        rel=name[len(prefix):]; source=Path(r['source'])
        if source.is_file():
            if not rel.startswith(source.name): continue
            rel=rel[len(source.name):]
            data=source.read_bytes()
            if not rel: return data
            if not rel.startswith('__contents/'): continue
            parts=rel[len('__contents/'):].split('__contents/')
        else:
            parts=rel.split('__contents/')
            if not (source/parts[0]).is_file(): continue
            data=(source/parts.pop(0)).read_bytes()
        for part in parts:
            with zipfile.ZipFile(io.BytesIO(data)) as z: data=z.read(part)
        return data
    raise FileNotFoundError(name)
kept=[]; added=0
for e in d['exclusions']:
    name=e['path']; p=PurePosixPath(name)
    if e['reason']=='unapproved-extension' and (p.suffix.lower() in extra or p.name=='svg') and not any(x.lower() in {'pydeps','site-packages','vendor-source'} for x in p.parts):
        before=len(c.records)
        try: c.add(name,source_bytes(name))
        except Exception: kept.append(e); continue
        added+=len(c.records)-before
    else: kept.append(e)
d.update(files=c.records,objects=c.objects,flags=c.flags,exclusions=kept+c.excluded)
c.dump(path,d)
print(json.dumps({'addedFiles':added,'files':len(c.records),'uniqueObjects':len(c.objects)}))
