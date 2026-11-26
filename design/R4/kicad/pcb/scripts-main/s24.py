import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
def delpts(netn,pts,layer=None):
    dl=[]
    for t in tracks(b,netn):
        c=[t.GetPosition()] if t.Type()==pcbnew.PCB_VIA_T else [t.GetStart(),t.GetEnd()]
        if layer and t.Type()!=pcbnew.PCB_VIA_T and b.GetLayerName(t.GetLayer())!=layer: continue
        if any(abs(mm(q.x)-p[0])<0.01 and abs(mm(q.y)-p[1])<0.01 for q in c for p in pts): dl.append(t)
    remove(b,list({t.m_Uuid.AsString():t for t in dl}.values())); return len(dl)
print(delpts('PWR_KILL',[(66.13,18.205),(67.047,19.122)],'F.Cu'))
print(delpts('PWR_BOOT_OK',[(67.78,18.205),(67.251,18.205),(67.042,17.996)]))
for ref,x,y,r in [('R1301',71.25,17.75,0),('C1301',68.95,19.8,180),('C1109',66.4,19.0,90)]:
    f=move_fp(b,ref,x,y,r); print(ref,{p.GetNumber():(p.GetNetname(),xy(p.GetPosition())) for p in f.Pads()})
# drop C1301 old pad stubs: tracks of SYS/GND that end at old pad centres
print(delpts('SYS',[(69.05,19.8)],'F.Cu'), delpts('GND',[(67.55,19.8)],'F.Cu'))
save(b,fill=False)
