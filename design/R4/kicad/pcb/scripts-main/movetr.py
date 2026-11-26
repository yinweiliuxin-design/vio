# movetr.py REF dx dy : move footprint and drag track endpoints/vias that sit inside its pads
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); ref=sys.argv[1]; dx,dy=float(sys.argv[2]),float(sys.argv[3])
f=fp(b,ref); D=pt(dx,dy)
moved=0
for p in f.Pads():
    for t in tracks(b,p.GetNetname()):
        if t.Type()==pcbnew.PCB_VIA_T:
            if p.HitTest(t.GetPosition()): t.SetPosition(t.GetPosition()+D); moved+=1
            continue
        if not p.IsOnLayer(t.GetLayer()): continue
        for g,s_ in ((t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)):
            if p.HitTest(g()): s_(g()+D); moved+=1
f.SetPosition(f.GetPosition()+D)
print(ref,'moved ends',moved); save(b,fill=False)
