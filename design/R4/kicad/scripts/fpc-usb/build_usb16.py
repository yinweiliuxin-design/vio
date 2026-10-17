import sys,json; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/tmpl_fpc12.kicad_pcb')
NET={1:'USB_DATA_FAULT_N',2:'USB_DATA_DISABLE',3:'CC_FAULT_N',4:'V3D',5:'GND',6:'USB_DM_MCU',7:'USB_DP_MCU',8:'GND',9:'USB_5V_SAFE',
     10:'GND',11:'GND',12:'GND',13:'VBUS_RAW',14:'VBUS_RAW',15:'VBUS_RAW',16:'VBUS_RAW'}
# --- geometry (flat = physical XY at main level; Z-fold adds +2.712 in y beyond phys y 8.6; S-rise adds +1.08 in x beyond phys x 85.42)
XS=lambda n: 68.2+0.7*(n-1); YS=4.5
YT=lambda n: 24.462-0.5*(n-1)          # ZIF fingers, pin1 south (+y)
X0,X1=67.75,79.3; YTAIL=3.55; YB0,YB1=16.462,24.962; XEND=91.88
FX0,FX1=88.08,91.58                      # exposed finger copper (3.5 long, 0.3 to FPC end)
pts=[(X0,YTAIL),(X1,YTAIL),(X1,YB0-1.0)]
b.poly_outline  # (manual edges with fillet)
b.line((X0,YTAIL),(X1,YTAIL)); b.line((X1,YTAIL),(X1,YB0-1.0))
c=(X1+1.0,YB0-1.0); import math
b.arc((X1,YB0-1.0),(c[0]-math.cos(math.pi/4),c[1]+math.sin(math.pi/4)),(X1+1.0,YB0))
b.line((X1+1.0,YB0),(XEND,YB0)); b.line((XEND,YB0),(XEND,YB1)); b.line((XEND,YB1),(X0,YB1)); b.line((X0,YB1),(X0,YTAIL))
f=b.footprint('FPC3406','SmartVioV26:FPC_USB16',value='FPC-USB16 custom flex (FPC_USB16, DFM pending)')
f.SetAttributes(pcbnew.FP_SMD|pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES); f.SetAllowSolderMaskBridges(True)
f.Reference().SetPosition(V(73.45,20.0)); f.Reference().SetLayer(pcbnew.F_Fab)
f.Value().SetPosition(V(80.0,23.6)); f.Value().SetLayer(pcbnew.F_Fab); f.Value().SetTextSize(V(0.5,0.5)); f.Value().SetTextThickness(FM(0.08))
for n in range(1,17):
    b.pad(f,'S%d'%n,(XS(n),YS),(0.30,1.30),['B.Cu','B.Mask'],NET[n],mask_margin=0.05)
    b.pad(f,'T%d'%n,((FX0+FX1)/2,YT(n)),(FX1-FX0,0.30),['F.Cu','F.Mask'],NET[n],mask_margin=0.0)
fp_rect(f,87.98,YB0+0.15,XEND,YB1-0.15,'F.Mask',0.05,True)    # coverlay window over ZIF fingers
fp_poly(f,[(X0,YTAIL),(X1,YTAIL),(X1,YB0),(XEND,YB0),(XEND,YB1),(X0,YB1)],'F.CrtYd')
# --- no-via zones: Z-fold (flat y 5.45..11.5) and S-rise (flat x 82.3..86.7)
b.zone([(X0,5.45),(X1,5.45),(X1,11.5),(X0,11.5)],['F.Cu','B.Cu'],keepout=('vias','pads'))
b.zone([(82.3,YB0),(86.7,YB0),(86.7,YB1),(82.3,YB1)],['F.Cu','B.Cu'],keepout=('vias','pads'))
# --- B layer: all conductors single-layer through the Z-fold
W={1:0.15,2:0.15,3:0.15,4:0.25,6:0.15,7:0.15,9:0.25}
YV=12.5
for n,w in W.items():
    vx=XS(n)+(0.1 if n==1 else 0)
    b.track([(XS(n),YS),(XS(n),YV-0.6),(vx,YV)] if n==1 else [(XS(n),YS),(XS(n),YV)],w,'B.Cu',NET[n]); b.via((vx,YV),NET[n])
for n in (5,8): b.track([(XS(n),YS),(XS(n),12.0)],0.3,'B.Cu','GND')
b.track([(75.2,4.7),(75.2,12.0)],1.7,'B.Cu','GND')                       # S10-S12 merged
b.track([(77.65,5.05),(77.65,13.0)],2.4,'B.Cu','VBUS_RAW')                 # S13-S16 merged, 2.4 mm on B
for vx in (77.35,77.95,78.55):
    for vy in (12.2,12.8): b.via((vx,vy),'VBUS_RAW')                     # 6 vias B->F
# --- F layer: VBUS bus >=1.8 mm (ECO >=1.2 mm @18um)
b.track([(77.95,12.0),(77.95,17.712),(88.3,17.712)],1.8,'F.Cu','VBUS_RAW')
# --- F signal lanes
C=0.2
lens={}
def lane(n,w,bumps=0):
    x=XS(n)+(0.1 if n==1 else 0); y=YT(n); p=[(x,YV)]
    if bumps:
        yy=13.2
        for k in range(bumps):
            p+= [(x,yy),(x+0.5,yy+0.5),(x+0.5,yy+0.9),(x,yy+1.4)]; yy+=1.9
    p+=[(x,y-C),(x+C,y),(FX0+0.2,y)]
    b.track(p,w,'F.Cu',NET[n]); lens[n]=round(tracklen(p)+ (YV-YS),3)
for n,w in W.items(): lane(n,w,bumps=3 if n==7 else 0)
# --- GND fingers -> vias behind coverlay window (>=0.5 from opening, outside S-rise)
for n in (5,8,10,11,12):
    b.track([(FX0+0.2,YT(n)),(87.15,YT(n))],0.3,'F.Cu','GND'); b.via((87.15,YT(n)),'GND')
# --- GND planes
b.zone([(X0,YTAIL),(X1,YTAIL),(X1,YB0),(XEND,YB0),(XEND,YB1),(X0,YB1)],['B.Cu'],net='GND',clearance=0.15,minw=0.15)
# --- stiffeners / notes
b.rect(86.7,YB0,XEND,YB1,'User.1',0.05); b.text('STIFF PI on B side, total 0.30+/-0.03 at ZIF (Hirose) - CONFIRM',(86.0,26.0),'User.1',0.5,0.08)
b.rect(X0,YTAIL,X1,5.45,'User.1',0.05); b.text('STIFF 0.2 FR4/PI on F side (hot-bar end)',(73.45,2.8),'User.1',0.5,0.08)
b.text('FPC-USB16 R4 - R4 ENGINEERING SAMPLE - NOT RELEASED unless DRC/parity 0',(75.0,27.0),'Cmts.User',0.6,0.08)
b.text('Z-fold R1.5 (no vias)',(73.45,8.5),'Cmts.User',0.6,0.08); b.text('S-rise',(84.5,15.8),'Cmts.User',0.5,0.08)
b.text('USB16 R4',(73.5,19.0),'F.SilkS',0.8,0.12)
b.fill()
b.save('/work/r4/pcb/SmartVio-fpc-usb16-r4.kicad_pcb'); b.savefp(f,'FPC_USB16')
print(json.dumps(lens)); print('D+/D- mismatch',round(lens[7]-lens[6],3))
