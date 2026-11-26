"""Compose the R5 installed-on-violin showcase image from the CAD renders and the violin photo.

Usage: python3 compose_showcase.py <photo.jpg> <top.png> <hero.png> <hero2.png> <out_dir>
  photo : the back of the white electric violin (square, scaled to 2000 px here)
  top   : render.html view=top, pxmm=24 (head up, G-string edge on the right, transparent background)
  hero  : render.html view=hero, 2400 x 1500 (az -100, el 36): 3/4 view
  hero2 : render.html view=hero, 2400 x 1200 (az -62, el 9): low view along the back, shows what stands proud
Outputs: r5-v03-on-violin-showcase.jpg (2560 x 1600) and r5-v03-on-violin-full.jpg (2000 x 2000).
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

photo_path, top_path, hero_path, hero2_path, out_dir = sys.argv[1:6]
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
RPX, MARG = 24.0, 8.0                 # render scale (px/mm) and margin (mm) of the top view
PPX = 3.18                            # photo scale (px/mm) at 2000 px
# module centre in the photo: on the centre line of the violin's centre beam (x 897..1100 at this height),
# at the height of the original control plate centre (the new pocket covers the original hole)
CX, CY = 998.5, 1415.0
OLD_PLATE = (930, 1282, 1100, 1552)   # original control plate incl. its shadow (x0, y0, x1, y1), painted out first

photo = Image.open(photo_path).convert("RGB").resize((2000, 2000), Image.LANCZOS)
top = Image.open(top_path).convert("RGBA")
hero = Image.open(hero_path).convert("RGBA")
hero2 = Image.open(hero2_path).convert("RGBA")


def paint_out_plate(img):
    """Replace the old plate with the beam surface: copy the clean rows just above (beam edge straight,
    x ~1100) and just below (lower bout, all white), blended across the lower right cut-out corner."""
    a = np.asarray(img).astype(np.float32).copy()
    x0, y0, x1, y1 = OLD_PLATE
    above, below = a[y0 - 2, x0:x1].copy(), a[y1, x0:x1].copy()
    for y in range(y0, y1):
        t = np.clip((y - 1450) / 25.0, 0, 1)
        a[y, x0:x1] = above * (1 - t) + below * t
    rng = np.random.default_rng(3)
    a[y0:y1, x0:x1] += rng.normal(0, 1.4, (y1 - y0, x1 - x0, 3))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def grade(mod, seed, grain):
    """Match the render to the photo: slightly lift the blacks (camera flare) and add sensor grain."""
    a = np.asarray(mod).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3:4]
    rgb = rgb * 0.93 + 10.0 * (al > 0)
    rng = np.random.default_rng(seed)
    rgb = rgb + rng.normal(0, grain, rgb.shape) * (al > 0)
    return Image.fromarray(np.concatenate([np.clip(rgb, 0, 255), al], axis=2).astype(np.uint8), "RGBA")


def place(base, scale_px_mm, cx, cy, blur, grain):
    """Paste the top render at scale_px_mm with the cover centre at (cx, cy)."""
    k = scale_px_mm / RPX
    m = top.resize((round(top.size[0] * k), round(top.size[1] * k)), Image.LANCZOS)
    m = grade(m, 7, grain)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    x0, y0 = round(cx - m.size[0] / 2), round(cy - m.size[1] / 2)
    out = base.convert("RGBA")
    out.alpha_composite(m, (x0, y0))
    return out.convert("RGB")


clean = paint_out_plate(photo)
full = place(clean, PPX, CX, CY, 0.45, 1.8)
full.save(f"{out_dir}/r5-v03-on-violin-full.jpg", quality=93)

# close-up: the photo region ×3 (soft), the module rendered at the same scale
UP = 3
crop_box = (868, 1128, 1129, 1702)
crop = clean.crop(crop_box).resize(((crop_box[2] - crop_box[0]) * UP, (crop_box[3] - crop_box[1]) * UP), Image.BICUBIC)
crop = crop.filter(ImageFilter.UnsharpMask(radius=2, percent=35, threshold=2))
ccx, ccy = (CX - crop_box[0]) * UP, (CY - crop_box[1]) * UP
CPX = PPX * UP
close = place(crop, CPX, ccx, ccy, 0.6, 2.2)

# ---- sheet
W, H = 2560, 1600
BG, INK, MUTED, LEAD = (236, 238, 240), (28, 32, 36), (96, 104, 112), (192, 57, 43)
sheet = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(sheet)
F = lambda s: ImageFont.truetype(FONT, s)
f_title, f_sub, f_lab, f_small, f_tiny = F(46), F(24), F(27), F(21), F(19)

d.text((40, 26), "SmartVio R5 · 装琴效果图", font=f_title, fill=INK)
d.text((640, 44), "按外壳 V0.3 首样图（M-R5-00…06）的 3D 模型渲染，合成在实拍琴身上 · 模块齐平嵌入琴背中央梁，距琴尾 110–258 mm",
       font=f_sub, fill=MUTED)

PANEL_Y, PANEL_H = 110, 1450
# A: whole violin
A_box = (560, 0, 1450, 2000)
lv = full.crop(A_box)
s_a = PANEL_H / lv.size[1]
lv = lv.resize((round(lv.size[0] * s_a), PANEL_H), Image.LANCZOS)
ax = 40
sheet.paste(lv, (ax, PANEL_Y))
bx0, by0 = ax + (crop_box[0] - A_box[0]) * s_a, PANEL_Y + (crop_box[1] - A_box[1]) * s_a
bx1, by1 = ax + (crop_box[2] - A_box[0]) * s_a, PANEL_Y + (crop_box[3] - A_box[1]) * s_a
d.rectangle([bx0, by0, bx1, by1], outline=LEAD, width=3)

# B: close-up
s_b = PANEL_H / close.size[1]
cl = close.resize((round(close.size[0] * s_b), PANEL_H), Image.LANCZOS)
bx = ax + lv.size[0] + 40
sheet.paste(cl, (bx, PANEL_Y))
d.rectangle([bx, PANEL_Y, bx + cl.size[0], PANEL_Y + PANEL_H], outline=(200, 205, 210), width=2)
d.line([(bx1, by0), (bx, PANEL_Y)], fill=(205, 165, 160), width=2)
d.line([(bx1, by1), (bx, PANEL_Y + PANEL_H)], fill=(205, 165, 160), width=2)


def cpt(X, y):
    """Cover coordinates (X from the head end, y from the G-string edge) -> sheet pixels in panel B."""
    px = ccx + (24.5 - y) * CPX
    py = ccy + (X - 74.0) * CPX
    return bx + px * s_b, PANEL_Y + py * s_b


LX = bx + cl.size[0] + 70
callouts = [
    ((5.3, 43.7), "4 颗沉头木螺钉", ["ST2.2 不锈钢，拧进琴体木垫；面盖压在", "2 mm 台阶上，与琴背齐平"]),
    ((17.0, 24.5), "扬声器", ["28 mm、4 Ω，默认最大约 1 W；", "91 孔网罩，底壳隔出密封背腔"]),
    ((50.5, 40.0), "3 颗指示灯", ["导光柱与面盖齐平：", "电源 · 蓝牙 · 输出 / 旋钮值"]),
    ((51.0, 9.0), "3 个旋钮", ["VOL 音量 · TONE 音色 · FX 效果；", "Ø13，高出琴背约 7 mm，与 App 同步"]),
    ((69.0, 40.0), "5 个按键", ["PWR · BT · MODE · FX · MIX；", "按键帽高出约 0.5 mm，方便盲摸"]),
    ((79.0, 24.5), "4 个 3.5 mm 插孔", ["PHONES 耳机 · AUX 伴奏 ·", "LINE 音箱 · SEND 干声"]),
    ((121.0, 34.0), "电池（面盖下）", ["约 1300 mAh；戴耳机练琴约 7–10 h"]),
    ((142.0, 24.5), "USB-C", ["充电（约 445 mA）、固件升级和 USB 诊断"]),
]
ty = PANEL_Y + 20
for (X, y), title, lines in callouts:
    sx, sy = cpt(X, y)
    d.ellipse([sx - 7, sy - 7, sx + 7, sy + 7], fill=LEAD, outline=(255, 255, 255), width=2)
    d.line([(sx, sy), (LX - 16, ty + 16)], fill=LEAD, width=2)
    d.text((LX, ty), title, font=f_lab, fill=INK)
    for i, t in enumerate(lines):
        d.text((LX, ty + 40 + i * 30), t, font=f_small, fill=MUTED)
    ty += 62 + 30 * len(lines) + 28

# C: two renders of the module installed in a piece of the centre beam
CX0, CW = 1960, 560


def render_panel(img, box, y, caption):
    c = img.crop(box)
    c = c.resize((CW, round(c.size[1] * CW / c.size[0])), Image.LANCZOS)
    g = np.linspace(0, 1, c.size[1])[:, None, None]
    grad = (np.array([214, 218, 223]) * (1 - g) + np.array([238, 240, 242]) * g) * np.ones((1, c.size[0], 1))
    p = Image.fromarray(grad.astype(np.uint8)).convert("RGBA")
    p.alpha_composite(c)
    sheet.paste(p.convert("RGB"), (CX0, y))
    d.rectangle([CX0, y, CX0 + CW, y + c.size[1]], outline=(200, 205, 210), width=2)
    y += c.size[1] + 12
    for t in caption:
        d.text((CX0, y), t, font=f_small, fill=MUTED)
        y += 30
    return y


yy = render_panel(hero, (250, 300, 2150, 1300), PANEL_Y, ["3/4 视角：琴头在左，旋钮靠 G 弦一侧"])
yy = render_panel(hero2, (300, 360, 2300, 960), yy + 26,
                  ["贴着琴背看：只有旋钮（约 7 mm）和按键帽", "（约 0.5 mm）高出，其余与琴背齐平"])
yy += 40
d.text((CX0, yy), "尺寸与做法", font=f_lab, fill=INK); yy += 48
for t in ["面盖 148 × 49 × 2 mm，哑光黑；首样 CNC POM-C",
          "琴体槽：2 mm 台阶放面盖，下面三段",
          "  扬声器段 / 功能区 / 电池段深 11 / 17 / 15 mm",
          "中央梁宽 60–65 mm，槽两侧各余 5 mm 以上",
          "底壳卡在面盖下面，四周和底部不碰琴槽",
          "主控 ESP32-S3：有线耳机、外放、蓝牙耳机、",
          "  安卓网页 App（电量、切换、调音器）"]:
    d.text((CX0, yy), t, font=f_small, fill=MUTED); yy += 32

note = ["效果示意：模块按 3D 模型渲染，琴身为实拍照片，按 3.18 px/mm",
        "等比合成。刻字填白；指示灯颜色和面盖量产材料以定稿为准；",
        "主板接口为建议值，待乙方确认。"]
for i, t in enumerate(note):
    d.text((CX0, PANEL_Y + PANEL_H - 3 * 28 + i * 28), t, font=f_tiny, fill=(120, 126, 132))
sheet.save(f"{out_dir}/r5-v03-on-violin-showcase.jpg", quality=92)
print("ok", sheet.size, "close-up", close.size, "panel B width", cl.size[0], "callout x", LX)
