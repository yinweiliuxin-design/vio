import pcbnew
FM=pcbnew.FromMM; mm=pcbnew.ToMM
b=pcbnew.LoadBoard('/work/r4/pcb/SmartVio-usb-r4.kicad_pcb')
c=pcbnew.VECTOR2I(FM(15.15),FM(14.7))
v=pcbnew.PCB_VIA(b); v.SetPosition(c); v.SetViaType(pcbnew.VIATYPE_MICROVIA); v.SetLayerPair(pcbnew.F_Cu,pcbnew.In1_Cu); v.SetDrill(FM(0.1)); v.SetWidth(FM(0.25))
for t in list(b.GetTracks())+[p for f in b.GetFootprints() for p in f.Pads()]:
    if t.GetNetname()=='GND': continue
    for l in (pcbnew.F_Cu,pcbnew.In1_Cu):
        if t.IsOnLayer(l) and t.GetEffectiveShape(l).Collide(v.GetEffectiveShape(l),FM(0.15)):
            print('hit',t.GetClass(),t.GetNetname(),b.GetLayerName(l), (mm(t.GetPosition().x),mm(t.GetPosition().y)) if t.GetClass()!='PCB_TRACK' else (mm(t.GetStart().x),mm(t.GetStart().y),mm(t.GetEnd().x),mm(t.GetEnd().y)))
