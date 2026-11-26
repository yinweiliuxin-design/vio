import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B(sys.argv[1]); x,y=float(sys.argv[2]),float(sys.argv[3])
b.text('R4 ENGINEERING SAMPLE - NOT RELEASED unless DRC/parity 0',(x,y),'Cmts.User',0.6,0.08)
b.save(sys.argv[1])
