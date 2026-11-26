import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); dead=[z for z in b.Zones() if z.GetZoneName()=='TMP_EDGE_KO']
for z in dead: b.Remove(z)
b.BuildConnectivity(); f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); b.Save(sys.argv[1]); print('rm tmp',len(dead))
