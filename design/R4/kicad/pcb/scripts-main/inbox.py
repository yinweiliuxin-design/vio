import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); x0,y0,x1,y1=map(float,sys.argv[1:5]); lay=sys.argv[5] if len(sys.argv)>5 else None
box=pcbnew.BOX2I(pt(x0,y0),pcbnew.VECTOR2I(int((x1-x0)*MM),int((y1-y0)*MM)))
for t in b.GetTracks():
    if not t.GetBoundingBox().Intersects(box): continue
    if t.Type()==pcbnew.PCB_VIA_T: print(t.GetNetname(),'VIA',xy(t.GetPosition()))
    elif lay is None or b.GetLayerName(t.GetLayer())==lay: print(t.GetNetname(),b.GetLayerName(t.GetLayer()),mm(t.GetWidth()),xy(t.GetStart()),xy(t.GetEnd()))
