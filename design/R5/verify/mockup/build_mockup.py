#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SmartVio R5 - 1:1 panel mockup for 3D printing + 1:1 paper template.

Run (CadQuery 2.8 on Python 3.13; cqpy = the pip --target folder that holds cadquery):
    PYTHONPATH=/path/to/cqpy python3 build_mockup.py              # build + check + previews
    PYTHONPATH=/path/to/cqpy python3 build_mockup.py --no-render  # skip the PNG previews

Outputs (written next to this script):
    cover_plate.step / cover_plate.stl   cover plate (STL already in print orientation: top up)
    knob.step                            knob in use orientation (bottom at Z=0)
    knob.stl                             knob in PRINT orientation (top face on the bed); print x3
    template_1to1.pdf / .svg             A4 1:1 paper template (print the PDF at 100 %)
    preview_top.png, preview_34.png, preview_knob.png

Coordinates (same as the R5 layout notes):
    X  along the plate: 0 = head (scroll) end, 148 = tail end.
    y  across the plate: 0 = G-string long edge, 49 = E-string long edge.
    Seen from OUTSIDE (looking at the violin back) with the head on the left, the G edge
    is at the TOP, so y runs DOWN the page (like image coordinates).
    CAD frame used for STEP/STL: X = X, Y = -y, Z = out of the visible face
    (plate bottom at Z = 0, top at Z = PLATE_T). This keeps the part un-mirrored.
"""
import argparse
import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np
import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))

# =====================================================================================
# PARAMETERS (mm)
# =====================================================================================
# --- cover plate ---------------------------------------------------------------------
PLATE_L, PLATE_W, PLATE_T, PLATE_R = 148.0, 49.0, 2.0, 4.0
LIP_H = 0.0   # underside perimeter rib height. 0 = off (default): a 2 mm plate is stiff
LIP_W = 1.6   # enough, and a rib would lift the plate from 2.0 to 3.5 mm above the back.

# --- holes for the MOCKUP panel-mount parts ------------------------------------------
ENC_HOLE_D = 7.3    # EC11 encoder bushing, M7x0.75
JACK_HOLE_D = 6.3   # 3.5 mm stereo panel jack, M6 thread (PJ-392 style)
BTN_HOLE_D = 7.2    # 7 mm panel momentary push button (PBS-110 style)
LED_HOLE_D = 3.2    # 3 mm LED
USBC_SLOT_L = 9.2   # along y (across the plate)
USBC_SLOT_W = 3.4   # along X, round ends (position only)
SCREW_D, CSK_D, CSK_ANGLE = 2.4, 4.5, 90.0          # corner holes, 90 deg countersink
GRILLE_HOLE_D, GRILLE_PITCH, GRILLE_FIELD_D = 1.2, 2.4, 26.0

# --- engraving -----------------------------------------------------------------------
LABEL_DEPTH = 0.6        # control labels, "SmartVio"
ICON_DEPTH = 0.4         # battery icon
LIGHT_DEPTH = 0.3        # zone lines, battery outline, speaker ring
LIGHT_LINE_W = 0.5
FONT_LABEL = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_CJK = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

# --- hardware envelopes used by the clearance check (measure your parts!) ------------
# above the plate (round envelopes, diameters)
KNOB_D = 13.0            # knob cap
ENC_NUT_D = 11.0         # M7 hex nut, across corners (approx.)
JACK_NUT_D = 9.2         # M6 hex nut across corners / knurled nut
BTN_TOP_D = 10.0         # PBS-110 nut / collar
# below the plate
ENC_BODY = (12.0, 12.0)  # EC11 body (X, y); turn pin rows toward head/tail (X)
JACK_BODY_D = 9.0
BTN_BODY_D = 10.0
LED_FLANGE_D = 3.8
MIN_WEB = 1.0            # min plastic between two holes, or hole and plate edge
MIN_GAP = 0.5            # min gap between hardware envelopes / labels
# height stack of a typical EC11 + nut
ENC_BUSHING_L = 5.0      # M7 bushing length above the encoder body
ENC_NUT_T = 2.0          # nut thickness

# --- knob cap ------------------------------------------------------------------------
KNOB_H = 7.0
KNOB_KNURL_N = 24        # grooves around
KNOB_GROOVE_D = 0.9      # round groove cutter
KNOB_GROOVE_DEPTH = 0.45
KNOB_SKIRT_H = 2.2       # smooth band at the bottom (wall around the nut recess)
KNOB_TOP_CHAMFER = 0.5
KNOB_INDEX_W, KNOB_INDEX_DEPTH, KNOB_INDEX_R0 = 0.8, 0.6, 3.4
SHAFT_D, SHAFT_FLAT = 6.0, 4.5   # 6 mm D-shaft, 4.5 mm across the flat
BORE_CLEAR = 0.15        # diametral clearance in the printed bore
BORE_DEPTH = 6.0         # from the knob bottom
NUT_REC_D, NUT_REC_H = 11.2, 1.8    # underside recess: swallows the M7 nut
BUSH_REC_D, BUSH_REC_H = 7.8, 2.8   # underside recess: swallows the bushing end
KNOB_LIFT = 0.5          # gap knob bottom -> plate top when mounted

# --- violin placement (README / template) --------------------------------------------
TAIL_DATUM_HEAD_END = 258.0   # plate head end (X=0) is 258 mm from the tail datum
CAVITY_FROM_TAIL = (145.0, 223.0)   # old control cavity, along the violin
CAVITY_WIDTH = 42.0                 # across; assumed centred under the plate

# =====================================================================================
# LAYOUT (X, y) - confirmed R5 layout
# =====================================================================================
SPEAKER = (17.0, 24.5)
SPEAKER_D = 28.0
ZONES = [0.0, 34.0, 104.0, 148.0]
KNOBS = [("VOL", 51.0, 9.0), ("TONE", 71.0, 9.0), ("FX", 91.0, 9.0)]
JACKS = [("PHONES", 49.0, 24.5), ("AUX", 64.0, 24.5), ("LINE", 79.0, 24.5), ("SEND", 94.0, 24.5)]
BUTTONS = [("PWR", 45.0, 40.0), ("BT", 57.0, 40.0), ("MODE", 69.0, 40.0), ("FX", 81.0, 40.0),
           ("MIX", 93.0, 40.0)]
LED_FOR = ["PWR", "BT", "MODE"]
LEDS_SPEC = [(50.5, 40.0), (62.5, 40.0), (74.5, 40.0)]      # final product (PCB tact switches)
LEDS_MOCKUP = [(51.0, 35.0), (63.0, 35.0), (75.0, 35.0)]    # mockup: above the button gaps
USE_SPEC_LED_POSITIONS = False   # True only if the buttons have no ~10 mm nut
USBC = (142.0, 24.5)
BATTERY = (107.0, 4.5, 137.0, 44.5)       # X0, y0, X1, y1 (reference outline only)
SCREWS = [(5.3, 5.3), (142.7, 5.3), (5.3, 43.7), (142.7, 43.7)]

# label = (text, centre X, centre y of the ink box, font size em)
KNOB_LABEL_Y, KNOB_LABEL_SIZE = 17.7, 3.0     # ink 16.6..18.8 (baseline ~18.8)
JACK_LABEL_Y, JACK_LABEL_SIZE = 31.3, 2.8     # ink 30.2..32.4 (moved up from ~33 for LEDs)
BTN_LABEL_Y, BTN_LABEL_SIZE = 46.95, 2.8      # ink 45.9..48.0
USBC_LABEL = ("USB-C", 142.3, 31.7, 2.4)
LOGO = ("SmartVio", 122.0, 29.5, 4.5)
BATTERY_ICON_C = (122.0, 16.0)


def leds():
    return LEDS_SPEC if USE_SPEC_LED_POSITIONS else LEDS_MOCKUP


def labels():
    out = [(t, x, KNOB_LABEL_Y, KNOB_LABEL_SIZE) for t, x, _ in KNOBS]
    out += [(t, x, JACK_LABEL_Y, JACK_LABEL_SIZE) for t, x, _ in JACKS]
    out += [(t, x, BTN_LABEL_Y, BTN_LABEL_SIZE) for t, x, _ in BUTTONS]
    out.append(USBC_LABEL)
    return out


def grille_points():
    pts = []
    rmax = GRILLE_FIELD_D / 2 - GRILLE_HOLE_D / 2
    dy = GRILLE_PITCH * math.sqrt(3) / 2
    n = int(GRILLE_FIELD_D / GRILLE_PITCH) + 2
    for j in range(-n, n + 1):
        off = GRILLE_PITCH / 2 if j % 2 else 0.0
        for i in range(-n, n + 1):
            xx, yy = i * GRILLE_PITCH + off, j * dy
            if math.hypot(xx, yy) <= rmax + 1e-9:
                pts.append((SPEAKER[0] + xx, SPEAKER[1] + yy))
    return pts


def battery_dashes(dash=2.0, gap=1.2):
    """Dashed battery outline as centre-line segments [(x0,y0,x1,y1)], spec coords."""
    x0, y0, x1, y1 = BATTERY
    w = LIGHT_LINE_W
    segs = []

    def side(a, b, fixed, horizontal):
        L = b - a
        n = max(1, round((L + gap) / (dash + gap)))
        d = (L - (n - 1) * gap) / n
        for k in range(n):
            s = a + k * (d + gap)
            segs.append((s, fixed, s + d, fixed) if horizontal else (fixed, s, fixed, s + d))

    side(x0 - w / 2, x1 + w / 2, y0, True)
    side(x0 - w / 2, x1 + w / 2, y1, True)
    side(y0 + w / 2 + gap, y1 - w / 2 - gap, x0, False)
    side(y0 + w / 2 + gap, y1 - w / 2 - gap, x1, False)
    return segs


def battery_icon_rects():
    """Battery icon as rectangles (X0, y0, X1, y1): body outline, nub, 3 bars."""
    cx, cy = BATTERY_ICON_C
    bw, bh, t = 14.0, 7.0, 0.7
    x0, x1, y0, y1 = cx - bw / 2, cx + bw / 2, cy - bh / 2, cy + bh / 2
    r = [(x0, y0, x1, y0 + t), (x0, y1 - t, x1, y1), (x0, y0 + t, x0 + t, y1 - t),
         (x1 - t, y0 + t, x1, y1 - t), (x1, cy - 1.5, x1 + 1.2, cy + 1.5)]
    inner0, inner1 = x0 + t + 0.8, x1 - t - 0.8
    bar_w = (inner1 - inner0 - 2 * 0.8) / 3
    for k in range(3):
        bx = inner0 + k * (bar_w + 0.8)
        r.append((bx, y0 + t + 0.8, bx + bar_w, y1 - t - 0.8))
    return r


# =====================================================================================
# CAD
# =====================================================================================
ZV = cq.Vector(0, 0, 1)


def V(X, y, z=0.0):
    """Spec (X, y) -> CAD vector (Y = -y)."""
    return cq.Vector(X, -y, z)


def sbox(x0, y0, x1, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, -y1, z0))


def hole(X, y, d, zlo, zhi):
    return cq.Solid.makeCylinder(d / 2, zhi - zlo, V(X, y, zlo), ZV)


_text_cache = {}


def text_solid(txt, size, font, height):
    key = (txt, size, font, height)
    if key not in _text_cache:
        s = cq.Workplane("XY").text(txt, size, height, fontPath=font, halign="center",
                                    valign="center", combine=False).val()
        bb = s.BoundingBox()
        s = s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, 0))
        _text_cache[key] = (s, bb.xlen, bb.ylen)
    return _text_cache[key]


def text_box(txt, size, font=FONT_LABEL):
    """Ink box size (w, h) of a label, from the actual glyph outlines."""
    _, w, h = text_solid(txt, size, font, 1.0)
    return w, h


def engrave_text(txt, cx, cy, size, depth, font=FONT_LABEL):
    s, _, _ = text_solid(txt, size, font, depth + 0.3)
    return s.translate(V(cx, cy, PLATE_T - depth))


def build_plate():
    T = PLATE_T
    base = (cq.Workplane("XY").center(PLATE_L / 2, -PLATE_W / 2).rect(PLATE_L, PLATE_W)
            .extrude(T).edges("|Z").fillet(PLATE_R)).val()
    if LIP_H > 0:
        outer = (cq.Workplane("XY").center(PLATE_L / 2, -PLATE_W / 2).rect(PLATE_L, PLATE_W)
                 .extrude(-LIP_H).edges("|Z").fillet(PLATE_R)).val()
        inner = (cq.Workplane("XY").center(PLATE_L / 2, -PLATE_W / 2)
                 .rect(PLATE_L - 2 * LIP_W, PLATE_W - 2 * LIP_W).extrude(-LIP_H - 1)
                 .edges("|Z").fillet(PLATE_R - LIP_W)).val()
        base = base.fuse(outer.cut(inner)).clean()

    zlo, zhi = -LIP_H - 1.0, T + 1.0
    cut = []
    for _, X, y in KNOBS:
        cut.append(hole(X, y, ENC_HOLE_D, zlo, zhi))
    for _, X, y in JACKS:
        cut.append(hole(X, y, JACK_HOLE_D, zlo, zhi))
    for _, X, y in BUTTONS:
        cut.append(hole(X, y, BTN_HOLE_D, zlo, zhi))
    for X, y in leds():
        cut.append(hole(X, y, LED_HOLE_D, zlo, zhi))
    for X, y in grille_points():
        cut.append(hole(X, y, GRILLE_HOLE_D, zlo, zhi))
    cut.append(cq.Workplane("XY").workplane(offset=zlo).center(USBC[0], -USBC[1])
               .slot2D(USBC_SLOT_L, USBC_SLOT_W, angle=90).extrude(zhi - zlo).val())
    csk_h = (CSK_D - SCREW_D) / 2 / math.tan(math.radians(CSK_ANGLE / 2))
    for X, y in SCREWS:
        cut.append(hole(X, y, SCREW_D, zlo, zhi))
        cut.append(cq.Solid.makeCone(SCREW_D / 2, CSK_D / 2, csk_h, V(X, y, T - csk_h), ZV))
        cut.append(hole(X, y, CSK_D, T, zhi))
    # labels
    for t, X, y, size in labels():
        cut.append(engrave_text(t, X, y, size, LABEL_DEPTH))
    t, X, y, size = LOGO
    cut.append(engrave_text(t, X, y, size, LABEL_DEPTH))
    # light engraving: zone lines, speaker ring, battery outline, battery icon
    w = LIGHT_LINE_W
    for X in ZONES[1:-1]:
        cut.append(sbox(X - w / 2, 6.0, X + w / 2, PLATE_W - 6.0, T - LIGHT_DEPTH, zhi))
    ring = cq.Solid.makeCylinder(SPEAKER_D / 2 + w / 2, zhi - (T - LIGHT_DEPTH),
                                 V(*SPEAKER, T - LIGHT_DEPTH), ZV)
    ring = ring.cut(cq.Solid.makeCylinder(SPEAKER_D / 2 - w / 2, 5, V(*SPEAKER, T - 2), ZV))
    cut.append(ring)
    for x0, y0, x1, y1 in battery_dashes():
        if y0 == y1:
            cut.append(sbox(x0, y0 - w / 2, x1, y0 + w / 2, T - LIGHT_DEPTH, zhi))
        else:
            cut.append(sbox(x0 - w / 2, y0, x0 + w / 2, y1, T - LIGHT_DEPTH, zhi))
    for x0, y0, x1, y1 in battery_icon_rects():
        cut.append(sbox(x0, y0, x1, y1, T - ICON_DEPTH, zhi))

    plate = base.cut(*cut).clean()
    return plate


def build_knob():
    R = KNOB_D / 2
    k = cq.Workplane("XY").circle(R).extrude(KNOB_H).faces(">Z").edges().chamfer(KNOB_TOP_CHAMFER)
    rc = R + KNOB_GROOVE_D / 2 - KNOB_GROOVE_DEPTH
    pts = [(rc * math.cos(2 * math.pi * i / KNOB_KNURL_N), rc * math.sin(2 * math.pi * i / KNOB_KNURL_N))
           for i in range(KNOB_KNURL_N)]
    grooves = (cq.Workplane("XY").workplane(offset=KNOB_SKIRT_H).pushPoints(pts)
               .circle(KNOB_GROOVE_D / 2).extrude(KNOB_H))
    k = k.cut(grooves)
    # index line on top, pointing +X (same side as the shaft flat)
    L = R + 1.0 - KNOB_INDEX_R0
    idx = (cq.Workplane("XY").workplane(offset=KNOB_H - KNOB_INDEX_DEPTH)
           .center(KNOB_INDEX_R0 + L / 2, 0).rect(L, KNOB_INDEX_W).extrude(KNOB_INDEX_DEPTH + 1))
    k = k.cut(idx)
    # underside: nut recess, bushing recess, D bore
    k = k.cut(cq.Workplane("XY").workplane(offset=-0.5).circle(NUT_REC_D / 2).extrude(NUT_REC_H + 0.5))
    k = k.cut(cq.Workplane("XY").workplane(offset=-0.5).circle(BUSH_REC_D / 2).extrude(BUSH_REC_H + 0.5))
    bd = SHAFT_D + BORE_CLEAR
    flat_from_centre = (SHAFT_FLAT + BORE_CLEAR / 2) - bd / 2
    d = cq.Workplane("XY").workplane(offset=-0.5).circle(bd / 2).extrude(BORE_DEPTH + 0.5)
    d = d.cut(cq.Workplane("XY").workplane(offset=-1).center(flat_from_centre + bd, 0)
              .rect(2 * bd, 2 * bd).extrude(BORE_DEPTH + 2))
    k = k.cut(d)
    return k.val().clean()


def build_preview_hardware():
    """Simple dummies for the 3/4 preview only (not exported)."""
    T = PLATE_T
    out = []

    def hexnut(X, y, corner_d, h, z0):
        return (cq.Workplane("XY").workplane(offset=z0).center(X, -y)
                .polygon(6, corner_d).extrude(h).val())

    for _, X, y in JACKS:
        nut = hexnut(X, y, JACK_NUT_D, 1.6, T)
        bush = cq.Workplane("XY").workplane(offset=T).center(X, -y).circle(3.0).circle(1.8).extrude(2.6).val()
        out.append(("metal", nut.fuse(bush)))
    for i, (name, X, y) in enumerate(BUTTONS):
        nut = hexnut(X, y, BTN_TOP_D, 2.0, T)
        bush = cq.Workplane("XY").workplane(offset=T).center(X, -y).circle(3.5).extrude(3.0).val()
        cap = cq.Workplane("XY").workplane(offset=T + 3.0).center(X, -y).circle(2.8).extrude(2.5).val()
        out.append(("metal", nut.fuse(bush)))
        out.append(("red" if name == "PWR" else "black", cap))
    for X, y in leds():
        body = cq.Workplane("XY").workplane(offset=T).center(X, -y).circle(1.5).extrude(1.8).val()
        dome = cq.Solid.makeSphere(1.5, V(X, y, T + 1.8))
        out.append(("led", body.fuse(dome)))
    return out


# =====================================================================================
# CHECKS
# =====================================================================================
class C:  # circle
    def __init__(s, name, x, y, d):
        s.name, s.x, s.y, s.r = name, x, y, d / 2


class R:  # axis-aligned rect
    def __init__(s, name, x0, y0, x1, y1):
        s.name, s.x0, s.y0, s.x1, s.y1 = name, x0, y0, x1, y1


def gap(a, b):
    if isinstance(a, C) and isinstance(b, C):
        return math.hypot(a.x - b.x, a.y - b.y) - a.r - b.r
    if isinstance(a, R) and isinstance(b, C):
        a, b = b, a
    if isinstance(a, C) and isinstance(b, R):
        dx = max(b.x0 - a.x, 0, a.x - b.x1)
        dy = max(b.y0 - a.y, 0, a.y - b.y1)
        if dx == 0 and dy == 0:
            return -min(a.x - b.x0, b.x1 - a.x, a.y - b.y0, b.y1 - a.y) - a.r
        return math.hypot(dx, dy) - a.r
    dx = max(b.x0 - a.x1, a.x0 - b.x1)
    dy = max(b.y0 - a.y1, a.y0 - b.y1)
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def edge_margin(s):
    """Distance from a shape to the rounded plate outline (positive = inside)."""
    a, b, r = PLATE_L / 2, PLATE_W / 2, PLATE_R

    def sd_inside(px, py):
        qx, qy = abs(px - a) - (a - r), abs(py - b) - (b - r)
        out = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - r
        return -out

    if isinstance(s, C):
        return sd_inside(s.x, s.y) - s.r
    return min(sd_inside(x, y) for x in (s.x0, s.x1) for y in (s.y0, s.y1))


def label_rects():
    out = []
    for t, X, y, size in labels() + [LOGO]:
        w, h = text_box(t, size)
        out.append(R(f"label {t}@{X:g}", X - w / 2, y - h / 2, X + w / 2, y + h / 2))
    return out


def run_checks():
    lines = []
    ok = True

    def p(s=""):
        lines.append(s)
        print(s)

    p("=== CLEARANCE CHECK (spec coords, mm; negative = overlap) ===")
    # 1) LED at spec positions vs mockup buttons
    p("1) LEDs at the SPEC positions (y=40, +5.5 mm right of the button):")
    for (lx, ly), bn in zip(LEDS_SPEC, LED_FOR):
        b = next(bb for bb in BUTTONS if bb[0] == bn)
        g_nut = gap(C("led", lx, ly, LED_HOLE_D), C("btn", b[1], b[2], BTN_TOP_D))
        web = gap(C("led", lx, ly, LED_HOLE_D), C("btn", b[1], b[2], BTN_HOLE_D))
        verdict = "CLASH" if (g_nut < MIN_GAP or web < MIN_WEB) else "ok"
        p(f"   LED {bn:4s} ({lx},{ly}): hole vs Ø{BTN_TOP_D:g} button nut {g_nut:+.2f}; "
          f"plastic web to button hole {web:.2f}  -> {verdict}")
    p(f"   -> using {'SPEC' if USE_SPEC_LED_POSITIONS else 'MOCKUP'} LED positions: {leds()}")

    # 2) plate holes: web between holes and to the edge
    holes = [C(f"enc {t}", x, y, ENC_HOLE_D) for t, x, y in KNOBS]
    holes += [C(f"jack {t}", x, y, JACK_HOLE_D) for t, x, y in JACKS]
    holes += [C(f"btn {t}", x, y, BTN_HOLE_D) for t, x, y in BUTTONS]
    holes += [C(f"led {i}", x, y, LED_HOLE_D) for i, (x, y) in enumerate(leds())]
    holes += [C(f"screw csk {i}", x, y, CSK_D) for i, (x, y) in enumerate(SCREWS)]
    holes.append(R("usb-c", USBC[0] - USBC_SLOT_W / 2, USBC[1] - USBC_SLOT_L / 2,
                   USBC[0] + USBC_SLOT_W / 2, USBC[1] + USBC_SLOT_L / 2))
    holes.append(C("grille field", SPEAKER[0], SPEAKER[1], GRILLE_FIELD_D))
    worst = min(((gap(a, b), a.name, b.name) for i, a in enumerate(holes) for b in holes[i + 1:]))
    em = min((edge_margin(h), h.name) for h in holes)
    f1 = worst[0] >= MIN_WEB and em[0] >= MIN_WEB
    ok &= f1
    p(f"2) hole-to-hole web min {worst[0]:.2f} ({worst[1]} / {worst[2]}); "
      f"hole-to-edge min {em[0]:.2f} ({em[1]})  [{'OK' if f1 else 'FAIL'} >= {MIN_WEB}]")

    # 3) above the plate: hardware envelopes + labels
    top = [C(f"knob {t}", x, y, KNOB_D) for t, x, y in KNOBS]
    top += [C(f"jack nut {t}", x, y, JACK_NUT_D) for t, x, y in JACKS]
    top += [C(f"button {t}", x, y, BTN_TOP_D) for t, x, y in BUTTONS]
    top += [C(f"led {n}", x, y, LED_HOLE_D) for n, (x, y) in zip(LED_FOR, leds())]
    top.append(R("usb-c", USBC[0] - USBC_SLOT_W / 2, USBC[1] - USBC_SLOT_L / 2,
                 USBC[0] + USBC_SLOT_W / 2, USBC[1] + USBC_SLOT_L / 2))
    top += [C(f"screw head {i}", x, y, CSK_D) for i, (x, y) in enumerate(SCREWS)]
    top.append(C("speaker ring", SPEAKER[0], SPEAKER[1], SPEAKER_D + LIGHT_LINE_W))
    hw = min(((gap(a, b), a.name, b.name) for i, a in enumerate(top) for b in top[i + 1:]))
    labs = label_rects()
    battery_lines = [R("battery outline", BATTERY[0] - LIGHT_LINE_W / 2, BATTERY[1] - LIGHT_LINE_W / 2,
                       BATTERY[2] + LIGHT_LINE_W / 2, BATTERY[3] + LIGHT_LINE_W / 2)]
    lab = []
    for L in labs:
        for o in top:
            lab.append((gap(L, o), L.name, o.name))
        for L2 in labs:
            if L2 is not L:
                lab.append((gap(L, L2), L.name, L2.name))
    # labels outside the battery box must not touch its outline; logo sits inside it
    bl = battery_lines[0]
    for L in labs:
        if L.name.startswith("label SmartVio"):
            inside = min(L.x0 - bl.x0, bl.x1 - L.x1, L.y0 - bl.y0, bl.y1 - L.y1) - LIGHT_LINE_W / 2
            lab.append((inside, L.name, "battery outline (inside)"))
        else:
            lab.append((gap(L, bl), L.name, "battery outline"))
    lab_min = min(lab)
    lab_edge = min((edge_margin(L), L.name) for L in labs)
    f2 = hw[0] >= MIN_GAP and lab_min[0] >= MIN_GAP and lab_edge[0] >= 0.8
    ok &= f2
    p(f"3) above plate: hardware-to-hardware min {hw[0]:.2f} ({hw[1]} / {hw[2]})")
    p(f"   labels: min gap {lab_min[0]:.2f} ({lab_min[1]} / {lab_min[2]}); "
      f"min to plate edge {lab_edge[0]:.2f} ({lab_edge[1]})  [{'OK' if f2 else 'FAIL'}]")
    for t, X, y, size in labels() + [LOGO]:
        w, h = text_box(t, size)
        if t in ("VOL", "PHONES", "PWR", "USB-C", "SmartVio"):
            p(f"   {t:8s} size {size:g} -> ink {w:.1f} x {h:.2f} mm, y {y - h / 2:.2f}..{y + h / 2:.2f}")

    # 4) below the plate: bodies, and the old cavity
    bot = [R(f"EC11 {t}", x - ENC_BODY[0] / 2, y - ENC_BODY[1] / 2, x + ENC_BODY[0] / 2, y + ENC_BODY[1] / 2)
           for t, x, y in KNOBS]
    bot += [C(f"jack body {t}", x, y, JACK_BODY_D) for t, x, y in JACKS]
    bot += [C(f"button body {t}", x, y, BTN_BODY_D) for t, x, y in BUTTONS]
    bot += [C(f"led flange {n}", x, y, LED_FLANGE_D) for n, (x, y) in zip(LED_FOR, leds())]
    bw = min(((gap(a, b), a.name, b.name) for i, a in enumerate(bot) for b in bot[i + 1:]))
    f3 = bw[0] >= 0.3
    ok &= f3
    p(f"4) below plate: body-to-body min {bw[0]:.2f} ({bw[1]} / {bw[2]})  [{'OK' if f3 else 'FAIL'}]")
    xs0 = min(b.x0 if isinstance(b, R) else b.x - b.r for b in bot)
    xs1 = max(b.x1 if isinstance(b, R) else b.x + b.r for b in bot)
    ys0 = min(b.y0 if isinstance(b, R) else b.y - b.r for b in bot)
    ys1 = max(b.y1 if isinstance(b, R) else b.y + b.r for b in bot)
    cx0 = TAIL_DATUM_HEAD_END - CAVITY_FROM_TAIL[1]
    cx1 = TAIL_DATUM_HEAD_END - CAVITY_FROM_TAIL[0]
    cy0, cy1 = PLATE_W / 2 - CAVITY_WIDTH / 2, PLATE_W / 2 + CAVITY_WIDTH / 2
    p(f"   bodies span X {xs0:.1f}..{xs1:.1f}, y {ys0:.1f}..{ys1:.1f} "
      f"(= {TAIL_DATUM_HEAD_END - xs1:.1f}..{TAIL_DATUM_HEAD_END - xs0:.1f} mm from tail; "
      f"{ys1 - ys0:.1f} mm across)")
    p(f"   old cavity (centred assumption) X {cx0:.0f}..{cx1:.0f}, y {cy0:.1f}..{cy1:.1f}: "
      f"margins head {xs0 - cx0:+.1f}, tail {cx1 - xs1:+.1f}, G {ys0 - cy0:+.1f}, E {cy1 - ys1:+.1f}")

    # 5) height stack
    bush_above = ENC_BUSHING_L - PLATE_T
    p("5) heights above the plate top (typical EC11, M7 bushing "
      f"{ENC_BUSHING_L:g} mm, nut {ENC_NUT_T:g} mm):")
    p(f"   thread above plate {bush_above:.1f} (nut needs {ENC_NUT_T:g}) -> "
      f"{'OK' if bush_above >= ENC_NUT_T else 'TOO SHORT'}")
    nut_ok = ENC_NUT_T <= KNOB_LIFT + NUT_REC_H - 0.2
    bush_ok = bush_above <= KNOB_LIFT + BUSH_REC_H - 0.2
    ok &= nut_ok and bush_ok
    p(f"   nut top {ENC_NUT_T:.1f} vs knob nut-recess roof {KNOB_LIFT + NUT_REC_H:.1f}; "
      f"bushing top {bush_above:.1f} vs bushing-recess roof {KNOB_LIFT + BUSH_REC_H:.1f} "
      f"[{'OK' if nut_ok and bush_ok else 'FAIL'}]")
    p(f"   cut shaft to {KNOB_LIFT + BORE_DEPTH - 0.2:.1f} above plate; D engagement "
      f"{BORE_DEPTH - BUSH_REC_H:.1f}; knob top {KNOB_LIFT + KNOB_H:.1f} above plate = "
      f"{KNOB_LIFT + KNOB_H + PLATE_T + LIP_H:.1f} above the violin back")
    p(f"=== {'ALL CHECKS OK' if ok else 'SOME CHECKS FAILED'} ===")
    return ok, lines


# =====================================================================================
# PAPER TEMPLATE (A4, 1:1)
# =====================================================================================
A4 = (210.0, 297.0)
TPL_ORIGIN = (31.0, 72.0)   # page position of plate (X=0, y=0); page y runs down
SCALEBAR = (31.0, 166.0, 50.0, 1.6)   # x, y (top), length, height


def rounded_rect_pts(x0, y0, x1, y1, r, n=24):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slot_pts(cx, cy, L, W, n=24):
    r = W / 2
    h = L / 2 - r
    pts = []
    for k in range(n + 1):
        a = math.radians(180 + 180 * k / n)
        pts.append((cx + r * math.cos(a), cy - h + r * math.sin(a)))
    for k in range(n + 1):
        a = math.radians(180 * k / n)
        pts.append((cx + r * math.cos(a), cy + h + r * math.sin(a)))
    return pts


def build_template(pdf_path, svg_path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    from matplotlib.patches import Circle, PathPatch, Polygon, Rectangle
    from matplotlib.textpath import TextPath
    from matplotlib.transforms import Affine2D
    from matplotlib.lines import Line2D

    plt.rcParams["lines.scale_dashes"] = False
    plt.rcParams["svg.hashsalt"] = "smartvio-r5-mockup"
    fp_cjk = FontProperties(fname=FONT_CJK)
    fp_lab = FontProperties(fname=FONT_LABEL)
    PT = 72.0 / 25.4   # mm -> pt (line widths)

    fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4[0])
    ax.set_ylim(A4[1], 0)
    ax.set_aspect("auto")
    ax.axis("off")

    def text(s, x, y, size, fp=fp_cjk, ha="center", va="center", color="black", rot=0, gid=None):
        if not s:
            return
        tp = TextPath((0, 0), s, size=size, prop=fp)
        bb = tp.get_extents()
        dx = {"left": -bb.x0, "center": -(bb.x0 + bb.x1) / 2, "right": -bb.x1}[ha]
        if va == "baseline":
            dy = 0.0
        else:
            dy = {"bottom": -bb.y0, "center": -(bb.y0 + bb.y1) / 2, "top": -bb.y1}[va]
        tr = Affine2D().translate(dx, dy).scale(1, -1).rotate_deg(-rot).translate(x, y)
        patch = PathPatch(tr.transform_path(tp), fc=color, ec="none", lw=0)
        if gid:
            patch.set_gid(gid)
        ax.add_patch(patch)

    def line(x0, y0, x1, y1, lw=0.2, color="black", ls="-", gid=None):
        l = Line2D([x0, x1], [y0, y1], lw=lw * PT, color=color, linestyle=ls, solid_capstyle="butt")
        if gid:
            l.set_gid(gid)
        ax.add_line(l)

    def circle(x, y, d, lw=0.2, color="black", ls="-", fill=None):
        ax.add_patch(Circle((x, y), d / 2, fill=fill is not None, fc=fill or "none", ec=color,
                            lw=lw * PT, linestyle=ls))

    def poly(pts, lw=0.2, color="black", ls="-", gid=None, fill=None):
        pg = Polygon(pts, closed=True, fill=fill is not None, fc=fill or "none", ec=color,
                     lw=lw * PT, linestyle=ls, joinstyle="round")
        if gid:
            pg.set_gid(gid)
        ax.add_patch(pg)

    ox, oy = TPL_ORIGIN

    def P(X, y):
        return ox + X, oy + y

    def cross(X, y, d):
        x, yy = P(X, y)
        e = d / 2 + (0.7 if d < 4 else 1.2)
        line(x - e, yy, x + e, yy, lw=0.12)
        line(x, yy - e, x, yy + e, lw=0.12)

    DASH = (0, (1.6 * PT, 0.9 * PT))
    DOT = (0, (0.4 * PT, 0.8 * PT))
    DASHDOT = (0, (3.0 * PT, 0.8 * PT, 0.5 * PT, 0.8 * PT))
    GREY = "#777777"
    ORANGE = "#e07b00"

    # ---- header ----
    text("SmartVio R5 面板 1:1 纸模板（样机）", 105, 13, 5.6, ha="center")
    info = [
        "1. 用 A4 纸打印本 PDF。选「实际大小」或 100%。不要选「适合页面」。",
        "2. 打印后先量下面红色比例尺，应为 50 mm。误差超过 0.5 mm 就改打印设置再打。",
        "3. 这是从琴背外面看的样子：琴头在左，G 弦侧在上。",
        "4. 沿蓝色外框剪下，琴尾端对准「距琴尾基准 110 mm」，贴到琴背上看位置。",
        "5. 孔心画了十字。可用针扎孔心，在琴上做记号。",
        "灰色虚线 = 旋钮 Ø13 / 螺母占位；橙色点线 = 旧琴控制腔 42×78（横向按居中画，以实物为准）。",
    ]
    for i, s in enumerate(info):
        text(s, 16, 22 + i * 5.6, 3.3, ha="left", va="baseline")

    # ---- direction marks ----
    text("← 琴头 HEAD", ox, oy - 6.5, 3.6, ha="left")
    text("琴尾 TAIL →", ox + PLATE_L, oy - 6.5, 3.6, ha="right")
    text("G 弦侧（G side）", ox + PLATE_L / 2, oy - 6.5, 3.6)
    text("E 弦侧（E side）", ox + PLATE_L / 2, oy + PLATE_W + 5.0, 3.6)

    # ---- plate ----
    poly([P(*q) for q in rounded_rect_pts(0, 0, PLATE_L, PLATE_W, PLATE_R)], lw=0.3,
         color="#0000ff", gid="plate_outline")
    for X in ZONES[1:-1]:
        line(*P(X, -3), *P(X, PLATE_W + 13), lw=0.15, color=GREY, ls=DASHDOT)
    # old cavity
    cx0 = TAIL_DATUM_HEAD_END - CAVITY_FROM_TAIL[1]
    cx1 = TAIL_DATUM_HEAD_END - CAVITY_FROM_TAIL[0]
    cy0, cy1 = PLATE_W / 2 - CAVITY_WIDTH / 2, PLATE_W / 2 + CAVITY_WIDTH / 2
    poly([P(cx0, cy0), P(cx1, cy0), P(cx1, cy1), P(cx0, cy1)], lw=0.25, color=ORANGE, ls=DOT)
    # speaker
    circle(*P(*SPEAKER), SPEAKER_D, lw=0.15, color=GREY, ls=DASH)
    circle(*P(*SPEAKER), GRILLE_FIELD_D, lw=0.1, color=GREY, ls=DOT)
    for X, y in grille_points():
        circle(*P(X, y), GRILLE_HOLE_D, lw=0.12)
    cross(*SPEAKER, 2.0)
    # controls
    for _, X, y in KNOBS:
        circle(*P(X, y), ENC_HOLE_D, lw=0.25)
        circle(*P(X, y), KNOB_D, lw=0.15, color=GREY, ls=DASH)
        cross(X, y, ENC_HOLE_D)
    for _, X, y in JACKS:
        circle(*P(X, y), JACK_HOLE_D, lw=0.25)
        circle(*P(X, y), JACK_NUT_D, lw=0.12, color=GREY, ls=DOT)
        cross(X, y, JACK_HOLE_D)
    for _, X, y in BUTTONS:
        circle(*P(X, y), BTN_HOLE_D, lw=0.25)
        circle(*P(X, y), BTN_TOP_D, lw=0.12, color=GREY, ls=DOT)
        cross(X, y, BTN_HOLE_D)
    for X, y in leds():
        circle(*P(X, y), LED_HOLE_D, lw=0.25)
        cross(X, y, LED_HOLE_D)
    poly([P(*q) for q in slot_pts(USBC[0], USBC[1], USBC_SLOT_L, USBC_SLOT_W)], lw=0.25)
    cross(*USBC, USBC_SLOT_W)
    for X, y in SCREWS:
        circle(*P(X, y), SCREW_D, lw=0.25)
        circle(*P(X, y), CSK_D, lw=0.12, ls=DASH)
        cross(X, y, SCREW_D)
    # battery
    for x0, y0, x1, y1 in battery_dashes():
        line(*P(x0, y0), *P(x1, y1), lw=0.2, color=GREY)
    for x0, y0, x1, y1 in battery_icon_rects():
        poly([P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)], lw=0.01, color=GREY, fill=GREY)
    # labels (same font/size/position as the engraving)
    for t, X, y, size in labels():
        text(t, *P(X, y), size, fp=fp_lab)
    t, X, y, size = LOGO
    text(t, *P(X, y), size, fp=fp_lab, color=GREY)

    # ---- dimensions below the plate ----
    yd = oy + PLATE_W + 12.0
    for X in ZONES:
        line(*P(X, PLATE_W + 1), ox + X, yd + 1.5, lw=0.12)
    line(ox, yd, ox + PLATE_L, yd, lw=0.15)
    for a, b, name in ((0, 34, "扬声器 34"), (34, 104, "功能区 70"), (104, 148, "电池 + USB-C 44")):
        text(name, ox + (a + b) / 2, yd - 1.9, 2.9)
    yd2 = yd + 6.5
    line(ox, yd2, ox + PLATE_L, yd2, lw=0.15)
    line(ox, yd2 - 1.5, ox, yd2 + 1.5, lw=0.15)
    line(ox + PLATE_L, yd2 - 1.5, ox + PLATE_L, yd2 + 1.5, lw=0.15)
    text("148", ox + PLATE_L / 2, yd2 - 1.9, 2.9)
    xr = ox + PLATE_L + 6.0
    line(xr, oy, xr, oy + PLATE_W, lw=0.15)
    line(xr - 1.5, oy, xr + 1.5, oy, lw=0.15)
    line(xr - 1.5, oy + PLATE_W, xr + 1.5, oy + PLATE_W, lw=0.15)
    text("49", xr + 2.8, oy + PLATE_W / 2, 2.9, rot=-90)
    # distance from the tail datum
    yt = yd2 + 8.0
    line(ox, yt, ox + PLATE_L, yt, lw=0.15)
    for d in range(110, 259, 10):
        X = TAIL_DATUM_HEAD_END - d
        line(ox + X, yt, ox + X, yt + (2.0 if d % 50 == 0 else 1.2), lw=0.15)
        if d % 20 == 10 and d < 250:
            text(str(d), ox + X, yt + 3.6, 2.4)
    X = 0.0
    line(ox + X, yt, ox + X, yt + 2.0, lw=0.15)
    text("258", ox + X, yt + 3.6, 2.4)
    text("距琴尾基准的距离 (mm)：琴头端 258，琴尾端 110", ox, yt - 1.6, 2.6, ha="left", va="baseline")

    # ---- scale bar ----
    sx, sy, sl, sh = SCALEBAR
    text("比例尺：打印后用尺量，应正好 50 mm", sx, sy - 6.5, 3.2, ha="left")
    bar = Rectangle((sx, sy), sl, sh, fc="#ff0000", ec="none", lw=0)
    bar.set_gid("scalebar_50mm")
    ax.add_patch(bar)
    for k in range(0, 51, 5):
        L = 2.6 if k % 10 == 0 else 1.5
        line(sx + k, sy - L - 0.3, sx + k, sy - 0.3, lw=0.15)
    for k in range(0, 51, 10):
        text(str(k), sx + k, sy + sh + 2.6, 2.6)
    text("mm", sx + sl + 4.0, sy + sh / 2, 2.8)
    text("A4 · 1:1 · 单位 mm · 非正式图纸", 200, sy + 1.0, 2.8, ha="right", color=GREY)

    # ---- hole table ----
    ty = 186.0
    cols = [16, 46, 92, 122, 140, 158, 178]
    heads = ["名称", "样机零件", "孔", "X", "y", "距琴尾", "备注"]
    for c, h in zip(cols, heads):
        text(h, c, ty, 3.0, ha="left", va="baseline")
    line(14, ty + 1.4, 198, ty + 1.4, lw=0.15)
    rows = []
    for t, X, y in KNOBS:
        rows.append((f"{t} 旋钮", "EC11 编码器", f"Ø{ENC_HOLE_D:g}", X, y, "旋钮 Ø13"))
    for t, X, y in JACKS:
        rows.append((f"{t} 插孔", "3.5 mm 面板插座 M6", f"Ø{JACK_HOLE_D:g}", X, y, ""))
    for t, X, y in BUTTONS:
        rows.append((f"{t} 按键", "7 mm 面板按钮", f"Ø{BTN_HOLE_D:g}", X, y, ""))
    for n, (X, y) in zip(LED_FOR, leds()):
        rows.append((f"LED（{n}）", "3 mm LED", f"Ø{LED_HOLE_D:g}", X, y,
                     "样机移位" if not USE_SPEC_LED_POSITIONS else ""))
    rows.append(("USB-C", "只示意位置", f"{USBC_SLOT_L:g}×{USBC_SLOT_W:g} 槽", USBC[0], USBC[1], ""))
    rows.append(("扬声器", f"Ø{SPEAKER_D:g}", f"Ø{GRILLE_HOLE_D:g}×{len(grille_points())}",
                 SPEAKER[0], SPEAKER[1], f"孔区 Ø{GRILLE_FIELD_D:g}"))
    rows.append(("四角螺丝孔 ×4", "沉头", f"Ø{SCREW_D:g}/Ø{CSK_D:g}", None, None,
                 "X = 5.3 或 142.7，y = 5.3 或 43.7"))
    for i, r in enumerate(rows):
        yy = ty + 6.0 + i * 4.75
        name, part, hd, X, y, note = r
        text(name, cols[0], yy, 2.9, ha="left", va="baseline")
        text(part, cols[1], yy, 2.9, ha="left", va="baseline")
        text(hd, cols[2], yy, 2.9, ha="left", va="baseline")
        if X is not None:
            text(f"{X:.1f}", cols[3], yy, 2.9, ha="left", va="baseline")
            text(f"{y:.1f}", cols[4], yy, 2.9, ha="left", va="baseline")
            text(f"{TAIL_DATUM_HEAD_END - X:.0f}", cols[5], yy, 2.9, ha="left", va="baseline")
        text(note, cols[6] if X is not None else cols[3], yy, 2.9, ha="left", va="baseline")
    text("X 从琴头端量，y 从 G 弦侧边量。由 build_mockup.py 生成。", 16, 290, 2.8, ha="left",
         va="baseline", color=GREY)

    fig.savefig(pdf_path, format="pdf", metadata={"CreationDate": None, "Creator": "build_mockup.py"})
    fig.savefig(svg_path, format="svg", metadata={"Date": None})
    plt.close(fig)
    # give the SVG explicit physical units (same size as the pt values matplotlib writes)
    with open(svg_path, encoding="utf-8") as f:
        s = f.read()
    s, n = re.subn(r'width="[0-9.]+pt" height="[0-9.]+pt"', f'width="{A4[0]:g}mm" height="{A4[1]:g}mm"', s, count=1)
    assert n == 1, "could not set SVG size"
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(s)


def verify_template(pdf_path, svg_path, tmpdir):
    """Check that the template is exactly 1:1. Returns report lines."""
    out = []

    def p(s):
        out.append(s)
        print(s)

    p("=== TEMPLATE 1:1 VERIFICATION ===")
    # --- SVG: root size + viewBox, then the scale bar and plate outline coordinates
    with open(svg_path, encoding="utf-8") as f:
        s = f.read()
    m = re.search(r'<svg[^>]*width="([0-9.]+)mm" height="([0-9.]+)mm" viewBox="0 0 ([0-9.]+) ([0-9.]+)"', s)
    wmm, hmm, vw, vh = map(float, m.groups())
    kx, ky = wmm / vw, hmm / vh

    def gid_xy(gid):
        g = re.search(r'<g id="%s">(.*?)</g>' % gid, s, re.S).group(1)
        d = re.search(r'\bd="([^"]+)"', g).group(1)
        nums = list(map(float, re.findall(r"-?[0-9]+(?:\.[0-9]+)?", d)))
        return np.array(nums[0::2]), np.array(nums[1::2])

    bx, by = gid_xy("scalebar_50mm")
    px, py = gid_xy("plate_outline")
    p(f"SVG: page {wmm:g} x {hmm:g} mm, viewBox {vw:g} x {vh:g} -> {kx:.6f} / {ky:.6f} mm per unit")
    p(f"SVG: scale bar length {(bx.max() - bx.min()) * kx:.4f} mm (want 50); plate outline "
      f"{(px.max() - px.min()) * kx:.4f} x {(py.max() - py.min()) * ky:.4f} mm (want {PLATE_L:g} x {PLATE_W:g})")
    # --- PDF: page box + rasterise with poppler and measure pixels
    txt = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True).stdout if shutil.which("pdfinfo") else ""
    mm = re.search(r"Page size:\s+([0-9.]+) x ([0-9.]+) pts", txt)
    if mm:
        w, h = float(mm.group(1)), float(mm.group(2))
        p(f"PDF: page {w} x {h} pt = {w * 25.4 / 72:.3f} x {h * 25.4 / 72:.3f} mm (A4 = 210 x 297)")
    if shutil.which("pdftoppm"):
        from PIL import Image
        dpi = 600
        base = os.path.join(tmpdir, "tpl_600dpi")
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", "-singlefile", pdf_path, base], check=True)
        im = np.asarray(Image.open(base + ".png").convert("RGB")).astype(float) / 255.0
        mmpx = 25.4 / dpi
        red = np.clip(im[..., 0] - np.maximum(im[..., 1], im[..., 2]), 0, 1)
        blue = np.clip(im[..., 2] - np.maximum(im[..., 0], im[..., 1]), 0, 1)
        row = int(round((SCALEBAR[1] + SCALEBAR[3] / 2) / mmpx))
        bar_len = red[row - 3:row + 4].sum(axis=1).mean() * mmpx   # coverage-weighted width

        def runs_centres(v):
            idx = np.nonzero(v > 0.05)[0]
            groups = np.split(idx, np.nonzero(np.diff(idx) > 3)[0] + 1)
            return [float((g * v[g]).sum() / v[g].sum()) for g in groups if len(g)]

        r_mid = int(round((TPL_ORIGIN[1] + PLATE_W / 2) / mmpx))
        c_mid = int(round((TPL_ORIGIN[0] + PLATE_L / 2) / mmpx))
        hc = runs_centres(blue[r_mid])
        vc = runs_centres(blue[:, c_mid])
        p(f"PDF @ {dpi} dpi (poppler): scale bar {bar_len:.3f} mm; plate outline "
          f"{(hc[-1] - hc[0]) * mmpx:.3f} x {(vc[-1] - vc[0]) * mmpx:.3f} mm "
          f"(stroke centres; 1 px = {mmpx:.4f} mm)")
        p(f"PDF: plate top-left at page ({hc[0] * mmpx:.2f}, {vc[0] * mmpx:.2f}) mm "
          f"(designed {TPL_ORIGIN[0]:g}, {TPL_ORIGIN[1]:g})")
        Image.open(base + ".png").resize((int(im.shape[1] / 4), int(im.shape[0] / 4)),
                                         Image.LANCZOS).save(os.path.join(tmpdir, "template_preview.png"))
    return out


# =====================================================================================
# PREVIEW RENDERER (small numpy z-buffer; no OpenGL needed)
# =====================================================================================
COLORS = {"plate": (0.80, 0.81, 0.83), "knob": (0.20, 0.20, 0.21), "metal": (0.66, 0.67, 0.69),
          "black": (0.13, 0.13, 0.14), "red": (0.78, 0.16, 0.12), "led": (0.93, 0.95, 0.88)}


def mesh_of(shape, tol=0.02, ang=0.2):
    vs, ts = shape.tessellate(tol, ang)
    Vv = np.array([(v.x, v.y, v.z) for v in vs], dtype=np.float64)
    F = np.array(ts, dtype=np.int64)
    return Vv, F


def render(meshes, out_png, view, size=(1800, 1000), ssaa=2, margin=60, caption=None,
           light=(-0.45, 0.35, 0.82), edge_thr=0.25, depth_tint=None):
    from PIL import Image, ImageDraw, ImageFont
    W, H = size[0] * ssaa, size[1] * ssaa
    if view == "top":
        r, u, f = np.array([1.0, 0, 0]), np.array([0, 1.0, 0]), np.array([0, 0, -1.0])
    else:
        az, el = map(math.radians, view)
        c = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        f = -c
        r = np.cross(f, [0, 0, 1.0])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
    allv = np.concatenate([m[0] for m in meshes])
    sx, sy = allv @ r, allv @ u
    top_pad = 70 * ssaa if caption else 0
    scale = min((W - 2 * margin * ssaa) / np.ptp(sx), (H - 2 * margin * ssaa - top_pad) / np.ptp(sy))
    cx, cy = (sx.max() + sx.min()) / 2, (sy.max() + sy.min()) / 2
    zbuf = np.full((H, W), -np.inf, np.float32)
    cbuf = np.ones((H, W, 3), np.float32)
    L = np.array(light) / np.linalg.norm(light)
    Hh = (L - f) / np.linalg.norm(L - f)
    for Vv, F, rgb in meshes:
        px = ((Vv @ r) - cx) * scale + W / 2
        py = H / 2 + top_pad / 2 - ((Vv @ u) - cy) * scale
        pz = -(Vv @ f)
        a, b, c3 = Vv[F[:, 0]], Vv[F[:, 1]], Vv[F[:, 2]]
        n = np.cross(b - a, c3 - a)
        nl = np.linalg.norm(n, axis=1)
        good = nl > 1e-12
        n[good] /= nl[good, None]
        flip = (n @ -f) < 0
        n[flip] *= -1
        diff = np.clip(n @ L, 0, 1)
        spec = np.clip(n @ Hh, 0, 1) ** 40
        inten = 0.38 + 0.62 * diff
        col = np.clip(np.array(rgb)[None, :] * inten[:, None] + 0.12 * spec[:, None], 0, 1).astype(np.float32)
        X0, X1, X2 = px[F[:, 0]], px[F[:, 1]], px[F[:, 2]]
        Y0, Y1, Y2 = py[F[:, 0]], py[F[:, 1]], py[F[:, 2]]
        Z0, Z1, Z2 = pz[F[:, 0]], pz[F[:, 1]], pz[F[:, 2]]
        A = (X1 - X0) * (Y2 - Y0) - (X2 - X0) * (Y1 - Y0)
        mnx = np.clip(np.floor(np.minimum(np.minimum(X0, X1), X2)).astype(int), 0, W - 1)
        mxx = np.clip(np.ceil(np.maximum(np.maximum(X0, X1), X2)).astype(int), 0, W - 1)
        mny = np.clip(np.floor(np.minimum(np.minimum(Y0, Y1), Y2)).astype(int), 0, H - 1)
        mxy = np.clip(np.ceil(np.maximum(np.maximum(Y0, Y1), Y2)).astype(int), 0, H - 1)
        for i in np.nonzero(good & (np.abs(A) > 1e-9))[0]:
            xs = np.arange(mnx[i], mxx[i] + 1, dtype=np.float32) + 0.5
            ys = np.arange(mny[i], mxy[i] + 1, dtype=np.float32)[:, None] + 0.5
            w0 = ((X1[i] - xs) * (Y2[i] - ys) - (X2[i] - xs) * (Y1[i] - ys)) / A[i]
            w1 = ((X2[i] - xs) * (Y0[i] - ys) - (X0[i] - xs) * (Y2[i] - ys)) / A[i]
            w2 = 1.0 - w0 - w1
            m = (w0 >= -1e-5) & (w1 >= -1e-5) & (w2 >= -1e-5)
            if not m.any():
                continue
            z = w0 * Z0[i] + w1 * Z1[i] + w2 * Z2[i]
            sub = zbuf[mny[i]:mxy[i] + 1, mnx[i]:mxx[i] + 1]
            upd = m & (z > sub)
            sub[upd] = z[upd]
            cbuf[mny[i]:mxy[i] + 1, mnx[i]:mxx[i] + 1][upd] = col[i]
    hit = np.isfinite(zbuf)
    if depth_tint is not None:
        z0, z1 = depth_tint
        t = np.clip((zbuf - z0) / (z1 - z0), 0, 1)
        k = (0.55 + 0.45 * t)[..., None]
        cbuf = np.where(hit[..., None], cbuf * k, cbuf)
    # feature lines from depth jumps
    zf = np.where(hit, zbuf, -1e3)
    e = np.zeros((H, W), bool)
    dzx = np.abs(np.diff(zf, axis=1)) > edge_thr
    dzy = np.abs(np.diff(zf, axis=0)) > edge_thr
    e[:, 1:] |= dzx
    e[:, :-1] |= dzx
    e[1:, :] |= dzy
    e[:-1, :] |= dzy
    cbuf[e] = cbuf[e] * 0.35 + 0.08
    bg = np.array([0.965, 0.967, 0.972], np.float32)
    cbuf[~hit & ~e] = bg
    img = cbuf.reshape(H // ssaa, ssaa, W // ssaa, ssaa, 3).mean(axis=(1, 3))
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    if caption:
        d = ImageDraw.Draw(im)
        fnt = ImageFont.truetype(FONT_CJK, 30)
        d.text((40, 24), caption, fill=(40, 40, 45), font=fnt)
    im.save(out_png)


def render_previews(plate, knob, outdir):
    print("rendering previews ...")
    pm = mesh_of(plate, 0.02, 0.25)
    render([(pm[0], pm[1], COLORS["plate"])], os.path.join(outdir, "preview_top.png"), "top",
           size=(1900, 820), ssaa=2, margin=40, edge_thr=0.2, depth_tint=(PLATE_T - 0.8, PLATE_T),
           caption="R5 面板样机 · 顶视（从琴背外面看：琴头在左，G 弦侧在上）  148 × 49 × 2 mm")
    km = mesh_of(knob, 0.01, 0.2)
    meshes = [(pm[0], pm[1], COLORS["plate"])]
    for _, X, y in KNOBS:
        meshes.append((km[0] + np.array([X, -y, PLATE_T + KNOB_LIFT]), km[1], COLORS["knob"]))
    for kind, s in build_preview_hardware():
        Vv, F = mesh_of(s, 0.02, 0.3)
        meshes.append((Vv, F, COLORS[kind]))
    render(meshes, os.path.join(outdir, "preview_34.png"), (-118.0, 38.0), size=(1900, 1100), ssaa=2,
           margin=40, edge_thr=0.35,
           caption="R5 面板样机 · 3/4 视图（装上旋钮、插座螺母、按钮、LED 的样子）")
    # knob: top and bottom 3/4 views side by side
    from PIL import Image
    tmp1, tmp2 = os.path.join(outdir, "_k1.png"), os.path.join(outdir, "_k2.png")
    render([(km[0], km[1], (0.35, 0.36, 0.38))], tmp1, (-60.0, 35.0), size=(800, 760), ssaa=3,
           margin=50, edge_thr=0.08, caption="旋钮 · 顶面（刻线对着 D 轴平面）")
    kb = km[0] * np.array([1, -1, -1]) + np.array([0, 0, KNOB_H])
    render([(kb, km[1], (0.35, 0.36, 0.38))], tmp2, (-60.0, 35.0), size=(800, 760), ssaa=3,
           margin=50, edge_thr=0.08, caption="旋钮 · 底面（螺母槽 + D 孔）")
    a, b = Image.open(tmp1), Image.open(tmp2)
    im = Image.new("RGB", (a.width + b.width, a.height), (246, 246, 248))
    im.paste(a, (0, 0))
    im.paste(b, (a.width, 0))
    im.save(os.path.join(outdir, "preview_knob.png"))
    os.remove(tmp1)
    os.remove(tmp2)


# =====================================================================================
# MAIN
# =====================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-render", action="store_true", help="skip PNG previews")
    ap.add_argument("--out", default=HERE, help="output folder (default: next to this script)")
    ap.add_argument("--tmp", default=None, help="folder for verification scratch files")
    args = ap.parse_args()
    out = args.out
    tmp = args.tmp or os.path.join(out, "_tmp")
    os.makedirs(tmp, exist_ok=True)

    ok, _ = run_checks()

    print("building cover plate ...")
    plate = build_plate()
    bb = plate.BoundingBox()
    print(f"   valid={plate.isValid()} bbox {bb.xlen:.3f} x {bb.ylen:.3f} x {bb.zlen:.3f} mm, "
          f"volume {plate.Volume() / 1000:.2f} cm3, grille holes {len(grille_points())}")
    # spot checks: hole centres empty, solid between holes
    for name, X, y in KNOBS + JACKS + BUTTONS:
        assert not plate.isInside(V(X, y, PLATE_T / 2)), name
    for X, y in leds() + [USBC] + SCREWS:
        assert not plate.isInside(V(X, y, PLATE_T / 2)), (X, y)
    assert plate.isInside(V(60.0, 30.0, 0.3)) and plate.isInside(V(122.0, 40.0, 1.0))
    cq.exporters.export(plate, os.path.join(out, "cover_plate.step"))
    cq.exporters.export(plate, os.path.join(out, "cover_plate.stl"), tolerance=0.01, angularTolerance=0.15)

    print("building knob ...")
    knob = build_knob()
    kb = knob.BoundingBox()
    print(f"   valid={knob.isValid()} bbox {kb.xlen:.3f} x {kb.ylen:.3f} x {kb.zlen:.3f} mm, "
          f"volume {knob.Volume() / 1000:.3f} cm3")
    cq.exporters.export(knob, os.path.join(out, "knob.step"))
    knob_print = knob.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 180).translate(cq.Vector(0, 0, KNOB_H))
    cq.exporters.export(knob_print, os.path.join(out, "knob.stl"), tolerance=0.005, angularTolerance=0.1)

    print("building paper template ...")
    pdf, svg = os.path.join(out, "template_1to1.pdf"), os.path.join(out, "template_1to1.svg")
    build_template(pdf, svg)
    verify_template(pdf, svg, tmp)

    if not args.no_render:
        render_previews(plate, knob, out)
    if not args.tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    print("done." if ok else "done (with check failures, see above).")


if __name__ == "__main__":
    main()
