# addvia.py net x y layer px py w : add via at x,y and track from (px,py) on layer to via
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load(); n=sys.argv[1]; x,y=float(sys.argv[2]),float(sys.argv[3]); lay=sys.argv[4]; px,py=float(sys.argv[5]),float(sys.argv[6]); w=float(sys.argv[7])
new=[add_via(b,n,(x,y))]
if (abs(px-x)+abs(py-y))>0.001: new+=add_track(b,n,lay,w,[(px,py),(x,y)])
r=collide_report(b,new)
if r: print('COLLIDE',r[:3]); sys.exit(1)
save(b,fill=False); print('ok')
