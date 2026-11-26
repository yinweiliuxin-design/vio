import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); mm=pcbnew.ToMM
for r in sys.argv[2:]:
    f=b.FindFootprintByReference(r)
    if not f: print(r,'absent'); continue
    print(r,f.GetFPIDAsString(),b.GetLayerName(f.GetLayer()),round(mm(f.GetPosition().x),3),round(mm(f.GetPosition().y),3),f.GetOrientationDegrees(),[(p.GetNumber(),p.GetNetname(),round(mm(p.GetPosition().x),3),round(mm(p.GetPosition().y),3),round(mm(p.GetSize(p.GetPrincipalLayer()).x),2)) for p in f.Pads()])
