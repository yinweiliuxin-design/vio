import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
# drop PWR_ONT route to old C1302 (keep U1301.3 stub + via at 65.971,25.008)
dele=[t for t in tracks(b,'PWR_ONT') if not (t.Type()!=pcbnew.PCB_VIA_T and b.GetLayerName(t.GetLayer())=='F.Cu' and min(xy(t.GetStart())[1],xy(t.GetEnd())[1])>23)]
dele=[t for t in dele if not (t.Type()==pcbnew.PCB_VIA_T and xy(t.GetPosition())==(65.971,25.008))]
print('drop PWR_ONT',len(dele)); remove(b,dele)
g=[t for t in tracks(b,'GND',layer='F.Cu') if set([xy(t.GetStart()),xy(t.GetEnd())]) & set([(63.3,11.125),(62.498,11.125)])]
print('drop GND',len(g)); remove(b,list({x.m_Uuid.AsString():x for x in g}.values()))
f=move_fp(b,'C1302',73.0,21.6,90)
for p in f.Pads(): print(p.GetNumber(),p.GetNetname(),xy(p.GetPosition()))
print(place_check(b,f))
save(b)
