"""Thin installed interconnects and their exact unfolded manufacturing outlines.

Design targets: two12um copper faces +25um PI +25um coverlay/adhesive
each face =99um nominal, <=110um accepted, static inside bend radius1.2.
The supplier must confirm this custom stack before ordering; no quote is implied.
"""
import math,json
from pathlib import Path
def build(cq,box,geo,BASE):
 R=1.255;T=.11;refs={};ledgers=[];flat=[]
 def fp(board,name):return next(v for v in geo['boards'][board]['components'] if v['ref']==name)
 assert fp('main','H_COVER_3_M')['side']=='F','Thin POTS3 source needs the explicit F-side ECO'
 origins={'main':[36.7,3.2],'cover':[0,0],'audio':[37.3,30]}
 KEYS6_DY=.30  # R4 ECO L-09: H_COVER_1_M moved +0.30 in Y so the KEYS6 riser clears the cup wall 0.49
 def pads(board,name):
  f=fp(board,name);o=origins[board];dy=KEYS6_DY if name=='H_COVER_1_M' else 0
  return {p['number']:[p['xy'][0]+o[0],p['xy'][1]+o[1]+dy,p['net']] for p in f['pads'] if p['number']}
 def prism(xy,z,thickness=T):
  return cq.Workplane('XY').polyline([(x,-y) for x,y in xy]).close().extrude(thickness).translate((0,0,z-thickness/2)).val()
 def curved_strip(x,width,y,z,r=R,upper=False):
  # Closed annular sector extruded across ribbon width. Exact constant radius.
  points=[]
  for radius,angles in [(r+T/2,[i*math.pi/2/48 for i in range(49)]),(r-T/2,[i*math.pi/2/48 for i in range(48,-1,-1)])]:
   for angle in angles:
    yy=y+radius*math.sin(angle)
    zz=z+r-radius*math.cos(angle) if not upper else z+radius*math.cos(angle)
    points.append((yy,zz))
  # LogicalY-to-world construction: extrude an actual YZ cross-section in X.
  wire=cq.Wire.makePolygon([cq.Vector(x-width/2,-yy,zz) for yy,zz in points],close=True)
  return cq.Solid.extrudeLinear(wire,[],cq.Vector(width,0,0))
 def make(name,fromref,toboard,toref,source_z,target_z,neck_center,neck_width,top_polygons,north=False):
  ps=pads('main',fromref);pt=pads(toboard,toref);n=len(ps);assert set(ps)==set(pt)
  assert all(ps[k][2]==pt[k][2] for k in ps)
  physical_source={k:v[:] for k,v in ps.items()};physical_target={k:v[:] for k,v in pt.items()}
  if north:
   ps={k:[v[0],-v[1],v[2]] for k,v in ps.items()};pt={k:[v[0],-v[1],v[2]] for k,v in pt.items()}
  source_x=sum(v[0] for v in ps.values())/n;source_y=sum(v[1] for v in ps.values())/n
  start_y=-4.3-KEYS6_DY if north else 44.30 if name=='POTS3' else 44.65;end_y=start_y+R
  lower_end=source_z+R;upper_start=target_z-R
  assert upper_start>lower_end
  source_min=min(v[0] for v in ps.values())-.75;source_max=max(v[0] for v in ps.values())+.75
  if north:
   # R4: tail 0.3 past the moved pad row (clears C605 at y7.48 after the +0.30 ECO shift)
   lower_poly=[(source_min,source_y-1.2),(source_max,source_y-1.2),(source_max,start_y),(source_min,start_y)]
  elif fromref=='H_COVER_3_M':
   # Native source moves toF. A flat L brings the narrow bend clear of the x67 latch.
   lower_poly=[(source_min,source_y-.75),(source_max,source_y-.75),(source_max,source_y-.4),
      (neck_center+neck_width/2,source_y-.4),(neck_center+neck_width/2,start_y),(source_min,start_y)]
  else:
   lower_poly=[(source_min,source_y-1.3),(source_max,source_y-1.3),(source_max,start_y),(source_min,start_y)]
  lower_width=source_max-source_min if name in ['AUDIO6','COVER6'] else neck_width
  upper_width=lower_width if name=='AUDIO6' else neck_width
  taper=3.2 if name=='COVER6' else 0
  sh=prism(lower_poly,source_z)
  sh=sh.fuse(curved_strip(neck_center,lower_width,start_y,source_z))
  if taper:
   points=[cq.Vector(neck_center-lower_width/2,-end_y+T/2,lower_end),cq.Vector(neck_center+lower_width/2,-end_y+T/2,lower_end),
     cq.Vector(neck_center+neck_width/2,-end_y+T/2,lower_end+taper),cq.Vector(neck_center-neck_width/2,-end_y+T/2,lower_end+taper)]
   sh=sh.fuse(cq.Solid.extrudeLinear(cq.Wire.makePolygon(points,close=True),[],cq.Vector(0,-T,0)))
  width=neck_width if taper else upper_width
  sh=sh.fuse(box(neck_center-width/2,end_y-T/2,lower_end+taper,width,T,upper_start-lower_end-taper))
  # Upper quarter is reflected to return toward the instrument interior.
  # It joins vertical at y=start+R,z=target-R and ends y=start,z=target.
  up=curved_strip(neck_center,upper_width,start_y,upper_start,upper=True)
  sh=sh.fuse(up)
  for poly in top_polygons:sh=sh.fuse(prism(poly,target_z))
  for board,refname,contacts,plane_z in [('main',fromref,ps,source_z),(toboard,toref,pt,target_z)]:
   face=fp(board,refname)['side'];surface={'main':(-11.75,-12.55),'audio':(-9.65,-10.65),'cover':(.5,.1)}[board][0 if face=='F' else 1]
   for point in contacts.values():
    zmin=min(surface,plane_z-T/2);zmax=max(surface,plane_z+T/2)
    sh=sh.fuse(box(point[0]-.45,point[1]-.45,zmin,.9,.9,zmax-zmin))
  sh=sh.clean();assert sh.isValid() and len(sh.Solids())==1,(name,len(sh.Solids()))
  if north:sh=sh.mirror('XZ')
  refs['FPC_'+name+'_installed_reference']=sh
  straight=upper_start-lower_end;unfold_end=start_y+math.pi*R+straight
  def unroll_top(poly):return [(x,unfold_end+start_y-y) for x,y in poly]
  # Flat board consists of source landing, straight bend corridor, and the
  # mirrored top planar regions. Contact positions derive from actual native pads.
  first_end=start_y+math.pi*R/2
  if taper:
   bridge=[(neck_center-lower_width/2,start_y),(neck_center+lower_width/2,start_y),
    (neck_center+lower_width/2,first_end),(neck_center+neck_width/2,first_end+taper),
    (neck_center+neck_width/2,unfold_end),(neck_center-neck_width/2,unfold_end),
    (neck_center-neck_width/2,first_end+taper),(neck_center-lower_width/2,first_end)]
  else:bridge=[(neck_center-upper_width/2,start_y),(neck_center+upper_width/2,start_y),(neck_center+upper_width/2,unfold_end),(neck_center-upper_width/2,unfold_end)]
  flat_offset=20.0 if north else 0.0
  polygons=[[(x,y+flat_offset) for x,y in poly] for poly in [lower_poly,bridge]+[unroll_top(p) for p in top_polygons]]
  flatbody=prism(polygons[0],0)
  for poly in polygons[1:]:flatbody=flatbody.fuse(prism(poly,0))
  flatbody=flatbody.clean()
  assert flatbody.isValid() and len(flatbody.Solids())==1
  face=cq.Workplane('XY').newObject([flatbody]).faces('<Z').val()
  def loop(wire):
   pairs=[([v.X,-v.Y] for v in edge.Vertices()) for edge in wire.Edges()]
   pairs=[list(v) for v in pairs];remaining=[v for v in pairs if len(v)==2]
   start=remaining[0][0];points=[start];current=start
   while remaining:
    index=next(i for i,q in enumerate(remaining) if math.dist(current,q[0])<1e-6 or math.dist(current,q[1])<1e-6)
    pair=remaining.pop(index);current=pair[1] if math.dist(current,pair[0])<1e-6 else pair[0];points.append(current)
   assert math.dist(points[0],points[-1])<1e-6
   return points[:-1]
  contours=[loop(face.outerWire())]+[loop(w) for w in face.innerWires()]
  source_contacts=[{'number':k,'net':v[2],'xy':[v[0],v[1]+flat_offset]} for k,v in sorted(ps.items())]
  target_contacts=[{'number':k,'net':v[2],'xy':[v[0],unfold_end+start_y-v[1]+flat_offset]} for k,v in sorted(pt.items())]
  entry={'id':name,'from_ref':fromref,'to_board':toboard,'to_ref':toref,'nominalFinishedThicknessMm':.099,
   'acceptedMaximumThicknessMm':.11,'staticInsideRadiusMinimumMm':1.2,'installedCenterRadiusMm':R,
   'sourcePlaneZ':source_z,'targetPlaneZ':target_z,'neckCenterX':neck_center,'neckWidthMm':neck_width,'lowerBendWidthMm':lower_width,'upperBendWidthMm':upper_width,'verticalTaperLengthMm':taper,
   'straightRiseMm':straight,'unfoldEndY':unfold_end+flat_offset,'flatPolygons':polygons,'flatContours':contours,'sourceContacts':source_contacts,
   'targetContacts':target_contacts,'bendNoViaAreas':[[neck_center-lower_width/2,start_y+flat_offset,neck_center+lower_width/2,start_y+math.pi*R/2+flat_offset],
      [neck_center-upper_width/2,unfold_end-math.pi*R/2+flat_offset,neck_center+upper_width/2,unfold_end+flat_offset]],
   'physicalTestStatus':'NOT_RUN','supplierStackConfirmation':'REQUIRED_BEFORE_ORDER',
   'replacesOrdinaryWireSpec':True,'staticInstallationOnly':True}
  entry.update(northMirror=north,flatNativeOffsetMm=[0,flat_offset],physicalSourceContacts=physical_source,physicalTargetContacts=physical_target)
  ledgers.append(entry);flat.append(entry)
 # AUDIO6 source isB, targetF. Narrow top neck avoids all four jack bodies.
 make('AUDIO6','H_AUDIO_1_M','audio','H_AUDIO_1_R',-12.605,-9.57,83.2,3.0,
  [[(78.7,44.65),(87.7,44.65),(87.7,41.8),(78.7,41.8)],
   [(54.1,41.8),(87.7,41.8),(87.7,44.8),(54.1,44.8)],
   [(54.1,32.5),(57.1,32.5),(57.1,44.8),(54.1,44.8)]])
 # COVER6 goes around the right of the actual jack bodies, below the cover PCB.
 make('COVER6','H_COVER_2_M','cover','H_COVER_2_R',-12.605,.02,73.95,3.0,
  [[(72.45,44.65),(75.45,44.65),(75.45,41.6),(72.45,41.6)],
   [(72.45,41.6),(111.0,41.6),(111.0,44.6),(72.45,44.6)],
   [(108.0,26.2),(111.0,26.2),(111.0,44.6),(108.0,44.6)],
   [(85.7,26.2),(111.0,26.2),(111.0,29.2),(85.7,29.2)],
   [(85.4,24.2),(97.0,24.2),(97.0,29.2),(85.4,29.2)]])
 # POTS3 requires the small native front-side termination ECO described in ledger.
 make('POTS3','H_COVER_3_M','cover','H_COVER_3_R',-11.47,-.20,77.0,1.4,
  [[(76.3,23.8),(77.7,23.8),(77.7,44.30),(76.3,44.30)],
   [(70.7,23.8),(81.0,23.8),(81.0,27.0),(70.7,27.0)]])
 make('KEYS6','H_COVER_1_M','cover','H_COVER_1_R',-11.47,.02,40.0,2.8,
  [[(38.6,-4.6),(41.4,-4.6),(41.4,-17.5),(38.6,-17.5)],
   [(38.6,-12.5),(84.5,-12.5),(84.5,-17.5),(38.6,-17.5)]],north=True)
 (BASE/'reference/flex-installed-and-unfolded.json').write_text(json.dumps({'revision':'R4 (KEYS6 source +0.30 per ECO L-09; flat pattern un-mirroring is PCB scope)','designs':ledgers,
  'nativeECORemaining':[],
  'stack':[{'material':'copper','thicknessUm':12},{'material':'PI','thicknessUm':25},{'material':'copper','thicknessUm':12},
           {'material':'coverlay+adhesive each face','thicknessUm':25,'faces':2}],
  'status':'GEOMETRY_AND_NATIVE_FLEX_ROUTING_REVIEW_REQUIRED','physicalTests':0},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return refs
