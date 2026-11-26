import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
for n in ['GND','PWR_ONT','SYS']:
    x=b.FindNet(n); print(n,type(x))
    y=b.GetNetInfo().GetNetItem(n); print(type(y), y.GetNetCode())
