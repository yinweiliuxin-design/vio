# delsel.py NET "x,y" ... : delete tracks of NET having an endpoint at x,y (or via at x,y)
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); n=sys.argv[1]; pts=[tuple(map(float,a.split(','))) for a in sys.argv[2:]]
dl=[]
for t in tracks(b,n):
    cand=[t.GetPosition()] if t.Type()==pcbnew.PCB_VIA_T else [t.GetStart(),t.GetEnd()]
    if any(abs(mm(c.x)-p[0])<0.01 and abs(mm(c.y)-p[1])<0.01 for c in cand for p in pts): dl.append(t)
print('del',len(dl)); remove(b,dl); save(b,fill=False)
