import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
for r in sys.argv[1].split(','):
    f=fp(b,r); c=f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
    for k in range(c.OutlineCount()):
        o=c.Outline(k); print(r,k,[xy(o.CPoint(j)) for j in range(o.PointCount())][:12])
