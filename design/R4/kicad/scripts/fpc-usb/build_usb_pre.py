import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/r4/pcb/SmartVio-usb-r4.kicad_pcb'); bd=b.b
def T(pts,w,l,n):
    for t in b.track(pts,w,l,n): t.SetLocked(True)
def Vv(xy,n,s=0.6,d=0.3,l1='F.Cu',l2='B.Cu'):
    v=b.via(xy,n,s,d,l1,l2); v.SetLocked(True); return v
VB='VBUS_RAW'
for (px,py),(vx,vy) in [((10.75,3.135),(10.0,3.135)),((10.75,4.865),(10.0,4.865)),((13.25,3.135),(14.0,3.135)),((13.25,4.865),(14.0,4.865))]:
    T([(px,py),(vx,vy)],0.3,'F.Cu',VB); Vv((vx,vy),VB)
# CC1 escape A5 -> via (column x10 has no connector pads)
T([(11.25,3.135),(11.25,3.6),(10.85,4.0),(10.0,4.0)],0.15,'F.Cu','CC1_PORT'); Vv((10.0,4.0),'CC1_PORT')
# CC_VBIAS: U1401.A2 -> C1401.1 (<=1 mm, L-11)
T([(16.2,8.8),(15.4,8.8),(14.8,9.4),(14.8,9.55)],0.2,'F.Cu','CC_VBIAS')
# DP: A6<->B6 on F between rows, then south to FL1501.1
T([(11.75,3.135),(11.75,3.75),(12.25,4.25),(12.25,4.865),(12.25,7.0),(12.0,7.25),(12.0,7.675)],0.2,'F.Cu','USB_DP_CONN')
# DM: B7 south to FL1501.2; A7 tie through In2 (keeps In1 solid)
T([(11.75,4.865),(11.75,5.6),(11.0,6.35),(11.2,6.55),(11.2,7.675)],0.2,'F.Cu','USB_DM_CONN'); Vv((11.0,6.35),'USB_DM_CONN')
T([(12.25,3.135),(12.25,2.55),(12.5,2.3),(13.05,2.3),(13.2,2.15)],0.2,'F.Cu','USB_DM_CONN'); Vv((13.2,2.15),'USB_DM_CONN')
T([(13.2,2.15),(11.0,6.35)],0.2,'In2.Cu','USB_DM_CONN')
# D401 anode GND via, C401 GND via
T([(12.0,2.6),(11.0,1.6)],0.5,'B.Cu','GND'); Vv((11.0,1.6),'GND')
T([(16.9,3.15),(16.9,2.2)],0.5,'B.Cu','GND'); Vv((16.9,2.2),'GND')
# VBUS copper: B and In2 zones from J401 to ZIF pins 13-16, plus stitching vias
poly=[(9.35,2.45),(14.6,2.45),(14.6,3.7),(17.5,3.7),(17.5,5.45),(13.7,5.45),(13.7,6.0),(12.3,6.0),(12.3,5.45),(9.35,5.45),(9.35,3.75),(8.05,3.75),(8.05,11.0),(5.3,11.0),(5.3,2.45)]
for lay,pri in (('B.Cu',5),('In2.Cu',5)):
    b.zone(poly,[lay],net=VB,clearance=0.2,minw=0.2,priority=pri)
pass
# board-edge routing keep-out frame (edge clearance 0.25 + margin) so the autorouter respects it
W_,H_=24.0,22.0; e=0.32
for r in [(0,0,W_,e),(0,H_-e,W_,H_),(0,0,e,H_),(W_-e,0,W_,H_)]:
    b.zone([(r[0],r[1]),(r[2],r[1]),(r[2],r[3]),(r[0],r[3])],['F.Cu','In1.Cu','In2.Cu','B.Cu'],keepout=('tracks','vias'))
mv=b.via((16.6,8.8),'GND',0.25,0.1,'F.Cu','In1.Cu'); mv.SetViaType(pcbnew.VIATYPE_MICROVIA); mv.SetLocked(True)
for z in bd.Zones():
    if not z.GetIsRuleArea() and z.GetNetname()=='GND': z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
bd.Save('/work/r4/pcb/SmartVio-usb-r4.kicad_pcb')
