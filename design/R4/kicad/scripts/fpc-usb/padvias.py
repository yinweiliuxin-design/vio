# add a GND via + stub next to each GND SMD pad that has no via within 1.2 mm. usage: padvias.py board vd drill clr [refs-to-skip]
import pcbnew,sys,math
FM=pcbnew.FromMM; mm=pcbnew.ToMM
bp=sys.argv[1]; vd=float(sys.argv[2]); dr=float(sys.argv[3]); clr=float(sys.argv[4]); skip=set(sys.argv[5].split(',')) if len(sys.argv)>5 and sys.argv[5] else set()
only=set(sys.argv[6].split(',')) if len(sys.argv)>6 else None
micro=len(sys.argv)>7 and sys.argv[7]=='micro'
if micro: cu=[pcbnew.F_Cu,pcbnew.In1_Cu]
b=pcbnew.LoadBoard(bp); g=b.FindNet('GND'); cu=list(b.GetEnabledLayers().CuStack())
outline=pcbnew.SHAPE_POLY_SET(); b.GetBoardPolygonOutlines(outline,True)
segs=[]
for k in range(outline.OutlineCount()):
    o=outline.Outline(k); segs+=[o.CSegment(i) for i in range(o.SegmentCount())]
    for h in range(outline.HoleCount(k)):
        oh=outline.Hole(k,h); segs+=[oh.CSegment(i) for i in range(oh.SegmentCount())]
ozones=[z for z in b.Zones() if not z.GetIsRuleArea() and z.GetNetname()!='GND']
rules=[z for z in b.Zones() if z.GetIsRuleArea()]+[z for f in b.GetFootprints() for z in f.Zones() if z.GetIsRuleArea()]
def items():
    for t in b.GetTracks(): yield t
    for f in b.GetFootprints():
        for p in f.Pads(): yield p
def ok_at(v,x,y,pad_own,stub):
    c=pcbnew.VECTOR2I(FM(x),FM(y))
    if not outline.Contains(c) or min(s.Distance(c) for s in segs)<FM(vd/2+0.45): return False
    for z in ozones:
        if z.Outline().Contains(c) or z.Outline().Collide(c,FM(vd/2+0.3)): return False
    for t in b.GetTracks():
        if t.GetClass()=='PCB_VIA' and math.hypot(mm(t.GetPosition().x)-x,mm(t.GetPosition().y)-y)<vd+0.3: return False
    for z in rules:
        if (z.GetDoNotAllowVias() and (z.Outline().Contains(c) or z.Outline().Collide(c,FM(vd/2+0.05)))): return False
    for it in items():
        if it.GetNetCode()==g.GetNetCode():
            if it.GetClass()=='PAD' and it is not pad_own:
                for l in cu:
                    if it.IsOnLayer(l) and it.GetEffectiveShape(l).Collide(v.GetEffectiveShape(l),FM(0.1)): return False
            continue
        for l in cu:
            if it.IsOnLayer(l) or it.GetClass()=='PCB_VIA':
                try:
                    if it.GetEffectiveShape(l).Collide(v.GetEffectiveShape(l),FM(clr)): return False
                    if stub is not None and stub.GetLayer()==l and it.GetEffectiveShape(l).Collide(stub.GetEffectiveShape(l),FM(clr)): return False
                except Exception: pass
        if it.GetClass()=='PAD' and it.HasHole():
            if it.GetEffectiveHoleShape().Collide(v.GetEffectiveShape(pcbnew.F_Cu),FM(0.3)): return False
    return True
vias=[t for t in b.GetTracks() if t.GetClass()=='PCB_VIA' and t.GetNetCode()==g.GetNetCode()]
added=0; miss=[]
for f in b.GetFootprints():
    if f.GetReference() in skip: continue
    if only and f.GetReference() not in only: continue
    for p in f.Pads():
        if p.GetNetCode()!=g.GetNetCode() or p.GetAttribute()!=pcbnew.PAD_ATTRIB_SMD: continue
        pc=p.GetPosition(); px,py=mm(pc.x),mm(pc.y)
        if any(math.hypot(mm(v.GetPosition().x)-px,mm(v.GetPosition().y)-py)<1.2 for v in vias): continue
        sz=p.GetSize(p.GetPrincipalLayer()); r=max(mm(sz.x),mm(sz.y))/2+vd/2+(0.05 if micro else 0.2)
        lay=p.GetPrincipalLayer(); done=False
        for rr in (r,r+0.3,r+0.6):
            for k in range(16):
                a=2*math.pi*k/16; x=px+rr*math.cos(a); y=py+rr*math.sin(a)
                v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(FM(x),FM(y))); v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu); v.SetDrill(FM(dr)); v.SetWidth(FM(vd))
                if micro: v.SetViaType(pcbnew.VIATYPE_MICROVIA); v.SetLayerPair(pcbnew.F_Cu,pcbnew.In1_Cu)
                t=pcbnew.PCB_TRACK(b); t.SetStart(pc); t.SetEnd(v.GetPosition()); t.SetWidth(FM(0.25)); t.SetLayer(lay)
                if ok_at(v,x,y,p,t):
                    b.Add(v); v.SetNet(g); b.Add(t); t.SetNet(g); vias.append(v); added+=1; done=True; break
            if done: break
        if not done: miss.append((f.GetReference(),p.GetNumber()))
b.BuildConnectivity(); fl=pcbnew.ZONE_FILLER(b); fl.Fill(b.Zones()); b.BuildConnectivity(); b.Save(bp)
print('padvias added',added,'missed',miss)
