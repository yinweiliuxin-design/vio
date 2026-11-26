import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/audio6_base.kicad_pcb'); bd=b.b
f=bd.FindFootprintByReference('FPC_AUDIO6'); f.SetReference('FPC3401'); f.SetValue('FPC-AUDIO6 custom flex (FPC_AUDIO6, DFM pending)')
T0=53.01769878025519
L=[('GND',79.45,49.6,55.6,0,0.6),('HP_DETECT_RAW',80.95,50.2,56.35,1,0.15),('HP_L_PORT',82.45,50.5,56.65,2,0.15),
   ('HP_R_PORT',83.95,50.8,56.95,3,0.15),('LINE_L_PORT',85.45,51.1,57.25,4,0.15),('LINE_R_PORT',86.95,51.4,57.55,5,0.15)]
for n,sx,by,cx,k,w in L:
    ty=T0+1.5*k
    p=[(sx,43.2),(sx,by),(cx,by),(cx,ty)]
    if k: p.append((55.6,ty))
    b.track(p,w,'F.Cu',n)
b.text('AUDIO6 R4: single-layer F routing, no vias (L-18); T tab +1.2 mm east (needs mech. check)',(70.0,55.0),'Cmts.User',0.5,0.08)
b.fill(); bd.Save('/work/r4/pcb/SmartVio-fpc-audio6-r4.kicad_pcb'); b.savefp(f,'FPC_AUDIO6')
