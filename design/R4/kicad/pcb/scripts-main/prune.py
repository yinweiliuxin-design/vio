import sys,json; sys.path.insert(0,'/work/scripts')
from lib import *
d=json.load(open(sys.argv[1])); b=load(); byid={t.m_Uuid.AsString():t for t in b.GetTracks()}
dl={}
for v in d['violations']:
    if v['type'] in ('track_dangling','via_dangling'):
        for i in v['items']:
            if i['uuid'] in byid: dl[i['uuid']]=byid[i['uuid']]
remove(b,list(dl.values())); save(b,fill=False); print('pruned',len(dl))
