import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/r4/pcb/SmartVio-usb-r4.kicad_pcb')
v=b.via((6.0,7.0),'VBUS_RAW'); print('after create',v.GetNetname())
n=b.net('VBUS_RAW'); print(n.GetNetname(), n.GetNetCode())
for z in b.b.Zones(): print('zone',z.GetNetname(),z.GetLayerName() if not z.GetIsRuleArea() else 'rule')
