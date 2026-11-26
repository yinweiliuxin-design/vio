import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA':
        print('VIA',t.GetNetname(),round(mm(t.GetPosition().x),3),round(mm(t.GetPosition().y),3),mm(t.GetWidth(pcbnew.F_Cu)),mm(t.GetDrillValue()),t.GetViaType(),b.GetLayerName(t.TopLayer()),b.GetLayerName(t.BottomLayer()))
