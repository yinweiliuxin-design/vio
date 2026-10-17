import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=pcbnew.LoadBoard(sys.argv[1])
for n in sys.argv[2].split(','):
    out=[]
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetNetname()==n: out.append('%s.%s%s@%s'%(f.GetReference(),p.GetNumber(),'B' if f.IsFlipped() else 'F',xy(p.GetPosition())))
    print(n,len(out),' '.join(out))
