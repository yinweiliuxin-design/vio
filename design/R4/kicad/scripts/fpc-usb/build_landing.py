import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/tmpl_fpc12.kicad_pcb')
f=b.footprint('J**','SmartVioV26:FPC_USB16_HotBar_Main_P0.70',value='FPC_USB16_HotBar_Main_P0.70')
f.SetAttributes(pcbnew.FP_SMD|pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES)
f.SetLibDescription('R4 L-10: main-board hot-bar landing for FPC-USB16 (16x 0.40x1.60 mm, pitch 0.70, F.Cu). Origin = pad-row centre (main local 36.75,1.25). FPC contacts 0.30x1.30 (+0.05/side, L-18). Pre-tin by paste print; FPC body envelope on F.Fab/F.CrtYd.')
f.Reference().SetPosition(V(0,-1.6)); f.Value().SetPosition(V(0,3.0)); f.Value().SetLayer(pcbnew.F_Fab)
for n in range(1,17):
    b.pad(f,str(n),(-5.25+0.7*(n-1),0),(0.40,1.60),['F.Cu','F.Mask','F.Paste'],None,mask_margin=0.05)
# FPC body envelope (flat on board): x -5.70..+6.55 rel (main local 31.05..43.3 incl. tolerance), y -0.9 (tail) .. +1.15 (Z-fold start, phys y5.6)
fp_rect(f,-5.70,-0.90,5.85,1.15,'F.Fab',0.1)
fp_rect(f,-5.95,-1.05,6.10,4.15,'F.CrtYd',0.05)   # includes Z-fold rise footprint to local y 5.4 (no parts >0.2 mm)
s=pcbnew.PCB_SHAPE(f); s.SetShape(pcbnew.SHAPE_T_CIRCLE); s.SetCenter(V(-5.25,-1.2)); s.SetEnd(V(-5.1,-1.2)); s.SetLayer(pcbnew.F_SilkS); s.SetWidth(FM(0.15)); f.Add(s)
b.savefp(f,'FPC_USB16_HotBar_Main_P0.70')
