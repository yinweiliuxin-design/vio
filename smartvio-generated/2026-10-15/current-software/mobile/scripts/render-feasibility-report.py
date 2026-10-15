"""Render the editable feasibility HTML into an audited, self-contained A4 PDF.

No browser, network, native application, or repeated artifact-operation marker.
The parent task already successfully marked this PDF authoring operation.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

REPO = Path(__file__).resolve().parent.parent
HTML_PATH = REPO / 'dist/reports/feasibility-20261014.html'
PDF_PATH = REPO / 'dist/reports/SmartVio-feasibility-20261014.pdf'
QA_PATH = REPO.parent / 'artifacts/feasibility-20261014/pdf-qa'
RUNTIME = Path(r'C:\Users\Admin\.cache\codex-runtimes\codex-primary-runtime\dependencies')
POPPLER = RUNTIME / 'native/poppler/Library/bin/pdftoppm.exe'
FONT = Path(r'C:\Windows\Fonts\msyh.ttc')
BOLD_FONT = Path(r'C:\Windows\Fonts\msyhbd.ttc')
INK = colors.black
RULE = colors.HexColor('#D6DED6')
TINT = colors.HexColor('#F0F4ED')
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}


@dataclass
class Node:
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    children: list = field(default_factory=list)


class TreeParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def walk(node):
    if not isinstance(node, Node):
        return
    yield node
    for child in node.children:
        yield from walk(child)


def normalized(text):
    return text.translate(str.maketrans({'\u2011': '-', '\u2013': '-', '\u2014': '-', '\u2212': '-'}))


def text_of(node):
    if isinstance(node, str):
        return normalized(node)
    if node.tag == 'br':
        return '\n'
    return ''.join(text_of(child) for child in node.children)


def inline(node):
    if isinstance(node, str):
        return escape(normalized(node))
    value = ''.join(inline(child) for child in node.children)
    if node.tag == 'br':
        return '<br/>'
    if node.tag in {'b', 'strong'}:
        return '<b>' + value + '</b>'
    if node.tag == 'a' and node.attrs.get('href', '').startswith('https://'):
        return '<link href=' + quoteattr(node.attrs['href']) + ' color="#2D5140">' + value + '</link>'
    # Internal HTML source anchors remain readable [1] labels; the PDF references
    # below contain complete clickable URLs, so no unresolved HTML destinations.
    return value


def content(node):
    return ''.join(inline(child) for child in node.children).strip()


def make_styles():
    body = ParagraphStyle('Body', fontName='MSYH', fontSize=9.7, leading=14.8,
                          alignment=TA_LEFT, wordWrap='CJK', splitLongWords=True,
                          textColor=INK, spaceAfter=7, allowWidows=0, allowOrphans=0)
    return {
        'body': body,
        'h1': ParagraphStyle('H1', parent=body, fontName='MSYHBold', fontSize=24,
                             leading=32, spaceBefore=25, spaceAfter=15, keepWithNext=True),
        'h2': ParagraphStyle('H2', parent=body, fontName='MSYHBold', fontSize=17,
                             leading=23, spaceBefore=4, spaceAfter=13, keepWithNext=True),
        'h3': ParagraphStyle('H3', parent=body, fontName='MSYHBold', fontSize=11.3,
                             leading=17, spaceBefore=9, spaceAfter=6, keepWithNext=True),
        'small': ParagraphStyle('Small', parent=body, fontSize=8.7, leading=13.1),
        'lead': ParagraphStyle('Lead', parent=body, fontSize=11.7, leading=18.5, spaceAfter=12),
        'table': ParagraphStyle('TableBody', parent=body, fontSize=8.7, leading=12.7, spaceAfter=0),
        'table_header': ParagraphStyle('TableHead', parent=body, fontName='MSYHBold',
                                       fontSize=8.7, leading=12.7, spaceAfter=0),
        'note': ParagraphStyle('Note', parent=body, backColor=TINT, borderColor=RULE,
                               borderWidth=.5, borderPadding=8, spaceBefore=8, spaceAfter=13),
        'metric': ParagraphStyle('Metric', parent=body, fontSize=9.7, leading=17, spaceAfter=0),
        'url': ParagraphStyle('URL', parent=body, fontSize=8.5, leading=12.4,
                              spaceBefore=0, spaceAfter=8, textColor=colors.HexColor('#2D5140')),
    }


def make_table(node, styles, width):
    rows = [item for item in walk(node) if item.tag == 'tr']
    data, widths = [], []
    for row_index, row in enumerate(rows):
        cells = [child for child in row.children if isinstance(child, Node) and child.tag in {'td', 'th'}]
        if not cells:
            continue
        data.append([Paragraph(content(cell), styles['table_header' if cell.tag == 'th' else 'table']) for cell in cells])
        if row_index == 0:
            for cell in cells:
                match = re.search(r'width\s*:\s*(\d+(?:\.\d+)?)%', cell.attrs.get('style', ''))
                widths.append(float(match.group(1)) / 100 if match else None)
    if not data:
        return []
    missing = sum(item is None for item in widths)
    rest = 1 - sum(item or 0 for item in widths)
    if missing:
        widths = [item if item is not None else rest / missing for item in widths]
    elif abs(sum(widths) - 1) > .001:
        widths = [item / sum(widths) for item in widths]
    table = Table(data, colWidths=[width * item for item in widths], repeatRows=1,
                  hAlign='LEFT', splitByRow=True, spaceBefore=3, spaceAfter=10)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TINT),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6), ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6), ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, 0), .7, RULE),
        ('LINEBELOW', (0, 1), (-1, -1), .35, RULE),
    ]))
    return [table]


def blocks(node, styles, width, reference_section=False):
    if isinstance(node, str):
        return []
    classes = set(node.attrs.get('class', '').split())
    if classes & {'topline', 'footer', 'toolbar'} or node.tag in {'script', 'style'}:
        return []
    if node.tag == 'table':
        return make_table(node, styles, width)
    if node.tag in {'h1', 'h2', 'h3'}:
        return [Paragraph(content(node), styles[node.tag])]
    if node.tag == 'p':
        style = 'small' if 'small' in classes or 'ref-note' in classes else 'lead' if 'lead' in classes else 'body'
        result = [Paragraph(content(node), styles[style])]
        if reference_section:
            for link in walk(node):
                uri = link.attrs.get('href', '')
                if link.tag == 'a' and uri.startswith('https://'):
                    result.append(Paragraph('<link href=' + quoteattr(uri) + '>' + escape(uri) + '</link>', styles['url']))
        return result
    if 'note' in classes:
        return [Paragraph(content(node), styles['note'])]
    if 'metrics' in classes:
        cells = []
        for metric in node.children:
            if isinstance(metric, Node):
                value = ''
                for child in metric.children:
                    if isinstance(child, Node) and child.tag == 'strong':
                        value += '<font size="18"><b>' + content(child) + '</b></font><br/>'
                    elif isinstance(child, Node):
                        value += content(child)
                cells.append(Paragraph(value, styles['metric']))
        table = Table([cells], colWidths=[width / len(cells)] * len(cells), spaceBefore=7, spaceAfter=13)
        table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), TINT), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                                   ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
                                   ('LEFTPADDING', (0, 0), (-1, -1), 9)]))
        return [table]
    if 'flow' in classes:
        return [Paragraph(content(child), styles['note']) for child in node.children if isinstance(child, Node)]
    if node.tag == 'span' and 'eyebrow' in classes:
        return [Paragraph(content(node), styles['small']), Spacer(1, 8)]
    result = []
    for child in node.children:
        result.extend(blocks(child, styles, width, reference_section))
    return result


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_pages = []

    def showPage(self):
        self.saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        count = len(self.saved_pages)
        for state in self.saved_pages:
            self.__dict__.update(state)
            self.setFont('MSYH', 8)
            self.setFillColor(colors.HexColor('#536259'))
            self.setStrokeColor(RULE)
            self.line(14 * mm, 13 * mm, A4[0] - 14 * mm, 13 * mm)
            self.drawString(14 * mm, 8.5 * mm, 'Silvio / VELLEN - 软件可行性与验收')
            self.drawRightString(A4[0] - 14 * mm, 8.5 * mm, f'{self._pageNumber} / {count}')
            super().showPage()
        super().save()


def header(canv, doc):
    canv.saveState()
    canv.setFont('MSYH', 8)
    canv.setFillColor(colors.HexColor('#536259'))
    canv.drawString(14 * mm, A4[1] - 11 * mm, 'Silvio / VELLEN - 电子小提琴 App')
    canv.drawRightString(A4[0] - 14 * mm, A4[1] - 11 * mm, '2026-10-14')
    canv.setStrokeColor(RULE)
    canv.line(14 * mm, A4[1] - 14 * mm, A4[0] - 14 * mm, A4[1] - 14 * mm)
    canv.restoreState()


def render_and_verify(sections):
    reader = PdfReader(PDF_PATH)
    page_count = len(reader.pages)
    digest = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
    render_dir = QA_PATH / ('render-' + digest[:12])
    render_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(POPPLER), '-r', '90', '-png', str(PDF_PATH), str(render_dir / 'report-page')], check=True)
    images = sorted(render_dir.glob('report-page-*.png'))
    if len(images) != page_count:
        raise RuntimeError('PDF page rendering count mismatch')
    page_texts = [page.extract_text() or '' for page in reader.pages]
    complete = '\n'.join(page_texts)
    compact = re.sub(r'\s+', '', complete)
    for required in ['172/172', '128组客户端', '4组后台', '267个音符', '275', 'ownerprivate', 'SysEx', 'HAP']:
        if required not in compact:
            raise RuntimeError('Missing expected report text: ' + required)
    actual_uris = set()
    for page in reader.pages:
        for ref in page.get('/Annots', []):
            action = ref.get_object().get('/A')
            if action and action.get('/URI'):
                actual_uris.add(str(action.get('/URI')))
    expected_uris = {item.attrs['href'] for section in sections if 'refs' in section.attrs.get('class', '').split()
                     for item in walk(section) if item.tag == 'a' and item.attrs.get('href', '').startswith('https://')}
    if not expected_uris.issubset(actual_uris):
        raise RuntimeError('PDF does not contain every complete source link')
    if any(not text.strip() for text in page_texts):
        raise RuntimeError('Empty report page')
    QA_PATH.mkdir(parents=True, exist_ok=True)
    (QA_PATH / 'extracted-text.txt').write_text(complete, encoding='utf-8')
    font = ImageFont.truetype(str(FONT), 19, index=0)
    tile_width, tile_height, columns = 360, 550, 4
    rows = (page_count + columns - 1) // columns
    contact = Image.new('RGB', (columns * tile_width, rows * tile_height), '#dde3dd')
    draw = ImageDraw.Draw(contact)
    for index, image_path in enumerate(images):
        picture = Image.open(image_path).convert('RGB')
        picture.thumbnail((tile_width - 18, tile_height - 45), Image.Resampling.LANCZOS)
        x, y = (index % columns) * tile_width, (index // columns) * tile_height
        contact.paste(picture, (x + (tile_width - picture.width) // 2, y + 32))
        draw.text((x + 12, y + 6), f'Page {index + 1} / {page_count}', fill='#26372b', font=font)
    contact_path = QA_PATH / 'contactsheet.png'
    contact.save(contact_path)
    summary = {'result': 'PASS', 'pages': page_count, 'renderedPages': len(images), 'dpi': 90,
               'sections': len(sections), 'sourceLinks': len(expected_uris), 'pdf': str(PDF_PATH),
               'pdfSha256': digest, 'htmlSha256': hashlib.sha256(HTML_PATH.read_bytes()).hexdigest(),
               'renderDirectory': str(render_dir), 'contactsheet': str(contact_path),
               'extractedText': str(QA_PATH / 'extracted-text.txt'), 'minimumTableFontPt': 8.7,
               'physicalDeviceTests': 0, 'visualInspection': 'pending-human-agent-image-review'}
    (QA_PATH / 'pdf-validation.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


def main():
    pdfmetrics.registerFont(TTFont('MSYH', str(FONT), subfontIndex=0))
    pdfmetrics.registerFont(TTFont('MSYHBold', str(BOLD_FONT), subfontIndex=0))
    pdfmetrics.registerFontFamily('MSYH', normal='MSYH', bold='MSYHBold', italic='MSYH', boldItalic='MSYHBold')
    parser = TreeParser()
    parser.feed(HTML_PATH.read_text(encoding='utf-8'))
    sections = [node for node in walk(parser.root) if node.tag == 'section' and 'sheet' in node.attrs.get('class', '').split()]
    if len(sections) != 12:
        raise ValueError('Expected the complete 12-section report')
    styles = make_styles()
    width = A4[0] - 28 * mm
    story = []
    for index, section in enumerate(sections):
        if index:
            story.append(PageBreak())
        story.extend(blocks(section, styles, width, 'refs' in section.attrs.get('class', '').split()))
    PDF_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(PDF_PATH), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=20 * mm, bottomMargin=19 * mm, title='Silvio / VELLEN 电子小提琴 App 功能可行性与验收报告',
                            author='SmartVio development review', subject='Software feasibility, protocol boundaries and acceptance evidence')
    doc.build(story, onFirstPage=header, onLaterPages=header, canvasmaker=NumberedCanvas)
    render_and_verify(sections)


if __name__ == '__main__':
    main()
