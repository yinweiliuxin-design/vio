import pcbnew
mm=pcbnew.ToMM
b=pcbnew.LoadBoard('/work/r4/pcb/SmartVio-audio-r4.kicad_pcb')
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': continue
    s,e=t.GetStart(),t.GetEnd()
    if t.GetNetname()=='GND' and (mm(s.x)>60 or mm(e.x)>60): print(b.GetLayerName(t.GetLayer()),round(mm(s.x),2),round(mm(s.y),2),'->',round(mm(e.x),2),round(mm(e.y),2),mm(t.GetWidth()))
for f in b.GetFootprints():
    bb=f.GetBoundingBox(False); print(f.GetReference(),b.GetLayerName(f.GetLayer()),[round(mm(v),2) for v in (bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())])
