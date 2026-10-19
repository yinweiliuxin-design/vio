"""Build the R4 board drawing set: cover + one page per board (layout top/bottom + 3D), as HTML for Chromium to print."""
import json, os, re, shutil, sys

PLOTS, OUT = sys.argv[1], sys.argv[2]
os.makedirs(f"{OUT}/img", exist_ok=True)
info = json.load(open(f"{PLOTS}/boardinfo.json"))

def drc(b):
    d = json.load(open(f"{PLOTS}/{b}.drc.json"))
    v = d.get("violations", [])
    err = sum(1 for x in v if x.get("severity") == "error")
    return err, len(v) - err, len(d.get("unconnected_items", [])), len(d.get("schematic_parity", []))

# Silkscreen and outline colours are pale in KiCad's theme; darken them for a white page.
RECOLOR = {"#F2EDA1": "#1F2328", "#E8B2A7": "#1F2328", "#D0D2CD": "#000000"}
def svg(b, side):
    s = open(f"{PLOTS}/{b}-{side}.svg").read()
    for a, c in RECOLOR.items():
        s = re.sub(a, c, s, flags=re.I)
    open(f"{OUT}/img/{b}-{side}.svg", "w").write(s)
    return f"img/{b}-{side}.svg"

BOARDS = [
    ("SmartVio-main-r3-linked", "主板", "STM32H743、ESP32、音频芯片、电源与充电全部在这块板上",
     "布线未完成，不能投板。R5 改单板后已停止，只作参考。"),
    ("SmartVio-usb-r4", "USB 子板", "USB-C 插座、ESD 与过压保护（TPD2S300 / TPD2S703 / USBLC6），经 16 芯 FPC 接主板", ""),
    ("SmartVio-audio-r4", "音频插座板", "4 个 3.5 mm 插座 J102 / J201 / J202 / J301，经 AUDIO6、AUDIO4 两条 FPC 接主板",
     "1 条警告：J3404 封装与库里的版本不一致（R4 改过焊盘，属预期）。"),
    ("SmartVio-cover-r4", "上盖板", "5 个按键、3 个滚轮电位器、3 颗指示灯、扬声器 LS901，经 KEYS6、COVER6、POTS3 三条 FPC 接主板", ""),
    ("SmartVio-fpc-usb16-r4", "FPC-USB16", "USB 子板 ↔ 主板，16 芯：VBUS、受保护 5 V、USB 数据、故障与关断信号", ""),
    ("SmartVio-fpc-audio6-r4", "FPC-AUDIO6", "音频插座板 ↔ 主板，6 芯：耳机 L/R、线路 L/R、耳机插入检测、地", ""),
    ("SmartVio-fpc-audio4-r4", "FPC-AUDIO4", "音频插座板 ↔ 主板，4 芯（R4 新增）：效果返回 L/R、SEND、地", ""),
    ("SmartVio-fpc-keys6-r4-bus", "FPC-KEYS6", "上盖板 ↔ 主板，6 芯：BT / FX / MIX / MODE 四个按键、FX 滚轮、地", ""),
    ("SmartVio-fpc-cover6-r4", "FPC-COVER6", "上盖板 ↔ 主板，6 芯：3 颗指示灯、电源键、扬声器 +/−", ""),
    ("SmartVio-fpc-pots3-r4", "FPC-POTS3", "上盖板 ↔ 主板，3 芯：VOL、TONE 两个滚轮和供电", ""),
]

rows, pages = [], []
for b, name, use, note in BOARDS:
    i = info[f"{b}.kicad_pcb"]
    err, warn, unc, par = drc(b)
    status = "通过（0 错误）" if err == 0 and unc == 0 else f"未完成：{err} 错误、{unc} 处未连接"
    if warn and err == 0:
        status += f"，{warn} 条警告"
    spec = f"{i['w']} × {i['h']} mm · {i['layers']} 层 · 板厚 {i['thick']} mm · 元件 {i['fps']}（正面 {i['top']} / 背面 {i['bot']}）"
    rows.append(f"<tr><td>{name}</td><td>{use}</td><td>{i['w']} × {i['h']}</td><td>{i['layers']} / {i['thick']}</td>"
                f"<td>{i['fps']}</td><td class='{'bad' if err or unc else 'ok'}'>{status}</td></tr>")
    for side in ("3dtop", "3dbot"):
        shutil.copy(f"{PLOTS}/{b}-{side}.png", f"{OUT}/img/{b}-{side}.png")
    pages.append(f"""
<section class="page">
  <header><h2>{name} <span class="file">{b}.kicad_pcb</span></h2>
  <p class="spec">{spec}</p><p class="spec">{use}。DRC：{status}。{note}</p></header>
  <div class="grid">
    <figure><div class="frame"><img src="{svg(b, 'top')}"></div><figcaption>正面布线（F.Cu 红 + 丝印 + 外形）</figcaption></figure>
    <figure><div class="frame"><img src="{svg(b, 'bot')}"></div><figcaption>背面布线（B.Cu 蓝 + 丝印 + 外形，镜像，从背面看）</figcaption></figure>
    <figure><div class="frame dark"><img src="img/{b}-3dtop.png"></div><figcaption>3D 正面（KiCad 渲染，未含元件 3D 模型）</figcaption></figure>
    <figure><div class="frame dark"><img src="img/{b}-3dbot.png"></div><figcaption>3D 背面</figcaption></figure>
  </div>
</section>""")

html = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>SmartVio 电路板图纸 R4</title>
<style>
@page {{ size: A4 landscape; margin: 10mm; }}
body {{ font-family: 'WenQuanYi Zen Hei', sans-serif; color: #1f2328; margin: 0; }}
.page {{ page-break-after: always; height: 188mm; display: flex; flex-direction: column; }}
h1 {{ font-size: 22pt; margin: 0 0 4mm; }} h2 {{ font-size: 15pt; margin: 0; }}
.file {{ font-size: 9pt; color: #6a737d; font-weight: normal; margin-left: 4mm; }}
.spec {{ font-size: 9.5pt; margin: 1.2mm 0 0; color: #3a4046; }}
.grid {{ flex: 1; display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 3mm; margin-top: 3mm; min-height: 0; }}
figure {{ margin: 0; display: flex; flex-direction: column; min-height: 0; }}
.frame {{ flex: 1; border: 0.3mm solid #c9ced3; display: flex; align-items: center; justify-content: center; min-height: 0; padding: 2mm; background: #fff; }}
.frame.dark {{ background: #f6f7f9; padding: 2mm; }}
.frame img {{ width: 100%; height: 100%; object-fit: contain; }}
figcaption {{ font-size: 8.5pt; color: #6a737d; margin-top: 1mm; }}
table {{ border-collapse: collapse; width: 100%; font-size: 9pt; margin-top: 3mm; }}
th, td {{ border: 0.25mm solid #c9ced3; padding: 1.4mm 2mm; text-align: left; vertical-align: top; }}
th {{ background: #f1f3f5; }} td.bad {{ color: #b42318; font-weight: 600; }} td.ok {{ color: #1a7f37; }}
.note {{ font-size: 10pt; line-height: 1.55; margin: 0 0 2mm; }}
.warn {{ border-left: 1.2mm solid #d4a72c; background: #fff8e1; padding: 2mm 3mm; font-size: 10pt; line-height: 1.55; }}
</style></head><body>
<section class="page">
  <h1>SmartVio 电路板图纸（R4，目前最新已画的版本）</h1>
  <p class="note">2026-10-19 · 由 KiCad 10.0.6 从仓库 <b>design/R4/kicad/</b> 的原生文件直接导出；DRC 为本次导出时重新运行的结果。</p>
  <div class="warn"><b>先看这里：</b>这是 R4 的多板方案（1 块主板 + 3 块子板 + 6 条 FPC）。R5 已决定改成一块单板，<b>R5 电路板还没有画</b>，要等你确认芯片方案（R5-A / R5-B）等待定项后才开始。
  R4 子板和 FPC 都已通过 DRC；<b>R4 主板布线未完成，不能投板</b>。R4 的电源、充电、耳机检测等电路会搬到 R5 单板上，所以这套图仍有参考价值。</div>
  <table><tr><th>板</th><th>用途</th><th>尺寸 mm</th><th>层数 / 板厚 mm</th><th>元件</th><th>DRC（本次重跑）</th></tr>{''.join(rows)}</table>
  <p class="note" style="margin-top:3mm">后面每块板一页：正面布线、背面布线、3D 正面、3D 背面。最后附 R4 原理图（25 页，ERC 0 错误）。3D 图只显示焊盘和走线，没有装元件 3D 模型。</p>
</section>
{''.join(pages)}
<section class="page" style="justify-content:center;align-items:center"><h1>附：R4 原理图（25 页）</h1>
<p class="note" style="max-width:200mm">第 1 页为总图（各分图框），第 2–25 页为各功能分图，ERC 0 错误。<br>注意：这套原理图从 R3 起就是用网络标签连接的——每个引脚只挂网络名、没有画连线，所以看起来像按功能分页的元件排列；连接关系以网络名为准。R5 单板原理图会按常规画法重画（画连线、按信号流排布）。</p></section>
</body></html>"""
open(f"{OUT}/boards.html", "w").write(html)
print("ok", len(pages))
