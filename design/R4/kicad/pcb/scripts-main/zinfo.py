import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=pcbnew.LoadBoard(sys.argv[1])
for z in b.Zones():
    o=z.Outline()
    print(z.GetZoneName(),z.GetNetname(),z.GetIsRuleArea(),'tracks',z.GetDoNotAllowTracks(),'vias',z.GetDoNotAllowVias(),'pads',z.GetDoNotAllowPads(),'pour',z.GetDoNotAllowZoneFills(),'fps',z.GetDoNotAllowFootprints(), [b.GetLayerName(l) for l in z.GetLayerSet().Seq()])
    print('  pts',[xy(o.CVertex(i)) for i in range(min(20,o.TotalVertices()))])
    print('  minw',mm(z.GetMinThickness()),'clr',mm(z.GetLocalClearance() or 0) if hasattr(z,'GetLocalClearance') else '', 'thermal',z.GetPadConnection())
for d in b.GetDrawings():
    if d.GetLayer()==pcbnew.Edge_Cuts: print('EDGE',d.GetShapeStr(),xy(d.GetStart()),xy(d.GetEnd()))
    elif d.GetClass()=='PCB_TEXT' or 'TEXT' in d.GetClass(): print('TXT',b.GetLayerName(d.GetLayer()),repr(d.GetText()[:80]))
    else: print('DRW',b.GetLayerName(d.GetLayer()),d.GetShapeStr() if hasattr(d,'GetShapeStr') else d.GetClass())
