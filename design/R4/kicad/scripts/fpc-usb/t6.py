import pcbnew
b=pcbnew.LoadBoard('/work/r4/pcb/SmartVio-cover-r4.kicad_pcb'); FM=pcbnew.FromMM; mm=pcbnew.ToMM
h=b.FindFootprintByReference('H905'); hp=list(h.Pads())[0]; hs=hp.GetEffectiveHoleShape()
best={}
for t in list(b.GetTracks())+[p for f in b.GetFootprints() for p in f.Pads() if f.GetReference()!='H905']:
    for l in (pcbnew.F_Cu,pcbnew.B_Cu):
        if not t.IsOnLayer(l): continue
        lo,hi=0,FM(3)
        if not t.GetEffectiveShape(l).Collide(hs,hi): continue
        while hi-lo>1000:
            m=(lo+hi)//2
            if t.GetEffectiveShape(l).Collide(hs,m): hi=m
            else: lo=m
        k=(t.GetClass(),t.GetNetname(),t.GetParentFootprint().GetReference() if t.GetClass()=='PAD' else '')
        best[k]=min(best.get(k,9),mm(hi))
for k,v in sorted(best.items(),key=lambda x:x[1])[:6]: print(k,'%.2f'%v)
