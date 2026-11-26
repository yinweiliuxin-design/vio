import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); ok=pcbnew.ImportSpecctraSES(b,sys.argv[2]); print('import',ok)
b.BuildConnectivity(); f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); b.Save(sys.argv[3] if len(sys.argv)>3 else sys.argv[1])
