import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=pcbnew.LoadBoard(sys.argv[1])
nets=sys.argv[2].split(',')
for t in b.GetTracks():
    n=t.GetNetname()
    if n in nets:
        if t.Type()==pcbnew.PCB_VIA_T:
            print(n,'VIA',xy(t.GetPosition()),mm(t.GetWidth(pcbnew.F_Cu)))
        else:
            print(n,b.GetLayerName(t.GetLayer()),mm(t.GetWidth()),xy(t.GetStart()),xy(t.GetEnd()),round(mm(t.GetLength()),2))
