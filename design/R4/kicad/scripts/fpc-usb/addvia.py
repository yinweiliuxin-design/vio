# addvia.py board x y net size drill [micro]
import pcbnew,sys
FM=pcbnew.FromMM
b=pcbnew.LoadBoard(sys.argv[1]); x,y=float(sys.argv[2]),float(sys.argv[3]); n=b.FindNet(sys.argv[4])
v=pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(FM(x),FM(y))); v.SetDrill(FM(float(sys.argv[6]))); v.SetWidth(FM(float(sys.argv[5])))
if len(sys.argv)>7: v.SetViaType(pcbnew.VIATYPE_MICROVIA); v.SetLayerPair(pcbnew.F_Cu,pcbnew.In1_Cu)
else: v.SetLayerPair(pcbnew.F_Cu,pcbnew.B_Cu)
b.Add(v); v.SetNet(n); v.SetLocked(True)
b.BuildConnectivity(); f=pcbnew.ZONE_FILLER(b); f.Fill(b.Zones()); b.Save(sys.argv[1]); print('ok')
