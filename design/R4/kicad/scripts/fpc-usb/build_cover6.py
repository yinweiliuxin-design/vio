import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/cover6_base.kicad_pcb'); bd=b.b
f=bd.FindFootprintByReference('FPC_COVER6'); f.SetReference('FPC3404'); f.SetValue('FPC-COVER6 custom flex (FPC_COVER6, DFM pending)')
W=0.15; SW=0.6
F=[('LED_ZONE_1_A',70.2,72.85,61.375,108.375,74.6,86.25),('LED_ZONE_2_A',71.7,73.2,61.075,108.675,74.9,87.75),
   ('LED_ZONE_3_A',73.2,73.55,60.775,108.975,75.2,89.25),('PWR_PB',74.7,73.86,60.475,109.275,75.5,90.75)]
TY=78.35769878025519; VY=77.1
for n,cx,nx,by,rx,ty,tx in F:
    p=[(cx,43.2),(cx,46.62),(nx,49.4),(nx,by),(rx,by),(rx,ty),(tx,ty),(tx,VY)]
    b.track(p,W,'F.Cu',n); b.via((tx,VY),n); b.track([(tx,VY),(tx,TY)],W,'B.Cu',n)
# speaker pair: broadside (SPK_N on F, SPK_P on B), laterally >=0.5 mm away from the F-layer LED/PWR lines (L-15)
spk=[(74.6,49.4),(74.6,59.6),(110.4,59.6),(110.4,76.55)]
b.track([(76.2,43.2),(76.2,46.62)]+spk+[(92.25,76.55),(92.25,VY)],SW,'F.Cu','SPK_N')
for vx in (92.25,91.75): b.via((vx,VY),'SPK_N',0.45,0.2)
b.track([(91.75,VY),(92.25,VY),(92.25,TY)],SW,'B.Cu','SPK_N')
b.track([(77.7,43.2),(77.7,44.4)],SW,'F.Cu','SPK_P'); b.via((77.7,44.4),'SPK_P',0.45,0.2)
b.track([(77.7,44.4),(77.55,44.55),(77.55,46.62)]+spk+[(93.75,76.55),(93.75,TY)],SW,'B.Cu','SPK_P')
b.text('COVER6 R4 (L-15: SPK broadside F/B, LED/PWR offset; L-18 no vias in contacts) - R4 ENGINEERING SAMPLE - NOT RELEASED unless DRC/parity 0',(90.0,63.5),'Cmts.User',0.5,0.08)
b.fill(); bd.Save('/work/r4/pcb/SmartVio-fpc-cover6-r4.kicad_pcb')
