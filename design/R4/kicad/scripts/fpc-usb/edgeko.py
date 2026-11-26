# edgeko.py board out: temporary track/via keepouts hugging each footprint Edge.Cuts item (bbox +0.6)
import pcbnew,sys
b=pcbnew.LoadBoard(sys.argv[1]); FM=pcbnew.FromMM; n=0
for f in b.GetFootprints():
    for g in f.GraphicalItems():
        if g.GetLayer()!=pcbnew.Edge_Cuts: continue
        bb=g.GetBoundingBox(); m=FM(0.62)
        x0,y0,x1,y1=bb.GetX()-m,bb.GetY()-m,bb.GetRight()+m,bb.GetBottom()+m
        z=pcbnew.ZONE(b); ls=pcbnew.LSET(); [ls.AddLayer(l) for l in b.GetEnabledLayers().CuStack()]; z.SetLayerSet(ls)
        o=z.Outline(); o.NewOutline(); o.Append(x0,y0); o.Append(x1,y0); o.Append(x1,y1); o.Append(x0,y1)
        z.SetIsRuleArea(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(False); z.SetZoneName('TMP_EDGE_KO'); b.Add(z); n+=1
b.Save(sys.argv[2]); print('edge KO',n)
