import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
NETS=['USB_DATA_FAULT_N','USB_DATA_DISABLE','CC_FAULT_N','V3D','USB_DM_MCU','USB_DP_MCU','USB_5V_SAFE','VBUS_RAW','GND']
box=(26.0,0.0,44.5,2.9)
dele=[]
for t in b.GetTracks():
    if t.GetNetname() not in NETS: continue
    if t.Type()==pcbnew.PCB_VIA_T:
        x,y=xy(t.GetPosition())
        if box[0]<=x<=box[2] and box[1]<=y<=box[3]: dele.append(t)
    else:
        s,e=xy(t.GetStart()),xy(t.GetEnd())
        if all(box[0]<=p[0]<=box[2] and box[1]<=p[1]<=box[3] for p in (s,e)): dele.append(t)
print('del',len(dele))
for t in dele: print(t.GetNetname(),'via' if t.Type()==pcbnew.PCB_VIA_T else b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()))
remove(b,dele); save(b,fill=False)
