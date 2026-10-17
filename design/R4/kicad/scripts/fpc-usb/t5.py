import pcbnew
mm=pcbnew.ToMM
b=pcbnew.LoadBoard('/work/r4/pcb/SmartVio-audio-r4.kicad_pcb')
f=b.FindFootprintByReference('J202')
for g in f.GraphicalItems():
    if g.GetLayer()==pcbnew.Edge_Cuts:
        bb=g.GetBoundingBox(); print(g.GetShapeStr(), [round(mm(v),2) for v in (bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())])
for t in b.GetTracks():
    if t.GetNetname()=='RETURN_L_PORT':
        print(t.GetClass(), b.GetLayerName(t.GetLayer()), [round(mm(v),2) for v in ((t.GetStart().x,t.GetStart().y,t.GetEnd().x,t.GetEnd().y) if t.GetClass()!='PCB_VIA' else (t.GetPosition().x,t.GetPosition().y))])
