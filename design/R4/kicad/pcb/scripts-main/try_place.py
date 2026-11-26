# try_place.py ref x y rot [flip]
import sys; sys.path.insert(0,'/work/scripts')
from lib import *
b=load()
ref=sys.argv[1]
for spec in sys.argv[2:]:
    x,y,r,*fl=spec.split(':')
    f=move_fp(b,ref,float(x),float(y),float(r),(fl[0]=='B') if fl else None)
    print(spec,place_check(b,f))
