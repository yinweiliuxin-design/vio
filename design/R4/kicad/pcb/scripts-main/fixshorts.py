# fixshorts.py drc.json NET1,NET2,... : delete tracks/vias of listed nets that short something (iterated externally)
import sys,json; sys.path.insert(0,'/work/scripts')
from lib import *
d=json.load(open(sys.argv[1])); nets=set(sys.argv[2].split(','))
types=('shorting_items','tracks_crossing') + (('clearance','hole_clearance','solder_mask_bridge') if '--clear' in sys.argv else ())
b=load(); byid={t.m_Uuid.AsString():t for t in b.GetTracks()}
dele={}
for v in d['violations']:
    if v['type'] not in types: continue
    its=v['items']
    cands=[i for i in its if i['uuid'] in byid and byid[i['uuid']].GetNetname() in nets]
    # prefer deleting track over via
    cands.sort(key=lambda i: byid[i['uuid']].Type()==pcbnew.PCB_VIA_T)
    if cands: dele[cands[0]['uuid']]=byid[cands[0]['uuid']]
for u,t in dele.items(): print('del',t.GetNetname(),'via' if t.Type()==pcbnew.PCB_VIA_T else b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()))
remove(b,list(dele.values())); save(b,fill=False); print('deleted',len(dele))
