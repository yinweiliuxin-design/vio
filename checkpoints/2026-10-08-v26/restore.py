"""Verify and restore the SmartVio continuation snapshot using Python 3 only."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def local_path(path):
    text = str(path)
    if os.name == 'nt' and not text.startswith('\\\\?\\'):
        return Path('\\\\?\\' + text)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--target', type=Path, help='New or empty directory for restored project files')
    ap.add_argument('--verify-only', action='store_true')
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    archives = load(here / 'ARCHIVES.json')['archives']
    records = load(here / 'FILE-MANIFEST.json')['files']
    expected = {r['path']: r for r in records}
    assert len(expected) == len(records), 'Duplicate manifest path'
    checked = set()
    for archive in archives:
        name = archive['path']
        assert Path(name).name == name and name.endswith('.zip'), 'Invalid archive path'
        data = (here / name).read_bytes()
        assert len(data) == archive['bytes'] and digest(data) == archive['sha256'], 'Archive hash mismatch: ' + name
        with zipfile.ZipFile(here / name) as z:
            assert z.testzip() is None, 'Archive CRC failure: ' + name
            assert len(z.infolist()) == archive['files'], 'Archive count mismatch'
            for info in z.infolist():
                p = PurePosixPath(info.filename)
                assert not p.is_absolute() and '..' not in p.parts and ':' not in info.filename and '\\' not in info.filename, 'Unsafe archive member'
                assert not stat.S_ISLNK(info.external_attr >> 16), 'Symlink not permitted'
                assert info.filename in expected and info.filename not in checked, 'Unexpected or duplicate member'
                r = expected[info.filename]
                body = z.read(info)
                assert len(body) == r['bytes'] and digest(body) == r['sha256'], 'Member hash mismatch: ' + info.filename
                checked.add(info.filename)
    assert checked == set(expected), 'Missing archived file'
    if args.verify_only:
        print(json.dumps({'verifiedFiles': len(checked), 'verifiedArchives': len(archives), 'sha256': 'PASS', 'zipCRC': 'PASS'}))
        return
    if args.target is None:
        ap.error('--target is required unless --verify-only is used')
    target = args.target.resolve()
    assert not target.is_symlink(), 'Target must not be a symlink'
    assert not target.exists() or (target.is_dir() and not any(target.iterdir())), 'Target must be new or empty; existing work is never overwritten'
    local_path(target).mkdir(parents=True, exist_ok=True)
    for archive in archives:
        with zipfile.ZipFile(here / archive['path']) as z:
            for info in z.infolist():
                dest = target.joinpath(*PurePosixPath(info.filename).parts)
                assert dest.resolve().is_relative_to(target), 'Member escapes target'
                local_path(dest.parent).mkdir(parents=True, exist_ok=True)
                with local_path(dest).open('xb') as f:
                    f.write(z.read(info))
    for path, r in expected.items():
        assert digest(local_path(target / path).read_bytes()) == r['sha256'], 'Restored hash mismatch: ' + path
    print(json.dumps({'restoredFiles': len(expected), 'verifiedArchives': len(archives), 'sha256': 'PASS', 'manufactureRelease': False}))


if __name__ == '__main__':
    main()
