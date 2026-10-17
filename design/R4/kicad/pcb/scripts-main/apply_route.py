# apply_route.py route.json net width [via_d via_drill] [width_inner]
import sys,json; sys.path.insert(0,'/work/scripts')
from lib import *
r=json.load(open(sys.argv[1])); netn=sys.argv[2]; w=float(sys.argv[3])
vd=float(sys.argv[4]) if len(sys.argv)>4 else 0.35; vdr=float(sys.argv[5]) if len(sys.argv)>5 else 0.15
wi=float(sys.argv[6]) if len(sys.argv)>6 else w
b=load(); new=[]
def snap(p):
    best=None;bd=0.02
    cands=[t.GetPosition() for t in b.GetTracks() if t.GetNetname()==netn and t.Type()==pcbnew.PCB_VIA_T]
    cands+=[q for t in b.GetTracks() if t.GetNetname()==netn and t.Type()!=pcbnew.PCB_VIA_T for q in (t.GetStart(),t.GetEnd())]
    cands+=[pd.GetPosition() for f in b.GetFootprints() for pd in f.Pads() if pd.GetNetname()==netn]
    for c in cands:
        d=((mm(c.x)-p[0])**2+(mm(c.y)-p[1])**2)**0.5
        if d<bd: bd=d;best=(mm(c.x),mm(c.y))
    return best or p
for s_ in r['segs']:
    s_['pts'][0]=snap(s_['pts'][0]); s_['pts'][-1]=snap(s_['pts'][-1])
for s in r['segs']:
    ww=w if s['layer'] in ('F.Cu','B.Cu') else wi
    new+=add_track(b,netn,s['layer'],ww,[tuple(p) for p in s['pts']])
for v in r['vias']: new.append(add_via(b,netn,tuple(v),vd,vdr))
rep=collide_report(b,new)
print('collisions',len(rep)); [print(' ',x) for x in rep[:20]]
if rep and '--force' not in sys.argv: print('NOT SAVED'); sys.exit(1)
save(b); print('saved')
