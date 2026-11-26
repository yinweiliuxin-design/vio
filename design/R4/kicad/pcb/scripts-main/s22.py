import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); f=reload_fp(b,'J3411'); print({p.GetNumber():(p.GetNetname(),xy(p.GetPosition())) for p in f.Pads()}); save(b,fill=False)
