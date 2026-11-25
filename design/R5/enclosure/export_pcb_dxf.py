"""Board outlines for the electronics supplier, as DXF (mm) for KiCad / Altium import.

Writes dxf/R5-PCB-main_主板板框.dxf and dxf/R5-PCB-usbc_USB-C小板板框.dxf from the same
parameters the enclosure, the drawings and the STEP files use (build_enclosure.py).

Coordinates are the enclosure's: X along the violin from the module's head end, y from the
G-string edge, viewed from the cover (component side up). DXF Y = -y, so the drawing looks
the same as the top view on M-R5-06. Text is ASCII so every CAD tool can read it.

Layers
  Edge.Cuts            board outline (import this one into KiCad Edge.Cuts)
  Holes                mounting holes (drill diameter)
  Keepout_Top          no parts on the top side (boss + screw clearance)
  Keepout_Bottom       no parts on the bottom side (screw head)
  Height_Top_6.5       top-side parts <= 6.5 mm above board top (under the cover ribs)
  Ref_Panel_Parts      encoder / jack / switch / LED / USB-C positions and body outlines
  Ref_Enclosure        module outline, shell inner wall, pickup cable hole (reference only)
  Notes                labels and height limits
Run:  PYTHONPATH=<cadquery site> python3 export_pcb_dxf.py
"""
from pathlib import Path

import ezdxf

import build_enclosure as E

HERE = Path(__file__).resolve().parent
OUT = HERE / "dxf"

LAYERS = {
    "Edge.Cuts": 7, "Holes": 1, "Keepout_Top": 6, "Keepout_Bottom": 5, "Height_Top_6.5": 3,
    "Ref_Panel_Parts": 4, "Ref_Enclosure": 8, "Notes": 2,
}


def P(X, y):
    return (X, -y)


def new_doc():
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    for name, color in LAYERS.items():
        doc.layers.add(name, color=color)
    return doc


def rect(msp, x0, y0, x1, y1, layer):
    msp.add_lwpolyline([P(x0, y0), P(x1, y0), P(x1, y1), P(x0, y1)], close=True, dxfattribs={"layer": layer})


def circle(msp, X, y, d, layer):
    msp.add_circle(P(X, y), d / 2, dxfattribs={"layer": layer})


def text(msp, s, X, y, h=1.0, layer="Notes"):
    msp.add_text(s, height=h, dxfattribs={"layer": layer}).set_placement(P(X, y))


def cross(msp, X, y, s=1.0, layer="Ref_Panel_Parts"):
    msp.add_line(P(X - s, y), P(X + s, y), dxfattribs={"layer": layer})
    msp.add_line(P(X, y - s), P(X, y + s), dxfattribs={"layer": layer})


def enclosure_ref(msp):
    rect(msp, 0, 0, E.L, E.W, "Ref_Enclosure")
    si = E.SHELL_IN
    rect(msp, si, si, E.L - si, E.W - si, "Ref_Enclosure")
    X, y, d = E.PICKUP_HOLE
    circle(msp, X, y, d, "Ref_Enclosure")
    text(msp, "PICKUP CABLE HOLE D%.1f (shell floor, adjustable)" % d, X - 20, y + 4.5, 0.8, "Ref_Enclosure")


def main_board():
    doc = new_doc()
    msp = doc.modelspace()
    x0, y0, x1, y1 = E.PCB
    rect(msp, x0, y0, x1, y1, "Edge.Cuts")
    for i, (X, y) in enumerate(E.PCB_BOSSES, 1):
        circle(msp, X, y, 2.2, "Holes")
        circle(msp, X, y, 4.4, "Keepout_Top")
        circle(msp, X, y, 3.8, "Keepout_Bottom")
        text(msp, "M%d" % i, X + 2.6, y + 0.4, 1.0)
    for rx0, ry0, rx1, ry1 in E.COVER_RIBS:
        rect(msp, max(rx0, x0), ry0 - 1.0, min(rx1, x1), ry1 + 1.0, "Height_Top_6.5")
    ex, ey = E.ENC_BODY
    for n, X, y in E.KNOBS:
        rect(msp, X - ex / 2, y - ey / 2, X + ex / 2, y + ey / 2, "Ref_Panel_Parts")
        cross(msp, X, y)
        text(msp, "ENC %s" % n, X - 5.5, y + 7.5, 1.0)
    for n, X, y in E.JACKS:
        circle(msp, X, y, E.JACK_BODY_D, "Ref_Panel_Parts")
        cross(msp, X, y)
        text(msp, "JACK %s" % n, X - 4.5, y + 6.0, 0.9)
    s = E.SW_BODY / 2
    for n, X, y in E.BUTTONS:
        rect(msp, X - s, y - s, X + s, y + s, "Ref_Panel_Parts")
        cross(msp, X, y, 0.8)
        text(msp, "SW %s" % n, X - 3.0, y - 3.8, 0.8)
    lx, ly = E.LED_BOX
    for i, (X, y) in enumerate(E.LEDS, 1):
        rect(msp, X - lx / 2, y - ly / 2, X + lx / 2, y + ly / 2, "Ref_Panel_Parts")
        text(msp, "LED%d" % i, X - 1.6, y - 1.6, 0.6)
    enclosure_ref(msp)
    notes = [
        "R5 MAIN BOARD OUTLINE - enclosure V0.2 proposal, see drawing M-R5-06",
        "Units mm. Module coordinates: X from head end, y from G-string edge; DXF Y = -y. View from cover = board TOP side.",
        "Board %.1f x %.1f mm (X %.1f-%.1f, y %.1f-%.1f), thickness 1.0, top face at Z-12.00." % (x1 - x0, y1 - y0, x0, x1, y0, y1),
        "Holes M1-M4: D2.2 through (M2 self-tapping screw from board bottom into cover bosses).",
        "Top keepout D4.4 at holes; bottom keepout D3.8 at holes (screw head 1.3 high).",
        "Top parts <= 9.5 above board top; inside Height_Top_6.5 boxes <= 6.5 (cover ribs).",
        "Bottom parts <= 1.5. Panel part positions are fixed by the cover openings.",
    ]
    for i, n in enumerate(notes):
        text(msp, n, 0, E.W + 4 + i * 2.0, 1.0)
    OUT.mkdir(exist_ok=True)
    p = OUT / "R5-PCB-main_主板板框.dxf"
    doc.saveas(p)
    return p


def usb_board():
    doc = new_doc()
    msp = doc.modelspace()
    x0, y0, x1, y1 = E.USB_BOARD
    rect(msp, x0, y0, x1, y1, "Edge.Cuts")
    for i, (X, y) in enumerate(E.USB_BOSSES, 1):
        circle(msp, X, y, 1.8, "Holes")
        circle(msp, X, y, 3.9, "Keepout_Top")
        text(msp, "N%d" % i, X + 2.2, y + 0.4, 0.8)
    X, y = E.USBC
    sx, sy = E.USBC_SLOT[1], E.USBC_SLOT[0]          # slot 9.4 long along y, 3.6 along X
    rect(msp, X - sx / 2, y - sy / 2, X + sx / 2, y + sy / 2, "Ref_Panel_Parts")
    cross(msp, X, y, 0.8)
    text(msp, "USB-C vertical, opening centre", X - 7, y + 6.5, 0.8)
    enclosure_ref(msp)
    notes = [
        "R5 USB-C BOARD OUTLINE - enclosure V0.2 proposal, see drawing M-R5-06",
        "Units mm. Same coordinates as the main board DXF (DXF Y = -y). View from cover = board TOP side.",
        "Board %.1f x %.1f mm (X %.1f-%.1f, y %.1f-%.1f), thickness 1.0, top face at Z-9.60." % (x1 - x0, y1 - y0, x0, x1, y0, y1),
        "Holes N1-N2: D1.8 through (M1.6 screws into cover bosses). Top keepout D3.9.",
        "Vertical USB-C receptacle: opening face at Z-0.3 (9.3 above board top), long side along y.",
    ]
    for i, n in enumerate(notes):
        text(msp, n, 0, E.W + 4 + i * 2.0, 1.0)
    OUT.mkdir(exist_ok=True)
    p = OUT / "R5-PCB-usbc_USB-C小板板框.dxf"
    doc.saveas(p)
    return p


if __name__ == "__main__":
    for p in (main_board(), usb_board()):
        print(p)
