# rmvia.py board x y [x y ...]  remove vias within 0.05 mm of the given points
import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B(sys.argv[1]); c=list(map(float,sys.argv[2:])); pts=list(zip(c[0::2],c[1::2])); mm=pcbnew.ToMM
dead=[t for t in b.b.GetTracks() if t.GetClass()=='PCB_VIA' and any(abs(mm(t.GetPosition().x)-x)<0.05 and abs(mm(t.GetPosition().y)-y)<0.05 for x,y in pts)]
for t in dead: b.b.Remove(t)
b.fill(); b.save(sys.argv[1]); print('removed',len(dead))
