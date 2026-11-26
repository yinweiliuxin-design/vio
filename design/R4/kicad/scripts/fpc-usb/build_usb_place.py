import sys,json; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/usb_base.kicad_pcb')
bd=b.b
def fp(ref): return bd.FindFootprintByReference(ref)
def place(ref,x,y,rot,side='F'):
    f=fp(ref)
    want=pcbnew.B_Cu if side=='B' else pcbnew.F_Cu
    if f.GetLayer()!=want: f.Flip(f.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
    f.SetOrientationDegrees(rot); f.SetPosition(V(x,y))
P=json.load(open('/work/scripts/fpc/usb_place.json'))
# new parts
io=pcbnew
zif=pcbnew.FootprintLoad('/usr/share/kicad/footprints/Connector_FFC-FPC.pretty','Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal')
zif.SetFPID(pcbnew.LIB_ID('Connector_FFC-FPC','Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal'))
zif.SetReference('J3412'); zif.SetValue('FH12-16S-0.5SH(55)'); bd.Add(zif)
d=pcbnew.FootprintLoad('/usr/share/kicad/footprints/Diode_SMD.pretty','D_SOD-123F'); d.SetFPID(pcbnew.LIB_ID('Diode_SMD','D_SOD-123F'))
d.SetReference('D401'); d.SetValue('SMF12A'); bd.Add(d)
NET={1:'USB_DATA_FAULT_N',2:'USB_DATA_DISABLE',3:'CC_FAULT_N',4:'V3D',5:'GND',6:'USB_DM_MCU',7:'USB_DP_MCU',8:'GND',9:'USB_5V_SAFE',10:'GND',11:'GND',12:'GND',13:'VBUS_RAW',14:'VBUS_RAW',15:'VBUS_RAW',16:'VBUS_RAW'}
for p in zif.Pads():
    if p.GetNumber().isdigit(): p.SetNet(b.net(NET[int(p.GetNumber())]))
for p in d.Pads(): p.SetNet(b.net({'1':'VBUS_RAW','2':'GND'}[p.GetNumber()]))
for ref,(x,y,rot,side) in P.items(): place(ref,x,y,rot,side)
# mechanical holes (pcb-interface-eco-R4.json, usb local) as board-only footprints with keep-outs
def hole(ref,xy,dia,ko,both=True):
    h=pcbnew.FOOTPRINT(bd); h.SetReference(ref); h.SetValue('NPTH %.1f KO %.1f'%(dia,ko) if dia else 'KEEPOUT %.1f F'%ko)
    h.SetFPID(pcbnew.LIB_ID('SmartVioV26','NPTH_D%.1f_KO%.1f'%(dia,ko) if dia else 'KEEPOUT_D%.1f_F'%ko))
    h.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES|pcbnew.FP_BOARD_ONLY)
    bd.Add(h); h.SetPosition(V(0,0)); xy0=xy; xy=(0,0)
    if dia: b.pad(h,'',xy,(dia,dia),['F.Cu','B.Cu','F.Mask','B.Mask'],None,shape='circle',attr='npth',drill=dia)
    z=pcbnew.ZONE(h); ls=pcbnew.LSET()
    for l in (['F.Cu','In1.Cu','In2.Cu','B.Cu'] if both else ['F.Cu']): ls.AddLayer(LAY[l])
    z.SetLayerSet(ls); o=z.Outline(); o.NewOutline()
    for i in range(32): o.Append(FM(xy[0]+ko/2*math.cos(2*math.pi*i/32)),FM(xy[1]+ko/2*math.sin(2*math.pi*i/32)))
    z.SetIsRuleArea(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowFootprints(False)
    h.Add(z)
    for lay in ('F.CrtYd',) if not dia else ('F.CrtYd','B.CrtYd'):
        s=pcbnew.PCB_SHAPE(h); s.SetShape(pcbnew.SHAPE_T_CIRCLE); s.SetCenter(V(*xy)); s.SetEnd(V(xy[0]+ko/2,xy[1])); s.SetLayer(LAY[lay]); s.SetWidth(FM(0.05)); h.Add(s)
    h.Reference().SetVisible(False); h.Value().SetVisible(False)
    b.savefp(h,h.GetFPID().GetLibItemName().wx_str()); h.SetPosition(V(*xy0))
    return h
hole('H401',(2,3),1.8,4.4); hole('H402',(22.3,3),1.8,4.4); hole('H403',(22.3,17),1.8,4.4); hole('KO401',(2,17),0,4.4,both=False)
bd.Save('/work/r4/pcb/SmartVio-usb-r4.kicad_pcb')
for ref in sorted(P)+['J3412','D401']:
    f=fp(ref); print(ref, bd.GetLayerName(f.GetLayer()), [(p.GetNumber(),p.GetNetname(),round(pcbnew.ToMM(p.GetPosition().x),3),round(pcbnew.ToMM(p.GetPosition().y),3)) for p in f.Pads()][:6])
