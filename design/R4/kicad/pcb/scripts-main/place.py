# place.py REF SIDE x y rot [REF SIDE x y rot ...]
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); a=sys.argv[1:]
for i in range(0,len(a),5):
    ref,side,x,y,r=a[i:i+5]; f=fp(b,ref)
    if (side=='B')!=f.IsFlipped(): f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    f.SetPosition(pt(float(x),float(y))); f.SetOrientationDegrees(float(r))
    print(ref,{p.GetNumber():(p.GetNetname()[:14],xy(p.GetPosition())) for p in f.Pads()})
save(b,fill=False)
