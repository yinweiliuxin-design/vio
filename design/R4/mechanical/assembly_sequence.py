"""R4 assembly order and swept-insertion interference check (review M1 fix 4).

Every rigid part (or rigid board assembly) is moved along its insertion direction from a start pose
L mm outside to its final pose. The exact swept volume is A(start) U A(final) U prisms of every boundary
face of A(start) extruded by L along the direction (faces parallel to the direction add nothing).
Each piece is intersected (OCC BRepAlgoAPI_Common) with every already-installed solid; a common volume
>1e-4 mm3 is an interference. Designed elastic snaps are listed explicitly and pass only if their
interference depth across the deflection axis stays within the designed hook overlap.
Thin flexible items (FPCs, RF coax) are not swept; they are checked at the final pose by the pairwise
collision check in build_mechanics.py.
"""
import json,math,time
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Plane,GeomAbs_Cylinder
from OCP.gp import gp_Vec

def run(cq,parts,refs,BASE,light=None):
 light=light or {}
 def get(n):return light.get(n) or (parts[n] if n in parts else refs[n])
 R=lambda pre:sorted(n for n in refs if n.startswith(pre))
 cover_board=["cover_native_reference"]+R("OCC_cover_")+R("wheel_")+R("switch_")
 usb_board=["usb_reference","GCT_USB4120_body_max","J_USB_U_FH12_16_envelope"]+R("OCC_usb_")
 audio_board=["audio_native_reference"]+R("Kycon_vendor_")+R("OCC_audio_")
 main_board=["main_reference","U901_module_dimensioned_reference"]+R("OCC_main_")
 UP=(0,0,1);DN=(0,0,-1)
 # (step id, description, moving names, direction, length, elastic {installed: (axis, max depth, what)})
 COVER=[
  ("C1","5 keys inserted from inside, stem through Ø5.2, flange into recess",[f"button_{i}" for i in range(1,6)],UP,12,{}),
  ("C2","3 light pipes from inside, flange under roof",[f"lightpipe_{i}" for i in range(1,4)],UP,12,{}),
  ("C3","speaker LS901 into roof pocket (rim to pocket ceiling)",["speaker_working_nominal_reference"],UP,12,{}),
  ("C4","control (cover) board with switches, wheels, LEDs; 2 roof pins locate",cover_board,UP,15,{}),
  ("C5","PET backer films under keys 1-2 and speaker",["key_backer_insulator","speaker_backer_insulator"],UP,10,{}),
  ("C6","key backer bracket + 2 M1.6 screws (clamps control board)",["key_backer_bracket"]+R("SCREW_keybacker"),UP,15,{}),
  ("C7","USB board onto 4 roof posts (J401 into tight roof opening)",usb_board,UP,20,{}),
  ("C8","USB bracket + 3 M1.6 screws (board clamped between bracket and 4 roof posts)",["usb_bracket"]+R("SCREW_usb"),UP,20,{}),
  ("C10","audio board with 4 Kycon jacks, shoulders to roof pads",audio_board,UP,25,{}),
  ("C11","audio frame snaps over south blade lips and hangs on key-backer ledge / USB-bracket rail",["audio_load_frame"],UP,25,
   {"upper_cover":(1,.4,"blade lip 0.35 overlap, blade flexes +Y"),"key_backer_bracket":(1,.35,"web hook 0.3 over backer ledge, web flexes"),"usb_bracket":(1,.4,"web tab 0.35 over bracket rail, web flexes")}),
 ]
 CUP=[
  ("L1","floor film, NTC separator, RT1921",["battery_bottom_insulator","ntc_electrical_separator","RT1921_body_reference"],DN,25,{}),
  ("L2","battery pack (max envelope)",["battery_max_reference"],DN,25,{}),
  ("L3","battery top foam + top separator",["battery_top_foam","battery_top_separator"],DN,25,{}),
  ("L4","main board assembly snaps under 4 latch teeth",main_board,DN,25,{"lower_cup":(1,.5,"latch teeth 0.45 overlap, wall flexes")}),
  ("L5","main/audio dielectric film",["main_audio_dielectric_separator"],DN,25,{}),
 ]
 def faces_for(shape,d):
  out=[]
  for f in shape.Faces():
   s=BRepAdaptor_Surface(f.wrapped);t=s.GetType()
   if t==GeomAbs_Plane:
    n=s.Plane().Axis().Direction()
    if abs(n.X()*d[0]+n.Y()*d[1]+n.Z()*d[2])<1e-6:continue
   elif t==GeomAbs_Cylinder:
    a=s.Cylinder().Axis().Direction()
    if abs(abs(a.X()*d[0]+a.Y()*d[1]+a.Z()*d[2])-1)<1e-9:continue
   out.append(f)
  return out
 def bb(s):b=s.BoundingBox();return (b.xmin,b.ymin,b.zmin,b.xmax,b.ymax,b.zmax)
 def hit(a,b,e=1e-6):return not any(a[k+3]<=b[k]+e or b[k+3]<=a[k]+e for k in range(3))
 def common(a,b):
  op=BRepAlgoAPI_Common(a.wrapped,b.wrapped);op.Build()
  if not op.IsDone():return -1,None,[]
  r=cq.Shape.cast(op.Shape());v=r.Volume()
  return v,(r.BoundingBox() if v>1e-4 else None),[x.BoundingBox() for x in r.Solids() if x.Volume()>1e-4]
 def prism(f,vec):
  pr=BRepPrimAPI_MakePrism(f.wrapped,gp_Vec(vec.x,vec.y,vec.z)).Shape();s=cq.Shape.cast(pr)
  v=s.Volume()
  if abs(v)<1e-7:return None   # face parallel to the motion (e.g. B-spline side wall): sweeps no volume
  return s if v>0 else cq.Shape.cast(pr.Reversed())
 def sweep_check(step,installed,check_pairs=True):
  sid,desc,names,d,L,elastic=step;t0=time.time()
  vec=cq.Vector(*d)*L;res={"step":sid,"description":desc,"moving":names,"direction":list(d),"start_offset_mm":L,"pieces_tested":0,"booleans":0,"interferences":[],"elastic_snaps":[]}
  inst=[(n,get(n),bb(get(n))) for n in installed]
  for mn in names:
   m=get(mn);start=m.translate(vec*-1)
   sw=tuple(min(a,b) for a,b in zip(bb(start)[:3],bb(m)[:3]))+tuple(max(a,b) for a,b in zip(bb(start)[3:],bb(m)[3:]))
   near=[x for x in inst if hit(sw,x[2])]
   if not near:continue
   pieces=[start,m]+[q for q in (prism(f,vec) for f in faces_for(start,d)) if q is not None]
   res["pieces_tested"]+=len(pieces)
   for n,S,sb in near:
    worst=0;box=None;depth=0
    for p in pieces:
     if not hit(bb(p),sb):continue
     res["booleans"]+=1;v,b,sb_list=common(p,S)
     if n in elastic:
      for q in sb_list:depth=max(depth,[q.xlen,q.ylen,q.zlen][elastic[n][0]])
     if v<0:worst=-1;break
     if v>worst:worst=v
     if b is not None:
      box=b if box is None else box.add(b)
    if worst==0 or (worst>0 and worst<=1e-4):continue
    item={"moving":mn,"installed":n,"swept_common_mm3":round(worst,6)}
    if box is not None:item["common_bbox"]=[round(v,3) for v in (box.xmin,box.ymin,box.zmin,box.xmax,box.ymax,box.zmax)]
    if n in elastic and box is not None:
     ax,lim,what=elastic[n]
     item.update(designed_snap=what,deflection_axis="XYZ"[ax],interference_depth_mm=round(depth,3),allowed_mm=lim,ok=depth<=lim+1e-6)
     res["elastic_snaps"].append(item)
    else:res["interferences"].append(item)
  # final-pose clearance to installed solids within 1 mm (0 = designed contact)
  clear=[]
  for mn in names:
   m=get(mn);mb=bb(m);mb=(mb[0]-1,mb[1]-1,mb[2]-1,mb[3]+1,mb[4]+1,mb[5]+1)
   for n,S,sb in inst:
    if hit(mb,sb):
     try:dist=m.distance(S)
     except Exception:continue
     if dist<1.0:clear.append({"moving":mn,"installed":n,"min_clearance_mm":round(dist,3)})
  res["final_pose_clearances_below_1mm"]=sorted(clear,key=lambda c:c["min_clearance_mm"])
  res["pass"]=not res["interferences"] and all(e["ok"] for e in res["elastic_snaps"])
  res["seconds"]=round(time.time()-t0,1)
  print(sid,"pass" if res["pass"] else "FAIL",res["booleans"],"booleans",res["seconds"],"s",flush=True)
  return res
 steps=[];installed=["upper_cover"]
 for st in COVER:
  steps.append(sweep_check(st,installed));installed+=st[2]
 cover_side=list(installed)
 installed=["lower_cup"]
 for st in CUP:
  steps.append(sweep_check(st,installed));installed+=st[2]
 cup_side=list(installed)
 steps.append(sweep_check(("F1","closed cup subassembly pushed into cover subassembly (4 zero-play snaps); FPCs pre-soldered and folded, coax mated",cup_side,UP,30,
  {"upper_cover":(1,.4,"cup hooks 0.35 over blades (R4.1), cup wall flexes")}),cover_side))
 module=cover_side+cup_side
 steps.append(sweep_check(("F2","module lowered into instrument cavity, 4 ST2.2 wood screws",["lower_cup"],DN,25,{}),["instrument_mount_land_INFERRED_REFERENCE"]))
 order=[{"step":s["step"],"description":s["description"]} for s in steps]
 out={"schema":"SmartVio.R4.assembly-sequence-check","method":__doc__.strip(),"orientation":"Cover subassembly built roof-down: parts move world +Z (toward the roof). Cup subassembly built upright: parts move world -Z. Then cup subassembly moves +Z into cover; finished module moves -Z into the instrument cavity.",
  "cover_light_model":"upper cover checked without the 0.15 mm top legends (legends are >=0.3 mm from every opening, checked separately)" if "upper_cover" in light else "full",
  "not_swept_flexible":sorted(n for n in refs if n.startswith("FPC_") or n.startswith("RF_")),"order":order,"steps":steps,"pass":all(s["pass"] for s in steps)}
 (BASE/"assembly-sequence-check.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf8")
 return out
