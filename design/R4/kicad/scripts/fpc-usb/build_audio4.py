import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/tmpl_fpc12.kicad_pcb')
# flat = physical XY (main level); Z-fold R1 rise 2.1 at phys y25.1-27.1 -> flat y25.1-28.59 (incl 0.25 slack); beyond: flat = phys + 1.5
SY,TY=24.5,34.0; DX=-6.7; J0,J1=28.8,33.0; K=(-DX)/(J1-J0)
P={1:('RETURN_L_PORT',82.0),2:('RETURN_R_PORT',80.5),3:('SEND_T_PORT',79.0),4:('GND',83.5)}  # ECO L-13 order; matches main J3403 as placed (pad4 relocated east)
xj=lambda x0,y: x0-K*(y-J0)
outline=[(78.3,23.7),(84.2,23.7),(84.2,24.9),(84.5,24.9),(84.5,J0+(85.05-84.5)/K),(77.5,J0+(85.05-77.5)/K),(77.5,34.8),(71.6,34.8),(71.6,J0+(78.2-71.6)/K),(78.3,J0+(78.2-78.3)/K)]
b.poly_outline(outline)
f=b.footprint('FPC3402','SmartVioV26:FPC_AUDIO4',value='FPC-AUDIO4 custom flex (FPC_AUDIO4, DFM pending)')
f.SetAttributes(pcbnew.FP_SMD|pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES)
f.Reference().SetPosition(V(80.5,27.0)); f.Reference().SetLayer(pcbnew.F_Fab); f.Value().SetPosition(V(74.5,31.5)); f.Value().SetLayer(pcbnew.F_Fab); f.Value().SetTextSize(V(0.5,0.5)); f.Value().SetTextThickness(FM(0.08))
for n,(net,x) in P.items():
    b.pad(f,'S%d'%n,(x,SY),(0.75,0.75),['B.Cu','B.Mask'],net,mask_margin=0.1)
    b.pad(f,'T%d'%n,(x+DX,TY),(0.75,0.75),['B.Cu','B.Mask'],net,mask_margin=0.1)
fp_poly(f,outline,'F.CrtYd')
b.zone([(78.0,25.0),(85.2,25.0),(85.2,28.7),(78.0,28.7)],['F.Cu','B.Cu'],keepout=('vias','pads','copperpour'))   # Z-fold bend
for n,(net,x) in P.items():
    w=1.0 if n==4 else 0.2
    if n==4:
        yb=32.6; xb=xj(x,yb)
        b.track([(x,SY),(x,25.5)],0.6,'B.Cu',net); b.track([(x,25.5),(x,J0),(xb,yb)],w,'B.Cu',net); b.track([(xb,yb),(x+DX,J1),(x+DX,TY)],0.75,'B.Cu',net)
    else: b.track([(x,SY),(x,J0),(x+DX,J1),(x+DX,TY)],w,'B.Cu',net)
# F GND plane on the upper flat (not over contacts, not in bend), stitched to the B GND lane
gv=[]
for y in (29.4,31.0,32.6):
    gv.append((xj(83.5,y),y)); b.via(gv[-1],'GND')
b.zone([(78.0,28.7),(85.2,28.7),(85.2,33.2),(71.0,33.2),(71.0,28.7)],['F.Cu'],net='GND',clearance=0.2,minw=0.2)
b.rect(78.3,23.7,84.2,25.0,'User.1',0.05); b.rect(71.6,33.4,77.5,34.8,'User.1',0.05)
b.text('STIFF 0.2 PI (F side) both ends',(81.2,22.9),'User.1',0.5,0.08)
b.text('Z-fold R1 rise 2.1 (no vias)',(81.2,26.8),'Cmts.User',0.5,0.08)
b.text('FPC-AUDIO4 R4 - R4 ENGINEERING SAMPLE - NOT RELEASED unless DRC/parity 0',(78.0,36.0),'Cmts.User',0.5,0.08)
b.fill()
b.save('/work/r4/pcb/SmartVio-fpc-audio4-r4.kicad_pcb'); b.savefp(f,'FPC_AUDIO4')
print('vias',gv)
