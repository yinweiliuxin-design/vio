"""SmartVio R4 real prototype mechanics. Units mm.
Logical drawing Y is PCB Y (down). STEP world coordinates are X, -Y, Z.
Datum A=instrument mounting plane. No alteration to original instrument cavity.
CadQuery2.8/OCP7.9. Engineering root (project/, verification/) = env SMARTVIO_ENG or BASE.parent.
R4 (review M1..M18, DECISIONS Q3/Q4/Q6): upper cover no longer carries any board tray; USB/sensor
carrier, key backer and audio frame are separate parts installed in a swept-checked order
(see cad/assembly_sequence.py and assembly-sequence-check.json).
"""
from pathlib import Path
import sys,os,json,hashlib,math,datetime
BASE=Path(__file__).resolve().parents[1]
ENG=Path(os.environ.get("SMARTVIO_ENG",str(BASE.parent))).resolve()
assert (ENG/"project").is_dir() and (ENG/"verification").is_dir(),"set SMARTVIO_ENG to the engineering root"
sys.path.insert(0,str(Path(__file__).resolve().parent))
import cadquery as cq
OUT=BASE/"cad";OUT.mkdir(exist_ok=True)
ECO=json.loads((BASE/"pcb-interface-eco.json").read_text("utf8"))
FONT=os.environ.get("SMARTVIO_FONT","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
PAR={
 "version":"R4 prototype engineering candidate","units":"mm","manufacturing_release":False,
 "datum":"A instrument mounting surface Z0; STEP Y=-logical drawing Y",
 "upper_outline":[148,49],"upper_corner_radius":2.0,"upper_roof_top":3.8,"upper_roof_thickness":1.3,"upper_side_wall":1.0,
 "cup_outline":[77.0,45.0],"cup_origin":[35.5,2.0],"cup_bottom":-20.8,"cup_floor_top":-20.25,"cup_floor_thickness":0.55,"cup_floor_note":"R4.1b: floor top -20.30 -> -20.25 (battery bottom insulator 0.10 -> 0.05 PET; battery bottom stays -20.20) and floor 0.60 -> 0.55: cup bottom -20.90 -> -20.80 closes worst-case total height (tolerance-stack chain 1)","cup_wall":0.8,"cup_corner_radius":1.2,"cup_inner_corner_radius":1.2,
 "main_origin":[36.7,3.2],"main_bottom":-12.55,"main_thickness":0.8,"main_xy":[74.6,42.6],"main_B_max_assembled_under_battery":1.05,
 "main_ledge_overlap":1.0,"main_xy_locating_gap":0.05,"main_latch_z_gap":0.0,
 "audio_origin":[37.3,30],"audio_pcb_top":-9.65,"audio_pcb_thickness":1.0,"jack_mouth_top":3.85,"jack_seat_to_mouth_nominal":13.5,
 "jack_shoulder_Z":1.45,"jack_shoulder_gap":0.005,"jack_shoulder_gap_note":"zero-gap design; 0.005 CAD offset only avoids coplanar boolean slivers on the vendor B-spline face","audio_frame_bottom":-11.15,"audio_frame_thickness":0.5,
 "usb_origin":[86,5],"usb_clamp_post":{"xy":[88,21.8],"lower_dia":3.6,"cover_hole_dia":4.0,"why":"R4.1c: (88,22) Ø4.4 left 0.35 to J3408 (COVER6) pads on the cover board; now 0.75 to the pads and 0.68 to the PWR_PB track"},"usb_top":-3.3,"usb_thickness":1.0,"sensor_board":"eliminated (ECO L-12, TMP117 on main B side)",
 "cover_pcb_top":.5,"cover_pcb_thickness":.4,
 "pack_box":[40,7.25,-20.2,92,41.75,-14.8],"battery_swell_Z_design_allowance":1.0,"battery_guide_gap":0.25,
 "battery_top_foam":"1.0 mm PORON 4701-30 class strips, fills swell allowance; ~50% compressible",
 "pack_bottom_insulation":.05,"pack_top_insulation":.1,"screw_xy":[[5.3,5.3],[142.7,5.3],[5.3,43.7],[142.7,43.7]],
 "screw_through":2.5,"screw_counterbore":4.5,"screw_seat_z":1.7,"screw_passing_boss_dia":5.2,"screw_boss_dia_above_cover_pcb":6.5,
 "instrument_screw":"ST2.2x6.5 A2 stainless pan-head wood screw (non-magnetic), pilot 1.6x5 in wood, 0.15 N.m; threaded insert in wood preferred",
 "internal_screw":"M1.6 thread-forming screw for plastics (PT/WN1452 type) into POM pilot 1.3; production PC/ABS: M1.6 heat-set brass insert",
 "button_switch_top_max_Z":2.15,"button_switch_top_nominal_Z":2.0,"button_initial_gap_at_max":.05,"switch_travel":0.25,
 "button_hole_dia":5.2,"button_stem_dia":5.0,"button_flange_dia":6.2,"button_flange_recess_dia":6.5,"button_top_Z":3.85,
 "button_fit_basis":"SKQGABE010 h1.5 +0.15/-0, travel0.25, 1.57N (native-components.json). Nub designed to max switch top2.15+0.05; trim stock blank to measured switch top+0.05",
 "wheel_window_dia":15.2,"wheel_thumb_notch":"north-edge notch 12 wide, floor Z1.5: knurled rim stands 1.5 above local floor (wheel top Z3.0 fixed by board stack)",
 "legend_depth":0.15,"legend_font":Path(FONT).name,
 "snap_stations_x":[67,102],"snap_beam":[8,.8,4],"snap_hook_overlap":.35,"snap_window_z_play":0.04,
 "snap_blade_leadin":0.55,"snap_locating_rib":{"on":"lower_cup inner wall at each snap flap root (4x)","height":0.15,"clearance_to_blade_face":0.05,"x_from_station":[-3.8,-2.8],"z":[-4.6,-1.2],"top_leadin":0.3,
  "why":"R4.1 tolerance stack: without ribs the cup floats +/-0.2 in Y between the blades and one-side hook engagement falls to 0.05 nominal / <0 worst case. Ribs on the cover blades were rejected: they would need wider cover-PCB snap slots (C4 sweep hit)"},
 "pickup_entry_xy":[60.6,4.6],
 "pickup_entry_xy_status":"PLACEHOLDER. TODO(measure): original pickup-wire hole of the violin (DECISIONS addendum 2026-10-15: no new hole is drilled in the violin). Convert: X = 258 - u (u = distance from tail metal datum, mm), Y = 24.5 + v (v = offset from module centre line toward the Y=0 / wheel-notch edge negative). Then set this value and rebuild.",
 "pickup_entry_mode":"slot",
 "pickup_entry_hole_dia":3.0,
 "pickup_entry_slot":[10.0,3.0],"pickup_entry_slot_axis_deg":0.0,
 "pickup_entry_slot_note":"first-sample default: 10 x 3 slot along X (instrument length) centred on pickup_entry_xy; accepts the original hole anywhere within +/-3.5 mm along X; across (Y) the 3.0 width only accepts the cable (<= dia 2.6). Must stay in the north cable strip Y 3.1..6.3 (cup wall 2.8 / battery guide 6.5) so the cable reaches the main-board notch x58.8-62.4 and J101",
 "usb_face_pocket":[13.0,7.4],"usb_face_pocket_floor_Z":2.85,"usb_opening_collar":{"wall":0.6,"z":[1.8,2.5],"why":"R4.1b: pocket depth 0.80 -> 0.95 closes worst-case USB-C depth with GCT +/-0.25 (chain 7d); collar restores the lateral bearing wall of the opening (0.35 roof + 0.7 collar)"},"usb_face_pocket_note":"R4.1 widened 12.0 -> 13.0: USB Type-C plug overmold reference max 12.35 x 6.5 must reach the receptacle face 0.6 below roof top (tolerance-stack.md chain 7)",
 "audio_frame_web_variants":[0.40,0.50,0.60],"audio_frame_selective_fit":"jack shoulder-pad loop is over-constrained (tolerance-stack.md chain 6); first sample: pick web 0.40/0.50/0.60 + 0.05 PET shims by measured gap",
 "upper_and_cup_join":"4 zero-play snaps (window=hook+0.04); four upper screws attach instrument",
 "nominal_total_height":24.75,"total_height_limit":25.0,"nonwheel_outward_limit":5,
 "process":"CNC POM-C for dimensional prototype, or PA12 additive blank with post-machined precision datum/ledges; unverified fatigue/acoustics are first-article tests",
 "factory_tuning":"Main shims (ledge-shaped set) only when measured latch gap >0; do not compress pack or machine vendor parts",
 "pending":"Native board ECO (holes listed in pcb-interface-eco-R4.json) and final assembly collision rerun after board routing; worst-case/RSS stack done in tolerance-stack.md (R4.1): chains 4 (keys) and 6 (jack loop) close only with first-sample selective fit; Kycon/GCT title-block tolerances still to be obtained; pickup_entry_xy awaits measurement"
}
(BASE/"parameters.json").write_text(json.dumps(PAR,ensure_ascii=False,indent=2),encoding="utf8")
def box(x,y,z,w,h,d):return cq.Workplane("XY").box(w,h,d,centered=(False,False,False)).translate((x,-y-h,z)).val()
def rr(x,y,z,w,h,d,r):
 s=cq.Workplane("XY").box(w,h,d,centered=(False,False,False)).edges("|Z").fillet(r).val()
 return s.translate((x,-y-h,z))
def cyl(x,y,z,r,h):return cq.Workplane("XY").center(x,-y).circle(r).extrude(h).translate((0,0,z)).val()
def yzprism(yz,x,w):return cq.Workplane("YZ").polyline([(-y,z) for y,z in yz]).close().extrude(w).translate((x,0,0)).val()
def sub(shape,tool):return shape.cut(tool)
parts={};screws={}
# ---------------- UPPER COVER ----------------
up=rr(0,0,PAR["upper_roof_top"]-PAR["upper_roof_thickness"],*PAR["upper_outline"],PAR["upper_roof_thickness"],PAR["upper_corner_radius"])
skirt=rr(0,0,0,148,49,2.5,2).cut(rr(1,1,-.1,146,47,2.7,1))
up=up.fuse(skirt)
# R4 M1: the 0.1 mm edge ledges are deleted. The cover PCB is located by two roof pins and clamped against
# roof standoffs (bottom face Z0.5) by the key backer and USB/sensor carrier screws; outboard of the cavity
# the instrument face (via 0.1 PET) backs it.
for x,y in [(3.5,24.5),(144.5,24.5)]:
 up=up.fuse(cyl(x,y,.5,1.5,2.0)).fuse(cyl(x,y,.05,.7,.45))
for x,y,r in [(25,10,1.2),(45,10,1.2),(70,20,1.5),(108,28,1.5),(140,10,1.5)]:
 up=up.fuse(cyl(x,y,.5,r,2.0))
# M14: stepped instrument-screw boss, Ø5.2 through the PCB cut-out, Ø6.5 above the PCB (wall 1.0 to counterbore).
for x,y in PAR["screw_xy"]:
 up=up.fuse(cyl(x,y,0,2.6,3.8)).fuse(cyl(x,y,.5,3.25,3.3))
 up=up.cut(cyl(x,y,-.2,1.25,4.2)).cut(cyl(x,y,1.7,2.25,2.3))
# Q3/M9: wheel window plus north-edge thumb notch with floor Z1.5 (rim top Z3.0 stands 1.5 proud of it).
for x in [15,35,55]:
 up=up.fuse(box(x-6,0,.6,12,3.2,.9).cut(cyl(x,10,.5,7.6,1.2)))
 up=up.cut(box(x-6,-.1,1.5,12,10.1,2.5))
 up=up.cut(cyl(x,10,.6,7.6,3.4))
# M10: one-piece key, Ø5.0 stem in Ø5.2 hole, Ø6.2 flange in Ø6.5 x0.6 underside recess (retention overlap 0.5).
KEYS=[10,23,36,49,62]
for i,x in enumerate(KEYS):
 up=up.cut(cyl(x,25,2.3,PAR["button_hole_dia"]/2,1.8)).cut(cyl(x,25,2.3,PAR["button_flange_recess_dia"]/2,.8))
 tip=PAR["button_switch_top_max_Z"]+PAR["button_initial_gap_at_max"]
 pl=cyl(x,25,3.1,PAR["button_stem_dia"]/2,PAR["button_top_Z"]-3.1).fuse(cyl(x,25,2.6,PAR["button_flange_dia"]/2,.5)).fuse(cyl(x,25,tip,.8,2.6-tip))
 parts[f"button_{i+1}"]=pl.clean()
# M4: key 3..5 reaction now through a separate backer plate screwed to two roof bosses (not through the cup).
for x in [42.5,55.5]:
 up=up.fuse(cyl(x,25,.5,2.0,2.0)).cut(cyl(x,25,.4,.65,2.9))
# M11: light pipes Ø1.4 with Ø2.0 flange under the roof, 0.1 above LED; LP2 offset (-0.3,-0.3) for 0.5 wall to key 3.
LP=[(15,21),(34.7,20.7),(55,21)]
for i,(x,y) in enumerate(LP):
 up=up.cut(cyl(x,y,2.3,.75,1.8))
 parts[f"lightpipe_{i+1}"]=cyl(x,y,1.45,.7,3.8-1.45).fuse(cyl(x,y,2.1,1.0,.4)).clean()
ports=[(46.5,37),(64.8,37),(83.1,37),(101.4,37)]
JACK_NAMES=["FX SEND","LINE OUT","AUX","PHONES"]
src=ENG/"verification/references/STX-353K7A-6N-KTTR_rA1.STEP"
vendor_original=cq.importers.importStep(str(src)).val()
# Third vendor solid is the 0.1 mm shipping Kapton tape per official drawing; removed for installation.
vendor=cq.Compound.makeCompound(vendor_original.Solids()[:2]).rotate((0,0,0),(1,0,0),90)
def upward_sweep(solid,z0,z1):
 """Tool = the section of solid at z0 extruded to z1 (nose narrows upward, so this bounds it)."""
 bb=solid.BoundingBox();slab=solid.intersect(cq.Solid.makeBox(bb.xlen+2,bb.ylen+2,.002,cq.Vector(bb.xmin-1,bb.ymin-1,z0)))
 tool=None
 for f in slab.Faces():
  if f.geomType()=="PLANE" and f.normalAt().z<-.99:
   w=f.outerWire().translate(cq.Vector(0,0,-.02)).offset2D(.02)[0]   # 0.02 clearance on the nose flank
   s=cq.Solid.extrudeLinear(w,[],cq.Vector(0,0,z1-z0+.02));tool=s if tool is None else tool.fuse(s)
 return tool
for x,y in ports:
 # M5: shoulder pad bears on the Kycon shoulder face Z1.45 (zero gap): plug withdrawal goes jack->roof.
 jack=vendor.translate((x,-y,3.85))
 pad=box(x-5.4,y-5.85,PAR["jack_shoulder_Z"]+PAR["jack_shoulder_gap"],10.8,11.7,2.5-PAR["jack_shoulder_Z"])
 for zs in [1.4505,1.5,1.55,1.6,1.65,1.7,1.8,2.0,2.3]:pad=pad.cut(upward_sweep(jack,zs,4.5))
 pad=pad.cut(cyl(x,y,.8,3.3,3.2))
 up=up.fuse(pad)
 up=up.cut(cyl(x,y,.8,3.3,3.2)).cut(cyl(x,y,3.0,6.0,1.0))
# USB-C: opening tightened to official max body +0.1 for lateral load into roof; face pocket kept.
# R4.1b: bearing collar under the roof around the USB-C opening (the deeper face pocket leaves only 0.35 of roof).
UCO=PAR["usb_opening_collar"]
up=up.fuse(rr(93.305-UCO["wall"],7.195-UCO["wall"],UCO["z"][0],9.39+2*UCO["wall"],3.61+2*UCO["wall"],UCO["z"][1]-UCO["z"][0]+.05,1.6+UCO["wall"]))
up=up.cut(rr(93.305,7.195,UCO["z"][0]-.1,9.39,3.61,4.1-UCO["z"][0]+.1,1.6))
UFP=PAR["usb_face_pocket"];UPZ=PAR["usb_face_pocket_floor_Z"];up=up.cut(rr(98-UFP[0]/2,9-UFP[1]/2,UPZ,UFP[0],UFP[1],4.0-UPZ,1.5))
# M1/M5: four roof posts through cover-PCB ECO holes clamp USB board between post ends and the carrier.
# R4.1c: clamp-only post moved (88,22)->(88,21.8) and slimmed to Ø3.6 below the cover PCB (cover hole Ø4.0):
# cover-board copper (J3408/COVER6 pads, PWR_PB track) then stays >=0.5 from the hole edge without rerouting.
USBPOST=[(88,8),(108.3,8),tuple(PAR["usb_clamp_post"]["xy"]),(108.3,22)];USBSCREW=[(88,8),(108.3,8),(108.3,22)]
for x,y in USBPOST:
 lo=PAR["usb_clamp_post"]["lower_dia"]/2 if (x,y) not in USBSCREW else 2.0
 up=up.fuse(cyl(x,y,.5,2.5,2.0)).fuse(cyl(x,y,PAR["usb_top"],lo,.5-PAR["usb_top"]))
 if (x,y) in USBSCREW:up=up.cut(cyl(x,y,PAR["usb_top"]-.1,.65,4.5))
# M6/M8: speaker pocket ceiling at PCB top+2.8 working height (rim compressed), integral POM slots (no metal grille).
up=up.cut(rr(125.225,15.725,2.3,13.55,18.55,1.0,1.2))
for yy in [17.4,19.4,21.4,23.4,25.4,27.4,29.4,31.4]:
 up=up.cut(rr(126.4,yy,3.2,11.2,.8,.7,.35))
# M15: coax retaining ribs (0.05 each side) on the y4.5 run and the x112.5 run.
up=up.fuse(box(104,3.45,1.0,2,.55,1.5)).fuse(box(104,5.0,1.0,2,.55,1.5))
up=up.fuse(box(111.45,31,1.0,.55,2,1.5)).fuse(box(113.0,31,1.0,.55,2,1.5))
# Four receiver blades pass only through the existing PCB slots. R4: zero-play window, bottom lead-in chamfer,
# no Z-stop below the cover PCB (M1). South blades extend to Z-11.65 with a lip that carries the audio frame (M5).
for x in PAR["snap_stations_x"]:
 for yy in [3.0,45.3]:
  north=yy<10
  tab=box(x-4,yy,-5.2,8,.7,7.7)
  if not north:
   x0,x1=(x-4,69.0) if x<80 else (x-4,104.5)
   tab=tab.fuse(box(x0,yy,-11.65,x1-x0,.7,6.5))
   tab=tab.fuse(yzprism([(44.85,-11.15),(45.3,-11.15),(45.3,-11.65),(44.85,-11.3)],x0,x1-x0))
   tab=tab.cut(yzprism([(46.0,-11.66),(45.6,-11.66),(46.01,-11.25)],x0-.01,x1-x0+.02))
  LI=PAR["snap_blade_leadin"];face=3.0 if north else 46.0;s=LI if north else -LI;c0=x-4 if north else x1
  tab=tab.cut(yzprism([(face,-5.21),(face+s,-5.21),(face,-5.2+LI)],c0-.01,x+4-c0+.02))

  tab=tab.cut(box(x+2.0,yy-.1,-2.32,2.2,.9,.84))
  up=up.fuse(tab)
cover_noleg=up.clean()
# Q4: engraved legends 0.15 deep on the roof top.
LEG=[("VOL",15,18.9,1.8),("TONE",35,18.9,1.8),("FX",55,18.9,1.8)]+[(t,x,29.7,1.8) for t,x in zip(["FX","MODE","MIX","PWR","BT"],KEYS)]
LEG+=[(t,x,45.4,1.8) for t,(x,y) in zip(JACK_NAMES,ports)]+[("USB",98,15.6,1.8)]
legend_solids=[]
for t,x,y,fs in LEG:
 tx=cq.Workplane("XY").text(t,fs,.3,combine=False,fontPath=FONT,halign="center",valign="center").val()
 tx=tx.translate((x,-y,PAR["upper_roof_top"]-PAR["legend_depth"]))
 legend_solids.append((t,x,y,tx));up=up.cut(tx)
parts["upper_cover"]=up.clean()
# ---------------- LOWER CUP ----------------
cup=rr(*PAR["cup_origin"],PAR["cup_bottom"],*PAR["cup_outline"],-PAR["cup_bottom"],PAR["cup_corner_radius"]).cut(rr(36.3,2.8,PAR["cup_floor_top"],75.4,43.4,21,PAR["cup_inner_corner_radius"]))
# Four integral cantilever latches from wall material, 0.5 service slots (M2), rectangular hook = positive stop both ways.
for x in PAR["snap_stations_x"]:
 for side in [0,1]:
  yy=2 if side==0 else 46.2
  cup=cup.cut(box(x-4,yy-.1,-5.5,8.4,1.0,.5))
  cup=cup.cut(box(x-4,yy-.1,-1.0,8.4,1.0,.5))
  cup=cup.cut(box(x+3.6,yy-.1,-5.5,.5,1.0,5.0))
  yz=[(2.7,-2.3),(3.0+PAR["snap_hook_overlap"],-2.3),(3.0+PAR["snap_hook_overlap"],-1.5),(2.7,-1.5)]
  if side:yz=[(49-y,z) for y,z in yz]
  cup=cup.fuse(yzprism(yz,x+2.2,1.2))
  # R4.1 Y locating rib (0.15 high, 0.05 to the blade face) on the flap root, top lead-in 0.3.
  RB=PAR["snap_locating_rib"];rh=RB["height"];rx0,rx1=RB["x_from_station"];rz0,rz1=RB["z"]
  wall=2.8 if side==0 else 46.2;fr=wall+rh if side==0 else wall-rh
  rib=box(x+rx0,(wall-.05) if side==0 else fr,rz0,rx1-rx0,rh+.05,rz1-rz0)
  fo=fr+.01 if side==0 else fr-.01
  rib=rib.cut(yzprism([(fo,rz1+.01),(wall,rz1+.01),(fo,rz1-RB["top_leadin"])],x+rx0-.01,rx1-rx0+.02))
  cup=cup.fuse(rib)
# M3: main ledges overlap the board edge by 1.0 (were 0.2); north-west segment stops before the pickup notch;
# 0.5 overlap at x78.3-88 where B-side C811/C903 (h1.9/1.55) sit 0.56/0.73 from the edge.
LEDGES=[(36.7,21.6,2.8,1.4),(75,3.3,2.8,1.4),(78.3,9.7,2.8,.9),(88,23.3,2.8,1.4),(36.7,25,44.8,1.5),(93,18.3,44.8,1.5)]
for x,w,y,h in LEDGES:
 cup=cup.fuse(box(x,y,-13.35,w,h,.8))
# M3: lateral locating pads 0.05 from the board edge (replace the ineffective end stops below the board).
for x,y,w,h in [(55,2.8,3,.35),(85,2.8,3,.35),(56,45.85,3,.35),(108,45.85,2,.35),(36.3,10,.35,3),(36.3,36,.35,3),(111.35,10,.35,3),(111.35,36,.35,3)]:
 cup=cup.fuse(box(x,y,PAR["main_bottom"],w,h,PAR["main_thickness"]))
# M16: battery lateral guides with 0.25 clearance (east guide stays the NTC contact side).
for x,y,w,h in [(39.25,6.5,53.25,.5),(39.25,42.0,53.25,.5),(39.25,6.5,.5,36.0),(92,7.25,.5,34.5)]:
 cup=cup.fuse(box(x,y,-20.3,w,h,3.2))
cup=cup.cut(box(91.9,16,-18,1,5,1.5))
cup=cup.cut(box(91.9,11.3,-20.0,.7,4.7,4.0))
ntcwall=box(92.0,11.3,-20.3,4.8,4.7,4.2).cut(box(91.9,11.8,-20.0,4.3,3.7,4.2))
cup=cup.fuse(ntcwall)
# M7 / DECISIONS addendum 2026-10-15: the pickup wire comes up through the violin's ORIGINAL wire hole (no new hole is
# drilled in the instrument). The cup-floor entry is aligned to that hole: position = PAR["pickup_entry_xy"]
# (TODO: measured value; placeholder under the main-board edge notch x58.8-62.4, route to J101).
# Mode "hole": dia 3.0 at the measured position. Mode "slot" (first-sample default): 10 x 3 slot along X so the
# module can be built before the measurement (+/-3.5 along X).
PEX,PEY=PAR["pickup_entry_xy"]
if PAR["pickup_entry_mode"]=="hole":
 pe_tool=cyl(PEX,PEY,PAR["cup_bottom"]-.1,PAR["pickup_entry_hole_dia"]/2,1.0);pe_ext=(PEX-1.5,PEY-1.5,PEX+1.5,PEY+1.5)
else:
 SL,SW=PAR["pickup_entry_slot"];ang=PAR["pickup_entry_slot_axis_deg"]
 pe_tool=cq.Workplane("XY").slot2D(SL,SW,ang).extrude(1.0).translate((PEX,-PEY,PAR["cup_bottom"]-.1)).val()
 ca,sa=abs(math.cos(math.radians(ang))),abs(math.sin(math.radians(ang)))
 hx=(SL-SW)/2*ca+SW/2;hy=(SL-SW)/2*sa+SW/2;pe_ext=(PEX-hx,PEY-hy,PEX+hx,PEY+hy)
assert 37.0<=pe_ext[0] and pe_ext[2]<=91.5 and 3.1-1e-6<=pe_ext[1] and pe_ext[3]<=6.3+1e-6, \
 f"pickup entry {pe_ext} outside the north cable strip (X37-91.5, Y3.1-6.3): the cable could not reach J101 past the battery; re-layout needed"
PAR["pickup_entry_extent_xy"]=[round(v,3) for v in pe_ext]
(BASE/"parameters.json").write_text(json.dumps(PAR,ensure_ascii=False,indent=2),encoding="utf8")
cup=cup.cut(pe_tool)
# R4: the R3 end shelves are removed (they lay inside the main-board footprint, so the board could not be
# inserted past them); the audio frame now hangs from the cover side only (blade lips, key backer, USB bracket).
# Main-board latches: 0.5 slots, tooth bottom at board top (zero Z gap, M3).
for x in [38.0,95.0]:
 for side in [0,1]:
  yy=2.0 if side==0 else 46.2
  cup=cup.cut(box(x,yy-.1,-12.3,12.1,1.0,.5))
  cup=cup.cut(box(x,yy-.1,-10.8,12.1,1.0,.5))
  cup=cup.cut(box(x+11.6,yy-.1,-12.3,.5,1.0,2.0))
  yz=[(2.7,-11.75),(3.65,-11.75),(3.65,-11.5),(2.9,-11.05),(2.7,-11.05)]
  if side:yz=[(49-y,z) for y,z in yz]
  cup=cup.fuse(yzprism(yz,x+10.0,1.5))
parts["lower_cup"]=cup.clean()
# ---------------- AUDIO FRAME (separate, snaps onto south blade lips) ----------------
def build_audio_frame(ft):
 fb=PAR["audio_frame_bottom"]
 carrier=box(36.5,29.2,fb,75,16.0,ft).cut(box(37.3,30,fb-.1,73.4,14,ft+.2))
 for x in [37.3,110.2]:
  for y in [30.0,42.8]:
   carrier=carrier.fuse(box(x,y,fb,.5,1.2,ft))
 # Transverse ribs under the board between jacks (no jack body / THT pin tail there).
 for x in [55.0,73.5,91.7]:
  carrier=carrier.fuse(box(x,30,fb,1.0,14,ft))
 # North stiffening web beside the board edge, up to Z-4.0; two hanger zones: over the key-backer ledge
 # (x40-62, hook Z-1.6..-1.2) and over the USB-bracket south rail (x88-108, tab Z-4.3..-3.9).
 carrier=carrier.fuse(box(36.6,29.2,fb+ft,74.8,.8,-4.0-(fb+ft)))
 carrier=carrier.fuse(box(40,29.2,-4.0,22,.8,2.8)).fuse(box(40,28.8,-1.6,22,.4,.4))
 carrier=carrier.fuse(box(88,27.25,-4.3,20,1.95,.4))
 carrier=carrier.cut(box(97.8,29.15,fb-.1,6.1,.95,1.5))
 carrier=carrier.cut(box(75.8,44.95,fb-.1,2.4,.4,ft+.2))   # POTS3 lower bend passes under/behind the bar
 return carrier.clean()
parts["audio_load_frame"]=build_audio_frame(PAR["audio_frame_thickness"])
fb=PAR["audio_frame_bottom"];ft=PAR["audio_frame_thickness"]
# R4.1 selective-fit variants (not in the assembly or collision set; exported to cad/variants/)
frame_variants={f"audio_load_frame_web{str(t).replace('.','p')}":build_audio_frame(t) for t in PAR["audio_frame_web_variants"] if abs(t-PAR["audio_frame_thickness"])>1e-9}
# ---------------- KEY BACKER (keys 3-5) ----------------
kb=box(36.6,21.3,-1.1,30.0,7.4,1.2).fuse(box(40,28.0,-2.0,22,.7,.9)).fuse(box(40,28.7,-2.0,22,.4,.4))
for x in [42.5,55.5]:
 kb=kb.cut(cyl(x,25,-1.2,.9,1.4));screws[f"SCREW_keybacker_{x}"]=cyl(x,25,-2.0,1.5,.9)
parts["key_backer_bracket"]=kb.clean()
# ---------------- USB BRACKET (sensor board eliminated by ECO L-12) ----------------
# Frame under the USB board; open window over all B-side parts incl. the FH12-16 ZIF (ECO L-10) so the
# USB16 FPC enters the ZIF from -X below the west rail. Screws at 3 posts; post 4 (88,22) clamps only.
ub=rr(85.4,4.4,-4.9,25.2,23.2,.6,1.0).cut(box(86.6,6.0,-5.0,19.6,20.2,.8))
for x,y in USBSCREW:
 ub=ub.cut(cyl(x,y,-5.0,.9,.8));screws[f"SCREW_usb_{x}_{y}"]=cyl(x,y,-5.8,1.5,.9)
ub=ub.fuse(cyl(88,8,-4.9,1.6,.6)).cut(cyl(88,8,-5.0,.9,.8))
parts["usb_bracket"]=ub.clean()
# Thin support shims: now the full ledge set (M3), used only when measured latch gap>0.
for t in [.05,.10,.20]:
 sh=None
 for x,w,y,h in LEDGES:
  b=box(x,y+.4,PAR["main_bottom"],w,h-.4,t);sh=b if sh is None else sh.fuse(b)
 parts[f"main_shim_{str(t).replace('.','p')}mm"]=sh.clean()
parts["battery_bottom_insulator"]=box(40,7.25,PAR["cup_floor_top"],52,34.5,PAR["pack_bottom_insulation"])
parts["main_audio_dielectric_separator"]=box(37.3,30,-11.75,73.4,14,.1).cut(box(64.45,42.3,-11.85,5.0,1.7,.3))
parts["key_backer_insulator"]=box(7.0,21.5,0,28.0,7.0,.1)
parts["speaker_backer_insulator"]=box(124.5,15.0,0,15.0,20.0,.1)
parts["ntc_electrical_separator"]=box(92.0,11.8,-19.9,.1,3.7,2.4)
parts["battery_top_separator"]=box(39.5,6.75,-13.8,53,35.5,.1)
parts["battery_top_foam"]=box(42,9.0,-14.8,48,30.8,1.0).cut(box(44,15.0,-14.9,44,6.4,1.2)).cut(box(44,27.4,-14.9,44,6.4,1.2))
# ---------------- REFERENCES ----------------
refs={}
for i,(x,y) in enumerate(ports):refs[f"Kycon_vendor_{i+1}"]=vendor.translate((x,-y,3.85))
refs["battery_max_reference"]=box(40,7.25,-20.2,52,34.5,5.4)
refs["instrument_mount_land_INFERRED_REFERENCE"]=box(0,0,-22,148,49,22).cut(box(35,1,-22.1,78,47,22.2))
(BASE/"reference/instrument-fit-basis.json").write_text(json.dumps({"cavityMm":[78,47,22],"inferredCavityOriginXY":[35,1],"datumZ":0,"basis":"inherited nominal cavity dimensions, origin inferred from centered cup; actual violin must be measured before machining instrument","physicalMeasurement":False,"mountHoles":"new reserved pattern, factory fits actual instrument as authorized","pickupEntry":"NO new hole in the instrument (DECISIONS addendum 2026-10-15). The pickup wire uses the violin's ORIGINAL wire hole; the cup-floor entry (parameters.json pickup_entry_xy, mode %s, extent %s) must be aligned to the measured hole. TODO measure: original hole position in the cavity (distance from tail metal datum u, offset from centre line v); X=258-u."%(PAR["pickup_entry_mode"],PAR["pickup_entry_extent_xy"]),"centralBeam":"TODO measure: central solid beam width >= 49 mm over 110-258 mm from the tail datum (cover X 148..0)","longitudinal":"cover X = 258 - u (u = distance from tail metal datum); cavity u 145..223 = X 113..35; wheel end (X=0) toward the head"},ensure_ascii=False,indent=2),encoding="utf8")
geo=json.loads((BASE/"reference/current-native-geometry.json").read_text("utf8"))
for bd in geo["boards"].values():
 bd["native_body_STEP"]=bd["native_body_STEP"].replace("\\","/")       # M17 POSIX paths
 bd["file"]="project/pcb/"+bd["file"].replace("\\","/").split("/")[-1]  # M17 no local absolute path
(BASE/"reference/current-native-geometry.json").write_text(json.dumps(geo,ensure_ascii=False,indent=1),encoding="utf8")
native_body_ledger=[]
def board_body(role,origin,top,thickness):
 bd=geo["boards"][role];path=BASE/bd["native_body_STEP"]
 assert hashlib.sha256(path.read_bytes()).hexdigest()==bd["native_body_sha256"]
 body=cq.importers.importStep(str(path)).val();b=body.BoundingBox();assert b.zlen>0
 transform=cq.Matrix([[1,0,0,0],[0,1,0,0],[0,0,thickness/b.zlen,0],[0,0,0,1]])
 body=body.transformGeometry(transform);bb=body.BoundingBox();body=body.translate((origin[0],-origin[1],top-bb.zmax))
 native_body_ledger.append({"board":role,"native_board_sha256":bd["sha256"],"native_body_sha256":bd["native_body_sha256"],
  "imported_laminate_body_height":b.zlen,"finished_board_contract_height":thickness,"XY_unchanged":True,"Z_normalized_to_contract":True})
 return body
ECO_DELETED={"H_USB_1_M","H_USB_2_M","H_USB_1_R","H_USB_2_R","J1801"}   # ECO L-10/L-12
# R4 mechanical ECO holes in the native boards (to be executed in KiCad; listed in pcb-interface-eco-R4.json).
ECO_R4={"cover":[{"id":"KEYBACKER_%d"%i,"xy":[x,25],"dia":1.8,"type":"NPTH"} for i,x in enumerate([42.5,55.5])]+
 [{"id":"USBPOST_%d"%i,"xy":list(p),"dia":4.4 if p in USBSCREW else PAR["usb_clamp_post"]["cover_hole_dia"],"type":"NPTH, keep copper 0.5 away"+("" if p in USBSCREW else "; R4.1c clamp-only post moved from (88,22), hole Ø4.4->Ø4.0")} for i,p in enumerate(USBPOST)]+
 [{"id":"PIN_ROUND","xy":[3.5,24.5],"dia":1.5,"type":"NPTH"},{"id":"PIN_SLOT","xy":[144.5,24.5],"slot":[2.5,1.5],"type":"NPTH slot along X"}]+
 [{"id":"SNAP_SLOT_S_%d"%i,"rect":[x0,44.75,x0+8.8,46.1],"type":"enlarge existing south snap slot from y44.9 to y44.75 (blade lip passage)"} for i,x0 in enumerate([62.6,97.6])],
 "usb":[{"id":"USBSCREW_%d"%i,"xy":[round(p[0]-86,2),p[1]-5],"dia":1.8,"type":"NPTH, keep-out Ø4.4 both sides"} for i,p in enumerate(USBSCREW)]+[{"id":"USBPOST_CLAMP","xy":[round(PAR["usb_clamp_post"]["xy"][0]-86,2),round(PAR["usb_clamp_post"]["xy"][1]-5,2)],"keepout_top_dia":4.4,"type":"no hole; F-side keep-out for clamp post (R4.1c: post Ø3.6 at local (2,16.8) lies inside the existing Ø4.4 keep-out at (2,17); USB board needs no change)"}]}
refs["main_reference"]=board_body("main",PAR["main_origin"],-11.75,.8)
usbb=board_body("usb",PAR["usb_origin"],-3.3,1.0)
for p in USBSCREW:usbb=usbb.cut(cyl(p[0],p[1],-4.5,.9,1.4))
refs["usb_reference"]=usbb
refs["RT1921_body_reference"]=box(92.1,11.8,-19.9,4.0,3.7,2.4)
refs["speaker_working_nominal_reference"]=rr(125.425,15.925,.5,13.15,18.15,2.8,1.0)
for i,x in enumerate([15,35,55]):
 refs[f"wheel_{i+1}_max_reference"]=box(x-5.2,4.8,.5,10.4,10.4,1.5).fuse(cyl(x,10,2.0,7.1,1.0))
for i,x in enumerate(KEYS):
 refs[f"switch_{i+1}_max_reference"]=box(x-2.6,22.4,.5,5.2,5.2,PAR["button_switch_top_max_Z"]-.5)
refs["audio_native_reference"]=board_body("audio",PAR["audio_origin"],-9.65,1.0)
cov=board_body("cover",[0,0],.5,.4)
for e in ECO_R4["cover"]:
 if "rect" in e:cov=cov.cut(box(e["rect"][0],e["rect"][1],0,e["rect"][2]-e["rect"][0],e["rect"][3]-e["rect"][1],.6));continue
 x,y=e["xy"]
 cov=cov.cut(box(x-1.25,y-.75,0,2.5,1.5,.6) if "slot" in e else cyl(x,y,0,e["dia"]/2,.6))
refs["cover_native_reference"]=cov
oldpath=BASE/"reference/legacy-occupancy-sources.json"
old={o["id"]:o for o in json.loads(oldpath.read_text("utf8"))["objects"]}
components={o["ref"]:o for o in json.loads((ENG/"project/electrical/native-components.json").read_text("utf8"))}
transforms={"main":([36.7,3.2],-11.75,.8),"cover":([0,0],.5,.4),"usb":([86,5],-3.3,1),"sensor":([90,16],-7,.8),"audio":([37.3,30],-9.65,1)}
occupancy=[]
custom={"J401","J101","J102","J103","J104","J201","J202","J203","J204","RV810","RV811","RV812","SW810","SW811","SW812","SW813","SW814","LS810","SP810","LS901","J301"}
for bn,bd in geo["boards"].items():
 origin,top,th=transforms[bn]
 for f in bd["components"]:
  ref=f["ref"];o=old.get(ref,{})
  if ref in custom or bn=="sensor" or ref in ECO_DELETED:continue
  if ref=="U901":continue
  if ref in ["H_AUDIO_1_M","H_AUDIO_1_R","H_COVER_2_M","H_COVER_2_R","H_COVER_3_M","H_COVER_3_R","H_COVER_1_M","H_COVER_1_R"]:continue
  co=f["court"]
  if not co:continue
  comp=components.get(ref,{})
  mpn=comp.get("mpn") or "";lib=f["library"]
  h=o.get("height_screen_mm")
  basis=o.get("height_basis","package-specific height not established")
  if mpn.startswith("RT0603"):
   h=.55;basis="YAGEO RT series V17 Feb2026 p5 RT0603 thickness0.45+/-0.1; +0.1 assembly budget"
  if mpn.startswith("CC0603"):
   h=.9;basis="YAGEO actual0603 MPN body thickness max0.9 + assembly budget0.1"
  if mpn.startswith("CC0805"):
   h=1.45;basis="YAGEO actual0805 MPN body thickness1.25+/-0.2 + assembly budget0.1"
  if mpn=="CC0805KKX5R6BB106":
   h=.95;basis="YAGEO exact MPN official0.85+/-0.1 mm; +0.1 assembly budget"
  if ref in ["C811","C830","C831","C832"]:
   h=1.8;basis="KEMET1206 1.8 maximum body + assembly0.1"
  if ref.startswith("H_") or "WirePads" in lib:
   h=1.5;basis="ASSEMBLY REQUIREMENT horizontal thin-wall insulated wires + solder <=1.5; R4: these become FPC lands (<=0.3) per DECISIONS Q6, screen kept conservative"
  if ref in ["J801","J902"]:
   h=.05;basis="DNP bare production test copper; no header installed"
  if h is None:h=2.0;basis="UNKNOWN maximum:2.0 screening reserve only; not source-verified"
  height=h if ("ASSEMBLY REQUIREMENT" in basis or ref in ["J801","J902"]) else h+.1
  z=top if f["side"]=="F" else top-th-height
  x,y=origin[0]+co[0],origin[1]+co[1]
  name="OCC_"+bn+"_"+ref
  polygons=f.get("courtContours",[])
  if polygons:
   solids=[cq.Workplane("XY").polyline([(origin[0]+px,-origin[1]-py) for px,py in pp]).close().extrude(height).translate((0,0,z)).val() for pp in polygons]
   refs[name]=solids[0]
   for solid in solids[1:]:refs[name]=refs[name].fuse(solid)
  else:refs[name]=box(x,y,z,co[2]-co[0],co[3]-co[1],height)
  if ref=="J501":
   refs[name]=refs[name].fuse(box(98.675,17.675,-18.35,10.2,10.0,5.8))
   basis+="; includes mated PHR-3 nominal reference plus factory acceptance envelope10.2x10.0x5.8, not guaranteed vendor maximum"
  occupancy.append({"name":name,"ref":ref,"board":bn,"mpn":mpn,"side":f["side"],"body_or_assembly_height":height,"basis":basis,"xy_conservative_courtyard":co,"source_board_sha256":bd["sha256"]})
# ECO L-10: FH12-16S-0.5SH ZIF on USB board B side + USB16 FPC upper route reservation (centre-line per ECO,
# flexible part: final-pose check only). Lower Z-fold on the main board is PCB scope.
refs["J_USB_U_FH12_16_envelope"]=box(86.8,11.5,-6.3,5.5,13.0,2.0)
refs["FPC_USB16_route_reservation"]=box(73.0,8.6,-7.75,6.5,13.9,.3).fuse(box(79.5,13.5,-7.75,7.3,9.0,.3)).fuse(box(85.0,13.5,-7.75,1.8,9.0,2.4))
refs["GCT_USB4120_body_max"]=rr(98-9.19/2,9-3.41/2,-3.3,9.19,3.41,6.85,1.5)
from rf_reference import build as build_rf_reference
refs.update(build_rf_reference(cq,box,geo,BASE))
from flex_reference import build as build_flex_reference
refs.update(build_flex_reference(cq,box,geo,BASE))
refs.update(screws)
(BASE/"reference/native-board-body-ledger.json").write_text(json.dumps(native_body_ledger,ensure_ascii=False,indent=2),encoding="utf8")
(BASE/"reference/component-occupancy-ledger.json").write_text(json.dumps({"snapshot":geo,"objects":occupancy},ensure_ascii=False,indent=2),encoding="utf8")
(BASE/"pcb-interface-eco-R4.json").write_text(json.dumps({"schema":"SmartVio.R4.mechanical_to_electrical.v1","units":"mm","coordinates":"cover: cover-PCB XY (= global logical XY); usb: usb-PCB local XY",
 "holes":ECO_R4,"recommended":[{"board":"cover","ref":"D851","move_to":[34.7,20.7],"why":"centre under offset light pipe 2 (M11)"},
 {"board":"main","note":"chamfer main-board outline corners >=1.0x45 deg (cup inner corners now R1.2, 0.07 clearance)"},
 {"board":"usb","note":"USB16 FPC (ECO L-10) enters the ZIF from -X under the bracket west rail (rail bottom z-4.9, FPC <= z-5.3); bend radius >=1.5"},
 {"board":"usb","note":"keep F-side copper/parts out of dia4.4 at clamp post (88,21.8) [local (2,16.8); existing keep-out at local (2,17) still covers the Ø3.6 post]; ZIF J_USB_U envelope x86.8-92.3 y11.5-24.5 z-6.3..-4.3 is inside the bracket window"},
 {"board":"cover","note":"antenna window GND keep-out >=5 mm is PCB-05; mechanical grille is now non-metallic"}]},ensure_ascii=False,indent=2),encoding="utf8")

STOCK=OUT/"stock";STOCK.mkdir(exist_ok=True)
stock=parts["button_1"].fuse(cyl(10,25,1.75,.8,.5))
cq.exporters.export(stock,str(STOCK/"button_blank_TRIM_TIP_TO_MEASURED_SWITCH.step"))
VAR=OUT/"variants";VAR.mkdir(exist_ok=True)
for vn,vs in frame_variants.items():cq.exporters.export(vs,str(VAR/(vn+".step")))
checks=[];file_manifest=[]
for name,sh in parts.items():
 fn=OUT/(name+".step");cq.exporters.export(sh,str(fn))
 re=cq.importers.importStep(str(fn)).val();bb=re.BoundingBox()
 checks.append({"part":name,"valid":re.isValid(),"solids":len(re.Solids()),"volume_mm3":round(re.Volume(),6),"bbox":[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax]})
 file_manifest.append({"file":str(fn.relative_to(BASE)),"sha256":hashlib.sha256(fn.read_bytes()).hexdigest()})
assy=cq.Assembly(name="SmartVio_R4_MECHANICAL_CANDIDATE")
for n,s in parts.items():
 if "shim_" not in n:assy.add(s,name=n,color=cq.Color(.2,.28,.26,.9))
assy.save(str(OUT/"mechanical_parts_assembly.step"))
refassy=cq.Assembly(name="REFERENCE_NO_MANUFACTURING")
for n,s in refs.items():refassy.add(s,name=n,color=cq.Color(.4,.65,.35,.6))
refassy.save(str(OUT/"reference_components_NOT_MANUFACTURING.step"))
from itertools import combinations
collisions=[];pair_count=0;exact_count=0
allsh={**{n:s for n,s in parts.items() if "shim_" not in n},**refs}
bounds={}
for n,q in allsh.items():
 bb=q.BoundingBox();bounds[n]=(bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax)
for an,bn in combinations(allsh,2):
 pair_count+=1;a=bounds[an];b=bounds[bn]
 if any(a[k+3]<=b[k]+1e-7 or b[k+3]<=a[k]+1e-7 for k in range(3)):continue
 exact_count+=1
 try:v=allsh[an].intersect(allsh[bn]).Volume()
 except Exception:v=-1
 if v>1e-6 or v<0:collisions.append({"a":an,"b":bn,"intersection_mm3":round(v,8),"requires_review":True})
reference_ledger=[]
REFOUT=BASE/"reference/components";REFOUT.mkdir(exist_ok=True)
for name,sh in refs.items():
 bb=sh.BoundingBox()
 fn=REFOUT/(name+".step");cq.exporters.export(sh,str(fn))
 reference_ledger.append({"name":name,"file":str(fn.relative_to(BASE)),"sha256":hashlib.sha256(fn.read_bytes()).hexdigest(),"valid":sh.isValid(),"solids":len(sh.Solids()),"volume_mm3":sh.Volume(),"bbox":[bb.xmin,bb.ymin,bb.zmin,bb.xmax,bb.ymax,bb.zmax],"source":"official Kycon nominal CAD packaging removed" if name.startswith("Kycon") else "native-board/courtyard screen or drawing-based dimensioned reference; see occupancy ledger"})
flex_designs=json.loads((BASE/'reference/flex-installed-and-unfolded.json').read_text('utf8'))['designs']
modeled_connections=sum(len(d['sourceContacts']) for d in flex_designs)
# Envelope checks (R3 constraints kept).
up_bb=parts["upper_cover"].BoundingBox();cup_bb=parts["lower_cup"].BoundingBox()
cover_side=[n for n in parts if n.startswith(("button_","lightpipe_","upper_cover"))]+[n for n in refs if n.startswith("Kycon") or n=="GCT_USB4120_body_max"]
zmax_nonwheel=max(allsh[n].BoundingBox().zmax for n in cover_side)
zmin_all=min(b[2] for n,b in bounds.items() if not n.startswith("instrument_mount"))
envelope={"cover_xy":[round(up_bb.xlen,3),round(up_bb.ylen,3)],"cover_xy_limit":[148,49],"nonwheel_protrusion":round(zmax_nonwheel,3),"nonwheel_protrusion_limit":5,
 "wheel_top_Z":3.0,"cup_xy":[round(cup_bb.xlen,3),round(cup_bb.ylen,3)],"cup_depth":round(-cup_bb.zmin,3),"cavity":[78,47,22],
 "total_height":round(zmax_nonwheel-zmin_all,3),"total_height_limit":25.0}
envelope["pass"]=envelope["cover_xy"]==[148.0,49.0] and zmax_nonwheel<=5 and cup_bb.xlen<=77.0001 and cup_bb.ylen<=45.0001 and -cup_bb.zmin<22 and envelope["total_height"]<=25
# Legend clearance: each legend bbox +0.3 must sit on solid roof (no hole/edge within 0.3).
legend_check=[]
for t,x,y,tx in legend_solids:
 b=tx.BoundingBox();probe=cq.Solid.makeBox(b.xlen+.6,b.ylen+.6,.15,cq.Vector(b.xmin-.3,b.ymin-.3,PAR["upper_roof_top"]-.35))
 v=cover_noleg.intersect(probe).Volume();legend_check.append({"text":t,"xy":[x,y],"bbox_xy":[round(b.xmin,2),round(-b.ymax,2),round(b.xmax,2),round(-b.ymin,2)],"solid_fraction_under_margin":round(v/probe.Volume(),6),"ok":v/probe.Volume()>.9999})
status={"schema":"SmartVio.R4.mechanical.assembly-status","status":"MODELED_CAD_SCOPE_ZERO_INTERSECTIONS_NOT_FULL_ASSEMBLY_RELEASE" if not collisions else "CAD_INTERSECTIONS_REQUIRE_REVIEW","production_released":False,
"parameters":PAR,"real_parts_exported":len(parts),"source_vendor_model":str(src.relative_to(ENG)),"shipping_packaging_removed":"Only vendor third0.1mm Kapton shipping tape solid removed from installed reference.","vendor_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),
"step_roundtrip":checks,"reference_components":reference_ledger,"collision_pair_count":pair_count,"exact_intersection_count":exact_count,"file_manifest":file_manifest,"intersections":collisions,
"envelope":envelope,"legend_clearance":legend_check,
"nominal_Z_chain":[["cup bottom",PAR["cup_bottom"]],["floor top",PAR["cup_floor_top"]],["bottom insulation top / battery bottom",-20.2],["battery max top",-14.8],["foam (swell allowance) top",-13.8],["top separator top",-13.7],["main B max bottom",-13.6],["main board bottom",-12.55],["main board top / latch tooth bottom",-11.75],["audio frame bottom / blade lip top",PAR["audio_frame_bottom"]],["audio PCB top",-9.65],["jack shoulder / roof pad",1.45],["jack mouth nominal",3.85],["key top",PAR["button_top_Z"]]],
"nominal_limits":{"total":round(3.85-PAR["cup_bottom"],3),"nonwheel":3.85,"raw_cavity_depth":22},
"tolerance_limit_status":"Worst case dimensions and final board height-map not yet closed; assembly is not released merely by nominal dimensions.",
"physical_tests":0,"manufacturing_process":PAR["process"],
"modeled_board_interconnections":modeled_connections,"required_board_interconnections":37,"complete_harness_closed":False,
"remaining":["Board ECO holes (pcb-interface-eco-R4.json) must be executed natively, then rerun","Q6: 16 discrete wires become FPCs (USB FPC, sensor FPC or merge, AUDIO6->wider); mechanical slots reserved, FPC geometry by PCB team","measure the violin's ORIGINAL pickup-wire hole and set pickup_entry_xy (slot 10x3 used until then); no new hole in the instrument","FPC custom thin stack and microdrill require supplier DFM confirmation","measure actual violin cavity and mounting surface","freeze actual material and qualified tolerance/process","speaker back volume not provided (acoustic test)"]}
from assembly_sequence import run as run_sequence
seq=run_sequence(cq,parts,refs,BASE,light={"upper_cover":cover_noleg})
status["assembly_sequence"]={"file":"assembly-sequence-check.json","pass":seq["pass"],"steps":len(seq["steps"])}
(BASE/"assembly-status.json").write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding="utf8")
(BASE/"drawings").mkdir(exist_ok=True)
cq.exporters.export(cq.Compound.makeCompound([parts["upper_cover"],parts["lower_cup"]]),str(BASE/"drawings/assembly-isometric.svg"),opt={"width":1000,"height":700,"projectionDir":(1,-1,0.7),"showAxes":False,"showHidden":False,"strokeWidth":.6})
(BASE/"requirements.txt").write_text("cadquery==2.8.0\n",encoding="ascii")
print(json.dumps({"parts":len(parts),"all_valid":all(x["valid"] and (x["part"].startswith("main_shim") or x["solids"]==1) and x["volume_mm3"]>0 for x in checks),"intersections":collisions,"envelope":envelope,"legends_ok":all(l["ok"] for l in legend_check),"sequence_pass":seq["pass"]},ensure_ascii=False))
