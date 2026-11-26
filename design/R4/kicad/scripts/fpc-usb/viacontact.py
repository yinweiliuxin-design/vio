# report vias within 0.5 mm (edge) of FPC contact mask openings
import pcbnew,sys
mm=pcbnew.ToMM; FM=pcbnew.FromMM
b=pcbnew.LoadBoard(sys.argv[1]); out=[]
pads=[p for f in b.GetFootprints() for p in f.Pads() if p.GetAttribute()==pcbnew.PAD_ATTRIB_SMD]
for v in b.GetTracks():
    if v.GetClass()!='PCB_VIA': continue
    r=mm(v.GetWidth(pcbnew.F_Cu))/2; best=9
    for p in pads:
        bb=p.GetBoundingBox(); m=mm(p.GetLocalSolderMaskMargin() or 0)
        x0,y0,x1,y1=mm(bb.GetX())-m,mm(bb.GetY())-m,mm(bb.GetRight())+m,mm(bb.GetBottom())+m
        vx,vy=mm(v.GetPosition().x),mm(v.GetPosition().y)
        dx=max(x0-vx,0,vx-x1); dy=max(y0-vy,0,vy-y1); d=(dx*dx+dy*dy)**0.5-r
        if d<best: best=d; bp=p
    if best<0.5: out.append((v.GetNetname(),round(mm(v.GetPosition().x),2),round(mm(v.GetPosition().y),2),'gap %.2f'%best,bp.GetParentFootprint().GetReference()+'.'+bp.GetNumber()))
print(sys.argv[1].split('/')[-1],'vias <0.5mm from contact opening:',len(out),out)
