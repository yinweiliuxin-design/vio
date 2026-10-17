# report GND filled islands (per layer) lacking a GND via; write candidate points inside them
import pcbnew,sys
FM=pcbnew.FromMM; mm=pcbnew.ToMM
b=pcbnew.LoadBoard(sys.argv[1]); out=open(sys.argv[2],'w'); vd=float(sys.argv[3]) if len(sys.argv)>3 else 0.6
gv=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetname()=='GND']
n=0
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname()!='GND': continue
    for l in z.GetLayerSet().CuStack():
        if not z.HasFilledPolysForLayer(l): continue
        fp=z.GetFilledPolysList(l)
        for i in range(fp.OutlineCount()):
            one=pcbnew.SHAPE_POLY_SET(); one.AddOutline(fp.Outline(i))
            for h in range(fp.HoleCount(i)): one.AddHole(fp.Hole(i,h))
            if any(one.Contains(v.GetPosition()) for v in gv): continue
            bb=fp.Outline(i).BBox(); area=one.Area()/1e12
            # candidate points where a via of radius vd/2 fits inside the island
            pts=[]
            x=bb.GetX()
            while x<bb.GetRight():
                y=bb.GetY()
                while y<bb.GetBottom():
                    c=pcbnew.VECTOR2I(int(x),int(y))
                    if one.Contains(c) and not one.Collide(c,0) is False:
                        # distance to island boundary
                        d=min(fp.Outline(i).CSegment(k).Distance(c) for k in range(fp.Outline(i).SegmentCount()))
                        if d>=FM(vd/2+0.05): pts.append((mm(x),mm(y),d))
                    y+=FM(0.1)
                x+=FM(0.1)
            pts.sort(key=lambda p:-p[2])
            print(b.GetLayerName(l),'island',i,'area %.2f'%area,'bbox',[round(mm(v),2) for v in (bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())],'cands',len(pts))
            for p in pts[:6]: out.write('%.3f %.3f\n'%(p[0],p[1]))
            n+=1
print('islands without via',n)
