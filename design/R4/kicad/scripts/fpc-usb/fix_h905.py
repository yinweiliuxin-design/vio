import sys,math; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/r4/pcb/SmartVio-cover-r4.kicad_pcb'); bd=b.b
h=bd.FindFootprintByReference('H905')
h.SetPosition(V(0,0)); h.SetFPID(pcbnew.LIB_ID('SmartVioV26','NPTH_D4.0_KO5.0')); h.SetValue('NPTH_D4.0_KO5.0')
for p in h.Pads(): p.SetSize(pcbnew.F_Cu,V(4.0,4.0)); p.SetDrillSize(V(4.0,4.0)); p.SetPosition(V(0,0))
for z in h.Zones():
    o=z.Outline(); o.RemoveAllContours(); o.NewOutline()
    for i in range(36): o.Append(FM(2.5*math.cos(2*math.pi*i/36)),FM(2.5*math.sin(2*math.pi*i/36)))
for g in h.GraphicalItems():
    if g.GetShape()==pcbnew.SHAPE_T_CIRCLE: g.SetCenter(V(0,0)); g.SetEnd(V(2.02,0))
b.savefp(h,'NPTH_D4.0_KO5.0'); h.SetPosition(V(88,21.8))
b.fill(); b.save('/work/r4/pcb/SmartVio-cover-r4.kicad_pcb')
p=list(h.Pads())[0]; print(pcbnew.ToMM(p.GetPosition().x),pcbnew.ToMM(p.GetPosition().y),pcbnew.ToMM(p.GetDrillSize().x))
