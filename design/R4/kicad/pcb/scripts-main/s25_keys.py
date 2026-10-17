import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
f=reload_fp(b,'J3405'); f.SetPosition(pt(2.45,3.05))
pads={p.GetNumber():p for p in f.Pads()}
new=[]
for num,p in pads.items():
    px,py=xy(p.GetPosition()); oldv=(px,round(py-0.3,3))
    nv=(px,1.35) if py<3 else (px,4.75)
    vs=[v for v in tracks(b,p.GetNetname(),vias=True) if abs(xy(v.GetPosition())[0]-oldv[0])<0.01 and abs(xy(v.GetPosition())[1]-oldv[1])<0.01]
    if not vs: print('no via for',num,oldv); continue
    v=vs[0]; v.SetPosition(pt(*nv))
    for t in tracks(b,p.GetNetname(),vias=False):
        for g,s_ in ((t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)):
            q=xy(g())
            if abs(q[0]-oldv[0])<0.01 and abs(q[1]-oldv[1])<0.01: s_(pt(*nv))
    new+=add_track(b,p.GetNetname(),'F.Cu',0.25,[(px,py),nv])+[v]
print(collide_report(b,new))
save(b,fill=False)
