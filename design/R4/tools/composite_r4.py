"""Composite the rendered R4 module onto the user's violin photo and build one showcase image.

Usage: python3 composite_r4.py <photo.jpg> <module_top.png> <out_dir>
Module render: 12.72 px/mm, 5 mm margin, screen up = toward the head, jacks on the left.
Photo scale: 3.18 px/mm (existing 78 mm control plate = 248 px); cavity centre at (1015.5, 1414).
"""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

photo_path, module_path, out_dir = sys.argv[1:4]
RENDER_PXMM, PHOTO_PXMM = 12.72, 3.18
CX, CY = 1015.5, 1414.0
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

photo = Image.open(photo_path).convert("RGB")
module = Image.open(module_path).convert("RGBA")


def tone(mod, seed):
    """Darken the matte POM to match the photo's exposure and add matching sensor grain."""
    a = np.asarray(mod).astype(np.float32)
    rgb, al = a[..., :3], a[..., 3:4]
    lum = rgb.mean(axis=2, keepdims=True)
    glow = (rgb[..., 2:3] - rgb[..., 0:1]) > 40  # keep the lit light pipe
    dark = rgb * 0.62
    rgb = np.where(glow, rgb, dark)
    rng = np.random.default_rng(seed)
    rgb = rgb + rng.normal(0, 2.2, rgb.shape) * (al > 0)
    out = np.concatenate([np.clip(rgb, 0, 255), al], axis=2).astype(np.uint8)
    del lum
    return Image.fromarray(out, "RGBA")


def place(base, mod, scale, cx, cy, shadow_px):
    """Scale the module render onto base with its centre at (cx, cy) and a soft cast shadow."""
    w, h = mod.size
    m = mod.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    m = tone(m, 7).filter(ImageFilter.GaussianBlur(0.35 * scale / 0.25))
    x0, y0 = round(cx - m.size[0] / 2), round(cy - m.size[1] / 2)
    alpha = m.split()[3]
    sh = Image.new("L", base.size, 0)
    sh.paste(alpha, (x0 + round(shadow_px[0]), y0 + round(shadow_px[1])))
    sh = sh.filter(ImageFilter.GaussianBlur(shadow_px[2]))
    b = np.asarray(base).astype(np.float32)
    k = 1 - 0.42 * (np.asarray(sh).astype(np.float32) / 255)[..., None]
    base = Image.fromarray(np.clip(b * k, 0, 255).astype(np.uint8))
    base.paste(m, (x0, y0), m)
    return base, (x0, y0, m.size[0], m.size[1])


# 1. Full photo composite at photo scale.
scale_full = PHOTO_PXMM / RENDER_PXMM
full, _ = place(photo.copy(), module, scale_full, CX, CY, (3, 7, 5))
full.save(f"{out_dir}/r4-on-violin-full.jpg", quality=93)

# 2. Close-up: upsample the photo region ×3 and place a sharper module render at 9.54 px/mm.
UP = 3
crop_box = (855, 1115, 1175, 1715)
crop = photo.crop(crop_box).resize(((crop_box[2] - crop_box[0]) * UP, (crop_box[3] - crop_box[1]) * UP), Image.BICUBIC)
crop = crop.filter(ImageFilter.UnsharpMask(radius=2, percent=40, threshold=2))
ccx, ccy = (CX - crop_box[0]) * UP, (CY - crop_box[1]) * UP
close, (mx, my, mw, mh) = place(crop, module, PHOTO_PXMM * UP / RENDER_PXMM, ccx, ccy, (8, 18, 12))
CPXMM = PHOTO_PXMM * UP


def cpt(X, yd):
    """Cover coordinates (X along from the wheel end, drawing y across) → close-up pixels."""
    return (ccx - (yd - 24.5) * CPXMM, ccy + (X - 74) * CPXMM)


# 3. Showcase sheet.
W, H = 2400, 1600
BG, INK, MUTED, LEAD = (236, 238, 240), (28, 32, 36), (96, 104, 112), (192, 57, 43)
sheet = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(sheet)
f_title = ImageFont.truetype(FONT, 46)
f_sub = ImageFont.truetype(FONT, 24)
f_lab = ImageFont.truetype(FONT, 27)
f_small = ImageFont.truetype(FONT, 21)

# Left: whole violin (crop around the instrument).
lv = full.crop((560, 0, 1470, 2000))
lv = lv.resize((round(lv.size[0] * 1490 / 2000), 1490), Image.LANCZOS)
sheet.paste(lv, (40, 90))
lv_x, lv_y, lv_s = 40, 90, 1490 / 2000
# Box on the whole-violin view showing the close-up area.
bx0, by0 = lv_x + (crop_box[0] - 560) * lv_s, lv_y + crop_box[1] * lv_s
bx1, by1 = lv_x + (crop_box[2] - 560) * lv_s, lv_y + crop_box[3] * lv_s
d.rectangle([bx0, by0, bx1, by1], outline=LEAD, width=3)

# Middle: close-up.
cw = round(close.size[0] * 1490 / close.size[1])
cl = close.resize((cw, 1490), Image.LANCZOS)
cl_x, cl_y, cl_s = 790, 90, 1490 / close.size[1]
sheet.paste(cl, (cl_x, cl_y))
d.rectangle([cl_x, cl_y, cl_x + cw, cl_y + 1490], outline=(200, 205, 210), width=2)
d.line([(bx1, by0), (cl_x, cl_y)], fill=(200, 160, 155), width=2)
d.line([(bx1, by1), (cl_x, cl_y + 1490)], fill=(200, 160, 155), width=2)

d.text((40, 22), "SmartVio R4 · 装琴效果图", font=f_title, fill=INK)
d.text((640, 40), "按你的实拍照片合成：模块取代原黑色控制盒，下杯嵌入原腔体（78 × 47 mm）", font=f_sub, fill=MUTED)

# Right: callouts.
LX = cl_x + cw + 60


def callout(X, yd, y_text, title, sub):
    px, py = cpt(X, yd)
    sx, sy = cl_x + px * cl_s, cl_y + py * cl_s
    d.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=LEAD)
    d.line([(sx, sy), (LX - 14, y_text + 16)], fill=LEAD, width=2)
    d.text((LX, y_text), title, font=f_lab, fill=INK)
    d.text((LX, y_text + 38), sub, font=f_small, fill=MUTED)


callout(5.3, 5.3, 130, "4 颗不锈钢木螺钉", "固定在琴背，A2 无磁")
callout(15, 21, 270, "3 颗状态灯", "电源、蓝牙等状态指示")
callout(35, 4.5, 410, "3 个拇指滚轮", "VOL 音量 · TONE 音色 · FX 效果；右侧拇指缺口拨动")
callout(52, 25, 550, "5 个按键", "FX · MODE · MIX · PWR · BT")
callout(66.4, 41.5, 690, "4 个 3.5 mm 插孔", "FX SEND · LINE OUT · AUX · PHONES")
callout(98, 9, 830, "USB-C", "充电")
callout(132, 21, 970, "扬声器出声槽", "不插耳机时外放；插入 PHONES 自动切到耳机")

d.text((LX, 1150), "尺寸", font=f_lab, fill=INK)
for i, t in enumerate(["上盖 148 × 49 mm，凸出琴背 3.85 mm", "下杯 77 × 45 mm 嵌入原腔，总高 24.75 mm",
                       "哑光黑 POM，字符雕刻 0.15 mm", "滚轮一端朝琴头"]):
    d.text((LX, 1196 + i * 36), t, font=f_small, fill=MUTED)
for i, t in enumerate(["合成示意：琴体为你的实拍照片，", "模块为 R4 CAD 渲染，按 3.18 px/mm 等比放置；", "未做实物装配。"]):
    d.text((LX, 1440 + i * 32), t, font=f_small, fill=MUTED)
sheet.save(f"{out_dir}/r4-on-violin-showcase.jpg", quality=92)
print("ok", sheet.size, (mx, my, mw, mh))
