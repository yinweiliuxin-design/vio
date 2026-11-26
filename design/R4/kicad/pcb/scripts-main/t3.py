import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load('/work/tst/t.kicad_pcb')
for poly in ([(48.5,20),(50.5,20),(50.5,25),(48.5,25)],[(56,10),(58.5,10),(58.5,12.5),(56,12.5)]):
    z=pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetLayerSet(pcbnew.LSET.AllCuMask()); z.SetZoneName('R4_SL')
    z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowFootprints(False)
    o=z.Outline(); o.NewOutline()
    for x,y in poly: o.Append(int(x*MM),int(y*MM))
    b.Add(z)
b.Save('/work/tst/t.kicad_pcb')
