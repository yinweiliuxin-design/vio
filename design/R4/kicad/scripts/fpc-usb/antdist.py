import pcbnew,sys
FM=pcbnew.FromMM; mm=pcbnew.ToMM
b=pcbnew.LoadBoard(sys.argv[1])
box=pcbnew.SHAPE_POLY_SET(); box.NewOutline()
for x,y in [(113.5,37.1),(138.5,37.1),(138.5,46.1),(113.5,46.1)]: box.Append(FM(x),FM(y))
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname()!='GND': continue
    for l in z.GetLayerSet().CuStack():
        fp=z.GetFilledPolysList(l); best=1e9; where=None
        for i in range(fp.OutlineCount()):
            o=fp.Outline(i)
            for k in range(o.PointCount()):
                p=o.CPoint(k)
                # distance point->box
                dx=max(FM(113.5)-p.x,0,p.x-FM(138.5)); dy=max(FM(37.1)-p.y,0,p.y-FM(46.1))
                d=(dx*dx+dy*dy)**0.5
                if d<best: best=d; where=(mm(p.x),mm(p.y))
        print(b.GetLayerName(l),'min fill->antenna_box %.2f mm at'%mm(best),where)
