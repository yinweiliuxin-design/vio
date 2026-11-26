"""Export the visible R5 enclosure V0.3 parts as triangle meshes for the photoreal renders.

Usage: python3 export_meshes.py <out.json>
Geometry comes straight from build_enclosure.py (same parameters as drawings M-R5-00…06).
Model coordinates: X along the cover from the head end, Y = -y (y from the G-string edge), Z up (0 = cover top).
The cover is split into two materials: the matte top/sides and the engraved recesses (labels and logo).
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import numpy as np                       # noqa: E402
import cadquery as cq                    # noqa: E402
import build_enclosure as E              # noqa: E402


def tess(shape, tol=0.01, ang=0.12):
    vs, ts = shape.tessellate(tol, ang)
    return np.array([(v.x, v.y, v.z) for v in vs], np.float32), np.array(ts, np.uint32).reshape(-1)


def tess_faces(faces, tol=0.01, ang=0.12):
    if not faces:
        return None
    return tess(cq.Compound.makeCompound(faces), tol, ang)


def pack(vi):
    v, i = vi
    return {"pos": base64.b64encode(v.tobytes()).decode(), "idx": base64.b64encode(i.tobytes()).decode()}


def beam_slab():
    """A 62 mm wide piece of the violin's centre beam with the stepped pocket (for the 3/4 view)."""
    half = 31.0
    slab = (cq.Workplane("XY").workplane(offset=-25.0).center(E.L / 2, -E.W / 2)
            .rect(E.L + 400.0, 2 * half).extrude(25.0).edges("|X").fillet(3.0).val())
    rebate = E.rrect(-E.POCKET_GAP, -E.POCKET_GAP, E.L + E.POCKET_GAP, E.W + E.POCKET_GAP,
                     E.R + E.POCKET_GAP, E.ZC, 1.0)
    e = E.LEDGE_IN
    zones = [(e, E.POCKET_STEP_X[0], -E.DEPTH[0]), (E.POCKET_STEP_X[0], E.POCKET_STEP_X[1], -E.DEPTH[1]),
             (E.POCKET_STEP_X[1], E.L - e, -E.DEPTH[2])]
    deep = E.fuse([E.box(x0, e, x1, E.W - e, zb, E.ZC + 0.5) for x0, x1, zb in zones])
    for X, y in E.SCREWS:
        deep = deep.cut(E.notch_tool(X, y, E.PAD_R))
    return slab.cut(rebate).cut(deep).clean()


def main(out):
    print("building cover with engraving ...", flush=True)
    cover = E.build_cover(text=True)
    top, eng = [], []
    for f in cover.Faces():
        bb = f.BoundingBox()
        # engraved recess: floor at -0.15 and walls between -0.15 and 0, small in plan
        # (glyph islands such as the inside of "O" stay at Z 0 and keep the matte finish)
        if bb.zmin > -E.ENGRAVE - 0.02 and bb.zmin < -0.01 and bb.zmax < 0.01 and bb.xlen < 40 and bb.ylen < 40:
            eng.append(f)
        else:
            top.append(f)
    print(f"  cover faces: {len(top)} matte, {len(eng)} engraved", flush=True)
    parts = {"cover": pack(tess_faces(top)), "cover_engrave": pack(tess_faces(eng))}

    knob = E.build_knob()
    parts["knob"] = pack(tess(knob, 0.006, 0.08))
    parts["cap"] = pack(tess(E.build_cap(), 0.005, 0.1))
    parts["lightpipe"] = pack(tess(E.build_lightpipe(), 0.005, 0.1))
    scr = E.build_screws()
    parts["screw"] = pack(tess(scr["screw_ST2.2x9.5_1"], 0.005, 0.1))
    print("building beam slab ...", flush=True)
    parts["beam"] = pack(tess(beam_slab(), 0.02, 0.15))

    meta = {k: getattr(E, k) for k in ("L", "W", "R", "POCKET_GAP", "KNOB_LIFT", "ENGRAVE", "SCREW_D", "CSK_D",
                                       "JACK_HOLE_D", "JACK_NOSE_D", "JACK_TOP", "LP_HOLE_D", "BTN_HOLE_D")}
    meta.update(KNOBS=E.KNOBS, JACKS=E.JACKS, BUTTONS=E.BUTTONS, LEDS=E.LEDS, USBC=E.USBC, USBC_SLOT=E.USBC_SLOT,
                REC=E.REC, SCREWS=E.SCREWS, SPEAKER=E.SPEAKER, SPEAKER_D=E.SPEAKER_D)
    with open(out, "w") as fp:
        json.dump({"meta": meta, "parts": parts}, fp)
    print("wrote", out, os.path.getsize(out) // 1024, "KB")


if __name__ == "__main__":
    main(sys.argv[1])
