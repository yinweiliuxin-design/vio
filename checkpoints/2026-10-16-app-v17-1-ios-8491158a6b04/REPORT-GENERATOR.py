"""Build and verify the finalized V17.1 iOS audio supplement.

The root agent owns the once-only authoring marker. This artifact-local helper
does not execute that marker, mutate application source or alter the V17 report.
The renderer only writes QA PNGs; it never saves the final DOCX.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import zipfile

BASE = Path(__file__).resolve().parent
INPUT = BASE / "ios-final-validation.json"
OUTPUT = BASE / "SmartVio-V17.1-iOS-声音修复补充交付报告.docx"
QA = BASE / "word-render"
SKILL = Path("E:/codex/.codex/plugins/cache/openai-primary-runtime/documents/26.1013.11914/skills/documents")
DEPS = BASE.parent / "v17-20261016" / "docx-render-deps"
TEMP = Path("E:/codex/Temp")
TITLE = "SmartVio iOS 声音修复补充交付报告"
TAIL = "原 V17 九页交付报告保留作为历史记录，本补充报告说明 V17.1 的新增修复与验证范围。"
STATES = {"passed": "通过", "fixed": "已修复", "partial": "部分验证", "untested": "未测", "not-tested": "未测", "pending": "待测", "verified": "已验证", "failed": "未通过"}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path=INPUT):
    if not path.is_file():
        raise ValueError("缺少最终验证数据，不创建占位 DOCX")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def text(item, *keys, default="未记录"):
    if not isinstance(item, dict):
        return str(item) if item not in (None, "") else default
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return str(value)
    return default


def state(item):
    raw = text(item, "status", default="未测")
    return STATES.get(raw, raw)


def safe_url(raw):
    parts = urlsplit(str(raw))
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ValueError("交付链接必须是已确认的 HTTP 或 HTTPS 地址")
    forbidden = {"token", "access_token", "auth", "authorization", "key", "signature", "sig", "bypass"}
    host = parts.hostname + ((":" + str(parts.port)) if parts.port else "")
    query = urlencode([(key, value) for key, value in parse_qsl(parts.query) if key.lower() not in forbidden])
    return urlunsplit((parts.scheme, host, parts.path, query, parts.fragment))


def finalized():
    data = load()
    if data.get("finalized") is not True or data.get("version") != "V17.1":
        raise ValueError("仅接受 finalized true 且 version V17.1 的实际验证记录")
    if not data.get("summary") or not isinstance(data.get("fixes"), list) or not data["fixes"]:
        raise ValueError("需要实际总结与修复清单")
    for fix in data["fixes"]:
        if not fix.get("issue") or not fix.get("change") or not fix.get("status"):
            raise ValueError("修复条目必须有 issue change status")
    tests = data.get("automatedTests", {})
    if not all(type(tests.get(key)) is int and tests[key] >= 0 for key in ("passed", "failed", "skipped")):
        raise ValueError("自动测试计数必须是真实非负整数")
    if not isinstance(data.get("browserTests"), dict) or not data["browserTests"].get("summary"):
        raise ValueError("需要实际浏览器覆盖总结")
    delivery = data.get("delivery", {})
    if not re.fullmatch(r"[0-9a-fA-F]{7,40}", str(delivery.get("sourceCommit", ""))):
        raise ValueError("需要实际源码提交号")
    safe_url(delivery.get("url", ""))
    backup = delivery.get("githubBackup", {})
    if not backup.get("status"):
        raise ValueError("需要明确 GitHub 备份状态")
    if backup.get("url"):
        safe_url(backup["url"])
    if not isinstance(data.get("audioEvidence", []), list) or not isinstance(data.get("limitations", []), list):
        raise ValueError("audioEvidence 与 limitations 应为清单")
    if data.get("physicalIosTested") is True:
        raise ValueError("当前补充报告以无实体 iPhone/iPad 测试为边界，若真机证据变化请重新审查报告")
    return data


def build(data):
    from docx import Document
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Cm(21), Cm(29.7)
    section.top_margin, section.bottom_margin = Cm(1.7), Cm(1.7)
    section.left_margin, section.right_margin = Cm(1.9), Cm(1.9)
    section.footer_distance = Cm(.65)
    for name in ("Normal", "Title", "Heading 1", "Heading 2", "Footer"):
        style = doc.styles[name]
        style.font.name = "Microsoft YaHei"
        style.font.color.rgb, style.font.underline, style.font.italic = RGBColor(0, 0, 0), False, False
        rpr = style.element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = OxmlElement("w:rFonts")
            rpr.insert(0, fonts)
        for key in ("ascii", "hAnsi", "eastAsia", "cs"):
            fonts.set(qn("w:" + key), "Microsoft YaHei")
        ppr = style.element.get_or_add_pPr()
        for element in list(ppr.findall(qn("w:pBdr"))):
            ppr.remove(element)
        color = rpr.find(qn("w:color"))
        for key in ("themeColor", "themeTint", "themeShade"):
            if color is not None:
                color.attrib.pop(qn("w:" + key), None)
    normal = doc.styles["Normal"]
    normal.font.size = Pt(9.5)
    normal.paragraph_format.line_spacing = 1.16
    normal.paragraph_format.space_after = Pt(6)
    snap = OxmlElement("w:snapToGrid")
    snap.set(qn("w:val"), "false")
    normal.element.get_or_add_pPr().append(snap)
    doc.styles["Title"].font.size = Pt(22)
    doc.styles["Title"].paragraph_format.space_after = Pt(9)
    doc.styles["Heading 1"].font.size = Pt(14)
    doc.styles["Heading 1"].paragraph_format.space_before = Pt(10)
    doc.styles["Heading 1"].paragraph_format.space_after = Pt(6)

    def para(value, *, bold=False, size=None):
        p = doc.add_paragraph()
        p.paragraph_format.widow_control = True
        run = p.add_run(str(value))
        run.bold = bold
        if size:
            run.font.size = Pt(size)
        return p

    def heading(value):
        return doc.add_heading(value, 1)

    def link(label, raw_url, display):
        p = doc.add_paragraph()
        p.add_run(label + "  ")
        target = OxmlElement("w:hyperlink")
        target.set(qn("r:id"), p.part.relate_to(safe_url(raw_url), RT.HYPERLINK, is_external=True))
        run = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        color = OxmlElement("w:color")
        color.set(qn("w:val"), "245778")
        rpr.append(color)
        run.append(rpr)
        node = OxmlElement("w:t")
        node.text = display
        run.append(node)
        target.append(run)
        p._p.append(target)

    def table(headers, rows):
        widths = [4.0, 11.5, 1.7]
        table = doc.add_table(rows=1, cols=3)
        table.autofit = False
        for i, width in enumerate(widths):
            table.columns[i].width = Cm(width)
        for i, value in enumerate(headers):
            table.rows[0].cells[i].text = value
        for row in rows:
            cells = table.add_row().cells
            for i, value in enumerate(row):
                cells[i].text = str(value).rstrip("。")
        for row_index, row in enumerate(table.rows):
            trpr = row._tr.get_or_add_trPr()
            trpr.append(OxmlElement("w:cantSplit"))
            if row_index == 0:
                trpr.append(OxmlElement("w:tblHeader"))
            for col, cell in enumerate(row.cells):
                cell.width = Cm(widths[col])
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                tcpr = cell._tc.get_or_add_tcPr()
                fill = OxmlElement("w:shd")
                fill.set(qn("w:fill"), "253B52" if row_index == 0 else "F2F5F8" if row_index % 2 == 0 else "FFFFFF")
                tcpr.append(fill)
                margin = OxmlElement("w:tcMar")
                for side, value in (("top", 65), ("bottom", 65), ("left", 90), ("right", 90)):
                    node = OxmlElement("w:" + side)
                    node.set(qn("w:w"), str(value))
                    node.set(qn("w:type"), "dxa")
                    margin.append(node)
                tcpr.append(margin)
                borders = OxmlElement("w:tcBorders")
                for side in ("top", "bottom", "left", "right", "insideH", "insideV"):
                    node = OxmlElement("w:" + side)
                    for key, value in (("val", "single"), ("sz", "5"), ("color", "D9D9D9")):
                        node.set(qn("w:" + key), value)
                    borders.append(node)
                tcpr.append(borders)
                for p in cell.paragraphs:
                    p.paragraph_format.line_spacing = 1.1
                    p.paragraph_format.space_before = p.paragraph_format.space_after = Pt(0)
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if col == 2 else WD_ALIGN_PARAGRAPH.LEFT
                    for run in p.runs:
                        run.font.size = Pt(9)
                        run.bold = row_index == 0
                        run.font.color.rgb = RGBColor(255, 255, 255) if row_index == 0 else RGBColor(0, 0, 0)

    now = datetime.now(timezone.utc).replace(microsecond=0)
    props = doc.core_properties
    props.title, props.subject, props.author, props.last_modified_by = TITLE, "V17.1 iPhone iPad Safari 和应用内浏览器声音修复", "Codex", "Codex"
    props.created, props.modified, props.revision = now, now, 1
    doc.add_paragraph(TITLE, "Title")
    para("应用版本 V17.1    交付日期 " + str(data.get("date", "2026-10-16")) + "    编制 Codex    交付对象 项目负责人", size=8.5)
    para(data["summary"], bold=True)
    para("本次处理 iPhone 和 iPad 的 Safari 及应用内浏览器播放无声反馈。针对用户点击、麦克风授权、音频会话与原生媒体音量的时序修复，不能代替受影响设备的实际听音验收。")
    heading("新增缺陷与针对修复")
    table(["问题", "修复内容", "状态"], [[fix["issue"], fix["change"], state(fix)] for fix in data["fixes"]])
    heading("本轮回归结果")
    tests = data["automatedTests"]
    para(f"自动测试 {tests['passed']} 项通过，{tests['failed']} 项未通过，{tests['skipped']} 项跳过。命令 {text(tests, 'command')}。", size=9)
    para(str(data["browserTests"]["summary"]).rstrip("。") + "。", size=9)
    para(text(data["browserTests"], "platform", default="浏览器与生成设备覆盖以本轮验收记录为准"), size=8.5)
    evidence = data.get("audioEvidence", [])
    measured = [r for r in evidence if isinstance(r, dict) and type(r.get("rms")) in (int, float)]
    if measured:
        nonzero = sum(r["rms"] > 0 for r in measured)
        para(f"本轮 {len(measured)} 项 RMS 记录中 {nonzero} 项大于零。RMS 为线性幅值，证据来源以原始记录为准；浏览器内信号不等同实体扬声器已出声。", size=8.5)
    else:
        para("实际信号与录制流程按本轮验收 JSON 记录；这些结果不代替 iOS 设备端的听音确认。", size=8.5)

    h = heading("使用步骤与实际设备验收")
    h.paragraph_format.page_break_before = True
    steps = data.get("userSteps") or [
        "从本报告的最新版链接重新进入应用；在聊天内置浏览器仍无声时，复制链接到 Safari 打开。不要清空整个站点数据，以免删除本机录音。",
        "检查手机系统音量及当前耳机或扬声器输出，在应用中主动点击声音测试或播放；若提示需要再次点击，按提示重新触发，避免仅等待自动恢复。",
        "麦克风授权完成后再验证调音或录音，退出麦克风功能后检查参考音与示范播放。原生媒体音量不能由网页控制时，使用设备音量键。",
        "应用返回前台或系统中断后，主动点击恢复播放；如仍无声，记录设备型号、系统版本、宿主应用、浏览器、输出设备及声音测试信息。",
    ]
    for index, step in enumerate(steps, 1):
        para(f"{index}  {text(step, 'text', 'instruction', 'summary')}")
    heading("验证边界与待测事项")
    para("本轮未连接实体 iPhone 或 iPad。Node 行为测试、Windows 浏览器测试和移动端视口检查分别记录，不视为 iOS 真机通过；应用内 WKWebView 还受宿主应用的音频与授权配置影响。", bold=True, size=9)
    for limitation in data.get("limitations", []):
        para("• " + text(limitation, "summary", "result", "name"), size=9)
    heading("交付入口与源码备份")
    delivery, backup = data["delivery"], data["delivery"]["githubBackup"]
    link("应用访问", delivery["url"], "点击打开 V17.1 最新版")
    para("源码提交 " + delivery["sourceCommit"], size=8.5)
    if backup.get("url"):
        link("GitHub 备份", backup["url"], "点击查看私密源码备份")
    para("备份状态 " + state(backup) + "。" + text(backup, "result", "summary", "commit"), size=8.5)
    para(TAIL, size=8.5)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("SmartVio V17.1    ").font.size = Pt(8)
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), "PAGE")
    footer._p.append(field)
    QA.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    audit = audit_ooxml(data)
    manifest = {"output": str(OUTPUT), "bytes": OUTPUT.stat().st_size, "sha256": sha(OUTPUT), "validationSha256": sha(INPUT), "sourceCommit": delivery["sourceCommit"], "createdUtc": now.isoformat(), "modifiedUtc": now.isoformat(), "revision": 1, "author": "python-docx", "rootOwnsMarker": True, **audit}
    (QA / "authoring-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def audit_ooxml(data=None):
    from lxml import etree
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(OUTPUT) as archive:
        if archive.testzip() is not None:
            raise ValueError("DOCX ZIP 完整性失败")
        xml = etree.fromstring(archive.read("word/document.xml"))
        paragraphs = len(xml.xpath("//w:p", namespaces=ns))
        if paragraphs >= 100:
            raise ValueError("报告必须少于一百个段落以保持精简并避免评估版限制")
        titles = xml.xpath("//w:p[w:pPr/w:pStyle[@w:val='Title']]", namespaces=ns)
        if len(titles) != 1 or "".join(titles[0].xpath(".//w:t/text()", namespaces=ns)) != TITLE:
            raise ValueError("Title 样式或标题错误")
        if titles[0].xpath(".//w:pBdr|.//w:u[not(@w:val='none')]", namespaces=ns):
            raise ValueError("标题不得有下划线或边框")
        styles = etree.fromstring(archive.read("word/styles.xml"))
        if styles.xpath("//w:style[@w:styleId='Title']/w:rPr/w:color/@w:val", namespaces=ns) != ["000000"]:
            raise ValueError("标题必须黑色")
        all_text = "".join(xml.xpath("//w:t/text()", namespaces=ns))
        if TAIL not in all_text or any(token in all_text for token in ("TODO", "待填写", "turn0search")):
            raise ValueError("报告不完整或存在占位符")
        if any(b"Aspose" in archive.read(name) for name in archive.namelist() if name.startswith("word/") and name.endswith(".xml")):
            raise ValueError("最终 DOCX 不应包含 QA 渲染器的水印")
        if data and data["delivery"]["sourceCommit"] not in all_text:
            raise ValueError("最终源码提交号不匹配")
    return {"paragraphs": paragraphs, "titleBlack": True, "docxHasNoRendererWatermark": True}


def env():
    environment = os.environ.copy()
    environment.update(TEMP=str(TEMP), TMP=str(TEMP), PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1")
    return environment


def aspose():
    from xml.etree import ElementTree
    if not OUTPUT.is_file():
        raise ValueError("未生成最终 DOCX")
    sys.path.insert(0, str(DEPS))
    import aspose.words as aw
    before = sha(OUTPUT)
    document = aw.Document(str(OUTPUT))
    content = document.get_text()
    with zipfile.ZipFile(OUTPUT) as archive:
        xml = ElementTree.fromstring(archive.read("word/document.xml"))
        runs = [node.text for node in xml.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t") if node.text]
    if TAIL not in content or any(part not in content for part in runs) or "This document was truncated" in content:
        raise ValueError("渲染载入有缺失或评估截断")
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    if fonts.is_dir():
        settings = aw.fonts.FontSettings()
        settings.set_fonts_sources([aw.fonts.FolderFontSource(str(fonts), False)])
        document.font_settings = settings
    count = document.page_count
    if not 1 <= count <= 2:
        raise ValueError(f"补充报告实际 {count} 页，需要调整为一至两页")
    target = QA / "aspose"
    target.mkdir(parents=True, exist_ok=True)
    settings = aw.saving.ImageSaveOptions(aw.SaveFormat.PNG)
    settings.horizontal_resolution = settings.vertical_resolution = 144
    pages = []
    for index in range(count):
        settings.page_set = aw.saving.PageSet(index)
        path = target / f"page-{index + 1}.png"
        document.save(str(path), settings)
        pages.append(str(path))
    if not target.resolve().is_relative_to(QA.resolve()):
        raise ValueError("QA 目录不在预定范围")
    for old in target.glob("page-*.png"):
        if str(old) not in pages:
            old.unlink()
    if sha(OUTPUT) != before:
        raise ValueError("渲染修改了最终 DOCX")
    result = {"renderer": "Aspose Words PNG only", "evaluationRenderer": True, "pageCount": count, "pages": pages, "allSourceTextRunsPresent": True, "verifiedTextRuns": len(runs), "lastSentencePresent": True, "docxUnchangedByRenderer": True, "docxSha256": before, "visualReviewCompleted": False}
    (target / "render-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))


def render():
    audit_ooxml()
    QA.mkdir(parents=True, exist_ok=True)
    before, environment = sha(OUTPUT), env()
    dependencies = Path(sys.executable).resolve().parents[1]
    safe_paths = [dependencies / "bin" / "override", Path(sys.executable).parent]
    safe_paths.extend(path for path in (dependencies / "native").glob("**/bin") if path.is_dir())
    environment["PATH"] = os.pathsep.join(str(path) for path in safe_paths)
    canonical_target = Path(tempfile.mkdtemp(prefix="canonical-", dir=str(QA)))
    canonical = subprocess.run([sys.executable, "-B", str(SKILL / "render_docx.py"), str(OUTPUT), "--output_dir", str(canonical_target), "--verbose"], env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    (QA / "canonical-render.log").write_text(f"EXIT {canonical.returncode}\nSTDOUT\n{canonical.stdout}\nSTDERR\n{canonical.stderr}", encoding="utf-8")
    pages = sorted(canonical_target.glob("page-*.png"))
    if canonical.returncode == 0 and pages:
        result = {"renderer": "bundled canonical", "pageCount": len(pages), "pages": [str(p) for p in pages], "docxSha256": before, "docxUnchangedByRenderer": True, "visualReviewCompleted": False}
    else:
        fallback = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--aspose-worker"], env=env(), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
        (QA / "aspose-render.log").write_text(f"EXIT {fallback.returncode}\nSTDOUT\n{fallback.stdout}\nSTDERR\n{fallback.stderr}", encoding="utf-8")
        if fallback.returncode:
            raise ValueError("报告未完成完整渲染，查看 QA 日志，不交付部分页面")
        result = load(QA / "aspose" / "render-result.json")
    if sha(OUTPUT) != before or not 1 <= result["pageCount"] <= 2:
        raise ValueError("报告渲染后校验失败")
    result.update(canonicalReturnCode=canonical.returncode, canonicalOutput=str(canonical_target), usedUserLibreOffice=False)
    (QA / "render-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-input", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--marker-confirmed", action="store_true")
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--aspose-worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.aspose_worker:
        aspose()
        return
    if args.build and not args.marker_confirmed:
        parser.error("根代理未确认本 turn 唯一 authoring marker，不创建 DOCX")
    if not (args.check_input or args.build or args.render):
        parser.error("选择 --check-input --build 或 --render")
    result = {}
    if args.check_input or args.build:
        data = finalized()
        result["input"] = {"finalized": True, "sha256": sha(INPUT)}
        if args.build:
            result["build"] = build(data)
    if args.render:
        result["render"] = render()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
