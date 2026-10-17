import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/audio_base.kicad_pcb'); bd=b.b
j=bd.FindFootprintByReference('H_AUDIO_1_R'); j.SetReference('J3402'); j.SetValue('AUDIO6 remote-end FPC landing (H_AUDIO_1_R)')
r=pcbnew.FootprintLoad('/work/view/tmpR.pretty','R_0603_1608Metric')
f=pcbnew.FootprintLoad('/work/r4/footprints/SmartVioV25.pretty','WirePads_4_P1.5'); f.SetFPID(pcbnew.LIB_ID('SmartVioV25','WirePads_4_P1.5'))
f.SetReference('J3404'); f.SetValue('AUDIO4 remote-end FPC landing (H_AUDIO_2_R)'); bd.Add(f)
f.SetOrientationDegrees(180); f.SetPosition(V(35.75,2.5))
NET={'1':'RETURN_L_PORT','2':'RETURN_R_PORT','3':'SEND_T_PORT','4':'GND'}
for p in f.Pads():
    p.SetNet(b.net(NET[p.GetNumber()]))
    if p.GetNumber()=='4': p.SetPosition(V(39.5,2.5))   # ECO L-13: GND contact east of RETURN_L (same as main J3403)
# E-01: J301.6 -> HP_DET_B, isolate from GND copper, add R323 (DNP 0R) <=3 mm
j3=bd.FindFootprintByReference('J301')
for p in j3.Pads():
    if p.GetNumber()=='6': p.SetNet(b.net('HP_DET_B'))
mm=pcbnew.ToMM
r.SetFPID(pcbnew.LIB_ID('SmartVioV25','R_0603_1608Metric'))
r.SetReference('R323'); r.SetValue('0R'); bd.Add(r); r.Flip(r.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM); r.SetOrientationDegrees(90); r.SetPosition(V(70.6,11.0))
r.SetAttributes(r.GetAttributes()|pcbnew.FP_DNP)
for p in r.Pads(): p.SetNet(b.net({'1':'HP_DET_B','2':'GND'}[p.GetNumber()]))
print('R323',[(p.GetNumber(),round(mm(p.GetPosition().x),3),round(mm(p.GetPosition().y),3)) for p in r.Pads()])
for t in bd.GetTracks(): t.SetLocked(True)
for z in bd.Zones():
    if not z.GetIsRuleArea(): z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
bd.Save('/work/r4/pcb/SmartVio-audio-r4.kicad_pcb')
print([(p.GetNumber(),p.GetNetname(),pcbnew.ToMM(p.GetPosition().x)) for p in f.Pads()])
