import sys; sys.path.insert(0,'/work/scripts/fpc')
from fpclib import *
b=B('/work/scripts/fpc/cover_base.kicad_pcb'); bd=b.b
REN={'H_COVER_1_R':('J3406','KEYS6 remote-end FPC landing (H_COVER_1_R)'),'H_COVER_2_R':('J3408','COVER6 remote-end FPC landing (H_COVER_2_R)'),'H_COVER_3_R':('J3410','POTS3 remote-end FPC landing (H_COVER_3_R)')}
for o,(n,v) in REN.items():
    f=bd.FindFootprintByReference(o); f.SetReference(n); f.SetValue(v)
# D851 under offset light pipe 2 (mechanical M11 recommendation)
bd.FindFootprintByReference('D851').SetPosition(V(34.7,20.7))
def mkfp(ref,libname,xy,pads,ko=None,ko_layers=('F.Cu','B.Cu')):
    h=pcbnew.FOOTPRINT(bd); h.SetReference(ref); h.SetValue(libname); h.SetFPID(pcbnew.LIB_ID('SmartVioV26',libname))
    h.SetAttributes(pcbnew.FP_EXCLUDE_FROM_BOM|pcbnew.FP_EXCLUDE_FROM_POS_FILES|pcbnew.FP_BOARD_ONLY); bd.Add(h); h.SetPosition(V(0,0))
    for shape,size,drill in pads:
        p=pcbnew.PAD(h); p.SetAttribute(pcbnew.PAD_ATTRIB_NPTH); ls=pcbnew.LSET()
        for l in ('F.Cu','B.Cu','F.Mask','B.Mask'): ls.AddLayer(LAY[l])
        p.SetLayerSet(ls)
        if shape=='oval':
            p.SetShape(pcbnew.PAD_SHAPE_OVAL); p.SetSize(pcbnew.F_Cu,V(*size)); p.SetDrillShape(pcbnew.PAD_DRILL_SHAPE_OBLONG); p.SetDrillSize(V(*size))
        else:
            p.SetShape(pcbnew.PAD_SHAPE_CIRCLE); p.SetSize(pcbnew.F_Cu,V(size,size)); p.SetDrillSize(V(size,size))
        h.Add(p); p.SetPosition(V(0,0))
    if ko:
        z=pcbnew.ZONE(h); ls=pcbnew.LSET()
        for l in ko_layers: ls.AddLayer(LAY[l])
        z.SetLayerSet(ls); o=z.Outline(); o.NewOutline()
        for i in range(36): o.Append(FM(ko/2*math.cos(2*math.pi*i/36)),FM(ko/2*math.sin(2*math.pi*i/36)))
        z.SetIsRuleArea(True); z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(True); z.SetDoNotAllowFootprints(False); h.Add(z)
    r=max((s if not isinstance(s,tuple) else max(s)) for _,s,_ in pads)/2+0.02   # courtyard = physical post/screw body
    for lay in ('F.CrtYd','B.CrtYd'):
        s=pcbnew.PCB_SHAPE(h); s.SetShape(pcbnew.SHAPE_T_CIRCLE); s.SetCenter(V(0,0)); s.SetEnd(V(r,0)); s.SetLayer(LAY[lay]); s.SetWidth(FM(0.05)); h.Add(s)
    h.Reference().SetVisible(False); h.Value().SetVisible(False)
    b.savefp(h,libname); h.SetPosition(V(*xy)); return h
# pcb-interface-eco-R4.json (cover)
mkfp('H901','NPTH_D1.8',(42.5,25),[('circle',1.8,1.8)])
mkfp('H902','NPTH_D1.8',(55.5,25),[('circle',1.8,1.8)])
for i,xy in enumerate([(88,8),(108.3,8),(88,22),(108.3,22)]):
    mkfp('H%d'%(903+i),'NPTH_D4.4_KO5.4',xy,[('circle',4.4,4.4)],ko=5.4)      # keep copper 0.5 away
mkfp('H907','NPTH_D1.5',(3.5,24.5),[('circle',1.5,1.5)])
mkfp('H908','SLOT_2.5x1.5',(144.5,24.5),[('oval',(2.5,1.5),None)])
# L-05 antenna window keep-out (F and B): no pour, tracks or vias
poly=[(107.0,31.0),(130.0,31.0),(130.0,35.0),(146.6,35.0),(146.6,47.6),(107.0,47.6)]
b.zone(poly,['F.Cu','B.Cu'],keepout=('copperpour','tracks','vias'))
# KEYS6 FPC alignment targets (FPC holes at flat (74.4,9.6),(60.0,9.6) -> cover y = 26.277 - flat y)
for x in (74.4,60.0):
    b.circle((x,16.677),0.5,'B.SilkS',0.12); b.circle((x,16.677),0.5,'B.Fab',0.1)
b.text('KEYS6 align',(67.2,18.2),'B.Fab',0.6,0.1,mirror=True)
for z in bd.Zones():
    if not z.GetIsRuleArea() and z.GetNetname()=='GND': z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
b.fill(); bd.Save('/work/r4/pcb/SmartVio-cover-r4.kicad_pcb')
