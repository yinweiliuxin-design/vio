"""Verify and restore this filtered snapshot using Python standard library only."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, json, zipfile, tempfile, shutil, gzip

def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--target',type=Path)
    p.add_argument('--verify-only',action='store_true')
    a=p.parse_args(); root=Path(__file__).resolve().parent
    package=json.loads((root/'SNAPSHOT.json').read_text(encoding='utf-8'))
    if not a.verify_only and not a.target: p.error('--target or --verify-only is required')
    target=a.target.resolve() if a.target else None
    if target and target.exists() and any(target.iterdir()): raise ValueError('Target must be new or empty; no overwrite allowed')
    work=root/'restore-temp'
    work.mkdir(exist_ok=True)
    archive=work/'assembled.zip'
    h=hashlib.sha256()
    with archive.open('wb') as output:
        for item in package['parts']:
            data=(root/item['path']).read_bytes()
            if sha(data)!=item['sha256']: raise ValueError('Part checksum mismatch: '+item['path'])
            h.update(data); output.write(data)
    if h.hexdigest()!=package['archiveSha256']: raise ValueError('Archive checksum mismatch')
    manifest_bytes=gzip.decompress((root/'FILE-MANIFEST.json.gz').read_bytes())
    if sha(manifest_bytes)!=package['manifestSha256']: raise ValueError('Manifest checksum mismatch')
    manifest=json.loads(manifest_bytes)
    with zipfile.ZipFile(archive) as z:
        if z.testzip(): raise ValueError('ZIP CRC mismatch')
        for digest in manifest['objects']:
            if sha(z.read('objects/'+digest))!=digest: raise ValueError('Object checksum mismatch')
        if target:
            target.mkdir(parents=True,exist_ok=True)
            for item in manifest['files']:
                rel=PurePosixPath(item['path'])
                if rel.is_absolute() or '..' in rel.parts or ':' in item['path']: raise ValueError('Unsafe restored path')
                dest=target.joinpath(*rel.parts)
                if not dest.resolve().is_relative_to(target): raise ValueError('Path escape')
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(z.read('objects/'+item['sha256']))
    print(json.dumps({'verifiedFiles':len(manifest['files']),'verifiedUniqueObjects':len(manifest['objects']),'restored':bool(target)}))
if __name__=='__main__': main()
