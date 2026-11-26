# reroute_net.py board NET layer width x1 y1 x2 y2 ...   (deletes all tracks/vias of NET first)
import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B(sys.argv[1]); n=sys.argv[2]; lay=sys.argv[3]; w=float(sys.argv[4]); c=list(map(float,sys.argv[5:]))
dead=[t for t in b.b.GetTracks() if t.GetNetname()==n]
for t in dead: b.b.Remove(t)
pts=list(zip(c[0::2],c[1::2])); b.track(pts,w,lay,n)
b.fill(); b.save(sys.argv[1]); print('removed',len(dead))
