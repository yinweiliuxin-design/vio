"""SmartVio R5 enclosure V0.3: cover, shell, knob, button cap, light pipe, the assembly and the violin pocket.

Run (CadQuery 2.x):   python3 build_enclosure.py [--no-render]
Writes step/, stl/, preview/ and enclosure_params.json next to this script, and prints the interference report
(also saved as checks.json).

Coordinates are the panel-mockup coordinates:
  X along the violin, X0 = head end of the module, X148 = tail end;
  y across, y0 = G-string edge;
  Z0 = violin back surface = cover top (flush), Z negative into the violin.
  CAD world = (X, -y, Z).

Mounting concept: the violin pocket has a 2.0 mm deep rebate the size of the cover (+0.2 per side). The cover
rests on the 1.2 mm wood ledge around the rebate and on four wood pads at the corners, and four countersunk
ST2.2 screws go through the cover corners into those pads. Flush therefore depends only on the rebate depth.
The shell hangs from the cover on 8 snaps and never touches the pocket (0.25 at the sides, 0.3 under the
floors). The main board and the USB board hang from bosses on the cover underside, so plug and button forces
go straight into the cover and the ledge, not through the snaps.

Electronics envelopes (main board, encoders, jacks, switches, LEDs, USB board, battery, speaker) are
PROPOSALS for the electronics supplier to confirm; see README.md.
"""
import argparse
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "verify", "mockup"))

import numpy as np            # noqa: E402
import cadquery as cq         # noqa: E402
import build_mockup as M      # noqa: E402  approved panel layout, label font, grille, renderer

# =====================================================================================
# PARAMETERS (mm)
# =====================================================================================
L, W, T, R = 148.0, 49.0, 2.0, 4.0           # cover outline and thickness (Z 0 .. -2)
ZC = -T                                      # cover underside

# approved panel layout (from the 1:1 mockup)
KNOBS, JACKS, BUTTONS = M.KNOBS, M.JACKS, M.BUTTONS
LEDS = M.LEDS_SPEC                           # final product: LEDs between the buttons
USBC = M.USBC
SPEAKER, SPEAKER_D = M.SPEAKER, M.SPEAKER_D
SCREWS = M.SCREWS

# cover openings for the production (PCB-mounted) parts
ENC_HOLE_D = 7.6       # EC11 M7 bushing Ø7.0 + 0.3 radial (covered by the knob)
JACK_HOLE_D = 6.5      # jack nose Ø6.0 + 0.25 radial
BTN_HOLE_D = 5.6       # button cap stem Ø5.4 (guides the cap)
LP_HOLE_D = 3.1        # light pipe Ø3.0
USBC_SLOT = (9.4, 3.6)  # along y, along X; USB-C receptacle shell 8.94 x 3.26 passes through
SCREW_D, CSK_D = 2.4, 4.5   # corner holes, 90° countersink (ST2.2 head Ø3.8 sits 0.35 below the top)
ENGRAVE = 0.15         # label / logo engraving depth

# pocket and shell
POCKET_GAP = 0.2       # cover edge -> rebate wall
LEDGE_IN = 1.0         # deep pocket wall, from the cover edge (wood ledge 1.2 wide)
SHELL_GAP = 0.25       # deep pocket wall -> shell outer face
SHELL_OUT = LEDGE_IN + SHELL_GAP    # 1.25
WALL = 1.2
SHELL_IN = SHELL_OUT + WALL         # 2.45  (inner width 44.1)
FLOOR = 1.0
DEPTH = (11.0, 17.0, 15.0)          # pocket depths: speaker / controls / battery zone (battery 14 -> 15, 11-09)
ZONE_X = (34.0, 104.0)              # shell outer riser faces
ZONE_GAP = 0.3                      # shell riser -> pocket step (along X)
FLOOR_GAP = 0.3                     # shell outer bottom -> pocket floor
RISER = 1.0
PAD_R = 4.6                         # wood pad around each corner screw (pocket keeps it)
NOTCH_R = PAD_R + SHELL_GAP         # shell corner notch
OUT_BOT = tuple(-(d - FLOOR_GAP) for d in DEPTH)     # -10.7, -16.7, -13.7
IN_FLOOR = tuple(z + FLOOR for z in OUT_BOT)          # -9.7, -15.7, -12.7
POCKET_STEP_X = (ZONE_X[0] - ZONE_GAP, ZONE_X[1] + ZONE_GAP)   # 33.7, 104.3
PILOT_WOOD = (1.6, 10.0)            # Ø, depth below the ledge (Z -2)

# snaps (tongues on the cover, windows in the shell walls)
SNAP_X = (20.0, 61.0, 81.0, 128.0)  # both long sides
SNAP_W, SNAP_T = 6.0, 1.0
SNAP_TIP = -7.5
HOOK_D, HOOK_TOP, HOOK_RAMP = 0.5, -6.45, 0.5
WIN_W, WIN_Z = SNAP_W + 0.6, (-7.6, -6.40)

# cover underside
PCB = (36.5, 3.0, 101.0, 46.0)      # main board outline X0, y0, X1, y1 (proposal)
PCB_TOP, PCB_T = -12.0, 1.0
PCB_BOSSES = [(39.0, 6.0), (39.0, 43.0), (86.5, 24.5), (98.5, 41.0)]
BOSS_D, BOSS_PILOT, BOSS_PILOT_DEPTH = 4.0, 1.7, 6.0      # M2 PT screw (K20)
USB_BOARD = (138.5, 14.5, 145.2, 34.5)
USB_TOP, USB_T = -9.6, 1.0
USB_BOSSES = [(142.0, 16.5), (142.0, 32.5)]
USB_BOSS_D, USB_PILOT, USB_PILOT_DEPTH = 3.5, 1.3, 4.5    # M1.6 PT screw
COVER_RIBS = [(37.0, 16.6, 101.0, 17.8), (37.0, 32.2, 101.0, 33.4)]   # X0, y0, X1, y1
RIB_Z = -5.0
SPK_RIB = dict(r_in=14.2, r_out=15.2, half_deg=15.0, angles=(0.0, 120.0, 240.0), z=-4.0)

# shell inside
BATTERY = (106.0, 4.5, 136.0, 44.5)  # 30 x 40 x 10 pack (moved 1 mm toward the head vs mockup outline)
BATT_Z = (-13.2, -3.2)               # 0.5 foam below, ~1.2 swelling room above
BATT_RIBS = [(104.8, 10.0, 105.8, 39.0), (136.3, 10.0, 137.3, 39.0)]
BATT_RIB_H = 3.0
PICKUP_HOLE = (99.0, 24.5, 4.0)      # default pigtail hole in the control-zone floor (X, y, Ø)
SPK_WALL = (34.0, 35.0, -2.4)        # speaker partition X0, X1, top Z (0.5 PORON strip seals to the cover)
SPK_WALL_NOTCH = (6.5, 9.5, 2.0)     # speaker-wire notch at the top of the partition: y0, y1, depth

# envelopes (electronics proposal)
ENC_BODY, ENC_BODY_TOP, BUSH_D, BUSH_TOP, SHAFT_TOP = (12.0, 12.0), -5.5, 7.0, -0.5, 5.0
JACK_BODY_D, JACK_BODY_TOP, JACK_NOSE_D, JACK_TOP = 9.0, -2.3, 6.0, -0.2
SW_BODY, SW_BODY_TOP, SW_ACT_D, SW_TOP = 6.0, -8.5, 3.5, -7.0
LED_BOX, LED_TOP = (1.6, 0.8), -11.2
BOTTOM_ENV = -14.5                   # main-board bottom-side parts and screw heads
REC = (3.26, 8.94, -0.3)             # USB-C receptacle (X, y, top Z)
SPK_Z = (-8.0, -2.5)                 # speaker body; front gasket -2.5..-2.0, rear foam to the floor

# small parts
KNOB_D, KNOB_H, KNOB_LIFT = 13.0, 6.5, 0.5
BORE_D, BORE_FLAT, BORE_DEPTH = 6.0, 4.5, 5.0
# V0.3: 3 crush ribs on the round part of the D bore (90/180/270 deg; the flat is at 0 deg) so the
# plastic knob keeps its grip on the metal shaft; 0.08 high = 0.16 diametral interference.
KNOB_RIB_ANGLES, KNOB_RIB_W, KNOB_RIB_H, KNOB_RIB_Z0 = (90, 180, 270), 0.5, 0.08, 0.8
CAP_STEM_D, CAP_TOP, CAP_FLANGE_D, CAP_FLANGE_T, CAP_PLUNGER_D, CAP_BOTTOM = 5.4, 0.5, 6.6, 0.8, 3.0, -6.9
LP_D, LP_TOP, LP_FLANGE_D, LP_FLANGE_T, LP_BOTTOM = 3.0, 0.0, 4.0, 0.8, -10.9

# =====================================================================================
# HELPERS
# =====================================================================================
ZV = cq.Vector(0, 0, 1)


def V(X, y, z=0.0):
    return cq.Vector(X, -y, z)


def box(x0, y0, x1, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, -y1, z0))


def cyl(X, y, d, z0, z1):
    return cq.Solid.makeCylinder(d / 2, z1 - z0, V(X, y, z0), ZV)


def rrect(x0, y0, x1, y1, r, z0, z1):
    s = (cq.Workplane("XY").workplane(offset=z0).center((x0 + x1) / 2, -(y0 + y1) / 2)
         .rect(x1 - x0, y1 - y0).extrude(z1 - z0))
    if r > 0:
        s = s.edges("|Z").fillet(r)
    return s.val()


def fuse(shapes):
    out = shapes[0]
    if len(shapes) > 1:
        out = out.fuse(*shapes[1:])
    return out.clean()


def arc_rib(cx, cy, r_in, r_out, a0, a1, z0, z1, n=12):
    pts_o = [(cx + r_out * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
              -(cy + r_out * math.sin(math.radians(a0 + (a1 - a0) * i / n)))) for i in range(n + 1)]
    pts_i = [(cx + r_in * math.cos(math.radians(a1 - (a1 - a0) * i / n)),
              -(cy + r_in * math.sin(math.radians(a1 - (a1 - a0) * i / n)))) for i in range(n + 1)]
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts_o + pts_i).close().extrude(z1 - z0).val()


def engrave(txt, cx, cy, size):
    s, _, _ = M.text_solid(txt, size, M.FONT_LABEL, ENGRAVE + 0.3)
    return s.translate(V(cx, cy, -ENGRAVE))


def snap_sides():
    """(side, X) for every snap; side 'near' = y0 wall, 'far' = y49 wall."""
    return [(s, x) for s in ("near", "far") for x in SNAP_X]


def wall_y(side, u):
    """spec y at outward offset u from the shell inner face of that side."""
    return SHELL_IN - u if side == "near" else W - SHELL_IN + u


def snap_tongue(side, X):
    y_a, y_b = sorted((wall_y(side, 0.0), wall_y(side, -SNAP_T)))
    tongue = box(X - SNAP_W / 2, y_a, X + SNAP_W / 2, y_b, SNAP_TIP, ZC + 0.1)
    prof = [(0.0, SNAP_TIP), (HOOK_D, SNAP_TIP + HOOK_RAMP), (HOOK_D, HOOK_TOP), (0.0, HOOK_TOP)]
    pts = [(-wall_y(side, u), z) for u, z in prof]           # (CAD Y, Z) in the YZ plane
    hook = (cq.Workplane("YZ").workplane(offset=X - SNAP_W / 2).polyline(pts).close()
            .extrude(SNAP_W).val())
    return tongue.fuse(hook).clean()


def notch_tool(X, y, r, z0=-30.0, z1=5.0):
    """Corner notch = disc r around the screw + the square from the screw to the corner."""
    xs = (-3.0, X) if X < L / 2 else (X, L + 3.0)
    ys = (-3.0, y) if y < W / 2 else (y, W + 3.0)
    sq = box(xs[0], ys[0], xs[1], ys[1], z0, z1)
    return cyl(X, y, 2 * r, z0, z1).fuse(sq)


# =====================================================================================
# PARTS
# =====================================================================================
def build_cover(text=True):
    plate = rrect(0, 0, L, W, R, ZC, 0.0)
    add = []
    for X, y in PCB_BOSSES:
        add.append(cyl(X, y, BOSS_D, PCB_TOP, ZC + 0.1))
    for X, y in USB_BOSSES:
        add.append(cyl(X, y, USB_BOSS_D, USB_TOP, ZC + 0.1))
    for x0, y0, x1, y1 in COVER_RIBS:
        add.append(box(x0, y0, x1, y1, RIB_Z, ZC + 0.1))
    for a in SPK_RIB["angles"]:
        add.append(arc_rib(SPEAKER[0], SPEAKER[1], SPK_RIB["r_in"], SPK_RIB["r_out"],
                           a - SPK_RIB["half_deg"], a + SPK_RIB["half_deg"], SPK_RIB["z"], ZC + 0.1))
    for side, X in snap_sides():
        add.append(snap_tongue(side, X))
    body = plate.fuse(*add).clean()

    zlo, zhi = -20.0, 1.0
    cut = []
    for _, X, y in KNOBS:
        cut.append(cyl(X, y, ENC_HOLE_D, zlo, zhi))
    for _, X, y in JACKS:
        cut.append(cyl(X, y, JACK_HOLE_D, zlo, zhi))
    for _, X, y in BUTTONS:
        cut.append(cyl(X, y, BTN_HOLE_D, zlo, zhi))
    for X, y in LEDS:
        cut.append(cyl(X, y, LP_HOLE_D, zlo, zhi))
    for X, y in M.grille_points():
        cut.append(cyl(X, y, M.GRILLE_HOLE_D, zlo, zhi))
    cut.append(cq.Workplane("XY").workplane(offset=zlo).center(USBC[0], -USBC[1])
               .slot2D(USBC_SLOT[0], USBC_SLOT[1], angle=90).extrude(zhi - zlo).val())
    csk_h = (CSK_D - SCREW_D) / 2
    for X, y in SCREWS:
        cut.append(cyl(X, y, SCREW_D, zlo, zhi))
        cut.append(cq.Solid.makeCone(SCREW_D / 2, CSK_D / 2, csk_h, V(X, y, -csk_h), ZV))
        cut.append(cyl(X, y, CSK_D, 0.0, zhi))
    for X, y in PCB_BOSSES:
        cut.append(cyl(X, y, BOSS_PILOT, PCB_TOP - 1, PCB_TOP + BOSS_PILOT_DEPTH))
    for X, y in USB_BOSSES:
        cut.append(cyl(X, y, USB_PILOT, USB_TOP - 1, USB_TOP + USB_PILOT_DEPTH))
    if text:
        for t, X, y, size in M.labels():
            cut.append(engrave(t, X, y, size))
        t, X, y, size = M.LOGO
        cut.append(engrave(t, X, y, size))
    return body.cut(*cut).clean()


def build_shell():
    zones = [(SHELL_OUT, ZONE_X[0], OUT_BOT[0]), (ZONE_X[0], ZONE_X[1], OUT_BOT[1]),
             (ZONE_X[1], L - SHELL_OUT, OUT_BOT[2])]
    outer = fuse([box(x0, SHELL_OUT, x1, W - SHELL_OUT, zb, ZC) for x0, x1, zb in zones])
    inner_zones = [(SHELL_IN, ZONE_X[0] + RISER, IN_FLOOR[0]), (ZONE_X[0] + RISER, ZONE_X[1] - RISER, IN_FLOOR[1]),
                   (ZONE_X[1] - RISER, L - SHELL_IN, IN_FLOOR[2])]
    inner = fuse([box(x0, SHELL_IN, x1, W - SHELL_IN, zf, ZC + 1.0) for x0, x1, zf in inner_zones])
    for X, y in SCREWS:
        inner = inner.cut(cyl(X, y, 2 * (NOTCH_R + WALL), -30, 5))
    shell = outer.cut(inner)
    ribs = [box(x0, y0, x1, y1, IN_FLOOR[2] - 0.1, IN_FLOOR[2] + BATT_RIB_H) for x0, y0, x1, y1 in BATT_RIBS]
    shell = shell.fuse(*ribs)
    cut = [notch_tool(X, y, NOTCH_R) for X, y in SCREWS]
    for side, X in snap_sides():
        y_a, y_b = sorted((wall_y(side, -0.2), wall_y(side, WALL + 0.2)))
        cut.append(box(X - WIN_W / 2, y_a, X + WIN_W / 2, y_b, WIN_Z[0], WIN_Z[1]))
    X, y, d = PICKUP_HOLE
    cut.append(cyl(X, y, d, OUT_BOT[1] - 1, IN_FLOOR[1] + 1))
    shell = shell.cut(*cut)
    x0, x1, zt = SPK_WALL
    wall = box(x0, SHELL_IN - 0.1, x1, W - SHELL_IN + 0.1, IN_FLOOR[0] - 0.1, zt)
    y0, y1, dn = SPK_WALL_NOTCH
    wall = wall.cut(box(x0 - 1, y0, x1 + 1, y1, zt - dn, zt + 1))
    return shell.fuse(wall).clean()


def build_knob():
    Rk = KNOB_D / 2
    k = (cq.Workplane("XY").circle(Rk).extrude(KNOB_H).faces(">Z").edges().chamfer(M.KNOB_TOP_CHAMFER)
         .faces("<Z").edges().chamfer(0.3))
    rc = Rk + M.KNOB_GROOVE_D / 2 - M.KNOB_GROOVE_DEPTH
    pts = [(rc * math.cos(2 * math.pi * i / M.KNOB_KNURL_N), rc * math.sin(2 * math.pi * i / M.KNOB_KNURL_N))
           for i in range(M.KNOB_KNURL_N)]
    k = k.cut(cq.Workplane("XY").workplane(offset=2.0).pushPoints(pts).circle(M.KNOB_GROOVE_D / 2).extrude(KNOB_H))
    Li = Rk + 1.0 - M.KNOB_INDEX_R0
    k = k.cut(cq.Workplane("XY").workplane(offset=KNOB_H - M.KNOB_INDEX_DEPTH)
              .center(M.KNOB_INDEX_R0 + Li / 2, 0).rect(Li, M.KNOB_INDEX_W).extrude(M.KNOB_INDEX_DEPTH + 1))
    flat = BORE_FLAT - BORE_D / 2                      # flat face distance from the axis (+X side)
    bore = cq.Workplane("XY").workplane(offset=-0.5).circle(BORE_D / 2).extrude(BORE_DEPTH + 0.5)
    bore = bore.cut(cq.Workplane("XY").workplane(offset=-1).center(flat + BORE_D, 0)
                    .rect(2 * BORE_D, 2 * BORE_D).extrude(BORE_DEPTH + 2))
    k = k.cut(bore)
    r_in = BORE_D / 2 - KNOB_RIB_H
    for a in KNOB_RIB_ANGLES:                      # ribs run from the lead-in (Z0) to the bore bottom
        rib = (cq.Workplane("XY").workplane(offset=KNOB_RIB_Z0).center(r_in + 0.15, 0)
               .rect(0.3, KNOB_RIB_W).extrude(BORE_DEPTH - KNOB_RIB_Z0)
               .rotate((0, 0, 0), (0, 0, 1), a))
        k = k.union(rib)
    return k.val().clean()                         # local: bottom at Z0, top at KNOB_H


def build_cap():
    s = cq.Workplane("XY").workplane(offset=ZC).circle(CAP_STEM_D / 2).extrude(CAP_TOP - ZC).faces(">Z").edges().chamfer(0.3)
    s = s.union(cq.Workplane("XY").workplane(offset=ZC - CAP_FLANGE_T).circle(CAP_FLANGE_D / 2).extrude(CAP_FLANGE_T))
    s = s.union(cq.Workplane("XY").workplane(offset=CAP_BOTTOM).circle(CAP_PLUNGER_D / 2)
                .extrude(ZC - CAP_FLANGE_T - CAP_BOTTOM + 0.01))
    return s.val().clean()                         # local: axis at X=Y=0, Z as installed


def build_lightpipe():
    s = cq.Workplane("XY").workplane(offset=LP_BOTTOM).circle(LP_D / 2).extrude(LP_TOP - LP_BOTTOM)
    s = s.union(cq.Workplane("XY").workplane(offset=ZC - LP_FLANGE_T).circle(LP_FLANGE_D / 2).extrude(LP_FLANGE_T))
    return s.faces("<Z").edges().chamfer(0.2).val().clean()


def build_violin():
    slab = box(-30.0, W / 2 - 35.0, L + 30.0, W / 2 + 35.0, -25.0, 0.0)
    rebate = rrect(-POCKET_GAP, -POCKET_GAP, L + POCKET_GAP, W + POCKET_GAP, R + POCKET_GAP, ZC, 1.0)
    e = LEDGE_IN
    zones = [(e, POCKET_STEP_X[0], -DEPTH[0]), (POCKET_STEP_X[0], POCKET_STEP_X[1], -DEPTH[1]),
             (POCKET_STEP_X[1], L - e, -DEPTH[2])]
    deep = fuse([box(x0, e, x1, W - e, zb, ZC + 0.5) for x0, x1, zb in zones])
    for X, y in SCREWS:
        deep = deep.cut(notch_tool(X, y, PAD_R))
    v = slab.cut(rebate).cut(deep)
    for X, y in SCREWS:
        v = v.cut(cyl(X, y, PILOT_WOOD[0], ZC - PILOT_WOOD[1], ZC + 0.5))
    return v.clean()


# ---- envelopes -------------------------------------------------------------------------
def build_pcba():
    x0, y0, x1, y1 = PCB
    pcb = box(x0, y0, x1, y1, PCB_TOP - PCB_T, PCB_TOP)
    for X, y in PCB_BOSSES:
        pcb = pcb.cut(cyl(X, y, 2.2, PCB_TOP - 2, PCB_TOP + 1))
    parts = {"pcb": pcb}
    top = []
    for _, X, y in KNOBS:
        ex, ey = ENC_BODY
        top.append(box(X - ex / 2, y - ey / 2, X + ex / 2, y + ey / 2, PCB_TOP, ENC_BODY_TOP))
        top.append(cyl(X, y, BUSH_D, ENC_BODY_TOP, BUSH_TOP))
        sh = cyl(X, y, BORE_D - 0.02, BUSH_TOP, SHAFT_TOP)
        sh = sh.cut(box(X + BORE_FLAT - BORE_D / 2 - 0.01, y - 4, X + 4, y + 4, BUSH_TOP + 1.0, SHAFT_TOP + 1))
        top.append(sh)
    for _, X, y in JACKS:
        top.append(cyl(X, y, JACK_BODY_D, PCB_TOP, JACK_BODY_TOP))
        top.append(cyl(X, y, JACK_NOSE_D, JACK_BODY_TOP, JACK_TOP))
    for _, X, y in BUTTONS:
        s = SW_BODY / 2
        top.append(box(X - s, y - s, X + s, y + s, PCB_TOP, SW_BODY_TOP))
        top.append(cyl(X, y, SW_ACT_D, SW_BODY_TOP, SW_TOP))
    for X, y in LEDS:
        lx, ly = LED_BOX
        top.append(box(X - lx / 2, y - ly / 2, X + lx / 2, y + ly / 2, PCB_TOP, LED_TOP))
    parts["top_parts"] = fuse(top)
    bot = box(x0 + 0.5, y0 + 0.5, x1 - 0.5, y1 - 0.5, BOTTOM_ENV, PCB_TOP - PCB_T)
    parts["bottom_envelope"] = bot
    return parts


def build_usb():
    x0, y0, x1, y1 = USB_BOARD
    b = box(x0, y0, x1, y1, USB_TOP - USB_T, USB_TOP)
    for X, y in USB_BOSSES:
        b = b.cut(cyl(X, y, 1.8, USB_TOP - 2, USB_TOP + 1))
    rx, ry, rz = REC
    X, y = USBC
    rec = (cq.Workplane("XY").workplane(offset=USB_TOP).center(X, -y).slot2D(ry, rx, angle=90)
           .extrude(rz - USB_TOP).val())
    return {"usb_board": b, "usb_receptacle": rec}


def build_misc():
    out = {}
    x0, y0, x1, y1 = BATTERY
    out["battery"] = box(x0, y0, x1, y1, *BATT_Z)
    out["speaker"] = cyl(SPEAKER[0], SPEAKER[1], SPEAKER_D, *SPK_Z)
    out["speaker_gasket"] = cyl(SPEAKER[0], SPEAKER[1], 28.0, SPK_Z[1], ZC).cut(
        cyl(SPEAKER[0], SPEAKER[1], 24.0, SPK_Z[1] - 1, 1))
    out["speaker_foam"] = cyl(SPEAKER[0], SPEAKER[1], 20.0, IN_FLOOR[0], SPK_Z[0])
    out["battery_foam"] = box(x0 + 2, y0 + 2, x1 - 2, y1 - 2, IN_FLOOR[2], BATT_Z[0])
    wx0, wx1, zt = SPK_WALL
    out["speaker_seal_strip"] = box(wx0, SHELL_IN, wx1, W - SHELL_IN, zt, ZC)
    return out


def build_screws():
    out = {}
    for i, (X, y) in enumerate(SCREWS, 1):
        head = cq.Solid.makeCone(1.1, 1.9, 0.8, V(X, y, -0.35 - 0.8), ZV)
        sh = cyl(X, y, 2.2, ZC, -1.15).fuse(cyl(X, y, PILOT_WOOD[0], -9.85, ZC + 0.01))
        out[f"screw_ST2.2x9.5_{i}"] = head.fuse(sh).clean()
    for i, (X, y) in enumerate(PCB_BOSSES, 1):
        out[f"screw_M2x5_{i}"] = cyl(X, y, 3.5, PCB_TOP - PCB_T - 1.3, PCB_TOP - PCB_T).fuse(
            cyl(X, y, BOSS_PILOT, PCB_TOP - PCB_T - 0.01, PCB_TOP + 4.0))
    for i, (X, y) in enumerate(USB_BOSSES, 1):
        out[f"screw_M1.6x4_{i}"] = cyl(X, y, 3.0, USB_TOP - USB_T - 1.0, USB_TOP - USB_T).fuse(
            cyl(X, y, USB_PILOT, USB_TOP - USB_T - 0.01, USB_TOP + 3.0))
    return out


# =====================================================================================
# ASSEMBLY + CHECKS
# =====================================================================================
def build_all(text=True):
    P = {}
    P["cover"] = build_cover(text)
    P["shell"] = build_shell()
    knob = build_knob()
    for i, (n, X, y) in enumerate(KNOBS, 1):
        P[f"knob_{n}"] = knob.translate(cq.Vector(X, -y, KNOB_LIFT))
    cap = build_cap()
    for n, X, y in BUTTONS:
        P[f"cap_{n}"] = cap.translate(cq.Vector(X, -y, 0))
    lp = build_lightpipe()
    for i, (X, y) in enumerate(LEDS, 1):
        P[f"lightpipe_{i}"] = lp.translate(cq.Vector(X, -y, 0))
    pc = build_pcba()
    P.update({f"pcba_{k}": v for k, v in pc.items()})
    P.update(build_usb())
    P.update(build_misc())
    P.update(build_screws())
    P["violin"] = build_violin()
    return P, knob, cap, lp


GROUP = lambda n: n.split("_")[0] if not n.startswith(("pcba", "usb", "screw_")) else (
    "pcba" if n.startswith("pcba") else "usb" if n.startswith("usb") else n)

# designed contacts or fits (zero-volume touch allowed, or modelled thread engagement)
ALLOWED = [
    ("knob", "pcba"),                       # knob bore on the encoder shaft (fit)
    ("cover", "pcba"),                      # bosses on the board, bushings and jack noses in holes
    ("cover", "usb"),                       # bosses on the USB board, receptacle in the slot
    ("cover", "cap"), ("cover", "lightpipe"), ("cover", "speaker"), ("cover", "screw"),
    ("screw", "violin"), ("screw", "pcba"), ("screw", "usb"),
    ("shell", "battery"), ("shell", "speaker"),       # foams sit on the floors
    ("speaker", "speaker"), ("battery", "battery"),
]


def allowed(a, b):
    ga, gb = GROUP(a), GROUP(b)
    ka = "screw" if ga.startswith("screw_") else ga
    kb = "screw" if gb.startswith("screw_") else gb
    ka = "speaker" if a.startswith("speaker") else "battery" if a.startswith("battery") else ka
    kb = "speaker" if b.startswith("speaker") else "battery" if b.startswith("battery") else kb
    return (ka, kb) in ALLOWED or (kb, ka) in ALLOWED


def interference(P, tol=1e-3):
    names = list(P)
    bbs = {n: P[n].BoundingBox() for n in names}
    res = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, B = bbs[a], bbs[b]
            if (A.xmax < B.xmin or B.xmax < A.xmin or A.ymax < B.ymin or B.ymax < A.ymin
                    or A.zmax < B.zmin or B.zmax < A.zmin):
                continue
            try:
                v = P[a].intersect(P[b]).Volume()
            except Exception as e:  # noqa: BLE001
                v = float("nan")
                print("  intersect failed", a, b, e)
            if v > tol or v != v:
                res.append((a, b, v, allowed(a, b)))
    return res


def min_distance(a, b):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value() if d.IsDone() else float("nan")


CLEARANCE_PAIRS = [
    ("shell", "violin", 0.2, "底壳与琴槽（侧 0.25 / 底 0.3）"),
    ("cover", "shell", 0.0, "面盖与底壳（卡扣贴合，0 = 正常接触）"),
    ("pcba_top_parts", "shell", 0.3, "主板元件与底壳"),
    ("pcba_pcb", "shell", 0.3, "主板与底壳"),
    ("pcba_bottom_envelope", "shell", 0.5, "主板背面包络与壳底"),
    ("pcba_top_parts", "cover", 0.0, "主板元件与面盖（插座/编码器在孔里）"),
    ("battery", "shell", 0.0, "电池与底壳/限位筋"),
    ("battery", "cover", 1.0, "电池顶与面盖（鼓胀余量）"),
    ("battery", "usb_board", 0.5, "电池与 USB 小板"),
    ("speaker", "shell", 0.5, "扬声器与底壳侧壁"),
    ("usb_board", "shell", 0.3, "USB 小板与底壳"),
    ("usb_receptacle", "cover", 0.05, "USB-C 座与面盖槽"),
]


def report_clearances(P):
    out = []
    for a, b, need, desc in CLEARANCE_PAIRS:
        d = min_distance(P[a], P[b])
        out.append(dict(a=a, b=b, min=round(d, 3), need=need, ok=d >= need - 1e-3, desc=desc))
    # per-feature clearances worth printing on the drawings
    cap = P[f"cap_{BUTTONS[0][0]}"]
    out.append(dict(a="cap", b="switch", min=round(CAP_BOTTOM - SW_TOP, 3), need=0.05, ok=CAP_BOTTOM - SW_TOP >= 0.05,
                    desc="按键帽触头与轻触开关（静止间隙）"))
    out.append(dict(a="lightpipe", b="LED", min=round(LP_BOTTOM - LED_TOP, 3), need=0.2, ok=LP_BOTTOM - LED_TOP >= 0.2,
                    desc="导光柱底与 LED 顶"))
    out.append(dict(a="knob", b="shaft top", min=round(KNOB_LIFT + BORE_DEPTH - SHAFT_TOP, 3), need=0.3,
                    ok=KNOB_LIFT + BORE_DEPTH - SHAFT_TOP >= 0.3, desc="旋钮孔底与轴端"))
    del cap
    return out


# =====================================================================================
# EXPORT
# =====================================================================================
COLORS = {"cover": (0.17, 0.17, 0.18), "shell": (0.30, 0.30, 0.32), "knob": (0.12, 0.12, 0.13),
          "cap": (0.12, 0.12, 0.13), "lightpipe": (0.85, 0.92, 0.95), "pcba": (0.20, 0.55, 0.30),
          "usb": (0.25, 0.50, 0.75), "battery": (0.85, 0.72, 0.35), "speaker": (0.55, 0.55, 0.60),
          "screw": (0.70, 0.70, 0.72), "violin": (0.72, 0.52, 0.32)}


def color_of(n):
    for k in COLORS:
        if n.startswith(k):
            return COLORS[k]
    return (0.6, 0.6, 0.6)


def export(P, knob, cap, lp, outdir):
    sd, td = os.path.join(outdir, "step"), os.path.join(outdir, "stl")
    os.makedirs(sd, exist_ok=True)
    os.makedirs(td, exist_ok=True)
    single = {"R5-01_cover": P["cover"], "R5-02_shell": P["shell"], "R5-03_knob": knob,
              "R5-04_button_cap": cap, "R5-05_light_pipe": lp, "R5-06_violin_pocket": P["violin"]}
    for n, s in single.items():
        cq.exporters.export(s, os.path.join(sd, n + ".step"))
        if n != "R5-06_violin_pocket":
            cq.exporters.export(s, os.path.join(td, n + ".stl"), tolerance=0.01, angularTolerance=0.1)
    env = cq.Compound.makeCompound([P[n] for n in P if n.startswith(("pcba", "usb", "battery", "speaker"))])
    cq.exporters.export(env, os.path.join(sd, "R5-90_electronics_envelopes.step"))
    asm = cq.Assembly(name="SmartVio_R5_module")
    for n, s in P.items():
        if n == "violin":
            continue
        asm.add(s, name=n, color=cq.Color(*color_of(n)))
    asm.save(os.path.join(sd, "R5-00_assembly.step"))
    asm2 = cq.Assembly(name="SmartVio_R5_installed")
    for n, s in P.items():
        asm2.add(s, name=n, color=cq.Color(*color_of(n)))
    asm2.save(os.path.join(sd, "R5-00_assembly_in_violin.step"))


def params():
    keys = [k for k in globals() if k.isupper() and not k.startswith("_")]
    out = {}
    for k in keys:
        v = globals()[k]
        if isinstance(v, (int, float, str, tuple, list, dict)) and k not in ("COLORS", "ALLOWED", "CLEARANCE_PAIRS"):
            out[k] = v
    out["grille_points"] = M.grille_points()
    out["labels"] = M.labels()
    out["logo"] = M.LOGO
    return out


# =====================================================================================
# PREVIEWS
# =====================================================================================
def render_previews(P, outdir):
    pd = os.path.join(outdir, "preview")
    os.makedirs(pd, exist_ok=True)
    mesh = {}

    def m(n, tol=0.03, ang=0.3):
        if n not in mesh:
            mesh[n] = M.mesh_of(P[n], tol, ang)
        return mesh[n]

    module = [n for n in P if n != "violin" and not n.endswith(("gasket", "foam"))]
    print("  preview: top")
    M.render([(*m("cover", 0.02, 0.25), (0.30, 0.30, 0.32))] + [(*m(n), color_of(n)) for n in P if n.startswith(("knob", "cap", "lightpipe"))]
             + [(*m(n), color_of(n)) for n in P if n.startswith(("screw_ST", "pcba_top", "usb_rec"))],
             os.path.join(pd, "01_top.png"), "top", size=(1900, 780), ssaa=2, margin=40, edge_thr=0.12,
             caption="R5 外壳 V0.3 · 顶视（琴头在左，G 弦侧在上）  148 × 49，旋钮高出 7 mm")
    print("  preview: installed 3/4")
    M.render([(*m("violin", 0.05, 0.4), color_of("violin"))] + [(*m(n), color_of(n)) for n in module if n.startswith(("cover", "knob", "cap", "lightpipe", "screw_ST", "pcba_top", "usb_rec"))],
             os.path.join(pd, "02_installed.png"), (-120.0, 35.0), size=(1900, 1100), ssaa=2, margin=40, edge_thr=0.3,
             caption="装琴状态：面盖与琴背齐平，只有旋钮高出")
    print("  preview: exploded")
    off = {"cover": 34.0, "knob": 46.0, "cap": 40.0, "lightpipe": 40.0, "pcba": 10.0, "usb": 10.0, "screw_M": 4.0,
           "battery": -8.0, "speaker": 22.0, "shell": -26.0}
    ex = []
    for n in module:
        if n.startswith("screw_ST"):
            continue
        dz = next((v for k, v in off.items() if n.startswith(k)), 0.0)
        Vv, F = m(n)
        ex.append((Vv + np.array([0, 0, dz]), F, color_of(n)))
    M.render(ex, os.path.join(pd, "03_exploded.png"), (-118.0, 28.0), size=(1900, 1300), ssaa=2, margin=40, edge_thr=0.3,
             caption="爆炸图：旋钮 / 按键帽、导光柱 / 面盖 / 扬声器 / 主板、USB 小板（包络）/ 电池 / 底壳")
    print("  preview: section")
    cutbox = box(-40, -40, L + 40, 24.5, -40, 20)
    sec = []
    for n in list(module) + ["violin"]:
        try:
            s = P[n].intersect(cutbox)
        except Exception:  # noqa: BLE001
            continue
        if s.Volume() < 1e-6:
            continue
        Vv, F = M.mesh_of(s, 0.03, 0.3)
        sec.append((Vv, F, color_of(n)))
    M.render(sec, os.path.join(pd, "04_section.png"), (-90.0, 6.0), size=(1900, 900), ssaa=2, margin=40, edge_thr=0.3,
             light=(0.15, -0.9, 0.45),
             caption="剖切 y = 24.5（插座中心线）：三段槽深 11 / 17 / 15，面盖压在 2 mm 台阶上")
    print("  preview: cover underside, shell")
    cv = m("cover", 0.02, 0.25)
    flip = np.array([1, -1, -1])
    M.render([(cv[0] * flip, cv[1], (0.30, 0.30, 0.32))], os.path.join(pd, "05_cover_underside.png"), (-115.0, 40.0),
             size=(1900, 1000), ssaa=2, margin=40, edge_thr=0.25, caption="面盖背面：主板凸台 4、USB 凸台 2、卡扣 8、加强筋 2、扬声器定位筋 3")
    M.render([(*m("shell"), (0.45, 0.45, 0.48))], os.path.join(pd, "06_shell.png"), (-115.0, 40.0),
             size=(1900, 1000), ssaa=2, margin=40, edge_thr=0.25, caption="底壳：三段台阶、四角让位缺口（让琴上木垫）、卡扣窗 8、电池限位筋、扬声器隔板")


# =====================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    print("building parts ...", flush=True)
    P, knob, cap, lp = build_all(text=True)
    for n in ("cover", "shell", "violin"):
        print(f"  {n}: valid={P[n].isValid()} volume={P[n].Volume():.1f} mm3", flush=True)
    print("interference check ...", flush=True)
    Pc = dict(P)
    Pc["cover"] = build_cover(text=False)        # engraving does not change fits; faster booleans
    bad = interference(Pc)
    hard = [r for r in bad if not r[3]]
    for a_, b_, v, ok in bad:
        print(f"  {'allowed ' if ok else 'CONFLICT'} {a_} x {b_}: {v:.4f} mm3")
    print("clearances ...", flush=True)
    cl = report_clearances(Pc)
    for c in cl:
        print(f"  {'ok ' if c['ok'] else 'LOW'} {c['desc']}: {c['min']} (need >= {c['need']})")
    export(P, knob, cap, lp, a.out)
    with open(os.path.join(a.out, "enclosure_params.json"), "w", encoding="utf8") as f:
        json.dump(params(), f, ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "checks.json"), "w", encoding="utf8") as f:
        json.dump(dict(interference=[dict(a=x, b=y, volume=round(v, 4), allowed=ok) for x, y, v, ok in bad],
                       clearances=cl, conflicts=len(hard)), f, ensure_ascii=False, indent=1)
    if not a.no_render:
        render_previews(P, a.out)
    print("done." if not hard and all(c["ok"] for c in cl) else "done WITH PROBLEMS (see above).")


if __name__ == "__main__":
    main()
