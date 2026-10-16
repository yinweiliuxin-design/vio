"""SmartVio R4 manufacturing drawings (review item M18), generated from the delivered STEP parts.

Run after build_mechanics.py:   python3 cad/engineering_drawings.py
Output: drawings/M-R4-*.svg, drawings/M-R4-*.pdf, drawings/M-R4-drawings-all.pdf, drawings/ctf-register.json
Views are exact OCC hidden-line projections of cad/*.step; dimensions are placed on projected model points.
Coordinates: X toward the tail (X0 = wheel/head end), logical Y toward the south (jack side), Z outward;
datum A = instrument mounting face Z0 (upper-cover skirt bottom).  STEP world Y = -logical Y.
"""
from pathlib import Path
import sys, os, json, ast, math
BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cadquery as cq
import drawlib as D
from drawlib import Page, View, section, crop, CTF_COLOR, INK

CAD = BASE / "cad"; REF = BASE / "reference/components"; OUT = BASE / "drawings"; OUT.mkdir(exist_ok=True)
PAR = json.loads((BASE / "parameters.json").read_text("utf8"))
SRC = (CAD / "build_mechanics.py").read_text("utf8")
DATE = "2026-10-16"; REV = "R4.1"


def const(name):
    for node in ast.parse(SRC).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


KEYS = const("KEYS"); LP = const("LP"); PORTS = const("ports"); USBPOST = const("USBPOST"); USBSCREW = const("USBSCREW")
LEDGES = const("LEDGES"); JACK_NAMES = const("JACK_NAMES")
SNAPX = PAR["snap_stations_x"]; SCREWS = PAR["screw_xy"]
LEG = [("VOL", 15, 18.9), ("TONE", 35, 18.9), ("FX", 55, 18.9)] + [(t, x, 29.7) for t, x in zip(["FX", "MODE", "MIX", "PWR", "BT"], KEYS)] \
    + [(t, x, 45.4) for t, (x, y) in zip(JACK_NAMES, PORTS)] + [("USB", 98, 15.6)]

_cache = {}


def part(n):
    if n not in _cache:
        p = CAD / f"{n}.step"
        if not p.exists():
            p = CAD / "variants" / f"{n}.step"
        if not p.exists():
            p = CAD / "stock" / f"{n}.step"
        if not p.exists():
            p = REF / f"{n}.step"
        _cache[n] = cq.importers.importStep(str(p)).val()
    return _cache[n]


def f2(v):
    return f"{v:.2f}"


def fz(v):
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return s if s != "-0" else "0"


CTF = []   # register for FAI / RFQ


def ctf(tag, part_name, feature, nominal, tol, method, chain="", qty=1):
    CTF.append(dict(id=tag, part=part_name, feature=feature, nominal=nominal, tol=tol, method=method, chain=chain, qty_per_part=qty))
    return tag


MAT_POM = "POM-C 共聚甲醛，黑色（整料 CNC，非染色后处理）"
FIN_POM = "外观面哑光：机加 Ra≤1.6，可选细喷砂（喷砂在雕字前）；雕字不填色"
GENERAL = [
    "1. 未注公差按 ISO 2768-m（GB/T 1804-m）；未注几何公差 ISO 2768-K。在 23±2 °C 下检验（POM 线胀系数约 1.1×10⁻⁴/K）。",
    "2. 红色尺寸与六角标签 Kn 为关键功能尺寸（CTF）：首件 100% 检测，结果记入 FAI-checklist.md；量产前另定抽样。",
    "3. 单位 mm；第一角画法；X 向琴尾（X0=滚轮端=琴头端），Y 向南（插座侧），Z 向外。基准 A=琴面安装面 Z0。",
    "4. 锐边倒钝 0.1–0.2（配合面、卡扣/卡钩根部与窗口棱边除外）；无毛刺、残料；深腔内角按 STEP（R≥1.2）。",
    "5. 形状以同名 STEP（step/*.step，R4.1）为准，图面只标关键尺寸；图与 STEP 冲突时停工询问，不得自行取舍。",
]


def frame(pg, no, title, partname, material, finish, qty, scale, sheet, extra=()):
    pg.rect(10, 10, 400, 277, 0.5)
    pg.text(14, 17, "SmartVio R4  首样结构件制造图", 3.6, bold=True)
    pg.text(110, 17, title, 3.6, bold=True)
    pg.text(406, 17, "状态：首样工程图 / 非量产放行（未经实物验证）", 2.6, "end", 0, "#a14a00")
    pg.line(10, 20, 410, 20, 0.3)
    # technical requirements
    x0, y0 = 12, 243
    pg.rect(x0, y0, 214, 42, 0.3)
    pg.text(x0 + 1.5, y0 + 4, "技术要求", 2.6, bold=True)
    lines = GENERAL + list(extra)
    for i, t in enumerate(lines[:9]):
        pg.text(x0 + 1.5, y0 + 8.4 + i * 4.0, t, 2.0)
    # title block
    tx, ty = 228, 243
    pg.rect(tx, ty, 180, 42, 0.4)
    rows = [("名称", partname), ("图号", f"{no}   版本 {REV}   第 {sheet} 页"), ("材料", material), ("表面/颜色", finish),
            ("数量", qty), ("比例 / 单位", f"{scale}   ·   mm   ·   第一角画法"), ("一般公差", "ISO 2768-m（CTF 按图）"),
            ("日期 / 编制", f"{DATE}   ·   CAD 生成稿，需工程师审签      审核：______  批准：______")]
    for i, (k, v) in enumerate(rows):
        y = ty + i * 5.25
        if i:
            pg.line(tx, y, tx + 180, y, 0.15)
        pg.text(tx + 1.5, y + 3.8, k, 2.2, bold=True)
        pg.text(tx + 21, y + 3.8, v, 2.1 if len(v) < 70 else 1.8)
    pg.line(tx + 19.5, ty, tx + 19.5, ty + 42, 0.15)
    # first-angle symbol
    sx, sy = 392, 266.5
    pg.poly([(sx - 13, sy - 1.6), (sx - 7, sy - 3), (sx - 7, sy + 3), (sx - 13, sy + 1.6)], 0.2, closed=True)
    pg.circle(sx - 1.5, sy, 3, 0.2); pg.circle(sx - 1.5, sy, 1.6, 0.2)


def head_tail(pg, x0, x1, y, note="滚轮端 X=0 朝琴头"):
    pg.line(x0 + 2, y, x1 - 2, y, 0.35)
    pg.arrow(x0, y, 180, 3); pg.arrow(x1, y, 0, 3)
    pg.text(x0 + 4, y - 1.4, "琴头 HEAD", 2.6, bold=True)
    pg.text(x1 - 4, y - 1.4, "琴尾 TAIL", 2.6, "end", 0, INK, True)
    pg.text((x0 + x1) / 2, y - 1.4, note, 2.2, "middle")


def cut_line(pg, view, y_log, x0, x1, letter, up=True):
    """Section line at logical Y on a top view, with view arrows (GB/T 4458.6 style)."""
    a, b = view.pt(x0 - 4, y_log), view.pt(x1 + 4, y_log)
    pg.line(a[0], a[1], b[0], b[1], 0.18, "#333333", "6 1 1 1")
    for (px, py) in (a, b):
        pg.line(px - 3 if px < b[0] else px, py, px + 3 if px < b[0] else px, py, 0.6)
        tip = py - 6 if up else py + 6
        xx = px - 1.5 if px < b[0] else px + 1.5
        pg.line(xx, py, xx, tip + (1.6 if up else -1.6), 0.3)
        pg.arrow(xx, tip, 270 if up else 90, 2.4)
        pg.text(xx + (-2.5 if px < b[0] else 2.5), tip + (0.5 if up else 2.5), letter, 3.2, "middle", 0, INK, True)


def cut_line_v(pg, view, x_log, y0, y1, letter, right=True):
    """Section line at logical X on a top view; arrows point toward +X page direction if right."""
    a, b = view.pt(x_log, y0 - 3), view.pt(x_log, y1 + 3)
    pg.line(a[0], a[1], b[0], b[1], 0.18, "#333333", "6 1 1 1")
    for (px, py) in (a, b):
        pg.line(px, py - 2.5 if py < b[1] else py, px, py + 2.5 if py < b[1] else py, 0.6)
        yy = py - 1.2 if py < b[1] else py + 1.2
        tip = px + 6 if right else px - 6
        pg.line(px, yy, tip - (1.6 if right else -1.6), yy, 0.3)
        pg.arrow(tip, yy, 0 if right else 180, 2.4)
        pg.text(tip + (2.4 if right else -2.4), yy + 1.1, letter, 3.2, "middle", 0, INK, True)


def save(pg, name, allpages):
    (OUT / f"{name}.svg").write_text(pg.svg(), encoding="utf8")
    from reportlab.pdfgen import canvas
    cv = canvas.Canvas(str(OUT / f"{name}.pdf"))
    pg.pdf(cv); cv.save()
    allpages.append(pg)
    print("sheet", name, flush=True)


def hole_chart(pg, x, y, rows, title, size=1.85, rowh=3.3, widths=(9, 30, 37, 34, 32)):
    pg.text(x, y - 1.2, title, 2.4, bold=True)
    cols = list(zip(["标号", "特征", "位置 X, Y", "尺寸", "Z / 深度"], widths))
    rr = [[r[0], r[1], r[2], r[3], r[4]] for r in rows]
    # colour CTF rows: last element flag
    yy = y
    tot = sum(widths)
    pg.rect(x, yy, tot, rowh, 0.2, INK, "#eeeeee")
    cx = x
    for t, w in cols:
        pg.text(cx + 0.7, yy + rowh - 0.95, t, size, bold=True); cx += w
    yy += rowh
    for r in rows:
        col = CTF_COLOR if len(r) > 5 and r[5] else INK
        pg.rect(x, yy, tot, rowh, 0.1, "#888888")
        cx = x
        for v, w in zip(r[:5], widths):
            pg.text(cx + 0.7, yy + rowh - 0.95, v, size, "start", 0, col); cx += w
        yy += rowh
    cx = x
    for w in widths[:-1]:
        cx += w; pg.line(cx, y, cx, yy, 0.1, "#888888")
    return yy


def ctf_table(pg, x, y, ids, size=1.85, rowh=3.3, widths=(9, 52, 30, 26, 27), maxrows=40):
    rows = [c for c in CTF if c["id"] in ids][:maxrows]
    pg.text(x, y - 1.2, "关键功能尺寸（CTF）", 2.4, bold=True, c=CTF_COLOR)
    hdr = ["Kn", "特征", "名义", "公差", "检具"]
    tot = sum(widths)
    pg.rect(x, y, tot, rowh, 0.2, INK, "#f6e3e6")
    cx = x
    for t, w in zip(hdr, widths):
        pg.text(cx + 0.7, y + rowh - 0.95, t, size, bold=True); cx += w
    yy = y + rowh
    for c in rows:
        pg.rect(x, yy, tot, rowh, 0.1, "#888888")
        cx = x
        for v, w in zip([c["id"], c["feature"], c["nominal"], c["tol"], c["method"]], widths):
            s = str(v)
            while D.text_width(s, size) > w - 1.2 and len(s) > 3:
                s = s[:-2] + "…"
            pg.text(cx + 0.7, yy + rowh - 0.95, s, size, "start", 0, CTF_COLOR if cx == x else INK); cx += w
        yy += rowh
    cx = x
    for w in widths[:-1]:
        cx += w; pg.line(cx, y, cx, yy, 0.1, "#888888")
    return yy


def tag_at(pg, p, tag, dx=1.5, dy=-1.5):
    pg.ctf_tag(p[0] + dx, p[1] + dy, tag, 1.7) if tag.startswith("U") or tag[0] in "LBSFKPIQ" and tag[1:].isdigit() else None


def idmark(pg, p, t, dx=0.0, dy=0.0, c="#1a4f8a"):
    x, y = p[0] + dx, p[1] + dy
    w = D.text_width(t, 1.8) + 1.2
    pg.rect(x - w / 2, y - 1.3, w, 2.6, 0.15, c, "#ffffff")
    pg.text(x, y + 0.65, t, 1.8, "middle", 0, c, True)


# =====================================================================================================
def sheet_assembly(allp):
    pg = Page()
    frame(pg, "M-R4-00", "总装与安装方向（零件表）", "SmartVio R4 结构总成 / mechanical assembly", "见零件表", "见各零件图",
          "1 套", "1.5:1（俯视）  2:1（A-A）", "1/1",
          ["6. 本图只定方向、基准和装配关系；零件尺寸见 M-R4-01…09。装配顺序与检查见 ASSEMBLY-SOP-R4.md。",
           "7. 琴体数据（原腔 78×47×22、腔位 145–223、中央梁宽、原穿线孔位置）均为继承名义值或待测，首样前必须实测。"])
    cover, cup = part("upper_cover"), part("lower_cup")
    s = 1.5
    v = View(pg, cover, "top", s, (34, 50), w=0.28)
    v.title("俯视（Z+，琴背外侧向下看）", "安装状态，上盖可见；虚线=下杯，点划线=原琴腔（名义）")
    # cup outline dashed, cavity phantom
    def rect_log(x0, y0, x1, y1, **kw):
        pts = [v.pt(x0, y0), v.pt(x1, y0), v.pt(x1, y1), v.pt(x0, y1)]
        pg.poly(pts, closed=True, **kw)
    rect_log(35.5, 2.0, 112.5, 47.0, w=0.25, c="#333333", dash="1.6 0.8")
    rect_log(35.0, 1.0, 113.0, 48.0, w=0.25, c="#1a4f8a", dash="5 1 1 1")
    ex = PAR["pickup_entry_extent_xy"]
    rect_log(ex[0], ex[1], ex[2], ex[3], w=0.35, c=CTF_COLOR, dash="1 0.6")
    pg.leader(v.pt((ex[0] + ex[2]) / 2, ex[1]), v.pt(72, -6)[0], v.pt(72, -6)[1],
              "拾音线入口 10×3 长槽：对齐琴上原穿线孔（不在琴上新钻孔）— TODO 实测原孔位置", ctf="L9")
    head_tail(pg, v.box[0], v.box[2], 30.5)
    # longitudinal stations
    yb = v.box[3] + 8
    pg.line(v.box[0], yb, v.box[2], yb, 0.2)
    for X, u in [(0, 258), (35, 223), (113, 145), (148, 110)]:
        px = v.pt(X, 0)[0]
        pg.line(px, yb - 1.5, px, yb + 1.5, 0.3)
        pg.text(px, yb + 4.4, f"u={u}", 2.2, "middle", 0, "#1a4f8a")
        pg.text(px, yb - 2.2, f"X={X}", 1.9, "middle", 0, "#555555")
    pg.text(v.box[0], yb + 8.6, "u = 距琴尾金属基准的距离（继承 V21 需求记录，待实测）；X = 258 − u。原腔 u 145–223；上盖覆盖 u 110–258。", 2.1)
    pg.dim_v(v.pt(148, 0), v.pt(148, 49), v.box[2] + 6, "49 0/−0.20", ctf="U1")
    cut_line(pg, v, 37, 0, 148, "A", up=True)
    pg.text(v.box[0], yb + 13, "A-A：Y=37（插座中心）剖切，视向箭头指向北边 Y0（滚轮拇指缺口一侧）。", 2.1)
    # Section A-A of the assembly
    names = ["upper_cover", "lower_cup", "audio_load_frame", "main_audio_dielectric_separator", "battery_top_separator", "battery_top_foam",
             "battery_bottom_insulator", "main_reference", "audio_native_reference", "battery_max_reference", "cover_native_reference"] + [f"Kycon_vendor_{i}" for i in range(1, 5)]
    pieces, faces = [], []
    cropbox = (34.0, -37.0 + 0.0, -22.0, 114.0, -33.5, 4.5)
    for i, n in enumerate(names):
        try:
            c, polys = section(cq, part(n), "Y", -37.0, +1, crop=cropbox)
        except Exception as e:
            print("section skip", n, e); continue
        if c.Volume() > 1e-6:
            pieces.append(c); faces.append((n, polys))
    sv = View(pg, cq.Compound.makeCompound(pieces), "front", 2.0, (40, 165), w=0.22)
    style = {"upper_cover": (45, "#e4e4e4"), "lower_cup": (45, "#e4e4e4"), "audio_load_frame": (135, "#e4e4e4"),
             "main_reference": (0, "#d9ecd9"), "audio_native_reference": (0, "#d9ecd9"), "cover_native_reference": (0, "#d9ecd9"),
             "battery_max_reference": (90, "#f3e6c8")}
    for n, polys in faces:
        ang, fill = style.get(n, (135, "#ffffff"))
        sv.hatch(polys, angle=ang, spacing=0.8 if ang != 0 else 0.6, fill=fill)
    sv.title("A-A（2:1，总装剖面，含参考板/电池/插座）", "绿=PCB，黄=电池最大包络，灰=结构件")
    z = lambda zz: sv.pt(40, 37, zz)
    xl = sv.box[0] - 4
    pg.dim_v(sv.pt(40, 37, 0), sv.pt(40, 37, 3.855), xl, "3.855（插口名义）")
    pg.dim_v(sv.pt(40, 37, 0), sv.pt(40, 37, -20.9), xl - 9, "20.90")
    xr = sv.box[2] + 6
    pg.dim_v(sv.pt(112, 37, 3.855), sv.pt(112, 37, -20.9), xr, "24.755 名义 / 25 MAX（见 tolerance-stack 链 1）", ctf="L2")
    pg.leader(sv.pt(46.5, 37, 1.455), sv.box[0] + 60, sv.box[1] - 5, "插座肩面顶住屋顶压台 Z1.455（插座 Z 基准）", ctf="U6")
    pg.leader(sv.pt(64, 37, -11.15), sv.box[0] + 70, sv.box[3] + 6, "音频框落在刀片唇 Z−11.15，选配腹板 0.40/0.50/0.60", ctf="F1")
    pg.text(sv.box[0], sv.box[3] + 13, "基准 A（Z0）= 上盖裙边底面 = 琴面；杯底离原腔底 1.10（名义，腔深待实测）", 2.1)
    # parts list
    rows = [["1", "upper_cover", "上盖", "M-R4-01", "POM-C 黑", "1"], ["2", "lower_cup", "下杯", "M-R4-02", "POM-C 黑", "1"],
            ["3", "key_backer_bracket", "按键背撑架", "M-R4-03", "POM-C 黑", "1"], ["4", "usb_bracket", "USB 托架", "M-R4-04", "POM-C 黑", "1"],
            ["5", "audio_load_frame(_web0p4/0p6)", "音频承载框", "M-R4-05", "POM-C 黑", "1(+2 选配)"],
            ["6", "button_1…5", "按键（毛坯修触头）", "M-R4-06", "POM-C 黑", "5"], ["7", "lightpipe_1…3", "导光柱", "M-R4-07", "PC 透明", "3"],
            ["8", "*_insulator / separator", "绝缘片 6 种", "M-R4-08", "PET / PI 0.1", "各 1"],
            ["9", "main_shim_0p05/0p1/0p2mm", "主板调整垫片", "M-R4-08", "PET", "各 1 套（选配）"],
            ["10", "battery_top_foam", "电池顶部泡棉", "M-R4-09", "PORON 1.0", "1"],
            ["11", "M1.6 塑料自攻钉", "背撑架 2 + USB 托架 3", "外购", "A2 不锈钢", "5"],
            ["12", "ST2.2×6.5 盘头木螺钉", "固定到琴体", "外购", "A2 不锈钢", "4"]]
    x0 = 268
    yy = pg.table(x0, 52, [("件", 6), ("STEP 名", 46), ("名称", 30), ("图号", 17), ("材料", 20), ("数量/套", 21)], rows, size=1.85, rowh=3.4)
    pg.text(x0, 48.5, "零件表（每套）", 2.6, bold=True)
    notes = ["首样订货：3 套 + 1 套备件（RFQ-mechanical.md）。",
             "螺钉：M1.6 PT 型塑料自攻 0.08 N·m；ST2.2 木螺钉 0.15 N·m。",
             "上下壳只靠 4 个零间隙卡扣，下杯不加螺钉。",
             "琴上 4 个螺钉导孔 Ø1.6×5 由工厂按实物配钻（预留孔，非既有孔）。",
             "拾音线：走琴上原有穿线孔，不在琴腔新钻孔。",
             "滚轮不计外突；非滚轮外突 ≤5（名义 3.855）。",
             "中央实心梁宽须 ≥49（u 110–258，待实测），上盖宽 49 0/−0.20。"]
    for i, t in enumerate(notes):
        pg.text(x0, yy + 6 + i * 4.2, f"• {t}", 2.05)
    save(pg, "M-R4-00_总装与安装方向", allp)


# =====================================================================================================
def cover_ctfs():
    P = "upper_cover"
    ctf("U1", P, "外形宽（中央梁 ≥49）", "49.00", "0/−0.20", "卡尺", "3")
    ctf("U2", P, "屋顶顶面 Z（至基准 A）", "3.80", "±0.05", "高度规/CMM", "1,2")
    ctf("U3", P, "按键沉槽顶面至承托面", "2.60", "±0.03", "CMM", "4", 5)
    ctf("U4", P, "承托面/销台/背撑凸台面 Z", "0.50", "±0.03，共面0.03", "CMM", "4", 9)
    ctf("U5", P, "按键孔 / 沉槽", "Ø5.20 / Ø6.50", "+0.05/0", "塞规", "4", 5)
    ctf("U6", P, "插座压台面 Z", "1.455", "±0.03", "CMM", "1,6", 4)
    ctf("U7", P, "压台面至刀片唇顶面", "12.605", "±0.05", "CMM", "6", 4)
    ctf("U8", P, "USB 开口 / 面槽", "9.39×3.61 / 13.0×7.4", "+0.05/0 ; +0.1/0", "塞规/影像", "7")
    ctf("U9", P, "USB 柱端面 Z", "−3.30", "±0.03", "CMM", "7", 4)
    ctf("U10", P, "卡扣窗下沿 Z / 窗高", "−2.32 / 0.84", "±0.03 / +0.03/0", "CMM", "1,5", 4)
    ctf("U11", P, "南北刀片外侧面间距", "43.00", "±0.05", "CMM", "5", 2)
    ctf("U12", P, "螺钉孔/沉孔/沉孔底 Z", "Ø2.5 / Ø4.5 / Z1.70", "+0.1/0 ; ±0.05", "塞规/深度尺", "2", 4)
    ctf("U13", P, "滚轮窗 / 拇指缺口底 Z", "Ø15.20 / Z1.50", "±0.05", "塞规/深度尺", "", 3)
    ctf("U14", P, "扬声器腔顶 Z", "3.30", "±0.05", "深度尺", "", 1)
    ctf("U15", P, "定位销 Ø×长 / 位置", "Ø1.40×0.45", "0/−0.03 ; 位置±0.03", "千分尺/CMM", "", 2)
    ctf("U16", P, "M1.6 自攻底孔", "Ø1.30", "+0.05/0", "塞规", "", 5)
    ctf("U17", P, "雕刻字符深度", "0.15", "±0.05", "深度尺/显微", "", 13)
    ctf("U18", P, "导光柱孔", "Ø1.50", "+0.05/0", "塞规", "", 3)
    ctf("U19", P, "插座孔 Ø / 位置", "Ø6.60", "±0.05", "塞规/CMM", "", 4)


def sheet_cover_outside(allp):
    pg = Page()
    frame(pg, "M-R4-01", "上盖  外观面（俯视/主视/左视、开孔表、雕刻字符）", "上盖 upper_cover", MAT_POM, FIN_POM, "1 / 套",
          "1.5:1", "1/3", ["6. 雕刻字符 13 处：DejaVu Sans Bold，字号 1.8（字高≈1.35），深 0.15±0.05，与外形同一次装夹雕刻，不填色、不印刷。",
                          "7. 外观面（屋顶顶面、裙边外侧）不得有夹痕、顶针/压板印；屋顶平面度 0.10。"])
    cover = part("upper_cover"); s = 1.5
    fv = View(pg, cover, "front", s, (30, 36), w=0.25)
    fv.title("主视（从南侧/插座侧看）")
    tv = View(pg, cover, "top", s, (30, 79), w=0.25)
    tv.title("俯视（外观面）")
    lv = View(pg, cover, "left", s, (268, 36), w=0.25)
    lv.title("左视（从琴头端看）")
    head_tail(pg, tv.box[0], tv.box[2], tv.box[3] + 12)
    # overall dims
    pg.dim_h(tv.pt(0, 49), tv.pt(148, 49), tv.box[3] + 5, "148 ±0.5")
    pg.dim_v(tv.pt(0, 0), tv.pt(0, 49), tv.box[0] - 6, "49 0/−0.20", ctf="U1")
    pg.dim_v(fv.pt(148, 49, 0), fv.pt(148, 49, 3.8), fv.box[2] + 5, "3.80±0.05", ctf="U2")
    pg.dim_v(fv.pt(0, 49, 0), fv.pt(0, 49, -11.65), fv.box[0] - 5, "11.65")
    pg.text(fv.pt(0, 49, 0)[0] - 13, fv.pt(0, 49, 0)[1] + 0.8, "A", 3.0, "middle", 0, INK, True)
    pg.line(fv.pt(0, 0, 0)[0] - 10, fv.pt(0, 0, 0)[1], fv.pt(0, 0, 0)[0] - 1, fv.pt(0, 0, 0)[1], 0.3)
    pg.leader(tv.pt(2, 47), tv.box[0] + 2, tv.box[3] + 18.5, "外角 R2（4×）", size=2.0)
    # tags on the top view
    for i, (x, y) in enumerate(SCREWS):
        idmark(pg, tv.pt(x, y), f"S{i+1}", 0, -4.2 if y < 20 else 4.2)
    for i, x in enumerate([15, 35, 55]):
        idmark(pg, tv.pt(x + 5.5, 4.2), f"W{i+1}")
    for i, x in enumerate(KEYS):
        idmark(pg, tv.pt(x, 25), f"K{i+1}", 5.5, -3.2)
    for i, (x, y) in enumerate(LP):
        idmark(pg, tv.pt(x, y), f"P{i+1}", 3.8, 0)
    for i, (x, y) in enumerate(PORTS):
        idmark(pg, tv.pt(x, y), f"J{i+1}", 8.5, -5.5)
    idmark(pg, tv.pt(98, 9), "U1", 0, 7.5)
    idmark(pg, tv.pt(132, 25), "G1", 0, 0)
    cut_line(pg, tv, 37, 38, 110, "A")
    cut_line(pg, tv, 25, 0, 68, "B")
    cut_line_v(pg, tv, 15, 0, 18, "F", right=True)
    # chart
    ex = []
    for i, (x, y) in enumerate(SCREWS):
        ex.append([f"S{i+1}", "木螺钉孔+沉孔", f"{x:.2f}, {y:.2f}", "Ø2.50 通 / 沉孔Ø4.50", "沉孔底 Z1.70", "U12"])
    for i, x in enumerate([15, 35, 55]):
        ex.append([f"W{i+1}", "滚轮窗+拇指缺口", f"{x:.2f}, 10.00", "Ø15.20 / 缺口宽12", "缺口底 Z1.50", "U13"])
    for i, x in enumerate(KEYS):
        ex.append([f"K{i+1}", "按键孔（内侧沉槽）", f"{x:.2f}, 25.00", "Ø5.20 / 沉槽Ø6.50", "槽顶 Z3.10", "U3"])
    for i, (x, y) in enumerate(LP):
        ex.append([f"P{i+1}", "导光柱孔", f"{x:.2f}, {y:.2f}", "Ø1.50 通", "—", "U18"])
    for i, (x, y) in enumerate(PORTS):
        ex.append([f"J{i+1}", f"插座孔 {JACK_NAMES[i]}", f"{x:.2f}, {y:.2f}", "Ø6.60 / 面窝Ø12", "窝深0.80；压台Z1.455", "U6"])
    ufp = PAR["usb_face_pocket"]
    ex.append(["U1", "USB-C 开口+面槽", "98.00, 9.00", f"9.39×3.61 R1.6 / {ufp[0]}×{ufp[1]} R1.5", "面槽深 0.80", "U8"])
    ex.append(["G1", "扬声器出声槽 8×", "X126.4–137.6", "11.2×0.8 R0.35 节距2", "腔顶 Z3.30", "U14"])
    yy = hole_chart(pg, 268, 80, ex, "外观面开孔表（坐标=基准 B/C，即 X0 琴头端 / Y0 北边）", widths=(8, 29, 26, 41, 31))
    # legends table
    lr = [[t, f"{x:.1f}, {y:.1f}"] for t, x, y in LEG]
    pg.text(30, 191, "雕刻字符（中心坐标，居中对齐）", 2.4, bold=True)
    half = (len(lr) + 1) // 2
    pg.table(30, 193, [("字符", 22), ("X, Y", 22)], lr[:half], size=1.85, rowh=3.2)
    pg.table(78, 193, [("字符", 22), ("X, Y", 22)], lr[half:], size=1.85, rowh=3.2)
    pg.leader(tv.pt(35, 18.9), 140, 196, "雕刻 0.15 深（13 处），字框外 0.3 内须为实体", ctf="U17")
    pg.text(130, 204, "剖面 A-A、B-B、F 见第 3 页；内侧结构见第 2 页。", 2.1)
    ctf_table(pg, 268, yy + 7, ["U1", "U2", "U5", "U8", "U12", "U13", "U17", "U18", "U19"], widths=(8, 42, 31, 27, 27))
    save(pg, "M-R4-01-1_上盖_外观面", allp)


def sheet_cover_inside(allp):
    pg = Page()
    frame(pg, "M-R4-01", "上盖  内侧（仰视、内部特征表）", "上盖 upper_cover", MAT_POM, FIN_POM, "1 / 套", "1.5:1", "2/3",
          ["6. 8 个承托面（Z0.50）、2 个定位销台、2 个背撑凸台须同一装夹精铣，共面 0.03：控制板顶面靠在这些面上（按键链）。",
           "7. 4 个刀片卡扣窗口、刀片唇（南侧）和插座压台的 Z 尺寸同一装夹加工；卡扣窗棱边保持锐边（≤0.05 倒钝）。"])
    cover = part("upper_cover"); s = 1.5
    bv = View(pg, cover, "bottom", s, (30, 40), w=0.22)
    bv.title("仰视（从内侧看，绕 X 轴翻转：北边 Y0 在下）")
    head_tail(pg, bv.box[0], bv.box[2], bv.box[3] + 10)
    rows = []
    for i, (x, y) in enumerate([(3.5, 24.5), (144.5, 24.5)]):
        idmark(pg, bv.pt(x, y), f"PN{i+1}", 0, -4.5)
        rows.append([f"PN{i+1}", "定位销（圆孔/长孔侧）", f"{x:.2f}, {y:.2f}", "销Ø1.40×0.45 / 台Ø3.0", "台面 Z0.50", "U15"])
    for i, (x, y, r) in enumerate([(25, 10, 1.2), (45, 10, 1.2), (70, 20, 1.5), (108, 28, 1.5), (140, 10, 1.5)]):
        idmark(pg, bv.pt(x, y), f"T{i+1}", 0, 3.6)
        rows.append([f"T{i+1}", "控制板承托柱", f"{x:.2f}, {y:.2f}", f"Ø{2*r:.1f}", "端面 Z0.50", "U4"])
    for i, x in enumerate([42.5, 55.5]):
        idmark(pg, bv.pt(x, 25), f"KB{i+1}", 0, -4.2)
        rows.append([f"KB{i+1}", "背撑架螺钉凸台", f"{x:.2f}, 25.00", "Ø4.0 / 底孔Ø1.30", "面Z0.50 深2.80", "U4"])
    for i, (x, y) in enumerate(USBPOST):
        idmark(pg, bv.pt(x, y), f"UP{i+1}", 0, 4.4 if y > 15 else -4.4)
        rows.append([f"UP{i+1}", "USB 板压柱" + ("（只压不锁）" if (x, y) not in [tuple(p) for p in USBSCREW] else ""), f"{x:.2f}, {y:.2f}",
                     "Ø4.0（上段Ø5.0）" + (" 底孔Ø1.30" if (x, y) in [tuple(p) for p in USBSCREW] else ""), "端面 Z−3.30", "U9"])
    for j, x in enumerate(SNAPX):
        for k, yy in enumerate([3.0, 45.3]):
            idmark(pg, bv.pt(x, yy + 0.35), f"BL{2*j+k+1}", 0, 4.5 if k == 0 else -4.5)
            rows.append([f"BL{2*j+k+1}", "卡扣刀片" + ("（北）" if k == 0 else "（南，带唇）"), f"{x-4:.1f}–{x+4:.1f}, {yy:.1f}–{yy+0.7:.1f}",
                         f"厚0.70 窗{x+2:.1f}–{x+4.2:.1f}", "窗 Z−2.32/−1.48" + ("" if k == 0 else " 唇顶−11.15"), "U10"])
    for i, (x, y) in enumerate(PORTS):
        idmark(pg, bv.pt(x, y), f"J{i+1}", 0, 7.2)
    rows.append(["J1–4", "插座压台（Kycon 肩形让位）", "同外观面 J", "10.8×11.7 / 孔Ø6.60", "压台面 Z1.455", "U6"])
    rows.append(["SP", "扬声器腔", "125.23–138.78, 15.73–34.28", "13.55×18.55 R1.2", "腔顶 Z3.30", "U14"])
    rows.append(["CR", "同轴线卡筋 4×", "104–106,3.45/5.0; 111.45/113,31", "2×0.55 / 0.55×2", "Z1.0–2.5", ""])
    yy = hole_chart(pg, 268, 44, rows, "内侧特征表", widths=(9, 33, 37, 33, 28))
    # Z level summary on the left bottom
    zl = [["Z3.80", "屋顶顶面（外观面）", "U2"], ["Z3.30", "扬声器腔顶", "U14"], ["Z3.10", "按键沉槽顶（法兰止挡）", "U3"],
          ["Z2.50", "屋顶内表面", ""], ["Z1.70", "螺钉沉孔底", "U12"], ["Z1.50", "滚轮拇指缺口底", "U13"], ["Z1.455", "插座压台面", "U6"],
          ["Z0.50", "承托面/销台/背撑凸台", "U4"], ["Z0", "裙边底面 = 基准 A", ""], ["Z−2.32/−1.48", "卡扣窗下沿/上沿", "U10"],
          ["Z−3.30", "USB 压柱端面", "U9"], ["Z−5.20", "刀片底（北）", ""], ["Z−11.15", "南刀片唇顶（音频框落座）", "U7"], ["Z−11.65", "南刀片底", ""]]
    pg.text(30, 142, "Z 向层位（至基准 A）", 2.4, bold=True)
    pg.table(30, 144, [("Z", 22), ("面", 50), ("CTF", 12)], zl, size=1.85, rowh=3.2, ctf_col=2)
    ctf_table(pg, 130, 144, ["U3", "U4", "U6", "U7", "U9", "U10", "U11", "U14", "U15", "U16"], widths=(8, 40, 30, 27, 22))
    save(pg, "M-R4-01-2_上盖_内侧", allp)


def sheet_cover_sections(allp):
    pg = Page()
    frame(pg, "M-R4-01", "上盖  剖面与局部（A-A 插座、B-B 按键、C 卡扣、D USB、E 螺钉沉孔、F 滚轮缺口）", "上盖 upper_cover",
          MAT_POM, FIN_POM, "1 / 套", "见各视图", "3/3",
          ["6. 插座压台按 Kycon 原厂 STEP 肩面做零间隙：压台面 Z1.455 是插座 Z 基准；压台侧面让位按 STEP，不得改为平面。",
           "7. 卡扣窗 0.84 高 = 钩高 0.80 + 0.04；刀片底外侧导入 0.55×45°。"])
    cover = part("upper_cover")
    # A-A through the jacks (crop)
    c, polys = section(cq, cover, "Y", -37.0, +1, crop=(38, -37, -0.3, 110, -30, 4.5))
    av = View(pg, c, "front", 3.0, (34, 46), w=0.22)
    av.hatch(polys)
    av.title("A-A（3:1）Y=37，插座中心，向北看（局部：屋顶与压台）", off=15)
    xl = av.box[0] - 4
    for zz, t, tg in [(3.8, "3.80", None), (1.455, "1.455±0.03", "U6")]:
        pass
    pg.dim_v(av.pt(38, 37, 0), av.pt(38, 37, 3.8), xl, "3.80")
    pg.dim_v(av.pt(38, 37, 0), av.pt(38, 37, 1.455), xl - 8, "1.455±0.03", ctf="U6")
    x63 = 63.5
    pg.dim_h(av.pt(46.5 - 3.3, 37, 0.8), av.pt(46.5 + 3.3, 37, 0.8), av.box[1] - 3, "Ø6.60", ctf="U19")
    pg.dim_h(av.pt(64.8 - 6, 37, 3.0), av.pt(64.8 + 6, 37, 3.0), av.box[1] - 3, "Ø12 深0.80")
    pg.dim_h(av.pt(46.5, 37, 3.8), av.pt(64.8, 37, 3.8), av.box[1] - 10, "18.30（插座节距，3×）")
    # B-B keys 1..3
    c, polys = section(cq, cover, "Y", -25.0, +1, crop=(3, -25, -0.5, 41, -18, 4.5))
    bv = View(pg, c, "front", 4.0, (30, 98), w=0.22)
    bv.hatch(polys)
    bv.title("B-B（4:1）Y=25，按键 K1–K3 中心，向北看")
    pg.dim_h(bv.pt(10 - 2.6, 25, 3.8), bv.pt(10 + 2.6, 25, 3.8), bv.box[1] - 3, "Ø5.20 +0.05/0", ctf="U5")
    pg.dim_h(bv.pt(23 - 3.25, 25, 2.3), bv.pt(23 + 3.25, 25, 2.3), bv.box[3] + 5, "Ø6.50 +0.05/0", ctf="U5")
    pg.dim_v(bv.pt(36, 25, 0.5), bv.pt(36, 25, 3.1), bv.box[2] + 5, "2.60±0.03（槽顶→承托面Z0.50）", ctf="U3")
    pg.dim_v(bv.pt(3, 25, 3.1), bv.pt(3, 25, 3.8), bv.box[0] - 4, "0.70")
    # F wheel notch (plane X=15, from +X)
    c, polys = section(cq, cover, "X", 15.0, -1, crop=(8, -20, -0.2, 15, 0.2, 4.5))
    fv = View(pg, c, "right", 4.0, (215, 98), w=0.22)
    fv.hatch(polys)
    fv.title("F（4:1）X=15 滚轮 W1 中心，从琴尾向琴头看")
    pg.dim_v(fv.pt(15, 1, 0), fv.pt(15, 1, 1.5), fv.box[2] + 5, "1.50±0.05 缺口底", ctf="U13")
    pg.dim_h(fv.pt(15, 10 - 7.6, 3.8), fv.pt(15, 10 + 7.6, 3.8), fv.box[1] - 3, "Ø15.20±0.05", ctf="U13")
    # C snap blades (plane X = station+3.1 through the window), north and south
    st = SNAPX[0]
    c, polys = section(cq, cover, "X", st + 3.1, -1, crop=(st - 1, -5.5, -6, st + 3.1, 0.2, 2.6))
    cv = View(pg, c, "right", 6.0, (30, 150), w=0.22)
    cv.hatch(polys)
    cv.title(f"C1（6:1）北刀片 X={st+3.1}", "（窗口中心）")
    pg.dim_v(cv.pt(st, 3.0, 0), cv.pt(st, 3.0, -2.32), cv.box[0] - 4, "2.32±0.03", ctf="U10")
    pg.dim_v(cv.pt(st, 3.7, -2.32), cv.pt(st, 3.7, -1.48), cv.box[2] + 5, "0.84 +0.03/0", ctf="U10")
    pg.leader(cv.pt(st, 3.2, -5.0), cv.box[2] + 3, cv.box[3] + 4, "导入 0.55×45°", size=2.0)
    c, polys = section(cq, cover, "X", 68.5, -1, crop=(st - 1, -46.3, -12, 68.5, -30.5, 2.6))
    cv2 = View(pg, c, "right", 3.0, (98, 150), w=0.22)
    cv2.hatch(polys)
    cv2.title("C2（3:1）X=68.5 南刀片唇 + 插座压台 J2")
    pg.dim_v(cv2.pt(st, 44.85, 1.455), cv2.pt(st, 44.85, -11.15), cv2.box[0] - 4, "12.605±0.05（压台面→唇顶）", ctf="U7")
    pg.leader(cv2.pt(st, 45.0, -11.15), cv2.box[2] + 2, cv2.box[3] + 4, "唇宽 0.45，承音频框南边", size=2.0)
    # D USB opening, plane Y=9 (front view), crop
    c, polys = section(cq, cover, "Y", -9.0, +1, crop=(84, -9, -3.6, 112, -3, 4.2))
    dv = View(pg, c, "front", 4.0, (160, 150), w=0.22)
    dv.hatch(polys)
    dv.title("D（4:1）Y=9 USB-C 开口中心，向北看")
    pg.dim_h(dv.pt(98 - 4.695, 9, 2.6), dv.pt(98 + 4.695, 9, 2.6), dv.box[3] + 5, "9.39 +0.05/0", ctf="U8")
    ufp = PAR["usb_face_pocket"]
    pg.dim_h(dv.pt(98 - ufp[0] / 2, 9, 3.8), dv.pt(98 + ufp[0] / 2, 9, 3.8), dv.box[1] - 3, f"{ufp[0]:.1f} +0.1/0（面槽，深0.80）", ctf="U8")
    pg.dim_v(dv.pt(88, 9, -3.3), dv.pt(88, 9, 0), dv.box[0] - 4, "3.30±0.03 压柱端面", ctf="U9")
    # E screw counterbore at (5.3,5.3)
    c, polys = section(cq, cover, "Y", -5.3, +1, crop=(-0.2, -5.3, -0.2, 11.5, 0.2, 4.2))
    ev = View(pg, c, "front", 6.0, (300, 150), w=0.22)
    ev.hatch(polys)
    ev.title("E（6:1）Y=5.3 螺钉孔 S1")
    pg.dim_h(ev.pt(5.3 - 2.25, 5.3, 3.8), ev.pt(5.3 + 2.25, 5.3, 3.8), ev.box[1] - 3, "Ø4.50 +0.1/0", ctf="U12")
    pg.dim_h(ev.pt(5.3 - 1.25, 5.3, 0), ev.pt(5.3 + 1.25, 5.3, 0), ev.box[3] + 5, "Ø2.50 +0.1/0")
    pg.dim_v(ev.pt(11, 5.3, 0), ev.pt(11, 5.3, 1.7), ev.box[2] + 4, "1.70±0.05", ctf="U12")
    pg.text(300, ev.box[3] + 13, "ST2.2 盘头头高 ≤1.6 → 头顶 ≤Z3.35", 2.0)
    save(pg, "M-R4-01-3_上盖_剖面与局部", allp)


# =====================================================================================================
def cup_ctfs():
    P = "lower_cup"
    ctf("L1", P, "外形长×宽（原腔 78×47）", "77.00×45.00", "±0.05", "卡尺/CMM", "3")
    ctf("L2", P, "卡钩下面至杯外底", "18.60", "±0.05", "高度规/CMM", "1", 4)
    ctf("L3", P, "卡钩高 / 凸出内壁", "0.80 / 0.55", "0/−0.03 ; ±0.03", "CMM/影像", "5", 4)
    ctf("L4", P, "卡扣处内宽（Y）", "43.40", "±0.05", "CMM", "5", 2)
    ctf("L5", P, "Y 定位筋高（4×，R4.1 新增）", "0.15", "±0.02", "CMM/影像", "5", 4)
    ctf("L6", P, "主板托台面至杯外底", "8.35", "±0.03", "CMM", "8", 6)
    ctf("L7", P, "侧向定位台内面间距", "74.70×42.70", "±0.03", "CMM", "8")
    ctf("L8", P, "底厚 / 壁厚", "0.60 / 0.80", "±0.05", "千分尺/超声", "", 1)
    ctf("L9", P, "拾音入口槽 10×3 中心（TODO 实测后定位）", "局部 25.10, 2.60", "±0.10；槽宽 +0.1/0", "CMM", "", 1)
    ctf("L10", P, "主板卡齿下面至托台面 / 搭接", "0.80 / 0.45", "±0.03 ; ±0.05", "CMM", "8", 4)
    ctf("L11", P, "电池仓（导向内面）", "52.25×35.00", "+0.10/0", "卡尺", "", 1)
    ctf("L12", P, "外竖角半径（原腔角 R≤3.0 才不干涉）", "R1.2", "±0.2", "R 规", "3", 4)


def sheet_cup(allp):
    pg = Page()
    frame(pg, "M-R4-02", "下杯（俯视/主视、特征表）", "下杯 lower_cup", MAT_POM, "机加本色黑；内腔不要求外观", "1 / 套", "2:1", "1/2",
          ["6. 局部坐标原点 = 外形西北角 (全局 X35.5, Y2.0)，Z 自杯外底向上（全局 Z = 局部 Z − 20.90）。",
           "7. 拾音入口：DECISIONS 补充 2026-10-15，拾音线走琴上原穿线孔，琴上不钻孔。首样按 10×3 长槽加工（沿 X 容差 ±3.5）；实测原孔后改为 Ø3.0 圆孔或移槽。",
           "8. 卡钩为矩形双向止挡（不倒角）；4 处 Y 定位筋 0.15（R4.1）在悬臂根部，离刀片面 0.05。"])
    cup = part("lower_cup"); s = 2.0
    ox, oy = 35.5, 2.0
    tv = View(pg, cup, "top", s, (30, 40), w=0.22)
    tv.title("俯视（开口朝上）")
    fv = View(pg, cup, "front", s, (30, 147), w=0.22)
    fv.title("主视（从南侧看）")
    head_tail(pg, tv.box[0], tv.box[2], 26.5)
    pg.dim_h(tv.pt(35.5, 2), tv.pt(112.5, 2), tv.box[1] - 3, "77.00±0.05", ctf="L1")
    pg.dim_v(tv.pt(112.5, 2), tv.pt(112.5, 47), tv.box[2] + 6, "45.00±0.05", ctf="L1")
    pg.dim_v(fv.pt(112.5, 47, 0), fv.pt(112.5, 47, -20.9), fv.box[2] + 6, "20.90±0.05")
    pg.dim_v(fv.pt(35.5, 47, -2.3), fv.pt(35.5, 47, -20.9), fv.box[0] - 5, "18.60±0.05（钩下面→外底）", ctf="L2")
    ex = PAR["pickup_entry_extent_xy"]
    pg.leader(tv.pt(ex[0], (ex[1] + ex[3]) / 2), tv.box[0] + 60, tv.box[3] + 8,
              f"拾音入口槽 {PAR['pickup_entry_slot'][0]:.0f}×{PAR['pickup_entry_slot'][1]:.0f} 通，中心局部 ({PAR['pickup_entry_xy'][0]-ox:.2f}, {PAR['pickup_entry_xy'][1]-oy:.2f})，TODO 对齐原穿线孔", ctf="L9")
    rows = []
    for j, x in enumerate(SNAPX):
        for k, side in enumerate(["北", "南"]):
            yy = 2.0 if k == 0 else 46.2
            p = tv.pt(x + 2.8, 3.35 if k == 0 else 45.65)
            idmark(pg, p, f"H{2*j+k+1}", 0, -3.6 if k == 0 else 3.6)
            rows.append([f"H{2*j+k+1}", f"上下壳卡扣（{side}）", f"钩 {x+2.2-ox:.2f}–{x+3.4-ox:.2f}", "钩1.2×0.80 凸0.55；筋0.15", "钩下面 局部Z18.60", "L2"])
    for j, x in enumerate([38.0, 95.0]):
        for k, side in enumerate(["北", "南"]):
            idmark(pg, tv.pt(x + 10.75, 3.4 if k == 0 else 45.6), f"T{2*j+k+1}", 0, -3.6 if k == 0 else 3.6)
            rows.append([f"T{2*j+k+1}", f"主板卡齿（{side}）", f"齿 {x+10-ox:.2f}–{x+11.5-ox:.2f}", "齿宽1.5 搭接0.45", "齿下面 局部Z9.15", "L10"])
    for i, (x, w, y, h) in enumerate(LEDGES):
        rows.append([f"LG{i+1}", "主板托台", f"{x-ox:.2f}–{x+w-ox:.2f}, {y-oy:.2f}–{min(y+h,46.2)-oy:.2f}", f"{w:.1f}×{min(h,46.2-y):.1f}", "台面 局部Z8.35", "L6"])
    rows.append(["LP", "侧向定位台 8×", "内面 X1.15/75.85, Y1.15/43.85", "离主板边 0.05", "局部Z8.35–9.15", "L7"])
    rows.append(["BG", "电池导向 4 边", "内面 X4.25/56.50, Y5.00/40.00", "高 3.2；东侧贴 NTC", "局部Z0.60–3.80", "L11"])
    rows.append(["NT", "NTC 侧仓（RT1921）", "X56.5–61.3, Y9.3–14.0", "仓 4.3×3.7", "底 局部Z0.90", ""])
    for i, (x, w, y, h) in enumerate(LEDGES[:1]):
        idmark(pg, tv.pt(x + w / 2, y + h / 2), "LG1", 0, 3.5)
    idmark(pg, tv.pt(66, 24.5), "BG", 0, 0)
    yy = hole_chart(pg, 236, 44, rows, "下杯特征表（局部坐标）", widths=(8, 30, 42, 41, 31))
    ctf_table(pg, 236, yy + 8, ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L10", "L11", "L12"], widths=(8, 52, 32, 30, 30))
    save(pg, "M-R4-02-1_下杯", allp)

    pg = Page()
    frame(pg, "M-R4-02", "下杯  剖面（卡扣、定位筋、主板托台与卡齿、拾音入口）", "下杯 lower_cup", MAT_POM, "机加本色黑", "1 / 套", "见各视图", "2/2",
          ["6. 卡扣/卡齿悬臂由 0.5 宽 U 形槽形成，槽须贯穿杯壁，根部 R≥0.2；悬臂表面不得有刀痕缺口（疲劳）。",
           "7. 定位筋与卡钩不在同一 X 段：筋 X(站位−3.8…−2.8)，钩 X(站位+2.2…+3.4)。"])
    st = SNAPX[0]
    # snap hook section at X=st+2.8 (through hook), north and south
    for i, (yy0, yy1, lab) in enumerate([(-6.5, 0.2, "北"), (-49.2, -42.5, "南")]):
        c, polys = section(cq, cup, "X", st + 2.8, -1, crop=(st - 1, yy0, -7, st + 2.8, yy1, 0.2))
        v = View(pg, c, "right", 7.0, (30 + i * 75, 40), w=0.22)
        v.hatch(polys)
        v.title(f"G{i+1}（7:1）X={st+2.8} 卡钩剖面（{lab}）")
        if i == 0:
            pg.dim_v(v.pt(st, 3.35, -2.3), v.pt(st, 3.35, -1.5), v.box[2] + 4, "0.80 0/−0.03", ctf="L3")
            pg.dim_h(v.pt(st, 2.8, -1.5), v.pt(st, 3.35, -1.5), v.box[1] - 3, "0.55±0.03", ctf="L3")
            pg.dim_h(v.pt(st, 2.0, -6.5), v.pt(st, 2.8, -6.5), v.box[3] + 5, "0.80 壁厚")
    # rib section X=st-3.3
    c, polys = section(cq, cup, "X", st - 3.3, -1, crop=(st - 5, -6.5, -7, st - 3.3, 0.2, 0.2))
    rv = View(pg, c, "right", 7.0, (190, 40), w=0.22)
    rv.hatch(polys)
    rv.title(f"G3（7:1）X={st-3.3} 定位筋剖面")
    pg.dim_h(rv.pt(st, 2.8, -1.2), rv.pt(st, 2.95, -1.2), rv.box[1] - 3, "0.15±0.02", ctf="L5")
    pg.dim_v(rv.pt(st, 2.95, -4.6), rv.pt(st, 2.95, -1.2), rv.box[2] + 4, "3.40（顶部导入 0.3）")
    # main ledge + latch tooth section at X=48.75
    c, polys = section(cq, cup, "X", 48.75, -1, crop=(44, -8, -21.0, 48.75, 0.2, -9.5))
    lv = View(pg, c, "right", 6.0, (270, 40), w=0.22)
    lv.hatch(polys)
    lv.title("G4（6:1）X=48.75 主板卡齿/托台（北）")
    pg.dim_v(lv.pt(48, 3.65, -12.55), lv.pt(48, 3.65, -11.75), lv.box[2] + 4, "0.80±0.03", ctf="L10")
    pg.dim_v(lv.pt(48, 2.0, -20.9), lv.pt(48, 2.0, -12.55), lv.box[0] - 4, "8.35±0.03", ctf="L6")
    # longitudinal section at Y=4.6 through the pickup slot
    c, polys = section(cq, cup, "Y", -4.6, +1, crop=(35, -4.6, -21, 113, 0.5, 0.2))
    pv = View(pg, c, "front", 2.0, (30, 150), w=0.22)
    pv.hatch(polys)
    pv.title("H（2:1）Y=4.6 纵剖（拾音入口槽、北侧卡扣、托台）")
    ex = PAR["pickup_entry_extent_xy"]
    pg.dim_h(pv.pt(ex[0], 4.6, -20.9), pv.pt(ex[2], 4.6, -20.9), pv.box[3] + 6, f"{ex[2]-ex[0]:.1f}（槽长，沿X ±3.5 容差）", ctf="L9")
    pg.dim_h(pv.pt(35.5, 4.6, -20.9), pv.pt(PAR["pickup_entry_xy"][0], 4.6, -20.9), pv.box[3] + 13, f"{PAR['pickup_entry_xy'][0]-35.5:.2f}（TODO 按实测原孔）", ctf="L9")
    pg.dim_v(pv.pt(112.5, 4.6, -20.9), pv.pt(112.5, 4.6, -20.3), pv.box[2] + 4, "0.60±0.05 底厚", ctf="L8")
    pg.text(30, 215, "原穿线孔实测换算：X = 258 − u（u = 原孔距琴尾金属基准），Y = 24.5 + v（v = 距模块中线，向北为负）。入口须落在北侧走线带 Y 3.1–6.3（局部 1.1–4.3），", 2.1)
    pg.text(30, 219, "否则线缆无法绕过电池到达 J101（主板北缘缺口 X58.8–62.4），需改结构。build_mechanics.py 中有断言检查。", 2.1)
    save(pg, "M-R4-02-2_下杯_剖面", allp)


# =====================================================================================================
def small_part_sheet(allp, no, title, name, material, finish, qty, scale, views, dims, ctfs, extra=(), tables=None, sheet="1/1"):
    pg = Page()
    frame(pg, no, title, name, material, finish, qty, scale, sheet, extra)
    vs = {}
    for key, shape, kind, sc, at, hid in views:
        vs[key] = View(pg, shape, kind, sc, at, hidden=hid, w=0.25)
    for fn in dims:
        fn(pg, vs)
    if tables:
        for fn in tables:
            fn(pg, vs)
    ctf_table(pg, 236, 165, ctfs, widths=(8, 52, 32, 30, 30))
    save(pg, f"{no}_{title.split('（')[0].strip()}", allp)
    return vs


def sheet_key_backer(allp):
    P = "key_backer_bracket"
    ctf("B1", P, "上表面平面度（托控制板）", "—", "0.03", "平台+塞尺", "4")
    ctf("B2", P, "螺钉孔 Ø / 孔距", "Ø1.80 / 13.00", "+0.10/0 ; ±0.05", "塞规/CMM", "", 2)
    ctf("B3", P, "托边上面至板顶面", "1.70", "±0.05", "高度规", "6")
    ctf("B4", P, "板厚", "1.20", "±0.05", "千分尺", "4")
    sh = part(P); ox, oy, ztop = 36.6, 21.3, 0.1
    def d(pg, v):
        t, f, l = v["t"], v["f"], v["l"]
        t.title("俯视（装配方向：顶面贴控制板底面）"); f.title("主视（从南侧看）"); l.title("左视")
        head_tail(pg, t.box[0], t.box[2], t.box[1] - 16)
        pg.dim_h(t.pt(36.6, 21.3), t.pt(66.6, 21.3), t.box[1] - 3, "30.00")
        pg.dim_v(t.pt(66.6, 21.3), t.pt(66.6, 28.7), t.box[2] + 6, "7.40")
        pg.dim_h(t.pt(42.5, 25), t.pt(55.5, 25), t.box[3] + 8, "13.00±0.05", ctf="B2")
        pg.dim_h(t.pt(36.6, 25), t.pt(42.5, 25), t.box[3] + 15, "5.90")
        pg.leader(t.pt(55.5 + 0.64, 25 - 0.64), t.box[2] + 4, t.box[1] + 2, "2× Ø1.80 +0.10/0 通", ctf="B2")
        pg.dim_v(f.pt(66.6, 0, 0.1), f.pt(66.6, 0, -1.1), f.box[2] + 6, "1.20±0.05", ctf="B4")
        pg.dim_v(f.pt(36.6, 0, 0.1), f.pt(36.6, 0, -1.6), f.box[0] - 5, "1.70±0.05（托边上面）", ctf="B3")
        pg.dim_h(f.pt(40, 0, -2.0), f.pt(62, 0, -2.0), f.box[3] + 6, "22.00（托边，X 局部 3.40 起）")
        pg.dim_v(l.pt(0, 28.0, -2.0), l.pt(0, 29.1, -2.0), l.box[2] + 5, "")
        pg.leader(l.pt(0, 29.1, -1.6), l.box[2] + 4, l.box[3] + 8, "托边 0.40×0.40（音频框北挂钩落在其上面）", size=2.0)
        pg.text(30, 160, "功能：键 3–5 按压力 → 控制板 → 本件 → 2 颗 M1.6 自攻钉 → 屋顶凸台 KB1/KB2（M4）。顶面整面贴控制板，平面度 0.03（B1）。", 2.1)
        pg.text(30, 164.5, "局部坐标原点 = 西北角顶面（全局 X36.6, Y21.3, Z0.10）。螺钉：M1.6×4 PT 型塑料自攻钉，A2，扭矩 0.08 N·m。", 2.1)
    small_part_sheet(allp, "M-R4-03", "按键背撑架（键 3–5）", "按键背撑架 key_backer_bracket", MAT_POM, "机加本色黑", "1 / 套", "5:1",
                     [("t", sh, "top", 5.0, (40, 45), True), ("f", sh, "front", 5.0, (40, 110), True), ("l", sh, "left", 5.0, (215, 110), True)],
                     [d], ["B1", "B2", "B3", "B4"])


def sheet_usb_bracket(allp):
    P = "usb_bracket"
    ctf("S1", P, "板厚（西轨下 USB16 FPC 净空）", "0.60", "±0.03", "千分尺", "7")
    ctf("S2", P, "螺钉孔 Ø / 位置", "Ø1.80", "+0.10/0 ; ±0.05", "塞规/CMM", "7", 3)
    ctf("S3", P, "窗口（ZIF 包络净空 0.2）", "19.60×20.20", "+0.10/0", "影像", "", 1)
    ctf("S4", P, "平面度", "—", "0.05", "平台+塞尺", "7")
    sh = part(P)
    def d(pg, v):
        t, f = v["t"], v["f"]
        t.title("俯视（装配方向：从 USB 板 B 面一侧装入）"); f.title("主视（从南侧看）")
        head_tail(pg, t.box[0], t.box[2], t.box[1] - 16)
        pg.dim_h(t.pt(85.4, 4.4), t.pt(110.6, 4.4), t.box[1] - 3, "25.20")
        pg.dim_v(t.pt(110.6, 4.4), t.pt(110.6, 27.6), t.box[2] + 6, "23.20")
        pg.dim_h(t.pt(86.6, 26.2), t.pt(106.2, 26.2), t.box[3] + 6, "19.60 +0.10/0（窗）", ctf="S3")
        pg.dim_v(t.pt(86.6, 6.0), t.pt(86.6, 26.2), t.box[0] - 5, "20.20 +0.10/0", ctf="S3")
        pg.dim_h(t.pt(88, 8), t.pt(108.3, 8), t.box[3] + 14, "20.30±0.05", ctf="S2")
        pg.dim_v(t.pt(108.3, 8), t.pt(108.3, 22), t.box[2] + 14, "14.00±0.05", ctf="S2")
        pg.leader(t.pt(108.3 + 0.64, 22 + 0.64), t.box[2] + 4, t.box[3] + 10, "3× Ø1.80 +0.10/0 通", ctf="S2")
        pg.dim_v(f.pt(110.6, 0, -4.3), f.pt(110.6, 0, -4.9), f.box[2] + 6, "0.60±0.03", ctf="S1")
        pg.text(30, 150, "局部坐标原点 = 西北角（全局 X85.4, Y4.4）；孔中心局部 (2.60, 3.60) (22.90, 3.60) (22.90, 17.60)。外角 R1.0。", 2.1)
        pg.text(30, 154.5, "西轨（宽 1.2）下方走 USB16 FPC：本件底面 Z−4.9，FPC ≤Z−5.3；南轨上面承音频框 USB 挂舌（搭接 0.35）。", 2.1)
        pg.text(30, 159, "DFM 注意：(88,8) 螺钉耳与西轨的连接弦宽约 1.55，加工/装配勿撬；首样如断裂，改为与北轨连成整片。", 2.1, c="#a14a00")
    small_part_sheet(allp, "M-R4-04", "USB托架", "USB 托架 usb_bracket", MAT_POM, "机加本色黑", "1 / 套", "4:1",
                     [("t", sh, "top", 4.0, (40, 45), True), ("f", sh, "front", 4.0, (40, 125), True)], [d], ["S1", "S2", "S3", "S4"])


def sheet_audio_frame(allp):
    P = "audio_load_frame"
    ctf("F1", P, "底网厚（选配 0.40/0.50/0.60）", "0.50", "±0.02", "千分尺", "6")
    ctf("F2", P, "底面平面度", "—", "0.05", "平台+塞尺", "6")
    ctf("F3", P, "北挂钩下面至底面", "9.55", "±0.05", "高度规", "6")
    ctf("F4", P, "USB 挂舌下面至底面", "6.85", "±0.05", "高度规", "6")
    ctf("F5", P, "外形（南边与刀片唇搭接 0.35）", "75.00×16.00", "±0.05", "卡尺", "6")
    sh = part(P)
    def d(pg, v):
        t, f, l = v["t"], v["f"], v["l"]
        t.title("俯视（底网朝下）"); f.title("主视（从南侧看）"); l.title("左视（从琴头端看）")
        head_tail(pg, t.box[0], t.box[2], t.box[1] - 15)
        pg.dim_h(t.pt(36.5, 45.2), t.pt(111.5, 45.2), t.box[3] + 6, "75.00±0.05", ctf="F5")
        pg.dim_v(t.pt(111.5, 29.2), t.pt(111.5, 45.2), t.box[2] + 6, "16.00±0.05", ctf="F5")
        pg.dim_h(t.pt(37.3, 44), t.pt(110.7, 44), t.box[3] + 13, "73.40（开口，同音频板外形）")
        pg.dim_v(f.pt(111.4, 0, -11.15), f.pt(111.4, 0, -10.65), f.box[2] + 6, "0.50±0.02 底网", ctf="F1")
        pg.dim_v(f.pt(40, 0, -11.15), f.pt(40, 0, -1.6), f.box[0] - 5, "9.55±0.05", ctf="F3")
        pg.dim_v(f.pt(88, 0, -11.15), f.pt(88, 0, -4.3), f.box[0] + 40, "6.85±0.05", ctf="F4")
        rows = [["audio_load_frame", "0.50", "名义；STEP 主件", "1"], ["audio_load_frame_web0p4", "0.40", "选配：实测间隙 G<0.50", "1"],
                ["audio_load_frame_web0p6", "0.60", "选配：实测 G≥0.60", "1"]]
        pg.text(30, 182, "选配件（底网厚度不同，其余同 STEP；底面 Z 固定在刀片唇上，只改顶面）", 2.3, bold=True)
        pg.table(30, 184, [("STEP", 50), ("底网", 14), ("用途", 46), ("数/套", 12)], rows, size=1.9, rowh=3.4)
        pg.text(30, 202, "选配方法（插座环链，tolerance-stack 链 6）：G = 实测(上盖压台面→唇顶) − 实测(插座肩面→音频板底面，4 个取最大)；", 2.1)
        pg.text(30, 206, "选腹板 t ≤ G 中最厚者，余量 (G − t) 用 0.05 PET 垫片补到 ≤0.05。G<0.40 时停：换插座/板或报工程。", 2.1)
    small_part_sheet(allp, "M-R4-05", "音频承载框（含选配腹板）", "音频承载框 audio_load_frame", MAT_POM, "机加本色黑", "1 / 套 + 选配 2",
                     "2.5:1", [("t", sh, "top", 2.5, (40, 46), False), ("f", sh, "front", 2.5, (40, 106), False), ("l", sh, "left", 2.5, (250, 106), False)],
                     [d], ["F1", "F2", "F3", "F4", "F5"])


def sheet_button(allp):
    P = "button_1"
    ctf("K1", "button", "键杆 Ø（配 Ø5.20 孔）", "Ø5.00", "0/−0.05", "千分尺", "4", 1)
    ctf("K2", "button", "法兰 Ø（止退搭接 0.50）", "Ø6.20", "±0.03", "千分尺", "", 1)
    ctf("K3", "button", "法兰顶面至触头端（按实测修整）", "0.90", "±0.03（修整后 ±0.02）", "高度规", "4", 1)
    ctf("K4", "button", "键杆高（凸出屋顶 0.05）", "0.75", "±0.02", "高度规", "2", 1)
    sh = part(P); bl = part("button_blank_TRIM_TIP_TO_MEASURED_SWITCH")
    def d(pg, v):
        f, t, b = v["f"], v["t"], v["b"]
        f.title("成品（按最高开关设计）主视"); t.title("俯视"); b.title("毛坯 stock：触头加长 0.45，按实测修整")
        x = 10
        pg.dim_h(f.pt(x - 2.5, 25, 3.85), f.pt(x + 2.5, 25, 3.85), f.box[1] - 4, "Ø5.00 0/−0.05", ctf="K1")
        pg.dim_h(f.pt(x - 3.1, 25, 2.6), f.pt(x + 3.1, 25, 2.6), f.box[3] + 8, "Ø6.20±0.03", ctf="K2")
        pg.dim_h(f.pt(x - 0.8, 25, 2.2), f.pt(x + 0.8, 25, 2.2), f.box[3] + 18, "Ø1.60 触头")
        pg.dim_v(f.pt(x + 2.5, 25, 3.1), f.pt(x + 2.5, 25, 3.85), f.box[2] + 6, "0.75±0.02", ctf="K4")
        pg.dim_v(f.pt(x + 3.1, 25, 2.6), f.pt(x + 3.1, 25, 3.1), f.box[2] + 22, "0.50")
        pg.dim_v(f.pt(x - 3.1, 25, 3.1), f.pt(x - 3.1, 25, 2.2), f.box[0] - 6, "0.90±0.03", ctf="K3")
        pg.dim_v(b.pt(x - 0.8, 25, 3.1), b.pt(x - 0.8, 25, 1.75), b.box[0] - 6, "1.35（毛坯）")
        pg.text(30, 170, "修整：干装 C4–C6（不装键），从屋顶顶面经键孔量到开关顶面深度 Dm（深度千分尺，±0.01）；量上盖屋顶顶面到沉槽顶 Rc（名义 0.70）；", 2.1)
        pg.text(30, 174.5, "把毛坯触头修到 L = Dm − Rc − 0.05（目标间隙 0.05），记录每键 Dm/L。键 1–2 在平台上垫同一片 0.1 PET 测量（见 SOP C1）。", 2.1)
        pg.text(30, 179, "开关：Alps SKQGABE010，高 1.5 +0.15/−0，行程 0.25，1.57 N（native-components.json）。每套 5 件，外加毛坯 5 件。", 2.1)
    small_part_sheet(allp, "M-R4-06", "按键（5 件同形）与修触头毛坯", "按键 button_1…5（同形）", MAT_POM, "机加本色黑；顶面哑光，外缘倒钝 0.1", "5 / 套（+毛坯 5）",
                     "10:1", [("f", sh, "front", 10.0, (60, 50), True), ("t", sh, "top", 10.0, (60, 105), False), ("b", bl, "front", 10.0, (200, 50), True)],
                     [d], ["K1", "K2", "K3", "K4"])


def sheet_lightpipe(allp):
    ctf("P1", "lightpipe", "柱体 Ø（配 Ø1.50 孔）", "Ø1.40", "0/−0.03", "千分尺", "", 1)
    ctf("P2", "lightpipe", "法兰顶面至出光面（与屋顶平）", "1.30", "±0.03", "高度规", "", 1)
    ctf("P3", "lightpipe", "总长（入光面离 LED 0.1）", "2.35", "±0.05", "高度规", "", 1)
    ctf("P4", "lightpipe", "入/出光面", "光学抛光；出光面可细雾化", "无划伤", "目视 10×", "", 1)
    sh = part("lightpipe_1")
    def d(pg, v):
        f, t = v["f"], v["t"]
        f.title("主视"); t.title("俯视")
        x, y = 15, 21
        pg.dim_h(f.pt(x - 0.7, y, 3.8), f.pt(x + 0.7, y, 3.8), f.box[1] - 4, "Ø1.40 0/−0.03", ctf="P1")
        pg.dim_h(f.pt(x - 1.0, y, 2.1), f.pt(x + 1.0, y, 2.1), f.box[3] + 8, "Ø2.00 法兰")
        pg.dim_v(f.pt(x + 1.0, y, 2.5), f.pt(x + 1.0, y, 3.8), f.box[2] + 6, "1.30±0.03", ctf="P2")
        pg.dim_v(f.pt(x - 0.7, y, 1.45), f.pt(x - 0.7, y, 3.8), f.box[0] - 6, "2.35±0.05", ctf="P3")
        pg.dim_v(f.pt(x + 1.0, y, 2.1), f.pt(x + 1.0, y, 2.5), f.box[2] + 22, "0.40")
        pg.text(30, 160, "装配：C2 从内侧装入，法兰顶住屋顶内表面；周边少量透明 UV 胶，胶不得进入出光面或 LED。LP2 位于 (34.7, 20.7)（M11 偏移）。", 2.1)
    small_part_sheet(allp, "M-R4-07", "导光柱（3 件同形）", "导光柱 lightpipe_1…3（同形）", "PC 透明（光学级，如 Makrolon LED/2407 类，候选）",
                     "两端面抛光，侧面原色", "3 / 套", "15:1", [("f", sh, "front", 15.0, (70, 50), False), ("t", sh, "top", 15.0, (180, 50), False)],
                     [d], ["P1", "P2", "P3", "P4"])


def sheet_films(allp):
    ctf("I1", "films", "绝缘片总厚（含胶）", "0.100", "±0.010", "千分尺", "4,8", 1)
    ctf("I2", "films", "外形（模切）", "按表", "±0.15", "卡尺/影像", "", 1)
    ctf("I3", "main_shim", "垫片厚度 0.05/0.10/0.20", "按名", "±0.005/±0.01/±0.01", "千分尺", "8", 1)
    pg = Page()
    frame(pg, "M-R4-08", "绝缘片与主板调整垫片（平面展开）", "绝缘片 6 种 + 主板垫片 3 种", "PET（聚酯）/ PI（聚酰亚胺），见表", "无印刷；去毛刺；装箱分层隔纸",
          "见表", "2:1 / 4:1", "1/1", ["6. 总厚指含胶厚度。背撑垫片（key/speaker_backer_insulator）单面压敏胶；其余无胶。",
                                       "7. 主板垫片只在实测主板卡齿间隙 >0 时单层选用，不得叠装；按托台形状 4 段为一套。"])
    items = [("battery_bottom_insulator", "电池底绝缘片", "PET 0.10 无胶", "1", 1.5, (30, 40)),
             ("battery_top_separator", "电池顶隔片", "PET 0.10 无胶", "1", 1.5, (130, 40)),
             ("main_audio_dielectric_separator", "主板/音频板绝缘片", "PET 0.10 无胶（缺口让 POTS3）", "1", 1.5, (230, 40)),
             ("key_backer_insulator", "按键 1–2 背垫（贴控制板底面）", "PET 0.10 含单面胶；选配 0.075/0.125", "1（+选配各1）", 2.0, (30, 125)),
             ("speaker_backer_insulator", "扬声器背垫", "PET 0.10 含单面胶", "1", 2.0, (110, 125)),
             ("ntc_electrical_separator", "NTC 电绝缘片", "PI 0.10 无胶", "1", 6.0, (170, 125)),
             ("main_shim_0p1mm", "主板调整垫片（0.05/0.10/0.20 同形）", "PET，按名厚", "各 1 套（4 段）", 1.0, (40, 192))]
    rows = []
    for n, cn, mat, q, sc, at in items:
        shp = part(n)
        kind = "left" if n.startswith("ntc") else "top"
        v = View(pg, shp, kind, sc, at, w=0.25)
        bb = shp.BoundingBox()
        dims = sorted([bb.xlen, bb.ylen, bb.zlen], reverse=True)
        v.title(f"{cn}", f"{n}")
        x0, y0, x1, y1 = v.box
        pg.dim_h((x0, y1), (x1, y1), y1 + 5, f"{dims[0]:.2f}")
        pg.dim_v((x1, y0), (x1, y1), x1 + 5, f"{dims[1]:.2f}")
        rows.append([n, cn, f"{dims[0]:.2f}×{dims[1]:.2f}×{dims[2]:.2f}", mat, q])
    pg.text(236, 150, "清单", 2.4, bold=True)
    pg.table(236, 152, [("STEP", 52), ("名称", 44), ("外形 L×W×T", 30), ("材料", 44)], [r[:4] for r in rows], size=1.7, rowh=3.3)
    ctf_table(pg, 236, 190, ["I1", "I2", "I3"], widths=(8, 52, 32, 30, 30))
    save(pg, "M-R4-08_绝缘片与调整垫片", allp)


def sheet_foam(allp):
    ctf("Q1", "battery_top_foam", "自由厚度", "1.00", "±0.10", "测厚规（低压）", "", 1)
    ctf("Q2", "battery_top_foam", "外形与 2 个窗口", "48.0×30.8；窗 44.0×6.4", "±0.20", "卡尺", "", 1)
    sh = part("battery_top_foam")
    def d(pg, v):
        t = v["t"]
        t.title("俯视（平面展开）")
        pg.dim_h(t.pt(42, 39.8), t.pt(90, 39.8), t.box[3] + 6, "48.00±0.20", ctf="Q2")
        pg.dim_v(t.pt(90, 9.0), t.pt(90, 39.8), t.box[2] + 6, "30.80±0.20", ctf="Q2")
        pg.dim_h(t.pt(44, 15.0), t.pt(88, 15.0), t.box[1] - 4, "44.00（窗）")
        pg.dim_v(t.pt(44, 15.0), t.pt(44, 21.4), t.box[0] - 5, "6.40")
        pg.dim_v(t.pt(44, 27.4), t.pt(44, 33.8), t.box[0] - 5, "6.40")
        pg.dim_v(t.pt(42, 9.0), t.pt(42, 15.0), t.box[0] - 14, "6.00")
        pg.text(30, 150, "材料：Rogers PORON 4701-30（极软级）1.0 mm 或等效微孔聚氨酯（候选，需供应商资料），无胶；压缩约 50% 时仍应可回弹。", 2.1)
        pg.text(30, 154.5, "作用：填满电池 1.0 膨胀余量并轻预压（M12）；两窗口避开电池中央。装配 L3：先泡棉后顶隔片，不得拉伸变形。", 2.1)
    small_part_sheet(allp, "M-R4-09", "电池顶部泡棉", "电池顶部泡棉 battery_top_foam", "PORON 4701-30 1.0（候选）", "模切，无胶", "1 / 套", "2.5:1",
                     [("t", sh, "top", 2.5, (40, 45), False)], [d], ["Q1", "Q2"])


def main():
    cover_ctfs(); cup_ctfs()
    allp = []
    sheet_assembly(allp)
    sheet_cover_outside(allp)
    sheet_cover_inside(allp)
    sheet_cover_sections(allp)
    sheet_cup(allp)
    sheet_key_backer(allp)
    sheet_usb_bracket(allp)
    sheet_audio_frame(allp)
    sheet_button(allp)
    sheet_lightpipe(allp)
    sheet_films(allp)
    sheet_foam(allp)
    from reportlab.pdfgen import canvas
    cv = canvas.Canvas(str(OUT / "M-R4-drawings-all.pdf"))
    for pg in allp:
        pg.pdf(cv)
    cv.save()
    (OUT / "ctf-register.json").write_text(json.dumps({"revision": REV, "date": DATE, "items": CTF}, ensure_ascii=False, indent=1), encoding="utf8")
    print(len(allp), "sheets;", len(CTF), "CTF items")


if __name__ == "__main__":
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    pdfmetrics.registerFont(TTFont("WQY", os.environ.get("SMARTVIO_CJK_FONT", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"), subfontIndex=0))
    main()
