import json, re, io, zipfile, tarfile, hashlib, sys, time
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent
INVENTORY = ROOT / 'inventory/inventory-files.json'
MAX_MEMBER = 256 * 1024 * 1024
MAX_DEPTH = 10
patterns = [
 ('github_token', re.compile(rb'(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36,255}(?![A-Za-z0-9])')),
 ('github_fine_grained_token', re.compile(rb'github_pat_[A-Za-z0-9_]{60,255}')),
 ('aws_access_key_id', re.compile(rb'(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])')),
 ('private_key', re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----[\s\S]{80,16384}?-----END (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----')),
 ('openai_api_key', re.compile(rb'(?<![A-Za-z0-9_])sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{48,250}(?![A-Za-z0-9_])')),
 ('literal_authorization_bearer', re.compile(rb'(?i)(?:Authorization[\x20\x22\x27]*[:=][\x20\x22\x27]*Bearer\s+)([A-Za-z0-9_./+=-]{28,1000})')),
 ('literal_secret_assignment_jwt', re.compile(rb'(?i)(?:access_token|refresh_token|api_token|auth_token|authorization|secret)[\x20\x22\x27]*[:=][\x20\x22\x27]*(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,})')),
]

def path_findings(name):
    norm = name.replace('\\', '/')
    parts = [p.lower() for p in PurePosixPath(norm).parts]
    base = parts[-1] if parts else ''
    result=[]
    if any(p in ('.openai', '.state', '.git', '.aws', '.ssh', 'browser-profile', 'browser_profile') for p in parts):
        result.append('local_account_browser_or_repository_state')
    if base == '.env' or (base.startswith('.env.') and base not in ('.env.example', '.env.sample', '.env.template', '.env.defaults', '.env.test')):
        result.append('environment_configuration_file')
    if base.endswith(('.sqlite', '.sqlite3', '.db', '.db-wal', '.sqlite-wal')):
        result.append('database_file_review')
    if re.fullmatch(r'(?:access[-_]?tokens?|refresh[-_]?tokens?|tokens?|cookies?|credentials?|secrets?|storage[-_]?state|auth[-_]?state)(?:\.[a-z0-9_-]+)?', base):
        result.append('credential_or_browser_state_filename')
    if norm.startswith(('/', '\\')) or '..' in parts or re.match(r'^[a-zA-Z]:', norm):
        result.append('unsafe_archive_member_path')
    return result

def is_dummy(match):
    s=match.decode('ascii',errors='ignore')
    low=s.lower()
    if any(x in low for x in ('example','placeholder','your_token','your_secret','test_token','dummy','redacted')):
        return True
    if s == 'AKIAIOSFODNN7EXAMPLE': return True
    tok=s.split('_',1)[-1]
    return len(set(tok)) < 5

cache={}; counts={'topLevelFiles':0,'uniquePayloads':0,'archives':0,'archiveMembers':0,'textCandidatesScanned':0,'bytesScanned':0,'cacheHits':0}

def scan(data, depth=0, name=''):
    digest=hashlib.sha256(data).hexdigest()
    key=(digest,depth)
    if key in cache:
        counts['cacheHits']+=1
        return cache[key]
    counts['uniquePayloads']+=1
    counts['bytesScanned']+=len(data)
    findings=[]; errors=[]
    is_zip=data.startswith((b'PK\x03\x04',b'PK\x05\x06',b'PK\x07\x08'))
    is_tar=(data[:2]==b'\x1f\x8b' or name.lower().endswith(('.tar','.tgz','.tar.gz')))
    if is_zip or is_tar:
        counts['archives']+=1
        if depth>=MAX_DEPTH:
            errors.append({'member':'','rule':'maximum_archive_depth_reached'})
        else:
            try:
                if is_zip:
                    archive=zipfile.ZipFile(io.BytesIO(data)); members=archive.infolist()
                else:
                    archive=tarfile.open(fileobj=io.BytesIO(data),mode='r:*'); members=archive.getmembers()
                for member in members:
                    nm=member.filename if is_zip else member.name
                    for rule in path_findings(nm): findings.append({'member':nm,'rule':rule,'kind':'archive_member_path'})
                    isdir=member.is_dir() if is_zip else member.isdir()
                    if isdir: continue
                    counts['archiveMembers']+=1
                    link=(not is_zip and (member.issym() or member.islnk())) or (is_zip and (member.external_attr>>16)&0o170000 == 0o120000)
                    if link:
                        findings.append({'member':nm,'rule':'archive_link_not_followed','kind':'archive_member_path'}); continue
                    size=member.file_size if is_zip else member.size
                    if size>MAX_MEMBER:
                        errors.append({'member':nm,'rule':'oversize_member_not_read','size':size}); continue
                    try:
                        stream=archive.open(member) if is_zip else archive.extractfile(member)
                        if stream is None: continue
                        payload=stream.read()
                        child_f, child_e=scan(payload,depth+1,nm)
                        for f in child_f: findings.append(dict(f,member=nm+('::'+f['member'] if f['member'] else '')))
                        for e in child_e: errors.append(dict(e,member=nm+('::'+e['member'] if e['member'] else '')))
                    except Exception as e:
                        errors.append({'member':nm,'rule':'archive_member_read_error','errorType':type(e).__name__})
                archive.close()
            except Exception as e:
                errors.append({'member':'','rule':'archive_open_error','errorType':type(e).__name__})
    else:
        # Inspect source/text payloads, including UTF-16, without emitting matching secrets.
        sample=data[:8192]
        textdata=data
        if data.startswith((b'\xff\xfe',b'\xfe\xff')):
            textdata=data.decode('utf-16',errors='ignore').encode('utf-8')
            sample=textdata[:8192]
        if b'\x00' not in sample:
            counts['textCandidatesScanned']+=1
            for rule,pattern in patterns:
                matches=[m for m in pattern.finditer(textdata) if not is_dummy(m.group())]
                if matches:
                    findings.append({'member':'','rule':rule,'kind':'credential_format','matchCount':len(matches),'lineNumbers':[textdata.count(b'\n',0,m.start())+1 for m in matches[:20]]})
    cache[key]=(findings,errors)
    return findings,errors

entries=json.loads(INVENTORY.read_text(encoding='utf-8-sig'))
all_findings=[]; all_errors=[]; scanned=[]; excluded_scope=[]
started=time.time()
for entry in entries:
    rel=entry['relativePath']
    if not (rel.lower().startswith('smartvio') or rel.startswith(('sites/smartvio-mobile/','sites/artifacts/'))):
        excluded_scope.append(rel); continue
    path=Path(entry['absolutePath'])
    counts['topLevelFiles']+=1
    for rule in path_findings(rel): all_findings.append({'source':rel,'member':'','rule':rule,'kind':'top_level_path'})
    try:
        data=path.read_bytes()
        found,errors=scan(data,0,path.name)
        all_findings.extend(dict(f,source=rel) for f in found)
        all_errors.extend(dict(e,source=rel) for e in errors)
        if path.name.lower().endswith(('.zip','.tar','.tar.gz','.tgz')):
            scanned.append({'source':rel,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'findingCount':len(found),'errorCount':len(errors)})
    except Exception as e: all_errors.append({'source':rel,'member':'','rule':'file_read_error','errorType':type(e).__name__})
    if counts['topLevelFiles']%1000==0: print(json.dumps({'progress':counts['topLevelFiles'],'findings':len(all_findings),'errors':len(all_errors)}),flush=True)

report={'schema':'smartvio.github-upload.privacy-audit.v1','auditDate':'2026-10-15','scope':'Inventory files limited to SmartVio* and sites/smartvio-mobile, sites/artifacts; no source modifications; archive members inspected recursively in memory, no extraction.','elapsedSeconds':round(time.time()-started,2),'counts':counts,'findings':all_findings,'errors':all_errors,'archives':scanned,'excludedFromThisSubtask':excluded_scope,'interpretation':['Path findings indicate material requiring exclusion or sanitization, not proof of an active secret.','Default demonstration passwords were not automatically treated as live credentials.','No matching credential values are included in this report.','Source archives with account state should not be uploaded unchanged. Use a sanitized derivative and preserve original locally.'],'status':'REVIEW_REQUIRED' if all_findings or all_errors else 'NO_CREDENTIAL_FORMAT_OR_SENSITIVE_ARCHIVE_PATH_FOUND'}
out=ROOT/'privacy/privacy-audit.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'status':report['status'],'counts':counts,'findings':len(all_findings),'credentialFindings':sum(f['kind']=='credential_format' for f in all_findings),'errors':len(all_errors),'archives':len(scanned),'report':str(out)}
(ROOT/'privacy/privacy-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False),flush=True)
