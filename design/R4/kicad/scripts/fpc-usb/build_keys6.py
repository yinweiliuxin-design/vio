import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
R3T=40.322698780255195; R3TOP0=36.822698780255195; R3TOP1=41.822698780255195
TY=50.6-R3T; Y0=50.6-R3TOP1; Y1=50.6-R3TOP0   # 10.2773, 8.7773, 13.7773
b=B('/work/scripts/fpc/tmpl_fpc12.kicad_pcb')
TAIL=37.45  # mechanical CHANGES.md: tail 0.3 past moved pad row (C605 at y7.48)
outline=[(36.9,TAIL),(41.4,TAIL),(41.4,Y1),(84.5,Y1),(84.5,Y0),(38.6,Y0),(38.6,34.6),(36.9,34.6)]
b.poly_outline(outline)
f=b.footprint('FPC3403','SmartVioV26:FPC_KEYS6_R4',value='FPC-KEYS6 custom flex (FPC_KEYS6, DFM pending)')
f.SetAttributes(pcbnew.FP_SMD|pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES)
f.Reference().SetPosition(V(60,12.0)); f.Reference().SetLayer(pcbnew.F_Fab)
f.Value().SetPosition(V(60,9.6)); f.Value().SetLayer(pcbnew.F_Fab); f.Value().SetTextSize(V(0.6,0.6))
# S contacts (main H_COVER_1_M, R4 phys +30 in y); row1 0.75x0.60, row2 0.75x0.55 (tail edge 0.30 clearance)
S={'S1':('FX_RAW',37.65,35.5,0.6),'S2':('GND',39.15,35.5,0.6),'S3':('KEY_BT',40.65,35.5,0.6),
   'S4':('KEY_FX',37.65,36.875,0.55),'S5':('KEY_MIX',39.15,36.875,0.55),'S6':('KEY_MODE',40.65,36.875,0.55)}
for k,(n,x,y,h) in S.items(): b.pad(f,k,(x,y),(0.75,h),['B.Cu','B.Mask'],n,mask_margin=0.1)
T=['FX_RAW','GND','KEY_BT','KEY_FX','KEY_MIX','KEY_MODE']
for i,n in enumerate(T): b.pad(f,'T%d'%(i+1),(76.25+1.5*i,TY),(0.75,0.75),['B.Cu','B.Mask'],n,mask_margin=0.1)
# courtyard = outline
for i in range(len(outline)):
    s=pcbnew.PCB_SHAPE(f); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*outline[i])); s.SetEnd(V(*outline[(i+1)%len(outline)])); s.SetLayer(pcbnew.F_CrtYd); s.SetWidth(FM(0.05)); f.Add(s)
# bend no-via corridors (ECO L-09)
for y0,y1 in [(50.3-17.671349390127595,34.6),(50.3-28.62269878025519,50.3-26.651349390127596)]:
    b.zone([(38.6,y0),(41.4,y0),(41.4,y1),(38.6,y1)],['F.Cu','B.Cu'],keepout=('vias','pads'))
W=0.15
# --- B.Cu routing (contact layer) ---
b.track([(37.65,35.5),(37.65,34.975),(38.975,34.975),(38.975,10.85),(76.25,10.85),(76.25,TY)],W,'B.Cu','FX_RAW')
b.track([(39.35,35.5),(39.35,33.9)],0.25,'B.Cu','GND')                     # neck-down inside S2 escape
b.track([(39.5,33.9),(39.5,11.5),(77.75,11.5),(77.75,TY)],0.6,'B.Cu','GND')  # 0.6 mm full length (L-09/L-15)
b.track([(39.15,36.875),(39.15,36.2),(39.75,36.2),(39.75,34.6),(40.05,34.3),(40.05,12.1),(82.25,12.1),(82.25,TY)],W,'B.Cu','KEY_MIX')
b.track([(40.65,36.875),(40.65,36.2),(40.05,36.2),(40.05,34.9),(40.35,34.6),(40.35,12.4),(83.75,12.4),(83.75,TY)],W,'B.Cu','KEY_MODE')
b.track([(40.7,35.5),(40.7,12.8),(43.0,12.8)],W,'B.Cu','KEY_BT')
b.via((43.0,12.8),'KEY_BT')
b.track([(43.0,12.8),(79.25,12.8),(79.25,11.6)],W,'F.Cu','KEY_BT')
b.via((79.25,11.6),'KEY_BT'); b.track([(79.25,11.6),(79.25,TY)],W,'B.Cu','KEY_BT')
b.track([(37.65,36.875),(38.4,36.2)],W,'B.Cu','KEY_FX')
b.via((38.4,36.2),'KEY_FX')
b.track([(38.4,36.2),(39.0,35.6),(40.0,34.6),(40.0,13.2),(80.75,13.2),(80.75,11.6)],W,'F.Cu','KEY_FX')
b.via((80.75,11.6),'KEY_FX'); b.track([(80.75,11.6),(80.75,TY)],W,'B.Cu','KEY_FX')
# stiffeners (user layer) and alignment holes
b.rect(36.9,34.6,41.4,TAIL,'User.1',0.05)
b.text('STIFF 0.2 PI (F side)',(39.15,38.4),'User.1',0.5,0.08)
b.rect(74.0,Y0,84.5,Y1,'User.1',0.05)
b.text('STIFF 0.2 PI (F side) over T1-T6 + align holes',(70.0,14.6),'User.1',0.5,0.08)
for xy in [(74.4,9.6),(60.0,9.6)]: b.pad(f,'',xy,(1.0,1.0),['F.Cu','B.Cu','F.Mask','B.Mask'],None,shape='circle',attr='npth',drill=1.0)
b.text('SmartVio KEYS6 R4 (L-09) - R4 ENGINEERING SAMPLE - NOT RELEASED unless DRC/parity 0',(61.0,15.6),'Cmts.User',0.6,0.08)
b.text('KEYS6-R4',(55.0,11.0),'F.SilkS',0.8,0.12)
b.save('/work/r4/pcb/SmartVio-fpc-keys6-r4-bus.kicad_pcb')
b.savefp(f,'FPC_KEYS6_R4')
