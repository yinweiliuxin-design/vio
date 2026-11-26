"""Small 2-D drafting engine for the SmartVio R4 manufacturing drawings (M18).

One list of primitives per sheet is written to both SVG and PDF (reportlab), so the two outputs are identical.
Page units are millimetres, origin top-left, y down (A3 landscape 420 x 297).
Model views come from OCC exact hidden-line removal (HLRBRep_Algo) with an explicit projection frame, so every
model point can be mapped to the page and dimensions are placed on real geometry, not on guessed offsets.
"""
import math, html
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.BRepLib import BRepLib
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE, TopAbs_REVERSED
from OCP.TopoDS import TopoDS
from OCP.BRepTools import BRepTools_WireExplorer

FONT_FAMILY = "'WenQuanYi Zen Hei','Noto Sans CJK SC','Microsoft YaHei','SimHei',sans-serif"
CTF_COLOR = "#b3001b"
INK = "#111111"

# Projection frames: (N toward the viewer, X = page right) in WORLD coordinates (STEP: X, -logicalY, Z).
VIEWS = {
    "top": ((0, 0, 1), (1, 0, 0)),       # from +Z, logical Y down the page
    "bottom": ((0, 0, -1), (1, 0, 0)),   # from -Z, flipped about X (logical Y up the page)
    "front": ((0, -1, 0), (1, 0, 0)),    # viewer at south (large logical Y) looking north; page right = +X
    "back": ((0, 1, 0), (-1, 0, 0)),
    "left": ((-1, 0, 0), (0, -1, 0)),    # viewer at the head end (X<0); page right = south (+logical Y)
    "right": ((1, 0, 0), (0, 1, 0)),     # viewer at the tail end; page right = north (-logical Y)
}


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _discretize(edge, defl=0.01):
    c = BRepAdaptor_Curve(edge)
    d = GCPnts_QuasiUniformDeflection(c, defl, c.FirstParameter(), c.LastParameter())
    if not d.IsDone():
        return []
    return [d.Value(i) for i in range(1, d.NbPoints() + 1)]


def hlr_polylines(shape, kind, hidden=False, defl=0.01):
    N, X = VIEWS[kind]
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*N), gp_Dir(*X))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)

    def grab(comp):
        if comp.IsNull():
            return []
        BRepLib.BuildCurves3d_s(comp, 1e-6)
        out = []
        exp = TopExp_Explorer(comp, TopAbs_EDGE)
        while exp.More():
            pts = _discretize(TopoDS.Edge_s(exp.Current()), defl)
            if len(pts) > 1:
                out.append([(p.X(), p.Y()) for p in pts])
            exp.Next()
        return out

    vis = grab(h.VCompound()) + grab(h.OutLineVCompound())
    smooth = grab(h.Rg1LineVCompound())
    hid = (grab(h.HCompound()) + grab(h.OutLineHCompound())) if hidden else []
    return vis, smooth, hid


def wire_polys(face, defl=0.01):
    """Ordered closed polygons (3-D world points) of a face's wires."""
    polys = []
    for w in [face.outerWire()] + face.innerWires():
        pts = []
        ex = BRepTools_WireExplorer(w.wrapped, face.wrapped)
        while ex.More():
            e = ex.Current()
            seg = _discretize(e, defl)
            if e.Orientation() == TopAbs_REVERSED:
                seg = seg[::-1]
            seg = [(p.X(), p.Y(), p.Z()) for p in seg]
            if pts and seg and math.dist(pts[-1], seg[0]) < 1e-6:
                seg = seg[1:]
            pts += seg
            ex.Next()
        if len(pts) > 2:
            polys.append(pts)
    return polys


def text_width(t, size):
    w = 0
    for ch in str(t):
        w += size * (1.0 if ord(ch) > 0x2E80 else 0.56)
    return w


class Page:
    def __init__(self, w=420, h=297):
        self.w, self.h = w, h
        self.items = []
        self._clip = 0

    # primitives -------------------------------------------------------------
    def line(self, x1, y1, x2, y2, w=0.25, c=INK, dash=None):
        self.items.append(("poly", [(x1, y1), (x2, y2)], w, c, dash, False, None))

    def poly(self, pts, w=0.25, c=INK, dash=None, closed=False, fill=None):
        if len(pts) > 1:
            self.items.append(("poly", list(pts), w, c, dash, closed, fill))

    def rect(self, x, y, w_, h_, w=0.25, c=INK, fill=None, dash=None):
        self.poly([(x, y), (x + w_, y), (x + w_, y + h_), (x, y + h_)], w, c, dash, True, fill)

    def circle(self, x, y, r, w=0.25, c=INK, fill=None, dash=None):
        self.items.append(("circle", x, y, r, w, c, fill, dash))

    def text(self, x, y, t, size=2.5, anchor="start", rot=0, c=INK, bold=False):
        t = str(t).replace("\u2212", "-").replace("\u2022", "\u00b7")   # glyphs missing in WenQuanYi Zen Hei
        self.items.append(("text", x, y, t, size, anchor, rot, c, bold))

    def arrow(self, x, y, ang_deg, size=2.2, c=INK):
        """Filled arrow head with its tip at (x,y) pointing along ang_deg (page coords, 0 = +x, 90 = +y)."""
        a = math.radians(ang_deg)
        bx, by = x - size * math.cos(a), y - size * math.sin(a)
        nx, ny = -math.sin(a) * size * 0.18, math.cos(a) * size * 0.18
        self.poly([(x, y), (bx + nx, by + ny), (bx - nx, by - ny)], 0.1, c, None, True, c)

    def hatch(self, polys, spacing=0.9, angle=45, w=0.12, c=INK, fill="#e9e9e9"):
        """Even-odd hatch of closed page polygons."""
        polys = [p for p in polys if len(p) > 2]
        if not polys:
            return
        xs = [x for p in polys for x, _ in p]
        ys = [y for p in polys for _, y in p]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        a = math.radians(angle)
        d = math.hypot(x1 - x0, y1 - y0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        lines = []
        n = int(d / spacing) + 2
        for i in range(-n, n + 1):
            off = i * spacing
            px, py = cx - math.sin(a) * off, cy + math.cos(a) * off
            lines.append((px - math.cos(a) * d, py - math.sin(a) * d, px + math.cos(a) * d, py + math.sin(a) * d))
        self._clip += 1
        self.items.append(("hatch", polys, lines, w, c, fill, self._clip))

    # composite helpers ----------------------------------------------------
    def ctf_tag(self, x, y, tag, size=2.0):
        """Critical-to-function flag: tag inside a flattened hexagon (red)."""
        tw = text_width(tag, size) + 1.6
        h = size * 1.25
        pts = [(x, y), (x + 0.8, y - h / 2), (x + tw - 0.8, y - h / 2), (x + tw, y), (x + tw - 0.8, y + h / 2), (x + 0.8, y + h / 2)]
        self.poly(pts, 0.25, CTF_COLOR, None, True, "#ffffff")
        self.text(x + tw / 2, y + size * 0.36, tag, size, "middle", 0, CTF_COLOR, True)
        return tw

    def label(self, x, y, t, size=2.2, c=INK, ctf=None, anchor="start", rot=0):
        if ctf and rot == 0:
            tw = text_width(t, size)
            x0 = x - (tw / 2 if anchor == "middle" else tw if anchor == "end" else 0)
            self.text(x0, y, t, size, "start", 0, CTF_COLOR)
            self.ctf_tag(x0 + tw + 0.8, y - size * 0.35, ctf, size * 0.85)
        else:
            self.text(x, y, t, size, anchor, rot, CTF_COLOR if ctf else c)
            if ctf and rot:
                tw = text_width(t, size)
                self.ctf_tag(x - size * 0.95, y - tw / 2 - 4.2 if anchor == "middle" else y - tw - 4.2, ctf, size * 0.85)

    def dim_h(self, p1, p2, yline, t, ctf=None, size=2.2, ext=1.2):
        (x1, y1), (x2, y2) = p1, p2
        c = CTF_COLOR if ctf else INK
        for x, y in ((x1, y1), (x2, y2)):
            s = 1 if yline > y else -1
            self.line(x, y + s * 0.6, x, yline + s * ext, 0.13, c)
        lo, hi = min(x1, x2), max(x1, x2)
        tw = text_width(t, size) + (6 if ctf else 0)
        if hi - lo > 7:
            self.line(lo, yline, hi, yline, 0.18, c)
            self.arrow(lo, yline, 180, 2.0, c)
            self.arrow(hi, yline, 0, 2.0, c)
            tx = (lo + hi) / 2
        else:
            self.line(lo - 4, yline, hi + 4 + (tw if hi - lo < tw else 0), yline, 0.18, c)
            self.arrow(lo, yline, 0, 2.0, c)
            self.arrow(hi, yline, 180, 2.0, c)
            tx = hi + 4 + tw / 2 if hi - lo < tw else (lo + hi) / 2
        self.label(tx, yline - 0.7, t, size, ctf=ctf, anchor="middle")

    def dim_v(self, p1, p2, xline, t, ctf=None, size=2.2, ext=1.2, lab_y=None):
        (x1, y1), (x2, y2) = p1, p2
        c = CTF_COLOR if ctf else INK
        for x, y in ((x1, y1), (x2, y2)):
            s = 1 if xline > x else -1
            self.line(x + s * 0.6, y, xline + s * ext, y, 0.13, c)
        lo, hi = min(y1, y2), max(y1, y2)
        if hi - lo > 7:
            self.line(xline, lo, xline, hi, 0.18, c)
            self.arrow(xline, lo, 270, 2.0, c)
            self.arrow(xline, hi, 90, 2.0, c)
            ty = (lo + hi) / 2
            self.text(xline - 0.8, ty, t, size, "middle", -90, c)
            if ctf:
                self.ctf_tag(xline - 0.8 - size * 1.1, ty + text_width(t, size) / 2 + 1.2, ctf, size * 0.85)
        else:
            self.line(xline, lo - 4, xline, hi + 4, 0.18, c)
            self.arrow(xline, lo, 90, 2.0, c)
            self.arrow(xline, hi, 270, 2.0, c)
            self.label(xline + 1.5, hi + 6.5 if lab_y is None else lab_y, t, size, ctf=ctf)

    def leader(self, p, tx, ty, t, ctf=None, size=2.2, dot=False):
        c = CTF_COLOR if ctf else INK
        x, y = p
        ang = math.degrees(math.atan2(y - ty, x - tx))
        self.line(tx, ty, x, y, 0.15, c)
        if dot:
            self.circle(x, y, 0.4, 0.1, c, c)
        else:
            self.arrow(x, y, ang, 1.8, c)
        right = tx >= x
        tw = text_width(t, size) + (6 if ctf else 0)
        x2 = tx + (tw + 1 if right else -(tw + 1))
        self.line(tx, ty, x2, ty, 0.15, c)
        self.label(tx + 0.5 if right else x2 + 0.5, ty - 0.6, t, size, ctf=ctf)

    def table(self, x, y, cols, rows, size=2.0, rowh=3.6, header_fill="#eeeeee", ctf_col=None):
        """cols = [(title, width)], rows = list of lists. Returns bottom y."""
        tot = sum(w for _, w in cols)
        self.rect(x, y, tot, rowh, 0.2, INK, header_fill)
        cx = x
        for t, w in cols:
            self.text(cx + 0.8, y + rowh - 1.0, t, size, "start", 0, INK, True)
            cx += w
        yy = y + rowh
        for r in rows:
            ctf = ctf_col is not None and r[ctf_col]
            self.rect(x, yy, tot, rowh, 0.12, "#777777")
            cx = x
            for (t, w), v in zip(cols, r):
                col = CTF_COLOR if (ctf and v) else INK
                self.text(cx + 0.8, yy + rowh - 1.0, v, size, "start", 0, col)
                cx += w
            yy += rowh
        cx = x
        for _, w in cols[:-1]:
            cx += w
            self.line(cx, y, cx, yy, 0.12, "#777777")
        return yy

    # output -----------------------------------------------------------------
    def svg(self):
        o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}mm" height="{self.h}mm" viewBox="0 0 {self.w} {self.h}">',
             f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>',
             f'<g font-family="{FONT_FAMILY}" stroke-linecap="round" stroke-linejoin="round">']
        for it in self.items:
            k = it[0]
            if k == "poly":
                _, pts, w, c, dash, closed, fill = it
                d = "M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in pts) + (" Z" if closed else "")
                da = f' stroke-dasharray="{dash}"' if dash else ""
                o.append(f'<path d="{d}" fill="{fill or "none"}" stroke="{c}" stroke-width="{w}"{da}/>')
            elif k == "circle":
                _, x, y, r, w, c, fill, dash = it
                da = f' stroke-dasharray="{dash}"' if dash else ""
                o.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r:.3f}" fill="{fill or "none"}" stroke="{c}" stroke-width="{w}"{da}/>')
            elif k == "text":
                _, x, y, t, size, anchor, rot, c, bold = it
                tr = f' transform="rotate({rot} {x:.3f} {y:.3f})"' if rot else ""
                fw = ' font-weight="bold"' if bold else ""
                o.append(f'<text x="{x:.3f}" y="{y:.3f}" font-size="{size}" text-anchor="{anchor}" fill="{c}"{fw}{tr}>{html.escape(t)}</text>')
            elif k == "hatch":
                _, polys, lines, w, c, fill, cid = it
                d = " ".join("M" + " L".join(f"{x:.3f},{y:.3f}" for x, y in p) + " Z" for p in polys)
                o.append(f'<clipPath id="h{cid}"><path d="{d}" clip-rule="evenodd"/></clipPath>')
                o.append(f'<path d="{d}" fill="{fill}" fill-rule="evenodd" stroke="none"/>')
                ls = "".join(f'<line x1="{a:.2f}" y1="{b:.2f}" x2="{e:.2f}" y2="{f:.2f}"/>' for a, b, e, f in lines)
                o.append(f'<g clip-path="url(#h{cid})" stroke="{c}" stroke-width="{w}">{ls}</g>')
        o.append("</g></svg>")
        return "\n".join(o)

    def pdf(self, cv):
        from reportlab.lib.units import mm
        from reportlab.pdfgen.canvas import FILL_EVEN_ODD
        from reportlab.lib.colors import HexColor
        H = self.h
        P = lambda x, y: (x * mm, (H - y) * mm)
        cv.setPageSize((self.w * mm, self.h * mm))
        cv.setFillColor(HexColor("#ffffff"))
        cv.rect(0, 0, self.w * mm, self.h * mm, stroke=0, fill=1)
        cv.setLineCap(1)
        cv.setLineJoin(1)

        def path(pts, closed):
            p = cv.beginPath()
            x, y = P(*pts[0])
            p.moveTo(x, y)
            for q in pts[1:]:
                p.lineTo(*P(*q))
            if closed:
                p.close()
            return p
        for it in self.items:
            k = it[0]
            if k == "poly":
                _, pts, w, c, dash, closed, fill = it
                cv.setStrokeColor(HexColor(c))
                cv.setLineWidth(w * mm)
                cv.setDash([float(v) * mm for v in str(dash).replace(",", " ").split()] if dash else [])
                if fill:
                    cv.setFillColor(HexColor(fill))
                cv.drawPath(path(pts, closed), stroke=1, fill=1 if fill else 0)
                cv.setDash([])
            elif k == "circle":
                _, x, y, r, w, c, fill, dash = it
                cv.setStrokeColor(HexColor(c))
                cv.setLineWidth(w * mm)
                cv.setDash([float(v) * mm for v in str(dash).replace(",", " ").split()] if dash else [])
                if fill:
                    cv.setFillColor(HexColor(fill))
                cv.circle(*P(x, y), r * mm, stroke=1, fill=1 if fill else 0)
                cv.setDash([])
            elif k == "text":
                _, x, y, t, size, anchor, rot, c, bold = it
                cv.saveState()
                cv.setFillColor(HexColor(c))
                cv.setFont("WQY", size * mm * (1.0 if not bold else 1.0))
                cv.translate(*P(x, y))
                if rot:
                    cv.rotate(-rot)
                if bold:
                    cv.setStrokeColor(HexColor(c))
                    cv.setLineWidth(0.05 * mm)
                    tobj = cv.beginText()
                    tobj.setTextRenderMode(2)
                    w = cv.stringWidth(t, "WQY", size * mm)
                    tobj.setTextOrigin(-w / 2 if anchor == "middle" else -w if anchor == "end" else 0, 0)
                    tobj.textLine(t)
                    cv.drawText(tobj)
                elif anchor == "middle":
                    cv.drawCentredString(0, 0, t)
                elif anchor == "end":
                    cv.drawRightString(0, 0, t)
                else:
                    cv.drawString(0, 0, t)
                cv.restoreState()
            elif k == "hatch":
                _, polys, lines, w, c, fill, cid = it
                cv.saveState()
                p = cv.beginPath()
                for poly in polys:
                    p.moveTo(*P(*poly[0]))
                    for q in poly[1:]:
                        p.lineTo(*P(*q))
                    p.close()
                cv.setFillColor(HexColor(fill))
                cv.clipPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
                cv.setStrokeColor(HexColor(c))
                cv.setLineWidth(w * mm)
                for a, b, e, f in lines:
                    cv.line(*P(a, b), *P(e, f))
                cv.restoreState()
        cv.showPage()


class View:
    """A model view placed on a page. pt(x, y_logical, z) -> page point."""

    def __init__(self, page, shape, kind, scale, at, hidden=False, w=0.3, smooth=True, defl=0.01, uvbox=None, draw=True):
        self.page, self.kind, self.s = page, kind, scale
        N, X = VIEWS[kind]
        self.N, self.X, self.Y = N, X, _cross(N, X)
        vis, sm, hid = hlr_polylines(shape, kind, hidden, defl) if shape is not None else ([], [], [])
        pts = [q for pl in vis + sm + hid for q in pl]
        if uvbox is None:
            umin, umax = min(u for u, _ in pts), max(u for u, _ in pts)
            vmin, vmax = min(v for _, v in pts), max(v for _, v in pts)
        else:
            umin, vmin, umax, vmax = uvbox
        self.umin, self.umax, self.vmin, self.vmax = umin, umax, vmin, vmax
        self.ox = at[0] - scale * umin
        self.oy = at[1] + scale * vmax
        self.box = (at[0], at[1], at[0] + scale * (umax - umin), at[1] + scale * (vmax - vmin))
        if draw:
            for pl in hid:
                page.poly([self.uv(u, v) for u, v in pl], 0.13, "#666666", "0.9 0.6")
            for pl in sm:
                page.poly([self.uv(u, v) for u, v in pl], 0.13 if smooth else 0.0, "#555555")
            for pl in vis:
                page.poly([self.uv(u, v) for u, v in pl], w, INK)

    def uv(self, u, v):
        return (self.ox + self.s * u, self.oy - self.s * v)

    def pt(self, x, y, z=0.0):
        W = (x, -y, z)
        u = sum(a * b for a, b in zip(W, self.X))
        v = sum(a * b for a, b in zip(W, self.Y))
        return self.uv(u, v)

    def wpt(self, p):  # world point
        u = sum(a * b for a, b in zip(p, self.X))
        v = sum(a * b for a, b in zip(p, self.Y))
        return self.uv(u, v)

    def hatch(self, polys3d, **kw):
        self.page.hatch([[self.wpt(p) for p in poly] for poly in polys3d], **kw)

    def title(self, t, sub=None, size=3.0, off=8.5):
        x0, y0, x1, y1 = self.box
        self.page.text(x0, y0 - off, t, size, "start", 0, INK, True)
        if sub:
            self.page.text(x0 + text_width(t, size) + 3, y0 - off, sub, 2.2, "start", 0, "#444444")


def section(cq, shape, axis, pos, keep, crop=None):
    """Cut shape by the world plane axis=pos, keep side keep(+1/-1), optional world crop box.
    Returns (cut solid, list of 3-D polygons of the cut faces on the plane)."""
    big = 1e4
    lo = list(crop[:3]) if crop else [-big] * 3
    hi = list(crop[3:]) if crop else [big] * 3
    i = "XYZ".index(axis)
    if keep > 0:
        lo[i] = pos
    else:
        hi[i] = pos
    tool = cq.Solid.makeBox(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2], cq.Vector(*lo))
    cut = shape.intersect(tool)
    polys = []
    for f in cut.Faces():
        if f.geomType() != "PLANE":
            continue
        n = f.normalAt()
        c = f.Center()
        if abs(abs((n.x, n.y, n.z)[i]) - 1) < 1e-6 and abs((c.x, c.y, c.z)[i] - pos) < 1e-5:
            polys += wire_polys(f)
    return cut, polys


def crop(cq, shape, box):
    x0, y0, z0, x1, y1, z1 = box
    return shape.intersect(cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0)))
