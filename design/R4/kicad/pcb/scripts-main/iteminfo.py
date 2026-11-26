import sys,json; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); want=set(json.load(open(sys.argv[1]))); out={}
for t in b.GetTracks():
    u=t.m_Uuid.AsString()
    if u in want:
        if t.Type()==pcbnew.PCB_VIA_T: out[u]={'kind':'via','net':t.GetNetname(),'pts':[xy(t.GetPosition())],'layer':'*'}
        else: out[u]={'kind':'track','net':t.GetNetname(),'pts':[xy(t.GetStart()),xy(t.GetEnd())],'layer':b.GetLayerName(t.GetLayer()),'w':mm(t.GetWidth())}
for f in b.GetFootprints():
    for p in f.Pads():
        u=p.m_Uuid.AsString()
        if u in want:
            th=p.GetAttribute()==pcbnew.PAD_ATTRIB_PTH
            ls=[b.GetLayerName(l) for l in p.GetLayerSet().CuStack()]
            out[u]={'kind':'pad','net':p.GetNetname(),'pts':[xy(p.GetPosition())],'layer':'*' if th else ls[0],'r':min(mm(p.GetSize(ls and p.GetLayerSet().CuStack()[0]).x),mm(p.GetSize(p.GetLayerSet().CuStack()[0]).y))/2*0.7 if hasattr(p,'GetSize') else 0.1,'ref':f.GetReference()+'.'+p.GetNumber(),'smd':not th,'bbox':[mm(p.GetBoundingBox().GetX()),mm(p.GetBoundingBox().GetY()),mm(p.GetBoundingBox().GetRight()),mm(p.GetBoundingBox().GetBottom())],'rect':p.GetOrientationDegrees()%90==0}
json.dump(out,open(sys.argv[2],'w'))
