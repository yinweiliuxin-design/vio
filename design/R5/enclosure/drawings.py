"""SmartVio R5 enclosure V0.1 manufacturing drawings, generated from the STEP files of build_enclosure.py.

Run after build_enclosure.py:   python3 drawings.py
Output: drawings/M-R5-*.svg|pdf, drawings/M-R5-drawings-all.pdf, ctf-register.json
Views are exact OCC hidden-line projections; dimensions are placed on projected model points.
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cadquery as cq                    # noqa: E402
import build_enclosure as E              # noqa: E402
import drawlib as D                      # noqa: E402
from drawlib import Page, View, section, crop, CTF_COLOR, INK   # noqa: E402

STEP = HERE / "step"
OUT = HERE / "drawings"
OUT.mkdir(exist_ok=True)
DATE = "2026-11-03"
REV = "V0.1"
BLUE = "#1a4f8a"

_cache = {}


def part(n):
    if n not in _cache:
        _cache[n] = cq.importers.importStep(str(STEP / f"{n}.step")).val()
    return _cache[n]


_asm = {}


def asm():
    if not _asm:
        P, *_ = E.build_all(text=False)
        _asm.update(P)
    return _asm


def f(v, n=2):
    s = f"{v:.{n}f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


CTF = []


def ctf(tag, part_name, feature, nominal, tol, method):
    CTF.append(dict(id=tag, part=part_name, feature=feature, nominal=nominal, tol=tol, method=method))
    return tag


MAT_POM = "POM-C 共聚甲醛 黑色（整料 CNC）"
GENERAL = [
    "1. 未注公差按 ISO 2768-m（GB/T 1804-m）；未注几何公差 ISO 2768-K；在 23±2 °C 下检验。",
    "2. 红色尺寸与六角标签 Kn 为关键功能尺寸（CTF）：首件 100% 检测，结果记入 FAI-checklist.md。",
    "3. 单位 mm，第一角画法。坐标：X 向琴尾（X0 = 琴头端）；y 向 E 弦侧（y0 = G 弦侧边）；Z 向外（Z0 = 琴背面 = 面盖顶面）。",
    "4. 锐边倒钝 0.1–0.2（卡扣根部、卡扣窗棱边、配合面除外）；无毛刺、无残料；未注内角 R ≤ 0.5。",
    "5. 形状以同名 STEP 为准，图面只标关键尺寸；图与 STEP 冲突时停工询问，不得自行取舍。",
]


def frame(pg, no, title, partname, material, finish, qty, scale, sheet, extra=()):
    pg.rect(10, 10, 400, 277, 0.5)
    pg.text(14, 17, "SmartVio R5  外壳首样工程图", 3.6, bold=True)
    pg.text(112, 17, title, 3.6, bold=True)
    pg.text(406, 17, "状态：V0.1 首样图 / 主板接口为建议值，待乙方确认", 2.6, "end", 0, "#a14a00")
    pg.line(10, 20, 410, 20, 0.3)
    x0, y0 = 12, 243
    pg.rect(x0, y0, 214, 42, 0.3)
    pg.text(x0 + 1.5, y0 + 4, "技术要求", 2.6, bold=True)
    lines = GENERAL + list(extra)
    for i, t in enumerate(lines[:9]):
        pg.text(x0 + 1.5, y0 + 8.4 + i * 4.0, t, 1.95)
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
    sx, sy = 392, 266.5
    pg.poly([(sx - 13, sy - 1.6), (sx - 7, sy - 3), (sx - 7, sy + 3), (sx - 13, sy + 1.6)], 0.2, closed=True)
    pg.circle(sx - 1.5, sy, 3, 0.2)
    pg.circle(sx - 1.5, sy, 1.6, 0.2)


def head_tail(pg, x0, x1, y, note="X0 = 琴头端"):
    pg.line(x0 + 2, y, x1 - 2, y, 0.35)
    pg.arrow(x0, y, 180, 3)
    pg.arrow(x1, y, 0, 3)
    pg.text(x0 + 4, y - 1.4, "琴头 HEAD", 2.6, bold=True)
    pg.text(x1 - 4, y - 1.4, "琴尾 TAIL", 2.6, "end", 0, INK, True)
    pg.text((x0 + x1) / 2, y - 1.4, note, 2.2, "middle")


def datum(pg, p, letter, side="up"):
    """Datum feature symbol: filled triangle on the edge, square box with the letter."""
    x, y = p
    d = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[side]
    tri = [(x - 1.2 * abs(d[1]) - 0.0, y - 1.2 * abs(d[0])), (x + 1.2 * abs(d[1]), y + 1.2 * abs(d[0])),
           (x + d[0] * 1.8, y + d[1] * 1.8)]
    pg.poly(tri, 0.15, INK, None, True, INK)
    bx, by = x + d[0] * 5.5, y + d[1] * 5.5
    pg.line(x + d[0] * 1.8, y + d[1] * 1.8, bx, by, 0.2)
    pg.rect(bx - 2.2, by - 2.2, 4.4, 4.4, 0.25, INK, "#ffffff")
    pg.text(bx, by + 1.0, letter, 2.8, "middle", 0, INK, True)


def cut_line(pg, view, y_log, x0, x1, letter, up=True):
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
    a, b = view.pt(x_log, y0 - 3), view.pt(x_log, y1 + 3)
    pg.line(a[0], a[1], b[0], b[1], 0.18, "#333333", "6 1 1 1")
    for (px, py) in (a, b):
        pg.line(px, py - 2.5 if py < b[1] else py, px, py + 2.5 if py < b[1] else py, 0.6)
        yy = py - 1.2 if py < b[1] else py + 1.2
        tip = px + 6 if right else px - 6
        pg.line(px, yy, tip - (1.6 if right else -1.6), yy, 0.3)
        pg.arrow(tip, yy, 0 if right else 180, 2.4)
        pg.text(tip + (2.4 if right else -2.4), yy + 1.1, letter, 3.2, "middle", 0, INK, True)


def tag(pg, p, t, dx=1.6, dy=-1.6, c=BLUE, size=2.0):
    pg.text(p[0] + dx, p[1] + dy, t, size, "start", 0, c, True)


def save(pg, name, allpages):
    (OUT / f"{name}.svg").write_text(pg.svg(), encoding="utf8")
    from reportlab.pdfgen import canvas
    cv = canvas.Canvas(str(OUT / f"{name}.pdf"))
    pg.pdf(cv)
    cv.save()
    allpages.append(pg)
    print("sheet", name, flush=True)


def table(pg, x, y, title, cols, rows, size=1.85, rowh=3.3, ctf_col=None):
    pg.text(x, y - 1.2, title, 2.4, bold=True)
    return pg.table(x, y, cols, rows, size=size, rowh=rowh, ctf_col=ctf_col)


def multi_section(parts, axis, pos, keep, cropbox, styles):
    """parts: {name: shape}. Returns (compound, [(style, polys)])."""
    pieces, faces = [], []
    for n, s in parts.items():
        try:
            c, polys = section(cq, s, axis, pos, keep, crop=cropbox)
        except Exception as e:  # noqa: BLE001
            print("  section skip", n, e)
            continue
        if c.Volume() > 1e-6:
            pieces.append(c)
            faces.append((styles(n), polys))
    return cq.Compound.makeCompound(pieces), faces


def hatch_all(view, faces):
    for (ang, fill, sp), polys in faces:
        if polys:
            view.hatch(polys, angle=ang, spacing=sp, fill=fill)


def style_of(n):
    if n.startswith("violin"):
        return (30, "#f1e2cc", 1.4)
    if n.startswith("cover"):
        return (45, "#e4e4e4", 0.8)
    if n.startswith("shell"):
        return (135, "#e4e4e4", 0.8)
    if n.startswith(("pcba_pcb", "usb_board")):
        return (0, "#d9ecd9", 0.5)
    if n.startswith(("pcba", "usb")):
        return (90, "#e3eef9", 1.2)
    if n.startswith("battery"):
        return (90, "#f3e6c8", 1.2)
    if n.startswith("speaker"):
        return (60, "#e8e8f0", 1.0)
    return (45, "#ffffff", 0.7)


# =====================================================================================================
# M-R5-00 assembly
# =====================================================================================================
def sheet_assembly(allp):
    pg = Page()
    frame(pg, "M-R5-00", "总装图（装琴状态、零件表）", "SmartVio R5 模块外壳总成", "见零件表", "见各零件图", "1 套",
          "1.5:1（俯视、A-A）  2:1（B-B）", "1/1",
          ["6. 装配顺序、扭矩和检查见 ASSEMBLY.md；主板、USB 小板、电池、扬声器为包络（乙方确认后更新）。",
           "7. 琴槽见 M-R5-05：面盖压在 2.0 深台阶上，与琴背齐平；底壳四周和底部都不碰琴槽。"])
    P = asm()
    s = 1.5
    comp = cq.Compound.makeCompound([P["cover"]] + [P[n] for n in P if n.startswith(("knob", "cap", "lightpipe", "screw_ST"))])
    v = View(pg, comp, "top", s, (34, 44), w=0.25)
    v.title("俯视（装琴状态，从琴背外侧看）", "琴头在左，G 弦侧在上")
    head_tail(pg, v.box[0], v.box[2], 30.5)
    pg.dim_v(v.pt(0, 0), v.pt(0, 49), v.box[0] - 6, "49", size=2.1)
    cut_line(pg, v, 24.5, 0, 148, "A", up=False)
    cut_line_v(pg, v, 51.0, 0, 49, "B", right=True)
    yb = v.box[3] + 13
    pg.line(v.box[0], yb, v.box[2], yb, 0.2)
    for X, u in [(0, 258), (34, 224), (104, 154), (148, 110)]:
        px = v.pt(X, 0)[0]
        pg.line(px, yb - 1.5, px, yb + 1.5, 0.3)
        pg.text(px, yb + 4.2, f"u={u}", 2.1, "middle", 0, BLUE)
        pg.text(px, yb - 2.2, f"X={X}", 1.9, "middle", 0, "#555555")
    pg.text(v.box[0], yb + 8.2, "u = 距琴尾基准的距离（安装位置 u 110–258，见 M-R5-05）。X = 258 − u。", 2.0)

    # A-A
    names = [n for n in P if not n.endswith(("gasket",))]
    parts = {n: P[n] for n in names}
    cb = (-6.0, -24.5, -21.0, 154.0, 40.0, 9.0)
    comp, faces = multi_section(parts, "Y", -24.5, +1, cb, style_of)
    sv = View(pg, comp, "front", s, (30, 164), w=0.2)
    hatch_all(sv, faces)
    sv.title("A-A（y = 24.5 插座中心线）", "木色 = 琴体，灰 = 面盖/底壳，绿 = 主板，蓝 = 元件包络，黄 = 电池")
    xl = sv.box[0] - 3
    pg.dim_v(sv.pt(0, 24.5, 0), sv.pt(0, 24.5, -11), xl - 5, "11")
    pg.dim_v(sv.pt(0, 24.5, 0), sv.pt(0, 24.5, -2), xl, "2.0")
    xr = sv.box[2] + 3
    pg.dim_v(sv.pt(148, 24.5, 0), sv.pt(148, 24.5, -14), xr, "14")
    p17 = sv.pt(70, 24.5, -17)
    pg.leader(p17, p17[0] + 18, p17[1] + 7, "控制区槽深 17", size=2.0)
    pg.text(sv.box[0], sv.box[3] + 7, "旋钮高出琴背 7.0；面盖与琴背齐平（台阶深 = 面盖厚 2.0）；底壳四周离槽 0.25、底部离槽底 0.3。", 2.0)

    # B-B at X = 51
    cb2 = (51.0, -55.0, -21.0, 58.0, 6.0, 9.0)
    comp2, faces2 = multi_section(parts, "X", 51.0, +1, cb2, style_of)
    bv = View(pg, comp2, "left", 2.0, (284, 44), w=0.2)
    hatch_all(bv, faces2)
    bv.title("B-B（X = 51：VOL 编码器、PHONES 插座、导光柱）", None, size=2.6)
    pg.leader(bv.pt(51, 9, 4.5), bv.box[0] + 4, bv.box[1] - 2, "旋钮 Ø13，底面离面盖 0.5", size=1.9)
    pg.leader(bv.pt(51, 40.5, -6.0), bv.box[2] - 30, bv.box[3] + 6, "导光柱 → LED", size=1.9)
    pg.leader(bv.pt(51, 24.5, -7.0), bv.box[0] + 2, bv.box[3] + 6, "插座包络", size=1.9)

    rows = [["1", "R5-01_cover", "面盖", "M-R5-01/02", "POM-C 黑", "1"],
            ["2", "R5-02_shell", "底壳", "M-R5-03", "POM-C 黑", "1"],
            ["3", "R5-03_knob", "旋钮", "M-R5-04", "POM-C 黑", "3"],
            ["4", "R5-04_button_cap", "按键帽", "M-R5-04", "POM-C 黑", "5"],
            ["5", "R5-05_light_pipe", "导光柱", "M-R5-04", "PC 透明", "3"],
            ["6", "ST2.2×9.5 沉头自攻", "面盖固定到琴体", "GB/T 846", "A2 不锈钢 黑", "4"],
            ["7", "M2×5 PT 自攻（K20×5）", "主板固定", "外购", "钢 镀镍", "4"],
            ["8", "M1.6×4 PT 自攻", "USB 小板固定", "外购", "钢 镀镍", "2"],
            ["9", "喇叭防尘网 Ø27", "面盖网孔背面", "外购", "无纺/金属网 背胶", "1"],
            ["10", "喇叭前密封圈 Ø28/Ø24×0.5", "喇叭与面盖之间", "外购", "PORON 背胶", "1"],
            ["11", "喇叭后泡棉 Ø20×2.0", "压住喇叭", "外购", "PORON", "1"],
            ["12", "电池底泡棉 26×36×0.5", "电池下面", "外购", "PORON 背胶", "1"],
            ["E1", "主板（乙方）", "64.5 × 43 × 1.0", "M-R5-06", "—", "1"],
            ["E2", "USB-C 小板（乙方）", "6.7 × 20 × 1.0", "M-R5-06", "—", "1"],
            ["E3", "电池 10×30×40", "约 1300 mAh", "乙方采购", "—", "1"],
            ["E4", "扬声器 Ø28×≤5.5", "4 Ω", "乙方采购", "—", "1"]]
    x0 = 286
    pg.text(x0, 136, "零件表（每套）", 2.6, bold=True)
    yy = pg.table(x0, 138, [("件", 6), ("名称 / STEP", 38), ("用途", 25), ("图号", 16), ("材料", 23), ("数量", 10)],
                  rows, size=1.65, rowh=3.3)
    pg.text(x0, yy + 4.5, "E 项为电子件，由乙方提供；尺寸是外壳预留的包络，", 1.9)
    pg.text(x0, yy + 8.5, "乙方确认后定稿。", 1.9)
    save(pg, "M-R5-00_总装图", allp)


# =====================================================================================================
# M-R5-01 cover, outside
# =====================================================================================================
def cover_ctfs():
    P = "面盖"
    ctf("K1", P, "外形 148 × 49（装入琴上 148.4 × 49.4 台阶）", "148.0 / 49.0", "±0.10", "卡尺")
    ctf("K2", P, "厚度 2.00（与琴背齐平）", "2.00", "±0.05", "千分尺，测 6 点")
    ctf("K3", P, "编码器 / 插座 / 按键 / 导光柱 15 孔位置（对凸台 B1–B4）", "孔表", "±0.05", "二次元 / CMM")
    ctf("K4", P, "按键孔 Ø5.6（导向按键帽 Ø5.4）", "5.60", "+0.05 / 0", "针规")
    ctf("K5", P, "USB-C 槽 9.4 × 3.6", "9.40 × 3.60", "+0.10 / 0", "二次元")
    ctf("K6", P, "四角沉头孔：Ø2.4 + 90° 沉头 Ø4.5", "Ø4.50", "±0.10", "二次元；装 ST2.2 头低于顶面 0.2–0.5")
    ctf("K7", P, "主板凸台 B1–B4 端面 Z−12.00（距顶面）", "12.00", "±0.05", "高度规")
    ctf("K8", P, "USB 凸台 U1–U2 端面 Z−9.60", "9.60", "±0.05", "高度规")
    ctf("K9", P, "卡扣 S1–S8：钩面 Z−6.45、外贴面位置", "6.45 / 2.45", "±0.05", "二次元；装底壳试卡 3 次")
    ctf("K10", P, "导光柱孔 Ø3.1", "3.10", "+0.05 / 0", "针规")


def sheet_cover_top(allp):
    pg = Page()
    frame(pg, "M-R5-01", "面盖 1/2：外观面（孔位、刻字）", "面盖 cover（R5-01_cover.step）", MAT_POM,
          "外观面哑光 Ra≤1.6（可细喷砂，喷砂在刻字前）；刻字不填色", "首样 3 + 1 件", "2:1（俯视）  8:1（详图 D）", "1/2",
          ["6. 刻字：DejaVu Sans Bold，深 0.15±0.05，CNC 刻或激光雕均可；字形、位置以 STEP 为准（字表见右）。",
           "7. 外观面不得有刀纹、夹痕、划伤；喇叭网孔 91 个孔口两面去毛刺，不得有披锋。"])
    cover = part("R5-01_cover")
    s = 2.0
    v = View(pg, cover, "top", s, (40, 46), w=0.25, defl=0.02)
    v.title("俯视：外观面", "琴头 X0 在左，G 弦侧 y0 在上；孔位坐标见孔表（基准 B = y0 边，C = X0 端）")
    pg.dim_h(v.pt(0, 49), v.pt(148, 49), v.box[3] + 9, "148 ±0.10", ctf="K1")
    pg.dim_v(v.pt(148, 0), v.pt(148, 49), v.box[2] + 8, "49 ±0.10", ctf="K1")
    pg.leader(v.pt(148 - 4 + 4 * 0.7071, 4 - 4 * 0.7071), v.box[2] - 6, v.box[1] - 5, "R4 ×4", size=2.0)
    datum(pg, v.pt(74, 0), "B", "up")
    datum(pg, v.pt(0, 34), "C", "left")
    groups = [("H1", [(X, y) for _, X, y in E.KNOBS], f"Ø{E.ENC_HOLE_D} +0.10/0", "编码器"),
              ("H2", [(X, y) for _, X, y in E.JACKS], f"Ø{E.JACK_HOLE_D} +0.10/0", "插座"),
              ("H3", [(X, y) for _, X, y in E.BUTTONS], f"Ø{E.BTN_HOLE_D} +0.05/0", "按键帽"),
              ("H4", list(E.LEDS), f"Ø{E.LP_HOLE_D} +0.05/0", "导光柱"),
              ("H5", [E.USBC], f"槽 {E.USBC_SLOT[0]}×{E.USBC_SLOT[1]} R1.8 +0.10/0", "USB-C"),
              ("H6", list(E.SCREWS), f"Ø{E.SCREW_D} 通 + 90° 沉头 Ø{E.CSK_D}", "固定螺钉")]
    rows = []
    tagpos = {"H1": (-0.75, -0.75, -5.5, -0.6), "H2": (-0.75, -0.75, -5.5, -0.6), "H3": (-0.75, -0.75, -5.5, -0.6),
              "H4": (0.0, -1.0, -2.2, -2.4), "H5": (-0.75, -0.75, -5.5, -0.6), "H6": (-0.75, -0.75, -5.5, -0.6)}
    for g, pts, size, what in groups:
        for i, (X, y) in enumerate(pts, 1):
            rows.append([f"{g}-{i}", what if i == 1 else "", f(X), f(y), size if i == 1 else "同上"])
        X, y = pts[0]
        rr = {"H1": E.ENC_HOLE_D, "H2": E.JACK_HOLE_D, "H3": E.BTN_HOLE_D, "H4": E.LP_HOLE_D, "H5": 4.7, "H6": E.CSK_D}[g] / 2
        kx, ky, dx, dy = tagpos[g]
        tag(pg, v.pt(X + kx * rr, y + ky * rr), g, dx=dx, dy=dy)
    rows.append(["H7", "喇叭网孔", f(E.SPEAKER[0]), f(E.SPEAKER[1]), "Ø1.2 ×91 六角 节距 2.4 圆域 Ø26"])
    gx, gy = E.SPEAKER
    tag(pg, v.pt(gx - 13, gy - 13), "H7", dx=-2, dy=0)
    xc = 352
    pg.text(xc, 52, "关键尺寸（CTF）", 2.4, "start", 0, INK, True)
    for i, (t, k) in enumerate([("外形 148 / 49 ±0.10", "K1"), ("厚 2.00 ±0.05", "K2"), ("H1–H4 位置 ±0.05", "K3"),
                                ("（对凸台 B1–B4）", None), ("H3 Ø5.6 +0.05/0", "K4"), ("H5 USB-C 槽 +0.10/0", "K5"),
                                ("H6 沉头 Ø4.5 ±0.10", "K6"), ("H4 Ø3.1 +0.05/0", "K10")]):
        pg.label(xc, 58 + i * 4.6, t, 2.0, ctf=k)
    pg.text(xc, 102, "孔位坐标都从基准 C（X0 端）", 2.0)
    pg.text(xc, 106.4, "和 B（y0 边）量；与背面凸台", 2.0)
    pg.text(xc, 110.8, "同一次装夹加工。", 2.0)
    yy = table(pg, 20, 170, "孔表（中心坐标，对基准 C / B）", [("编号", 10), ("用途", 13), ("X", 11), ("y", 10), ("尺寸 / 公差", 42)],
               rows, size=1.7, rowh=3.0)
    lab = [[t, f(X), f(y), f(sz)] for t, X, y, sz in E.M.labels()] + [[E.M.LOGO[0], f(E.M.LOGO[1]), f(E.M.LOGO[2]), f(E.M.LOGO[3])]]
    table(pg, 115, 170, "刻字表（字框中心；字号 = em）", [("文字", 18), ("X", 11), ("y", 11), ("字号", 10)], lab, size=1.7, rowh=3.0)
    # detail D: countersink, section through H6-1 along y = 5.3
    cb = (-1.5, -5.3, -2.6, 11.0, 4.0, 0.6)
    c, polys = section(cq, cover, "Y", -5.3, +1, crop=cb)
    dv = View(pg, c, "front", 8.0, (190, 186), w=0.3)
    dv.hatch(polys, angle=45, spacing=0.9, fill="#e9e9e9")
    dv.title("详图 D（8:1）：角孔沉头，过 H6-1 中心", None, size=2.6, off=12)
    X0, y0 = E.SCREWS[0]
    pg.dim_h(dv.pt(X0 - E.CSK_D / 2, y0, 0), dv.pt(X0 + E.CSK_D / 2, y0, 0), dv.box[1] - 3, "Ø4.5 ±0.10", ctf="K6", size=2.0)
    pg.dim_h(dv.pt(X0 - E.SCREW_D / 2, y0, -2), dv.pt(X0 + E.SCREW_D / 2, y0, -2), dv.box[3] + 4, "Ø2.4", size=2.0)
    pg.dim_v(dv.pt(11.0, y0, 0), dv.pt(11.0, y0, -2), dv.box[2] + 6, "2.00 ±0.05", ctf="K2", size=2.0)
    pg.text(dv.box[0], dv.box[3] + 13, "90° 沉头；配 ST2.2 沉头自攻钉（GB/T 846，头 Ø3.8）。", 2.0)
    pg.text(dv.box[0], dv.box[3] + 17.4, "装好后钉头低于顶面 0.2–0.5，不得凸出。", 2.0)
    save(pg, "M-R5-01_面盖-外观面", allp)


# =====================================================================================================
# M-R5-02 cover, underside
# =====================================================================================================
def sheet_cover_bottom(allp):
    pg = Page()
    frame(pg, "M-R5-02", "面盖 2/2：背面（凸台、卡扣、筋）", "面盖 cover（R5-01_cover.step）", MAT_POM,
          "背面机加本色，无外观要求", "首样 3 + 1 件", "2:1（仰视、C-C）  8:1（详图 S）", "2/2",
          ["6. 凸台底孔为自攻底孔：B1–B4 Ø1.7 深 6（M2 PT 自攻），U1–U2 Ø1.3 深 4.5（M1.6 PT 自攻），孔口倒角 0.2。",
           "7. 卡扣舌根部 R0.3，钩面锐角保留；卡扣舌不得有裂纹、毛刺。首件装底壳试卡 3 次不裂、不松。"])
    cover = part("R5-01_cover")
    s = 2.0
    v = View(pg, cover, "bottom", s, (30, 46), w=0.25, defl=0.02)
    v.title("仰视：背面（翻过来看，琴头仍在左，G 弦侧 y0 在下）", None)
    cut_line_v(pg, v, 39.0, 0, 49, "C", right=True)
    rows = []
    for i, (X, y) in enumerate(E.PCB_BOSSES, 1):
        rows.append([f"B{i}", "主板凸台", f(X), f(y), f"Ø{E.BOSS_D}，端面 Z−12.00；底孔 Ø{E.BOSS_PILOT}×{f(E.BOSS_PILOT_DEPTH)}"])
        tag(pg, v.pt(X + 2.2, y + 2.2), f"B{i}", dx=0.5, dy=0)
    for i, (X, y) in enumerate(E.USB_BOSSES, 1):
        rows.append([f"U{i}", "USB 凸台", f(X), f(y), f"Ø{E.USB_BOSS_D}，端面 Z−9.60；底孔 Ø{E.USB_PILOT}×{f(E.USB_PILOT_DEPTH)}"])
        tag(pg, v.pt(X - 2.0, y), f"U{i}", dx=-6.5, dy=0.7)
    k = 0
    for side in ("near", "far"):
        for X in E.SNAP_X:
            k += 1
            yy_ = E.SHELL_IN if side == "near" else E.W - E.SHELL_IN
            rows.append([f"S{k}", "卡扣舌", f(X), f(yy_), f"宽 {f(E.SNAP_W)} 厚 {f(E.SNAP_T)}，外贴面 y={f(yy_)}，见详图 S"])
            tag(pg, v.pt(X + 3.2, yy_), f"S{k}", dx=0.3, dy=(3.8 if side == "near" else -1.6))
    for i, (x0, y0, x1, y1) in enumerate(E.COVER_RIBS, 1):
        rows.append([f"R{i}", "加强筋", f"{f(x0)}–{f(x1)}", f"{f(y0)}–{f(y1)}", f"宽 {f(y1 - y0)}，到 Z{f(E.RIB_Z)}"])
        tag(pg, v.pt(x0 + 1, (y0 + y1) / 2), f"R{i}", dx=-6.0, dy=0.8)
    rows.append(["SR", "喇叭定位筋", f(E.SPEAKER[0]), f(E.SPEAKER[1]), "3 段弧 R14.2–R15.2，各 30°，到 Z−4.0"])
    tag(pg, v.pt(E.SPEAKER[0] + 15.5, E.SPEAKER[1]), "SR", dx=0.5, dy=0.7)
    x0 = 330
    yy = table(pg, x0, 30, "背面特征表（中心 / 范围）", [("编号", 9), ("名称", 14), ("X", 13), ("y", 12), ("说明", 30)], rows,
               size=1.55, rowh=3.0)
    pg.label(x0, yy + 4.2, "B1–B4 端面 Z−12.00 ±0.05", 1.9, ctf="K7")
    pg.label(x0, yy + 8.6, "U1–U2 端面 Z−9.60 ±0.05", 1.9, ctf="K8")
    pg.label(x0, yy + 13.0, "S1–S8 钩面 / 外贴面 ±0.05", 1.9, ctf="K9")
    # C-C at X = 39 (B1, B2), viewed from the head end
    cb = (39.0, -60.0, -14.0, 60.0, 12.0, 1.0)
    c, polys = section(cq, cover, "X", 39.0, +1, crop=cb)
    cv = View(pg, c, "left", 2.0, (30, 176), w=0.25)
    cv.hatch(polys, angle=45, spacing=0.9, fill="#e9e9e9")
    cv.title("C-C（X = 39，过 B1、B2），从琴头方向看", None, size=2.6, off=5)
    pg.dim_v(cv.pt(39, 6.0, 0), cv.pt(39, 6.0, -12), cv.box[0] - 4, "12.00 ±0.05", ctf="K7", size=2.0)
    pg.dim_v(cv.pt(39, 49, 0), cv.pt(39, 49, -2), cv.box[2] + 4, "2.00", size=2.0)
    pg.dim_h(cv.pt(39, 43 - 2, -12), cv.pt(39, 43 + 2, -12), cv.box[3] + 5, "Ø4.0", size=2.0)
    # detail S: snap S1 profile, section at X = 20
    cb2 = (20.0, -6.5, -8.2, 26.0, 1.0, 0.6)
    c2, polys2 = section(cq, cover, "X", 20.0, +1, crop=cb2)
    sv = View(pg, c2, "left", 8.0, (190, 160), w=0.3)
    sv.hatch(polys2, angle=45, spacing=0.9, fill="#e9e9e9")
    sv.title("详图 S（8:1）：卡扣舌 S1 截面（X = 20）", None, size=2.6, off=5)
    yi = E.SHELL_IN
    pg.dim_h(sv.pt(20, yi, E.SNAP_TIP), sv.pt(20, yi + E.SNAP_T, E.SNAP_TIP), sv.box[3] + 4, f"{f(E.SNAP_T)}", size=2.0)
    pg.dim_h(sv.pt(20, 0, -2.0), sv.pt(20, yi, -2.0), sv.box[1] - 2, f"{f(yi)} ±0.05", ctf="K9", size=2.0)
    pg.dim_v(sv.pt(20, 6.0, 0), sv.pt(20, 6.0, E.HOOK_TOP), sv.box[2] + 5, f"{f(-E.HOOK_TOP)} ±0.05", ctf="K9", size=2.0)
    pg.dim_v(sv.pt(20, 6.0, 0), sv.pt(20, 6.0, E.SNAP_TIP), sv.box[2] + 17, f"{f(-E.SNAP_TIP)}", size=2.0)
    pg.leader(sv.pt(20, yi - E.HOOK_D, E.HOOK_TOP - 0.2), sv.box[0] - 4, sv.box[3] + 10, f"钩深 {f(E.HOOK_D)}，导向斜面 45°", size=2.0)
    save(pg, "M-R5-02_面盖-背面", allp)


# =====================================================================================================
# M-R5-03 shell
# =====================================================================================================
def shell_ctfs():
    P = "底壳"
    ctf("K11", P, "外形 145.5 × 46.5（四周离琴槽 0.25）", "145.50 / 46.50", "±0.10", "卡尺")
    ctf("K12", P, "三段外底高 8.7 / 14.7 / 11.7（离槽底 0.3）", "8.70 / 14.70 / 11.70", "±0.10", "高度规")
    ctf("K13", P, "卡扣窗上沿 Z−6.40（距顶沿 4.40）", "4.40", "±0.05", "高度规；装面盖试卡")
    ctf("K14", P, "内宽 44.1（主板 43 宽）", "44.10", "+0.10 / 0", "卡尺")
    ctf("K15", P, "顶沿平面度（与面盖贴合）", "0.10", "平面度", "平台 + 塞尺")


def sheet_shell(allp):
    pg = Page()
    frame(pg, "M-R5-03", "底壳", "底壳 shell（R5-02_shell.step）", MAT_POM, "本色哑光，无外观面（装后看不见）", "首样 3 + 1 件",
          "1.5:1（俯视、A-A）  2.5:1（B-B）  6:1（详图 W）", "1/1",
          ["6. 壁厚 1.2、底厚 1.0；四角让位缺口 R4.85 以角孔中心（5.3, 5.3 等）为圆心，让开琴上 R4.6 木垫。",
           "7. 穿线孔 Ø4（X99, y24.5）为默认位置：按琴上拾音穿线孔实测位置可改，首样可先不钻，装琴时配钻。"])
    sh = part("R5-02_shell")
    s = 1.5
    v = View(pg, sh, "top", s, (34, 46), w=0.25)
    v.title("俯视（从开口看进去）", "琴头在左，G 弦侧 y0 在上", off=16)
    so = E.SHELL_OUT
    pg.dim_h(v.pt(so, E.W - so), v.pt(E.L - so, E.W - so), v.box[3] + 14, "145.50 ±0.10", ctf="K11")
    pg.dim_v(v.pt(E.L - so, so), v.pt(E.L - so, E.W - so), v.box[2] + 15, "46.50 ±0.10", ctf="K11")
    pg.dim_v(v.pt(60, E.SHELL_IN), v.pt(60, E.W - E.SHELL_IN), v.pt(60, 0)[0], "44.10 +0.10/0", ctf="K14", size=2.0)
    pg.dim_h(v.pt(so, so), v.pt(E.ZONE_X[0], so), v.box[1] - 9, f"{f(E.ZONE_X[0] - so)}", size=2.0)
    pg.dim_h(v.pt(E.ZONE_X[0], so), v.pt(E.ZONE_X[1], so), v.box[1] - 9, f"{f(E.ZONE_X[1] - E.ZONE_X[0])}", size=2.0)
    pg.dim_h(v.pt(E.ZONE_X[1], so), v.pt(E.L - so, so), v.box[1] - 9, f"{f(E.L - so - E.ZONE_X[1])}", size=2.0)
    Xs, ys = E.SCREWS[0]
    pg.leader(v.pt(Xs + E.NOTCH_R * 0.7071, ys + E.NOTCH_R * 0.7071), v.box[0] + 30, v.box[3] + 24,
              f"R{f(E.NOTCH_R)} ×4，圆心 = 角孔中心", size=2.0)
    px, py, pd = E.PICKUP_HOLE
    pg.leader(v.pt(px + 1.4, py + 1.4), v.box[0] + 150, v.box[3] + 24, "穿线孔 Ø4（默认位置）", size=2.0)
    for i, (X, _) in enumerate([(x, 0) for x in E.SNAP_X], 1):
        tag(pg, v.pt(X - 3, 0), f"W{i}", dx=-1.0, dy=-1.0)
        tag(pg, v.pt(X - 3, E.W), f"W{i + 4}", dx=-1.0, dy=3.6)
    cut_line(pg, v, 24.5, so, E.L - so, "A", up=False)
    cut_line_v(pg, v, 75.0, so, E.W - so, "B", right=True)
    # A-A
    cb = (-1.0, -24.5, -18.0, 150.0, 30.0, 0.0)
    c, polys = section(cq, sh, "Y", -24.5, +1, crop=cb)
    av = View(pg, c, "front", s, (34, 156), w=0.25)
    av.hatch(polys, angle=45, spacing=0.9, fill="#e9e9e9")
    av.title("A-A（y = 24.5）", None, size=2.6, off=5)
    for i, (x0, x1) in enumerate([(so, E.ZONE_X[0]), (E.ZONE_X[0], E.ZONE_X[1]), (E.ZONE_X[1], E.L - so)]):
        xm = x0 + 4 if i == 0 else x1 - 4 if i == 2 else (x0 + x1) / 2 - 18
        h = -E.OUT_BOT[i] - 2.0
        xl = av.box[0] - 6 if i == 0 else av.box[2] + 6 if i == 2 else av.pt(xm, 24.5)[0] + 6
        pg.dim_v(av.pt(x0 if i == 0 else x1 if i == 2 else xm, 24.5, -2), av.pt(x0 if i == 0 else x1 if i == 2 else xm, 24.5, E.OUT_BOT[i]),
                 xl, f"{f(h)} ±0.10", ctf="K12", size=2.0)
    pg.dim_v(av.pt(60, 24.5, E.IN_FLOOR[1]), av.pt(60, 24.5, E.OUT_BOT[1]), av.pt(60, 24.5)[0], "1.0", size=2.0)
    pg.text(av.box[0], av.box[3] + 6, "顶沿 Z−2.0 贴面盖背面（平面度 0.10）", 2.0)
    pg.ctf_tag(av.box[0] + 52, av.box[3] + 5.3, "K15", 1.7)
    # B-B at X = 70 (control zone)
    cb2 = (75.0, -60.0, -18.0, 150.0, 12.0, 0.0)
    c2, polys2 = section(cq, sh, "X", 75.0, +1, crop=cb2)
    bv = View(pg, c2, "left", 2.5, (282, 46), w=0.25)
    bv.hatch(polys2, angle=45, spacing=0.9, fill="#e9e9e9")
    bv.title("B-B（X = 75，控制区）", None, size=2.6, off=5)
    pg.dim_h(bv.pt(75, so, E.OUT_BOT[1]), bv.pt(75, so + E.WALL, E.OUT_BOT[1]), bv.box[3] + 5, "1.2", size=2.0)
    pg.dim_v(bv.pt(75, E.W - so, -2), bv.pt(75, E.W - so, E.OUT_BOT[1]), bv.box[2] + 6, "14.70", size=2.0)
    # detail W: window in the wall, seen from outside (near wall), X = 61
    cb3 = (55.0, -3.0, -9.0, 67.0, 0.5, -1.5)
    c3 = crop(cq, sh, cb3)
    wv = View(pg, c3, "back", 6.0, (285, 128), w=0.25)
    wv.title("详图 W（6:1）：卡扣窗 W2，从外侧看", None, size=2.6, off=5)
    xw = 61.0
    pg.dim_h(wv.pt(xw - E.WIN_W / 2, 0, E.WIN_Z[0]), wv.pt(xw + E.WIN_W / 2, 0, E.WIN_Z[0]), wv.box[3] + 5, f"{f(E.WIN_W)}", size=2.0)
    pg.dim_v(wv.pt(xw + E.WIN_W / 2, 0, -2.0), wv.pt(xw + E.WIN_W / 2, 0, E.WIN_Z[1]), wv.box[0] - 5, "4.40 ±0.05", ctf="K13", size=2.0)
    pg.dim_v(wv.pt(xw - E.WIN_W / 2, 0, E.WIN_Z[1]), wv.pt(xw - E.WIN_W / 2, 0, E.WIN_Z[0]), wv.box[2] + 6, "1.20", size=2.0)
    rows = [[f"W{i + 1}", f(X), f(E.SHELL_OUT) + "（G 侧壁）"] for i, X in enumerate(E.SNAP_X)] + \
           [[f"W{i + 5}", f(X), f(E.W - E.SHELL_OUT) + "（E 侧壁）"] for i, X in enumerate(E.SNAP_X)]
    table(pg, 330, 190, "卡扣窗（贯通侧壁）", [("编号", 10), ("中心 X", 14), ("所在壁 y", 32)], rows, size=1.7, rowh=3.0)
    rows2 = [["电池限位筋", "X 104.8–105.8、136.3–137.3，y 10–39，高 3.0"], ["台阶立壁", "X 34–35、103–104（厚 1.0）"]]
    table(pg, 282, 220, "其他", [("特征", 20), ("位置 / 尺寸", 105)], rows2, size=1.7, rowh=3.0)
    save(pg, "M-R5-03_底壳", allp)


# =====================================================================================================
# M-R5-04 knob, button cap, light pipe
# =====================================================================================================
def small_ctfs():
    ctf("K16", "旋钮", "D 孔 Ø6.0 / 平面距 4.5（推入 EC11 D 轴）", "6.00 / 4.50", "+0.04 / 0", "针规 + 卡尺；试装推入力 20–50 N")
    ctf("K17", "旋钮", "D 孔深 5.0", "5.00", "±0.10", "深度尺")
    ctf("K18", "按键帽", "杆径 Ø5.4（在 Ø5.6 孔里滑动）", "5.40", "0 / −0.05", "千分尺")
    ctf("K19", "按键帽", "总长 7.4（帽顶 +0.5 到触头 −6.9）", "7.40", "±0.05", "高度规")
    ctf("K20", "导光柱", "杆径 Ø3.0；长 10.9", "3.00 / 10.90", "0 / −0.05；±0.05", "千分尺 / 高度规")


def sheet_small(allp):
    pg = Page()
    frame(pg, "M-R5-04", "旋钮 / 按键帽 / 导光柱", "旋钮 knob ×3、按键帽 button cap ×5、导光柱 light pipe ×3",
          "旋钮、按键帽：POM-C 黑；导光柱：PC 透明（光学级棒料）", "旋钮、按键帽哑光；导光柱侧面抛光、顶面细磨雾化",
          "旋钮 3+1、按键帽 5+2、导光柱 3+2", "4:1（旋钮）  8:1（按键帽、导光柱）", "1/1",
          ["6. 旋钮滚花 24 条 R0.45 圆槽（距底 2.0 起），顶面刻线宽 0.8 深 0.6 与 D 孔平面同向。",
           "7. 导光柱用 UV 胶点在法兰上固定（禁用 502 瞬干胶，会让 PC 发白）；端面不得有划痕。"])
    knob = part("R5-03_knob")
    kv = View(pg, knob, "top", 4.0, (34, 46), w=0.25)
    kv.title("旋钮：俯视", None, size=2.6, off=5)
    pg.dim_h(kv.pt(-6.5, 6.5), kv.pt(6.5, 6.5), kv.box[3] + 6, "Ø13.0", size=2.0)
    c, polys = section(cq, knob, "Y", 0.0, +1, crop=(-8, 0, -1, 8, 8, 8))
    ks = View(pg, c, "front", 4.0, (34, 120), w=0.25)
    ks.hatch(polys, angle=45, spacing=0.9, fill="#e9e9e9")
    ks.title("旋钮：剖面（过轴线，看 D 孔平面）", None, size=2.6, off=5)
    pg.dim_v(ks.pt(6.5, 0, 0), ks.pt(6.5, 0, E.KNOB_H), ks.box[2] + 6, f"{f(E.KNOB_H)}", size=2.0)
    pg.dim_v(ks.pt(-3, 0, 0), ks.pt(-3, 0, E.BORE_DEPTH), ks.box[0] - 5, "5.00 ±0.10", ctf="K17", size=2.0)
    pg.dim_h(ks.pt(-3, 0, 0), ks.pt(E.BORE_FLAT - 3, 0, 0), ks.box[3] + 5, "4.50 +0.04/0", ctf="K16", size=2.0)
    pg.text(ks.box[0], ks.box[3] + 13, "D 孔 Ø6.00 +0.04/0（平面距 4.50）；装配：对准轴平面推到底，旋钮底离面盖 0.5。", 2.0)
    cap = part("R5-04_button_cap")
    c, polys = section(cq, cap, "Y", 0.0, +1, crop=(-5, 0, -8, 5, 5, 1))
    cv = View(pg, c, "front", 8.0, (150, 46), w=0.25)
    cv.hatch(polys, angle=45, spacing=0.9, fill="#e9e9e9")
    cv.title("按键帽：剖面", "Z 为装配高度（面盖顶面 = 0）", size=2.6, off=11)
    pg.dim_h(cv.pt(-E.CAP_STEM_D / 2, 0, E.CAP_TOP), cv.pt(E.CAP_STEM_D / 2, 0, E.CAP_TOP), cv.box[1] - 3, "Ø5.40 0/−0.05", ctf="K18", size=2.0)
    pg.dim_h(cv.pt(-E.CAP_FLANGE_D / 2, 0, -2.8), cv.pt(E.CAP_FLANGE_D / 2, 0, -2.8), cv.box[3] + 18, "Ø6.6", size=2.0)
    pg.dim_h(cv.pt(-E.CAP_PLUNGER_D / 2, 0, E.CAP_BOTTOM), cv.pt(E.CAP_PLUNGER_D / 2, 0, E.CAP_BOTTOM), cv.box[3] + 6, "Ø3.0", size=2.0)
    pg.dim_v(cv.pt(3.3, 0, E.CAP_TOP), cv.pt(3.3, 0, E.CAP_BOTTOM), cv.box[2] + 14, "7.40 ±0.05", ctf="K19", size=2.0)
    pg.dim_v(cv.pt(3.3, 0, E.CAP_TOP), cv.pt(3.3, 0, -2.0), cv.box[2] + 5, "2.5", size=2.0)
    pg.dim_v(cv.pt(-3.3, 0, -2.0), cv.pt(-3.3, 0, -2.8), cv.box[0] - 5, "0.8", size=2.0)
    lp = part("R5-05_light_pipe")
    c, polys = section(cq, lp, "Y", 0.0, +1, crop=(-3, 0, -12, 3, 3, 1))
    lv = View(pg, c, "front", 8.0, (290, 46), w=0.25)
    lv.hatch(polys, angle=45, spacing=0.9, fill="#eef6fb")
    lv.title("导光柱：剖面", None, size=2.6, off=11)
    pg.dim_h(lv.pt(-1.5, 0, 0), lv.pt(1.5, 0, 0), lv.box[1] - 3, "Ø3.00 0/−0.05", ctf="K20", size=2.0)
    pg.dim_h(lv.pt(-2.0, 0, -2.8), lv.pt(2.0, 0, -2.8), lv.box[3] + 6, "Ø4.0 × 0.8", size=2.0)
    pg.dim_v(lv.pt(2.0, 0, 0), lv.pt(2.0, 0, E.LP_BOTTOM), lv.box[2] + 6, "10.90 ±0.05", ctf="K20", size=2.0)
    pg.dim_v(lv.pt(-2.0, 0, 0), lv.pt(-2.0, 0, -2.0), lv.box[0] - 5, "2.0", size=2.0)
    notes = ["装配关系（静止状态）：",
             "• 按键帽：法兰被轻触开关弹力顶在面盖背面；帽顶高出面盖 0.5；触头离开关 0.1，按下总行程约 0.35。",
             "• 导光柱：顶面与面盖顶面平；底面离 LED 顶 0.3。",
             "• 旋钮：插到 EC11 轴上，旋钮底离面盖 0.5，D 孔底离轴端 0.5。",
             "以上间隙依赖主板高度（凸台端面 Z−12.00）和乙方选的元件高度（见 M-R5-06）。"]
    for i, t in enumerate(notes):
        pg.text(150, 182 + i * 4.6, t, 2.1, bold=(i == 0))
    save(pg, "M-R5-04_旋钮-按键帽-导光柱", allp)


# =====================================================================================================
# M-R5-05 violin pocket
# =====================================================================================================
def pocket_ctfs():
    P = "琴体槽"
    ctf("K21", P, "台阶轮廓 148.4 × 49.4 R4.2", "148.40 / 49.40", "+0.10 / 0", "卡尺；面盖放入四周有缝、不卡")
    ctf("K22", P, "台阶深 2.00（= 面盖厚，决定齐平）", "2.00", "±0.05", "深度规，测 8 点")
    ctf("K23", P, "深槽轮廓 146.0 × 47.0 + 四角木垫 R4.6", "146.00 / 47.00", "±0.10", "卡尺；底壳放入不碰")
    ctf("K24", P, "三段槽深 11 / 17 / 14", "11 / 17 / 14", "+0.20 / 0", "深度规")
    ctf("K25", P, "4 个螺钉导孔位置（对槽轮廓）", "孔表", "±0.10", "卡尺")


def sheet_pocket(allp):
    pg = Page()
    frame(pg, "M-R5-05", "琴体 CNC 槽加工图", "琴背嵌入槽（R5-06_violin_pocket.step）", "琴体背板（枫木）", "槽内不上漆；台阶面平整无毛刺",
          "按琴", "1.5:1", "1/1",
          ["6. 槽中心线 = 琴体中心线；X0（槽琴头端）距琴尾基准 u = 258.2（模块 X0 在 u 258）。琴体厚 25，槽底最少余 8。",
           "7. 深槽四角留木垫（R4.6，圆心 = 螺钉孔）；木垫与槽壁交角刀具半径 R ≤ 1.5。导孔 Ø1.6 深 10（从台阶面算）。"])
    vio = part("R5-06_violin_pocket")
    vc = crop(cq, vio, (-6.0, -55.0, -26.0, 154.0, 6.0, 1.0))
    s = 1.5
    v = View(pg, vc, "top", s, (34, 46), w=0.25)
    v.title("俯视：槽（琴背外侧看）", "细线 = 各级轮廓；点划线 = 原控制腔（继承名义值，待实测）")
    g = E.POCKET_GAP
    pg.dim_h(v.pt(-g, -g), v.pt(E.L + g, -g), v.box[1] - 4, "148.40 +0.10/0", ctf="K21", size=2.0)
    pg.dim_v(v.pt(E.L + g, -g), v.pt(E.L + g, E.W + g), v.box[2] + 6, "49.40 +0.10/0", ctf="K21", size=2.0)
    e = E.LEDGE_IN
    pg.dim_h(v.pt(e, E.W - e), v.pt(E.L - e, E.W - e), v.box[3] + 5, "146.00 ±0.10", ctf="K23", size=2.0)
    pg.dim_v(v.pt(E.L - e, e), v.pt(E.L - e, E.W - e), v.box[2] + 16, "47.00 ±0.10", ctf="K23", size=2.0)
    pg.dim_h(v.pt(-g, 30), v.pt(E.POCKET_STEP_X[0], 30), v.pt(0, 30)[1], f"{f(E.POCKET_STEP_X[0] + g)}", size=2.0)
    pg.dim_h(v.pt(E.POCKET_STEP_X[1], 30), v.pt(E.L + g, 30), v.pt(0, 30)[1], f"{f(E.L + g - E.POCKET_STEP_X[1])}", size=2.0)
    old = (35.0, E.W / 2 - 21.0, 113.0, E.W / 2 + 21.0)
    pts = [v.pt(old[0], old[1]), v.pt(old[2], old[1]), v.pt(old[2], old[3]), v.pt(old[0], old[3])]
    pg.poly(pts, 0.3, BLUE, "5 1 1 1", True)
    pg.text(pts[0][0] + 1, pts[0][1] + 3, "原控制腔 78 × 42（u 145–223，待实测）", 1.9, "start", 0, BLUE)
    Xs, ys = E.SCREWS[0]
    X2, y2 = E.SCREWS[3]
    pg.leader(v.pt(X2 - E.PAD_R * 0.7071, y2 - E.PAD_R * 0.7071), v.box[2] - 70, v.box[3] + 12, f"木垫 R{f(E.PAD_R)} ×4，圆心 = 导孔", size=2.0)
    pg.leader(v.pt(X2, y2), v.box[2] - 25, v.box[3] + 12, "导孔 Ø1.6 深 10 ×4", ctf="K25", size=2.0)
    cut_line(pg, v, 24.5, -2, E.L + 2, "A", up=False)
    # A-A
    cb = (-6.0, -24.5, -26.0, 154.0, 40.0, 1.0)
    c, polys = section(cq, vio, "Y", -24.5, +1, crop=cb)
    av = View(pg, c, "front", s, (34, 176), w=0.25)
    av.hatch(polys, angle=30, spacing=1.4, fill="#f1e2cc")
    av.title("A-A（y = 24.5，槽中心线）", None, size=2.6, off=5)
    for X, d, dx in [(15.0, 11.0, -1), (70.0, 17.0, 1), (126.0, 14.0, 1)]:
        xx = av.pt(X, 24.5)[0] + dx * 6
        pg.dim_v(av.pt(X, 24.5, 0), av.pt(X, 24.5, -d), xx, f"{f(d)} +0.20/0", ctf="K24", size=2.0)
    pg.dim_v(av.pt(-0.2, 24.5, 0), av.pt(-0.2, 24.5, -2), av.box[0] - 6, "2.00 ±0.05", ctf="K22", size=2.0)
    pg.dim_v(av.pt(154, 24.5, 0), av.pt(154, 24.5, -25), av.box[2] + 6, "25（琴体厚）", size=2.0)
    rows = [["台阶（放面盖）", "X −0.2…148.2，y −0.2…49.2，R4.2", "2.00"],
            ["深槽 1（扬声器）", f"X 1.0…{f(E.POCKET_STEP_X[0])}，y 1.0…48.0", "11"],
            ["深槽 2（控制区）", f"X {f(E.POCKET_STEP_X[0])}…{f(E.POCKET_STEP_X[1])}，y 1.0…48.0", "17"],
            ["深槽 3（电池区）", f"X {f(E.POCKET_STEP_X[1])}…147.0，y 1.0…48.0", "14"],
            ["四角木垫（保留）", "R4.6，圆心 (5.3, 5.3) (142.7, 5.3) (5.3, 43.7) (142.7, 43.7)", "到台阶面"],
            ["螺钉导孔", "Ø1.6，同上 4 个圆心", "台阶面下 10"]]
    yy = table(pg, 300, 50, "槽各级轮廓（模块坐标，X0 = 面盖琴头端）", [("层", 21), ("范围", 67), ("深度", 18)], rows, size=1.55, rowh=3.3)
    notes = ["加工建议：", "1. 先铣台阶（Ø6 刀），再铣深槽（Ø3 刀清木垫交角），", "    最后钻导孔。",
             "2. 台阶深以琴背实际表面为零点，逐点对刀。", "3. 加工后放入面盖首件试装：四周缝隙均匀；",
             "    面盖与琴背高低差 ≤ 0.10；底壳放入不碰任何槽壁。"]
    for i, t in enumerate(notes):
        pg.text(300, yy + 8 + i * 4.2, t, 2.0, bold=(i == 0))
    save(pg, "M-R5-05_琴体槽加工图", allp)


# =====================================================================================================
# M-R5-06 main board interface (for the electronics supplier)
# =====================================================================================================
def sheet_interface(allp):
    pg = Page()
    frame(pg, "M-R5-06", "主板结构接口图（给乙方）", "主板 / USB 小板 / 电池 / 扬声器 外形与高度限制", "—", "—", "—",
          "2:1（俯视）  1.5:1（B-B）", "1/1",
          ["6. 本图是外壳按此预留的建议值。乙方出 PCB 前确认或提出修改；甲方据此更新外壳后再开 CNC 首样。",
           "7. 高度均为距主板顶面（Z−12.00）的高度，或面盖坐标 Z（面盖顶面 = 0）。"])
    P = asm()
    s = 2.0
    comp = cq.Compound.makeCompound([P["pcba_pcb"], P["pcba_top_parts"], P["usb_board"], P["usb_receptacle"]])
    v = View(pg, comp, "top", s, (22, 46), w=0.22, uvbox=(0.0, -49.0, 148.0, 0.0))
    v.title("俯视：板外形、安装孔、面板件中心（从面盖方向看）", "外框 = 面盖外形；细虚线 = 底壳内壁；红虚框 = 面盖加强筋下方，元件高 ≤ 6.5")
    pg.poly([v.pt(0, 0), v.pt(148, 0), v.pt(148, 49), v.pt(0, 49)], 0.2, "#777777", None, True)
    si = E.SHELL_IN
    pg.poly([v.pt(si, si), v.pt(148 - si, si), v.pt(148 - si, 49 - si), v.pt(si, 49 - si)], 0.15, "#777777", "1.2 0.8", True)
    x0, y0, x1, y1 = E.BATTERY
    pg.poly([v.pt(x0, y0), v.pt(x1, y0), v.pt(x1, y1), v.pt(x0, y1)], 0.25, "#b07d00", "2 1", True)
    pg.text(v.pt((x0 + x1) / 2, (y0 + y1) / 2)[0], v.pt(0, (y0 + y1) / 2)[1], "电池 30 × 40 × 10", 2.1, "middle", 0, "#b07d00")
    pg.circle(*v.pt(*E.SPEAKER), E.SPEAKER_D / 2 * s, 0.25, "#555555", None, "2 1")
    pg.text(v.pt(*E.SPEAKER)[0], v.pt(*E.SPEAKER)[1], "扬声器 Ø28 × ≤5.5", 2.0, "middle")
    for x0_, y0_, x1_, y1_ in E.COVER_RIBS:
        pts = [v.pt(x0_, y0_ - 1.0), v.pt(x1_, y0_ - 1.0), v.pt(x1_, y1_ + 1.0), v.pt(x0_, y1_ + 1.0)]
        pg.poly(pts, 0.2, CTF_COLOR, "1 0.6", True)
    X0, Y0, X1, Y1 = E.PCB
    pg.dim_h(v.pt(X0, Y1), v.pt(X1, Y1), v.box[3] + 8, f"{f(X1 - X0)}（X {f(X0)}–{f(X1)}）", size=2.0)
    pg.dim_v(v.pt(X0, Y0), v.pt(X0, Y1), v.pt(X0, 0)[0] - 8, f"{f(Y1 - Y0)}", size=2.0)
    for i, (X, y) in enumerate(E.PCB_BOSSES, 1):
        tag(pg, v.pt(X + 1.4, y - 1.4), f"M{i}", dx=0.3, dy=0, c=CTF_COLOR)
    rows = []
    for i, (X, y) in enumerate(E.PCB_BOSSES, 1):
        rows.append([f"M{i}", "主板安装孔", f(X), f(y), "Ø2.2 通孔，顶面 Ø4.4 禁布（凸台）"])
    for i, (X, y) in enumerate(E.USB_BOSSES, 1):
        rows.append([f"N{i}", "USB 小板孔", f(X), f(y), "Ø1.8 通孔，顶面 Ø3.9 禁布"])
    for n, X, y in E.KNOBS:
        rows.append([n, "EC11 编码器", f(X), f(y), "轴中心"])
    for n, X, y in E.JACKS:
        rows.append([n, "3.5 mm 插座", f(X), f(y), "插口中心"])
    for n, X, y in E.BUTTONS:
        rows.append([n, "轻触开关 6×6", f(X), f(y), "按钮中心"])
    for i, (X, y) in enumerate(E.LEDS, 1):
        rows.append([f"LED{i}", "LED 0603", f(X), f(y), "发光面中心（对导光柱）"])
    rows.append(["USB-C", "立式 16P 座", f(E.USBC[0]), f(E.USBC[1]), "口中心，长边沿 y"])
    table(pg, 325, 30, "位置表（面盖坐标）", [("代号", 10), ("零件", 17), ("X", 8), ("y", 8), ("说明", 38)], rows, size=1.5, rowh=2.75)
    parts = {n: P[n] for n in ("cover", "shell", "pcba_pcb", "pcba_top_parts", "pcba_bottom_envelope", "knob_VOL", "lightpipe_1")}
    comp2, faces2 = multi_section(parts, "X", 51.0, +1, (51.0, -50.0, -18.0, 53.0, 1.0, 8.0), style_of)
    bv = View(pg, comp2, "left", 1.5, (330, 168), w=0.18)
    hatch_all(bv, faces2)
    bv.title("B-B（X = 51）各层高度（面盖坐标 Z）", None, size=2.4, off=7)
    xl = bv.box[0] - 3
    for z, t in [(5.0, "+5.0 轴端"), (0.0, "0 面盖顶"), (-2.0, "-2.0 面盖背"), (-12.0, "-12.0 板顶"), (-13.0, "-13.0 板底"),
                 (-14.5, "-14.5 背面限高"), (-15.7, "-15.7 壳内底")]:
        p = bv.pt(51, -1, z)
        pg.line(xl, p[1], bv.box[0] + 1, p[1], 0.1, "#777777")
        pg.text(xl - 0.5, p[1] + 0.6, t, 1.7, "end")
    hrows = [["主板", "顶面 Z−12.00，厚 1.0；外形 ≤ 64.5 × 43", "外形 / 孔位"],
             ["EC11 编码器", "本体 ≤ 12×12×6.5；M7 螺套顶 Z−0.5（不用螺母）；D 轴 Ø6/4.5，轴端 Z+5.0（距板顶 17.0）", "轴长要配"],
             ["3.5 mm 插座", "立式，本体 ≤ Ø9 到 Z−2.3；插口鼻 ≤ Ø6.0，口面 Z−0.2（距板顶 11.8）", "口面高度"],
             ["轻触开关", "6×6，总高 5.0（按钮顶 Z−7.0）；按键帽触头在 Z−6.9", "高度 ±0.1"],
             ["LED", "0603 顶发光，顶 ≤ Z−11.2；导光柱底 Z−10.9", ""],
             ["其他顶面元件", "≤ Z−2.5（距板顶 9.5）；红虚框内 ≤ Z−5.5（6.5）", ""],
             ["背面元件", "≤ 1.5（到 Z−14.5）；螺钉头另占 Ø3.8 × 1.3", ""],
             ["USB 小板", "X 138.5–145.2，y 14.5–34.5，顶面 Z−9.60；立式 USB-C 口面 Z−0.3（距板顶 9.3）", "口面高度"],
             ["电池", "X 106–136，y 4.5–44.5，Z −12.3…−2.3；两侧各留 2 mm 走线", ""],
             ["扬声器", "Ø28 × ≤5.5，前面朝面盖网孔（Z−2.5…−8.0）", ""]]
    yy = table(pg, 34, 156, "高度和包络限制（建议值，乙方确认）", [("项目", 22), ("限制", 148), ("关键", 20)], hrows, size=1.8, rowh=3.4)
    pg.text(34, yy + 5, "主板用 4 颗 M2×5 PT 自攻钉从板底拧进面盖凸台；USB 小板用 2 颗 M1.6×4。插拔力直接传到面盖，不经过底壳卡扣。", 2.0)
    pg.text(34, yy + 9.5, "拾音线：从琴上穿线孔进槽，经底壳穿线孔（默认 X99, y24.5，Ø4）接到主板背面的连接器；乙方定连接器位置后可改孔位。", 2.0)
    save(pg, "M-R5-06_主板结构接口图", allp)


def main():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("WQY", os.environ.get("SMARTVIO_CJK_FONT", "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"), subfontIndex=0))
    only = sys.argv[1:]
    cover_ctfs(); shell_ctfs(); small_ctfs(); pocket_ctfs()
    allp = []
    sheets = [("00", sheet_assembly), ("01", sheet_cover_top), ("02", sheet_cover_bottom), ("03", sheet_shell),
              ("04", sheet_small), ("05", sheet_pocket), ("06", sheet_interface)]
    for k, fn in sheets:
        if not only or k in only:
            fn(allp)
    if not only:
        from reportlab.pdfgen import canvas
        cv = canvas.Canvas(str(OUT / "M-R5-drawings-all.pdf"))
        for pg in allp:
            pg.pdf(cv)
        cv.save()
        (HERE / "ctf-register.json").write_text(json.dumps(CTF, ensure_ascii=False, indent=1), encoding="utf8")
        write_fai()
        print("all sheets + ctf-register.json + FAI-checklist.md")


def write_fai():
    """First-article inspection sheet generated from the CTF register (one column per sample)."""
    L = ["# R5 外壳首件检验表（FAI）", "",
         "由 `drawings.py` 根据图上的关键尺寸（CTF）自动生成，和图纸 M-R5-00…06 一致。改图后重新生成，不要手改。", "",
         "- 每个首样件都测，填实测值；超差写“NG”并拍照。",
         "- 检验环境 23 ± 2 °C；POM 件加工后放置 24 h 再测。",
         "- 琴体槽（K21–K25）由琴厂在第一把琴上测，并用面盖、底壳首件试装。", "",
         "| 编号 | 零件 | 项目 | 名义 | 公差 | 方法 | 样 1 | 样 2 | 样 3 | 判定 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for c in CTF:
        L.append(f"| {c['id']} | {c['part']} | {c['feature']} | {c['nominal']} | {c['tol']} | {c['method']} |  |  |  |  |")
    L += ["", "## 装配功能检查（每套）", "",
          "| 项目 | 标准 | 结果 |", "|---|---|---|",
          "| 面盖装入琴槽 | 四周缝隙目视均匀，不卡；面盖与琴背高低差 ≤ 0.10（塞尺 / 刀口尺） |  |",
          "| 底壳卡扣 | 8 个卡扣全部卡到位，顶沿与面盖之间无缝（0.05 塞尺塞不进）；拆装 3 次不裂 |  |",
          "| 底壳与琴槽 | 装上后底壳不碰槽壁和槽底（取下看无摩擦痕） |  |",
          "| 按键帽 | 5 个都能自由按下、自动弹回，不卡、不歪；帽顶高出面盖 0.3–0.7 |  |",
          "| 导光柱 | 顶面与面盖平（±0.1），不晃动，LED 亮时三颗亮度目视一致 |  |",
          "| 旋钮 | 推入力 20–50 N，拔出力 ≥ 20 N；旋钮底离面盖 0.3–0.7，转动不擦面盖 |  |",
          "| 插座 / USB-C | 3.5 mm 插头插到底有“咔”声；USB-C 线插到底，插拔 20 次不松 |  |",
          "| 螺钉 | 4 颗 ST2.2 沉头钉头不凸出面盖，扭矩 0.15 N·m 不打滑 |  |",
          "| 外观 | 外观面无划伤、夹痕、刀纹；刻字清晰、边缘无毛刺 |  |", "",
          "检验人：________  日期：________  结论：□ 合格 □ 让步接收 □ 不合格（附整改单）", ""]
    (HERE / "FAI-checklist.md").write_text("\n".join(L), encoding="utf8")


if __name__ == "__main__":
    main()
