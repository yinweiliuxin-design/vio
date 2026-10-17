import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
x0,y0,x1,y1=map(float,sys.argv[2:6])
for f in b.GetFootprints():
    bb=f.GetBoundingBox(False)
    if mm(bb.GetRight())>=x0 and mm(bb.GetX())<=x1 and mm(bb.GetBottom())>=y0 and mm(bb.GetY())<=y1:
        cy=f.GetCourtyard(f.GetLayer()); cb=cy.BBox() if cy.OutlineCount() else None
        print(f.GetReference(),b.GetLayerName(f.GetLayer()),'at',round(mm(f.GetPosition().x),2),round(mm(f.GetPosition().y),2),'crtyd',[round(mm(v),2) for v in (cb.GetX(),cb.GetY(),cb.GetRight(),cb.GetBottom())] if cb else None,f.GetValue()[:25])
