import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/pots3_base.kicad_pcb'); bd=b.b
f=bd.FindFootprintByReference('FPC_POTS3'); f.SetReference('FPC3405'); f.SetValue('FPC-POTS3 custom flex (FPC_POTS3, DFM pending)')
TY=76.30269878025518
# S end unchanged from R3 (geometry leaves no legal via site; V3D keeps the R3 via in S2 - documented deviation from L-18)
b.track([(68.45,43.2),(68.45,43.5),(77.25,43.5),(77.25,77.05),(71.5,77.05),(71.5,TY)],0.15,'B.Cu','TONE_RAW')
b.via((66.95,43.2),'V3D')
b.track([(66.95,43.2),(66.95,43.85),(77.0,43.85),(77.0,74.85),(76.75,75.1),(73.0,75.1)],0.3,'F.Cu','V3D')
b.via((73.0,75.1),'V3D'); b.track([(73.0,75.1),(73.0,TY)],0.3,'B.Cu','V3D')
b.track([(65.45,43.2),(65.45,43.85),(76.75,43.85),(76.75,TY),(74.5,TY)],0.15,'B.Cu','VOL_RAW')
b.fill(); bd.Save('/work/r4/pcb/SmartVio-fpc-pots3-r4.kicad_pcb')
