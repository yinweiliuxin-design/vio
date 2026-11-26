import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1])
mm=pcbnew.ToMM
bb=b.GetBoardEdgesBoundingBox()
print('bbox',mm(bb.GetX()),mm(bb.GetY()),mm(bb.GetRight()),mm(bb.GetBottom()),'layers',b.GetCopperLayerCount())
for f in b.GetFootprints():
    p=f.GetPosition(); cb=f.GetCourtyard(f.GetLayer()) if hasattr(f,'GetCourtyard') else None
    bx=f.GetBoundingBox(False)
    print('FP',f.GetReference(),f.GetFPIDAsString(),f.GetValue()[:30],'L=' + b.GetLayerName(f.GetLayer()),'at',round(mm(p.x),3),round(mm(p.y),3),'rot',f.GetOrientationDegrees(),'bbox',round(mm(bx.GetX()),2),round(mm(bx.GetY()),2),round(mm(bx.GetRight()),2),round(mm(bx.GetBottom()),2))
    if len(sys.argv)>2:
        for pd in f.Pads():
            q=pd.GetPosition(); s=pd.GetSize()
            print('   pad',pd.GetNumber(),pd.GetNetname(),round(mm(q.x),3),round(mm(q.y),3),round(mm(s.x),3),round(mm(s.y),3),[b.GetLayerName(l) for l in pd.GetLayerSet().Seq()][:3])
from collections import Counter
c=Counter(); v=0
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': v+=1
    else: c[(t.GetNetname(),b.GetLayerName(t.GetLayer()),round(mm(t.GetWidth()),3))]+=1
print('vias',v)
for k,n in sorted(c.items()): print('TR',k,n)
for z in b.Zones():
    print('ZONE',z.GetNetname(),[b.GetLayerName(l) for l in z.GetLayerSet().Seq()],'keepout' if z.GetIsRuleArea() else '', mm(z.GetBoundingBox().GetX()),mm(z.GetBoundingBox().GetY()),mm(z.GetBoundingBox().GetRight()),mm(z.GetBoundingBox().GetBottom()))
