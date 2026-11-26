import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
for t in b.GetTracks():
    if t.GetClass()=='PCB_VIA': print('VIA',t.GetNetname(),round(mm(t.GetPosition().x),3),round(mm(t.GetPosition().y),3))
    else: print(b.GetLayerName(t.GetLayer()),t.GetNetname(),round(mm(t.GetWidth()),2),round(mm(t.GetStart().x),3),round(mm(t.GetStart().y),3),'->',round(mm(t.GetEnd().x),3),round(mm(t.GetEnd().y),3))
