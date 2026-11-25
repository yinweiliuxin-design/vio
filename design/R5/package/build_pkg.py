#!/usr/bin/env python3
"""生成《SmartVio R5 工程交付包》。

用法：python3 build_pkg.py <输出目录>
需要：pandoc、node + playwright（出 PDF）、soffice（出 Word）、poppler-utils（自检）。

来源：
  exports/        在线文档导出的 PDF / HTML（合作方案、附件1、附件2、最终方案）
  docs/           包内说明的源文件（Markdown）
  ../enclosure    外壳 V0.2 的 3D、图纸、装配说明等
  ../verify       台架验证固件、面板样机、采购清单、询价表
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
R5 = os.path.dirname(HERE)
PKG_NAME = "SmartVio-R5-工程交付包"
PKG_DATE = "2026-11-16"

CSS = """
@page { size: A4 %(orient)s; margin: 16mm 14mm 16mm 14mm; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "WenQuanYi Zen Hei", "SimSun", sans-serif;
       font-size: 10pt; line-height: 1.55; color: #1a1a1a; }
h1 { font-size: 17pt; margin: 0 0 10pt; padding-bottom: 6pt; border-bottom: 2px solid #333; }
h2 { font-size: 13pt; margin: 16pt 0 6pt; padding-bottom: 3pt; border-bottom: 1px solid #bbb; }
h3 { font-size: 11pt; margin: 12pt 0 4pt; }
h1, h2, h3 { break-after: avoid; page-break-after: avoid; }
table.files th:first-child { width: 43%%; }
table.files td:first-child { word-break: break-all; }
table { border-collapse: collapse; width: 100%%; margin: 6pt 0 10pt; font-size: 9pt; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #999; padding: 3pt 5pt; vertical-align: top; text-align: left; }
th { background: #eeeeee; }
code { font-family: "WenQuanYi Zen Hei Mono", "Consolas", monospace; font-size: 9pt; background: #f3f3f3; padding: 0 2pt; }
pre { background: #f3f3f3; padding: 6pt; font-size: 8.5pt; white-space: pre-wrap; word-break: break-all; }
pre code { background: none; padding: 0; }
ul, ol { margin: 4pt 0 8pt; padding-left: 18pt; }
li { margin: 2pt 0; }
p { margin: 4pt 0 6pt; }
img { max-width: 100%%; }
strong, th, h1, h2, h3 { -webkit-text-stroke: 0.35px #000; }
"""


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.exit("命令失败：%s\n%s\n%s" % (" ".join(cmd), r.stdout[-2000:], r.stderr[-2000:]))
    return r.stdout


def wrap_html(body, title, landscape=False, base=None, for_word=False):
    css = CSS % {"orient": "landscape" if landscape else "portrait"}
    if for_word:
        # Writer 的 HTML 导入对 CSS 边框支持不全，直接写表格属性
        body = body.replace("<table>", '<table border="1" cellspacing="0" cellpadding="4" width="100%">')
        css = css.replace("strong, th, h1, h2, h3 { -webkit-text-stroke: 0.35px #000; }", "")
    else:
        # 很短的单元格不折行（编号、阶段等）
        def short(m):
            inner = re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if 0 < len(inner) <= 6:
                return '<%s style="white-space:nowrap">%s</%s>' % (m.group(1), m.group(2), m.group(1))
            return m.group(0)
        body = re.sub(r"<(td|th)>(.*?)</(?:td|th)>", short, body, flags=re.S)
    b = '<base href="file://%s/">' % base if base else ""
    return ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>%s</title>%s'
            "<style>%s</style></head><body>%s</body></html>") % (title, b, css, body)


def md_to_body(md):
    return run(["pandoc", "-f", "gfm", "-t", "html5"], input=md)


def html_to_pdf(html, pdf, landscape=False):
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        tmp = f.name
    js = """
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage();
await p.goto('file://'+process.argv[1]);
await p.pdf({path:process.argv[2],format:'A4',landscape:process.argv[3]==='1',printBackground:true,
 displayHeaderFooter:true,headerTemplate:'<span></span>',
 footerTemplate:'<div style="font-size:8px;width:100%;text-align:center;color:#666"><span class=pageNumber></span> / <span class=totalPages></span></div>',
 margin:{top:'16mm',bottom:'16mm',left:'14mm',right:'14mm'}});
await b.close();})();
"""
    run(["node", "-e", js, tmp, pdf, "1" if landscape else "0"])
    os.unlink(tmp)


def html_to_docx(html, docx):
    d = tempfile.mkdtemp()
    src = os.path.join(d, "doc.html")
    open(src, "w", encoding="utf-8").write(html)
    run(["soffice", "--headless", "--infilter=HTML (StarWriter)", "--convert-to",
         "docx:MS Word 2007 XML", "--outdir", d, src])
    shutil.move(os.path.join(d, "doc.docx"), docx)
    shutil.rmtree(d)


def md_file(src, dst_pdf, repl=(), landscape=False, docx=False, base=None):
    md = open(src, encoding="utf-8").read()
    for a, b in repl:
        if a not in md:
            sys.exit("替换目标不存在：%s 中的 %r" % (src, a))
        md = md.replace(a, b)
    title = md.splitlines()[0].lstrip("# ").strip()
    body = md_to_body(md)
    html_to_pdf(wrap_html(body, title, landscape, base), dst_pdf, landscape)
    if docx:
        html_to_docx(wrap_html(body, title, landscape, for_word=True), dst_pdf[:-4] + ".docx")


def export_html_to_docx(src, docx, title):
    body = open(src, encoding="utf-8").read()
    body = re.sub(r'<span data-atom="mention"[^>]*>[^<]*</span>', "wei", body)
    body = body.replace('<input type="checkbox" disabled>', "☐")
    html_to_docx(wrap_html(body, title, for_word=True), docx)


# ---------------------------------------------------------------- 目录说明

# (路径, 说明)。文件夹以 / 结尾，表示整个文件夹，不逐个列文件。
TREE = [
    ("01-合作方案与附件", "本项目的依据文件。**先看这个文件夹**", [
        ("SmartVio-R5-开发合作方案.pdf", "唯一依据：产品技术要求、甲乙方分工、开发阶段与周期、各阶段验证表、放行和签字规则"),
        ("SmartVio-R5-开发合作方案.docx", "同上，Word 版，用来批注和修改"),
        ("附件1-测试方法细则.pdf", "各验证项的测试条件、仪器、判法和样机分配，用来编写阶段 4 测试计划"),
        ("附件2-电子设计审查与修改报告（模板）.docx", "乙方开始前填写交回的审查报告模板"),
        ("附件2-电子设计审查与修改报告（模板）.pdf", "同上，PDF 版，用来阅读"),
        ("附件3-电子设计待定问题清单.pdf", "乙方要关闭的 32 项待定问题（含认证相关 7 项）、7 条布局规则、保护要求、固件约束、接口与管脚预算"),
        ("附件3-电子设计待定问题清单.docx", "同上，Word 版"),
    ]),
    ("02-最终方案", "产品技术细节和设计依据", [
        ("SmartVio-R5-最终方案.pdf", "整机结构、面板与交互、电子架构、器件清单、音频路由和芯片要求 ①–⑦、电源与续航估算、风险表。分工和验收以合作方案为准"),
    ]),
    ("03-结构/R5-外壳V0.2", "外壳和琴体槽（甲方负责）。乙方按 M-R5-06 设计主板，并按装配说明总装模块", [
        ("00-外壳说明.pdf", "文件夹说明、结构概要、和乙方有关的接口尺寸、未定事项"),
        ("01-装配说明.pdf", "模块装配（乙方）和装琴（琴厂 / 甲方）的步骤、工具和扭矩"),
        ("02-首件检验表.pdf", "外壳和琴体槽的关键尺寸 K1–K25 和装配功能检查"),
        ("02-首件检验表.docx", "同上，Word 版，用来填写"),
        ("03-干涉与间隙检查结果.pdf", "3D 总装的干涉和最小间隙"),
        ("04-外壳首样询价单.pdf", "甲方发给 CNC 厂、打印厂和琴厂的询价单（材料、工艺、数量），供乙方了解"),
        ("图纸/", "7 张工程图 M-R5-00…06（各一个 PDF）和合订本 `M-R5-全部图纸合订本.pdf`。**乙方重点看 M-R5-06 主板结构接口图**"),
        ("3D模型-STEP/", "9 个 STEP：总装、装琴总装、面盖、底壳、旋钮、按键帽、导光柱、琴体槽、电子件预留包络"),
        ("3D打印-STL/", "5 个零件的 STL，3D 打印试装用"),
        ("效果图/", "6 张：顶视、装琴状态、爆炸图、剖面、面盖背面、底壳"),
    ]),
    ("03-结构/R5-面板1比1样机", "阶段 2 面板样机试拉用（甲方执行），乙方了解面板布局", [
        ("00-面板样机说明.pdf", "样机用途、打印和装配方法、贴到琴上的位置、要测什么"),
        ("template_1to1.pdf", "A4 纸 1:1 模板（另有 `template_1to1.svg` 矢量版）"),
        ("cover_plate.step", "面板 3D（另有 `cover_plate.stl` 打印用）"),
        ("knob.step", "旋钮帽 3D（另有 `knob.stl` 打印用）"),
        ("preview_top.png", "预览图 3 张：`preview_top.png`、`preview_34.png`、`preview_knob.png`"),
        ("build_mockup.py", "生成以上文件的脚本，尺寸参数在开头"),
    ]),
    ("04-固件/R5-ESP32-S3台架验证固件", "阶段 1 开发板验证可以直接用的固件（源码和已编译文件）", [
        ("README.md", "固件说明：功能、当前状态、烧录、选择编解码器、控制台命令"),
        ("WIRING.md", "开发板、编解码器模块、功放、蓝牙模块、旋钮按键的接线表"),
        ("TEST-STEPS.md", "台架测试步骤和记录表（附件1 阶段 1 各项引用的 TEST-STEPS）"),
        ("CODEC-FINDINGS.md", "ES8388 和 TLV320AIC3204 按要求 ①–⑥ 的逐项核对"),
        ("build-out/", "已编译固件：`es8388/` 和 `aic3204/` 各一套（bootloader、分区表、固件和烧录脚本）"),
        ("main/", "固件源码：音频任务、编解码器驱动、参数、控制台、按键旋钮、BLE、蓝牙模块串口、调音器"),
        ("components/", "DSP 库 `r5dsp`（固件和电脑单元测试共用）"),
        ("tests/", "电脑单元测试"),
        ("CMakeLists.txt", "ESP-IDF 工程文件；另有 `sdkconfig.defaults`、`sdkconfig.defaults.es8388`、`sdkconfig.defaults.aic3204`、`.gitignore`"),
    ]),
    ("04-固件/固件文档-PDF版", "上面 4 份 Markdown 文档的 PDF 版，内容相同，方便阅读和打印", [
        ("README-固件说明.pdf", "固件说明"),
        ("WIRING-接线表.pdf", "接线表"),
        ("TEST-STEPS-台架测试步骤.pdf", "台架测试步骤"),
        ("CODEC-FINDINGS-编解码器核对.pdf", "编解码器核对"),
    ]),
    ("05-验证与采购", "阶段 1 的采购和询价资料", [
        ("阶段1验证采购清单.pdf", "A、B 两节是开发板验证的物料和耳机（乙方参照采购）；C 节是面板样机的物料（甲方）"),
        ("蓝牙发射模块询价表.pdf", "向供应商询价的 13 个问题和样品实测记录表"),
        ("蓝牙发射模块询价表.docx", "同上，Word 版，用来填写"),
    ]),
    ("06-App联调", "App 由甲方开发", [
        ("App联调说明.pdf", "App 控制 R5 的可行性结论、台架固件的蓝牙协议、正式 BLE 接口要求、开发板联调步骤"),
    ]),
    ("07-首样前待解决问题", "和实际应用可能有差异、首样前要解决的问题", [
        ("首样前待解决问题清单.pdf", "21 项问题（含认证相关 7 项）、解决办法和负责方；标“乙方”的请逐条回复"),
    ]),
]

README_HEAD = """# SmartVio R5 工程交付包 · 目录说明

版本日期：%(date)s　　甲方（产品方）交乙方（电子厂）

SmartVio R5 是一块齐平嵌入电子小提琴琴背的智能模块（含外壳 148 × 49 mm）：主控 ESP32-S3，带编解码器、4 Ω 扬声器、蓝牙发射和约 1300 mAh 电池。本包是 R5 开发合作的全部资料。

## 一、阅读顺序

| 顺序 | 文件 | 看什么 |
|---|---|---|
| 1 | `01-合作方案与附件/SmartVio-R5-开发合作方案.pdf` | 做什么、谁负责、分几个阶段、怎么验收 |
| 2 | `01-合作方案与附件/附件3-电子设计待定问题清单.pdf` | 电子设计里要乙方定的 32 个问题 |
| 3 | `02-最终方案/SmartVio-R5-最终方案.pdf` | 技术细节和设计依据 |
| 4 | `03-结构/R5-外壳V0.2/图纸/M-R5-06_主板结构接口图.pdf` | 主板外形、安装孔和元件高度限制 |
| 5 | `07-首样前待解决问题/首样前待解决问题清单.pdf` | 首样前要解决的问题，标“乙方”的请回复 |
| 6 | `01-合作方案与附件/附件2-电子设计审查与修改报告（模板）.docx` | 看完以上资料后填写交回 |
| 7 | `01-合作方案与附件/附件1-测试方法细则.pdf` | 报价和编写测试计划时看 |

## 二、文件夹一览

| 文件夹 | 内容 | 谁用 |
|---|---|---|
| `01-合作方案与附件` | 合作方案、附件1 测试方法细则、附件2 审查报告模板、附件3 待定问题清单 | 双方 |
| `02-最终方案` | R5 最终方案 | 乙方参考 |
| `03-结构` | R5 外壳 V0.2（图纸、3D、装配说明、首件检验表）；面板 1:1 样机 | 甲方负责，乙方按接口图设计主板 |
| `04-固件` | R5 台架验证固件（源码、已编译文件、接线表、测试步骤） | 乙方阶段 1 使用 |
| `05-验证与采购` | 阶段 1 验证采购清单、蓝牙发射模块询价表 | 乙方阶段 1 使用 |
| `06-App联调` | App 联调说明 | 乙方阶段 3 定 BLE 接口时使用 |
| `07-首样前待解决问题` | 首样前待解决问题清单 | 双方 |
| `文件校验值-SHA256SUMS.txt` | 包内每个文件的 SHA-256 校验值 | 核对文件是否完整 |

文件之间不一致时，以《开发合作方案》为准。

## 三、文件清单
"""

README_TAIL = """
## 四、现状

- R5 的正式原理图和 PCB 还没有画，由乙方在阶段 3 完成。
- 台架验证固件已在 ESP-IDF v5.4.3 下编译通过，电脑单元测试通过，**还没有在实物上运行过**。
- 外壳 V0.2 是首样图；主板外形、安装孔和元件高度是甲方预留的**建议值**，乙方选定元件后确认，甲方再定稿。
- App 与实体机的联调只在仿真里通过（19 / 19），还没有用开发板实测。
- 包内的电气数值来自计算和模拟估算，**硬件实测为 0 项**；标【建议值】【待核实】的要按规格书和实测确认。
- 控制 App 由甲方开发；乙方在阶段 3 中期提供 BLE 接口文档。
- 目标认证：美国 FCC、欧盟 CE（含欧盟电池法规和网络安全要求）；面向 12 岁及以下儿童销售时另做美国 CPC。乙方的设计要求见合作方案 2.8 节。

## 五、乙方开始前请做

1. 按“阅读顺序”看完资料，填写附件2《电子设计审查与修改报告》交回甲方。
2. 对标【建议值】的数字和各阶段周期给出意见，并报价。
3. 对《首样前待解决问题清单》中标“乙方”的项目给出初步意见。
4. 双方签字确认合作方案后，阶段 1（乙方）和阶段 2（甲方）同时启动。

## 六、文件格式

| 格式 | 用什么打开 |
|---|---|
| `.pdf` | 任意 PDF 阅读器。说明文件都有 PDF 版 |
| `.docx` | Word / WPS。要填写或批注的文件另附 Word 版 |
| `.step` | 任意 3D CAD（SolidWorks、Creo、UG、Fusion 等）。**零件形状以 STEP 为准**，图纸只标关键尺寸 |
| `.stl` | 3D 打印切片软件 |
| `.md` | 固件文件夹里的说明是 Markdown 纯文本，用记事本或代码编辑器打开；`04-固件/固件文档-PDF版` 里有相同内容的 PDF |

3D 文件名里的英文（如 `R5-01_cover`）是图纸标题栏引用的零件编号，后面的中文是零件名。
"""


def build_readme(out):
    lines = [README_HEAD % {"date": PKG_DATE}]
    for folder, desc, files in TREE:
        lines.append("\n### `%s`\n\n%s。\n\n| 文件 | 内容 |\n|---|---|" % (folder, desc))
        for name, d in files:
            path = os.path.join(out, folder, name.rstrip("/"))
            if not os.path.exists(path):
                sys.exit("目录说明里列了不存在的文件：%s/%s" % (folder, name))
            lines.append("| `%s` | %s |" % (name, d))
    lines.append(README_TAIL)
    md = "\n".join(lines)
    body = md_to_body(md)
    body = re.sub(r"<table>(\s*<thead>\s*<tr[^>]*>\s*<th>文件</th>)", r'<table class="files">\1', body)
    html_to_pdf(wrap_html(body, "SmartVio R5 工程交付包 · 目录说明"), os.path.join(out, "00-先读我-目录说明.pdf"))
    return md


# ---------------------------------------------------------------- 组包

def cp(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def build(outroot):
    out = os.path.join(outroot, PKG_NAME)
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    j = os.path.join
    ex, docs = j(HERE, "exports"), j(HERE, "docs")
    enc, ver = j(R5, "enclosure"), j(R5, "verify")

    # 01 合作方案与附件
    d = j(out, "01-合作方案与附件")
    cp(j(ex, "合作方案.pdf"), j(d, "SmartVio-R5-开发合作方案.pdf"))
    export_html_to_docx(j(ex, "合作方案.html"), j(d, "SmartVio-R5-开发合作方案.docx"), "SmartVio R5 开发合作方案")
    cp(j(ex, "附件1-测试方法细则.pdf"), j(d, "附件1-测试方法细则.pdf"))
    cp(j(ex, "附件2-审查报告模板.pdf"), j(d, "附件2-电子设计审查与修改报告（模板）.pdf"))
    export_html_to_docx(j(ex, "附件2-审查报告模板.html"), j(d, "附件2-电子设计审查与修改报告（模板）.docx"),
                        "SmartVio R5 电子设计审查与修改报告（模板）")
    md_file(j(docs, "附件3-电子设计待定问题清单.md"), j(d, "附件3-电子设计待定问题清单.pdf"), docx=True)

    # 02 最终方案
    cp(j(ex, "最终方案.pdf"), j(out, "02-最终方案", "SmartVio-R5-最终方案.pdf"))

    # 03 结构 / 外壳
    d = j(out, "03-结构", "R5-外壳V0.2")
    os.makedirs(d)
    md_file(j(docs, "外壳说明.md"), j(d, "00-外壳说明.pdf"))
    md_file(j(enc, "ASSEMBLY.md"), j(d, "01-装配说明.pdf"), repl=[("`FAI-checklist.md`", "《首件检验表》")])
    md_file(j(enc, "FAI-checklist.md"), j(d, "02-首件检验表.pdf"), landscape=True, docx=True)
    md_file(j(docs, "干涉与间隙检查结果.md"), j(d, "03-干涉与间隙检查结果.pdf"))
    md_file(j(enc, "RFQ-外壳首样.md"), j(d, "04-外壳首样询价单.pdf"), repl=[
        ("附件：`step/`、`stl/`、`drawings/M-R5-drawings-all.pdf`、`FAI-checklist.md`",
         "附件：`3D模型-STEP/`、`3D打印-STL/`、`图纸/M-R5-全部图纸合订本.pdf`、《首件检验表》"),
        ("`step/R5-06_violin_pocket.step`", "`3D模型-STEP/R5-06_violin_pocket_琴体槽.step`"),
        ("填 `FAI-checklist.md` 随货交付", "填《首件检验表》随货交付"),
        ("首件检验表（`FAI-checklist.md` 填好的）", "填好的首件检验表"),
    ])
    for f in sorted(os.listdir(j(enc, "drawings"))):
        if f.endswith(".pdf"):
            cp(j(enc, "drawings", f), j(d, "图纸", f.replace("M-R5-drawings-all", "M-R5-全部图纸合订本")))
    cn = {"R5-00_assembly": "模块总装", "R5-00_assembly_in_violin": "装琴总装", "R5-01_cover": "面盖",
          "R5-02_shell": "底壳", "R5-03_knob": "旋钮", "R5-04_button_cap": "按键帽", "R5-05_light_pipe": "导光柱",
          "R5-06_violin_pocket": "琴体槽", "R5-90_electronics_envelopes": "电子件包络"}
    for sub, dst in (("step", "3D模型-STEP"), ("stl", "3D打印-STL")):
        for f in sorted(os.listdir(j(enc, sub))):
            stem, ext = os.path.splitext(f)
            cp(j(enc, sub, f), j(d, dst, "%s_%s%s" % (stem, cn[stem], ext)))
    pv = {"01_top": "1-顶视", "02_installed": "2-装琴状态", "03_exploded": "3-爆炸图", "04_section": "4-剖面",
          "05_cover_underside": "5-面盖背面", "06_shell": "6-底壳"}
    for k, v in pv.items():
        cp(j(enc, "preview", k + ".png"), j(d, "效果图", "R5外壳-%s.png" % v))

    # 03 结构 / 面板样机
    d = j(out, "03-结构", "R5-面板1比1样机")
    os.makedirs(d)
    for f in sorted(os.listdir(j(ver, "mockup"))):
        if f != "README.md" and os.path.isfile(j(ver, "mockup", f)):
            cp(j(ver, "mockup", f), j(d, f))
    md_file(j(ver, "mockup", "README.md"), j(d, "00-面板样机说明.pdf"), base=j(ver, "mockup"))

    # 04 固件
    d = j(out, "04-固件", "R5-ESP32-S3台架验证固件")
    files = run(["git", "ls-files", "verify/firmware"], cwd=R5).split("\n")
    for f in filter(None, files):
        cp(j(R5, f), j(d, os.path.relpath(f, "verify/firmware")))
    d2 = j(out, "04-固件", "固件文档-PDF版")
    os.makedirs(d2)
    for src, name in (("README.md", "README-固件说明"), ("WIRING.md", "WIRING-接线表"),
                      ("TEST-STEPS.md", "TEST-STEPS-台架测试步骤"), ("CODEC-FINDINGS.md", "CODEC-FINDINGS-编解码器核对")):
        md_file(j(ver, "firmware", src), j(d2, name + ".pdf"), landscape=(src in ("CODEC-FINDINGS.md", "TEST-STEPS.md")))

    # 05 验证与采购
    d = j(out, "05-验证与采购")
    os.makedirs(d)
    md_file(j(ver, "PURCHASE-LIST.md"), j(d, "阶段1验证采购清单.pdf"), repl=[
        ("# R5 验证采购清单", "# R5 阶段 1 验证采购清单"),
        ("按 `BT-TX-INQUIRY.md`（资料库中为 `BT-TX-INQUIRY-蓝牙发射模块询价表.md`）筛选", "按《蓝牙发射模块询价表》筛选"),
        ("具体接法见 `firmware/WIRING.md`", "具体接法见台架验证固件的 `WIRING.md`"),
        ("（数值见 `firmware/WIRING.md`）", "（数值见台架验证固件的 `WIRING.md`）"),
        ("详见 `mockup/README.md`（模型文件、打印参数、装配方法）", "详见 `03-结构/R5-面板1比1样机/00-面板样机说明.pdf`（模型文件、打印参数、装配方法）"),
    ])
    md_file(j(ver, "BT-TX-INQUIRY.md"), j(d, "蓝牙发射模块询价表.pdf"), docx=True)

    # 06、07
    os.makedirs(j(out, "06-App联调"))
    md_file(j(docs, "App联调说明.md"), j(out, "06-App联调", "App联调说明.pdf"))
    os.makedirs(j(out, "07-首样前待解决问题"))
    md_file(j(docs, "首样前待解决问题清单.md"), j(out, "07-首样前待解决问题", "首样前待解决问题清单.pdf"), landscape=True)

    # 00 目录说明
    build_readme(out)

    # 校验值
    rows = []
    for root, _, fs in os.walk(out):
        for f in fs:
            p = j(root, f)
            rows.append((os.path.relpath(p, out), hashlib.sha256(open(p, "rb").read()).hexdigest()))
    rows.sort()
    with open(j(out, "文件校验值-SHA256SUMS.txt"), "w", encoding="utf-8") as f:
        f.write("SmartVio R5 工程交付包 %s 文件校验值（SHA-256）\n" % PKG_DATE)
        f.write("核对方法：Windows 用 certutil -hashfile 文件名 SHA256；Linux / macOS 用 sha256sum -c 本文件（先删掉前三行）\n\n")
        for p, h in rows:
            f.write("%s  %s\n" % (h, p))

    # 压缩包
    zpath = j(outroot, "%s-%s.zip" % (PKG_NAME, PKG_DATE.replace("-", "")))
    if os.path.exists(zpath):
        os.unlink(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, fs in os.walk(out):
            for f in sorted(fs):
                p = j(root, f)
                z.write(p, os.path.relpath(p, outroot))
    print("文件数：%d（含校验值文件 %d）" % (len(rows), len(rows) + 1))
    print("输出：", zpath, "%.1f MB" % (os.path.getsize(zpath) / 1e6))
    return out, zpath


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(os.path.abspath(sys.argv[1]))
