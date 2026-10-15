"""Verify and restore classified SmartVio project records. No networking or code execution."""
from pathlib import Path,PurePosixPath
import argparse,json,hashlib,zipfile,tempfile,shutil,os
HERE=Path(__file__).resolve().parent
def sha_file(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def safe_relative(s):
 p=PurePosixPath(s)
 if p.is_absolute() or '..' in p.parts or '\\' in s or ':' in s:raise ValueError('Unsafe archive path')
 return Path(*p.parts)
def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--verify-only',action='store_true')
 ap.add_argument('--target',type=Path,default=Path('E:/codex/SmartVio-GitHub恢复-20261015'))
 ap.add_argument('--temp',type=Path,default=Path('E:/codex/Temp'))
 args=ap.parse_args()
 manifest=json.loads((HERE/'FILE-MANIFEST.json').read_text('utf8'))
 archive=json.loads((HERE/'ARCHIVES.json').read_text('utf8'))
 target=args.target.resolve();work=args.temp.resolve();work.mkdir(parents=True,exist_ok=True)
 if not args.verify_only and target.exists() and any(target.iterdir()):raise RuntimeError('Target is not empty; choose a new directory. Existing files are never overwritten.')
 objects={r['sha256']:r['bytes'] for r in manifest['files']}
 for r in manifest['files']:safe_relative(r['restorePath'])
 with tempfile.TemporaryDirectory(prefix='smartvio-restore-',dir=work) as tmp:
  tmp=Path(tmp);packed=tmp/'objects.zip'
  with packed.open('wb') as out:
   for part in archive['parts']:
    path=HERE/safe_relative(part['file'])
    if path.stat().st_size!=part['bytes'] or sha_file(path)!=part['sha256']:raise RuntimeError('Part damaged or missing: '+part['file'])
    with path.open('rb') as f:shutil.copyfileobj(f,out)
  if sha_file(packed)!=archive['zipSHA256']:raise RuntimeError('ZIP SHA mismatch')
  with zipfile.ZipFile(packed) as z:
   if set(z.namelist())!={'objects/'+h for h in objects}:raise RuntimeError('Object list mismatch')
   for h,size in objects.items():
    data=z.read('objects/'+h)
    if len(data)!=size or hashlib.sha256(data).hexdigest()!=h:raise RuntimeError('Object damaged: '+h)
    if not args.verify_only:(tmp/h).write_bytes(data)
  if not args.verify_only:
   target.mkdir(parents=True,exist_ok=True)
   for r in manifest['files']:
    dest=target/safe_relative(r['restorePath'])
    if not dest.resolve().is_relative_to(target):raise RuntimeError('Path escaped target')
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(tmp/r['sha256'],dest)
    if sha_file(dest)!=r['sha256']:raise RuntimeError('Restored hash mismatch')
   (target/'恢复说明.txt').write_text('本目录按current、active-software、history分类。源路径与哈希见仓库FILE-MANIFEST.json。历史候选/渲染/模拟不等于当前已验证硬件。制造放行仍为HOLD。\n','utf8')
 result={'status':'PASS','objects':len(objects),'files':len(manifest['files']),'verifiedOnly':args.verify_only,'target':None if args.verify_only else str(target)}
 print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
