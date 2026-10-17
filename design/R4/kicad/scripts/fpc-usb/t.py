import pcbnew
fp=pcbnew.FootprintLoad('/usr/share/kicad/footprints/Connector_FFC-FPC.pretty','Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal')
b=pcbnew.LoadBoard('/work/scripts/fpc/tmpl_fpc12.kicad_pcb')
b.Add(fp)
for rot in (90,-90):
  fp.SetOrientationDegrees(0); 
  if fp.GetLayer()==pcbnew.B_Cu: fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM)
  fp.SetPosition(pcbnew.VECTOR2I(0,0)); fp.Flip(fp.GetPosition(),pcbnew.FLIP_DIRECTION_TOP_BOTTOM); fp.SetOrientationDegrees(rot)
  d={p.GetNumber()+('' if p.GetNumber()!='MP' else str(i)):(round(pcbnew.ToMM(p.GetPosition().x),3),round(pcbnew.ToMM(p.GetPosition().y),3)) for i,p in enumerate(fp.Pads())}
  bb=fp.GetBoundingBox(False)
  print(rot, b.GetLayerName(fp.GetLayer()), d['1'],d['16'],[v for k,v in d.items() if k.startswith('MP')], 'fab bbox',[round(pcbnew.ToMM(v),2) for v in (bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom())])
  for g in fp.GraphicalItems():
    if g.GetLayer() in (pcbnew.B_Fab,) :
      pass
