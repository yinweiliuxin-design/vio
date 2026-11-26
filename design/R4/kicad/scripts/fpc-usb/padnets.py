import pcbnew,sys,json
b=pcbnew.LoadBoard(sys.argv[1]); out={}
for f in b.GetFootprints():
    out[f.GetReference()]={'fp':f.GetFPIDAsString(),'value':f.GetValue(),'layer':b.GetLayerName(f.GetLayer()),'board_only':bool(f.GetAttributes() & pcbnew.FP_BOARD_ONLY),'pads':{p.GetNumber():p.GetNetname() for p in f.Pads() if p.GetNumber()}}
json.dump(out,open(sys.argv[2],'w'),indent=1)
