import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=pcbnew.LoadBoard('SmartVio-main-r3-linked.kicad_pcb')
t=[t for t in b.GetTracks() if t.GetNetname()=='SYS' and t.Type()==pcbnew.PCB_TRACE_T][0]
s=t.GetEffectiveShape(t.GetLayer())
print(type(s), s.Type() if hasattr(s,'Type') else '')
p=pad(b,'U501','10'); ps=p.GetEffectiveShape(pcbnew.F_Cu)
print(type(ps))
print(s.Collide(ps, 100000))
print([m for m in dir(s) if 'oll' in m])
print(b.GetDesignSettings().GetBiggestClearanceValue())
print([m for m in dir(pcbnew) if 'DRC' in m or 'Refill' in m or 'ZONE_FILLER' in m][:30])
