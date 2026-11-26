import pcbnew
f=pcbnew.FootprintLoad('/work/r4/footprints/SmartVioV26.pretty','FPC_USB16_HotBar_Main_P0.70')
print(f.GetFPID().GetUniStringLibId(), len(f.Pads()), [ (p.GetNumber(),p.GetPosition().x/1e6) for p in f.Pads()][:3])
