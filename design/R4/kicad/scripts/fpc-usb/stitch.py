# usage: stitch.py board.kicad_pcb pitch via_d drill clr [x0 y0 x1 y1] [extra points file]
import pcbnew,sys,math
FM=pcbnew.FromMM; mm=pcbnew.ToMM
bp=sys.argv[1]; pitch=float(sys.argv[2]); vd=float(sys.argv[3]); dr=float(sys.argv[4]); clr=float(sys.argv[5])
b=pcbnew.LoadBoard(bp); gnd=b.FindNet('GND')
bb=b.GetBoardEdgesBoundingBox()
X0,Y0,X1,Y1=(mm(bb.GetX()),mm(bb.GetY()),mm(bb.GetRight()),mm(bb.GetBottom()))
if len(sys.argv)>9: X0,Y0,X1,Y1=map(float,sys.argv[6:10])
pts=[]
extra=sys.argv[10] if len(sys.argv)>10 else None
micro=len(sys.argv)>11 and sys.argv[11]=='micro'
if extra:
    pts=[tuple(map(float,l.split())) for l in open(extra) if l.strip()]
else:
    y=Y0+pitch/2
    while y<Y1:
        x=X0+pitch/2
        while x<X1: pts.append((x,y)); x+=pitch
        y+=pitch
cu=[l for l in b.GetEnabledLayers().CuStack()]
if micro: cu=[pcbnew.F_Cu,pcbnew.In1_Cu]
edge=b.GetBoardEdgesBoundingBox()
outline=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outline,True)
items=[]
for t in b.GetTracks(): items.append(t)
for f in b.GetFootprints():
    for p in f.Pads(): items.append(p)
rules=[z for z in b.Zones() if z.GetIsRuleArea()]
ozones=[z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()!='GND']
for f in b.GetFootprints():
    for z in f.Zones():
        if z.GetIsRuleArea(): rules.append(z)
added=0
segs=[]
for k in range(outline.OutlineCount()):
    o=outline.Outline(k)
    segs+=[o.CSegment(i) for i in range(o.SegmentCount())]
    for h in range(outline.HoleCount(k)):
        oh=outline.Hole(k,h); segs+=[oh.CSegment(i) for i in range(oh.SegmentCount())]
import collections; why=collections.Counter()
for (x,y) in pts:
    v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(FM(x),FM(y))); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetDrill(FM(dr)); v.SetWidth(FM(vd))
    if micro: v.SetViaType(pcbnew.VIATYPE_MICROVIA); v.SetLayerPair(pcbnew.F_Cu,pcbnew.In1_Cu)
    c=pcbnew.VECTOR2I(FM(x),FM(y))
    # inside board with margin
    if not outline.Contains(c): why['outside']+=1; continue
    dmin=outline.SquaredDistance(c)
    if dmin < FM(vd/2+0.5)**2 and outline.Contains(c): 
        # distance to outline edge
        pass
    ok=True
    # board edge distance: check four directions approx via polygon outline distance
    dm=min(segs[i].Distance(c) for i in range(len(segs)))
    if dm < FM(vd/2+0.45): ok=False; why['edge']+=1
    for z in rules:
        if not ok: break
        if z.GetDoNotAllowVias() and (z.Outline().Contains(c) or z.Outline().Collide(c,FM(vd/2+0.05))): ok=False; why['rule']+=1
    for z in ozones:
        if ok and (z.Outline().Contains(c) or z.Outline().Collide(c,FM(vd/2+0.3))): ok=False; why['ozone']+=1
    if ok:
        for v2 in [t for t in items if t.GetClass()=='PCB_VIA']:
            if math.hypot(mm(v2.GetPosition().x)-x,mm(v2.GetPosition().y)-y)<max(1.0,vd+0.3): ok=False; why['viasp']+=1; break
    if ok:
        for it in items:
            if it.GetNetCode()==gnd.GetNetCode() and it.GetClass()!='PCB_VIA': 
                # same net pads/tracks: still keep 0.1 off pads to avoid via-in-pad
                if it.GetClass()=='PAD':
                    for l in cu:
                        if it.IsOnLayer(l) and it.GetEffectiveShape(l).Collide(v.GetEffectiveShape(l),FM(0.15)): ok=False;break
                if not ok: break
                continue
            for l in cu:
                if it.IsOnLayer(l):
                    try:
                        if it.GetEffectiveShape(l).Collide(v.GetEffectiveShape(l),FM(clr)): ok=False;break
                    except Exception: pass
            if not ok: break
            if it.GetClass()=='PAD' and it.HasHole():
                hs=it.GetEffectiveHoleShape()
                if hs.Collide(v.GetEffectiveShape(pcbnew.F_Cu),FM(0.3)): ok=False
            if not ok: break
    if not ok: why['other']+=1
    if ok:
        b.Add(v); v.SetNet(gnd); items.append(v); added+=1
b.BuildConnectivity(); f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); b.BuildConnectivity()
b.Save(bp); print('added',added,dict(why),len(pts))
