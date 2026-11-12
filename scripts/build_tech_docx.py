# -*- coding: utf-8 -*-
"""生成《技术说明：这个项目是怎么做出来的》Word 文档。

给项目作者本人看的代码导读：技术栈地图、代码从哪来、逐文件导读、
核心原理最小示例、动手改、答辩怎么讲、名词表。
"""
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"D:\作业\docs\技术说明-这个项目是怎么做出来的.docx"

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x6B, 0x6B, 0x6B)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
CODE = RGBColor(0x2A, 0x2A, 0x2A)
FONT = "微软雅黑"
MONO = "Consolas"

doc = Document()

# ---------- 页面 ----------
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.top_margin = Cm(2.2)
sec.bottom_margin = Cm(2.0)
sec.left_margin = Cm(2.4)
sec.right_margin = Cm(2.4)

# ---------- 默认样式 ----------
normal = doc.styles["Normal"]
normal.font.name = FONT
normal.font.size = Pt(10.5)
normal.font.color.rgb = INK
normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.line_spacing = 1.4
normal.paragraph_format.space_after = Pt(3)


def _shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _borders(table, color="D9D9D9", size="6"):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def _cell_text(cell, text, bold=False, size=9.5, color=INK, mono=False):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1.5)
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.line_spacing = 1.15
    run = p.add_run(text)
    fname = MONO if mono else FONT
    run.font.name = fname
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def table(headers, rows, widths=None, header_bg="1F4E79", first_col_bold=False, mono_cols=(), caption=None):
    if caption:
        para(caption, size=9, color=MUTED, space_after=2, keep=True)
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t)
    trPr = t.rows[0]._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    tblHeader.set(qn("w:val"), "true")
    trPr.append(tblHeader)
    mar = OxmlElement("w:tblCellMar")
    for side, w in (("top", "30"), ("bottom", "30"), ("left", "90"), ("right", "90")):
        el = OxmlElement("w:" + side)
        el.set(qn("w:w"), w)
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    t._tbl.tblPr.append(mar)
    for i, h in enumerate(headers):
        c = t.rows[0].cells[i]
        _shade(c, header_bg)
        _cell_text(c, h, bold=True, size=9.5, color=RGBColor(0xFF, 0xFF, 0xFF))
    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            _cell_text(cells[i], v, bold=(first_col_bold and i == 0), size=9.5, mono=(i in mono_cols))
            if i == 0 and first_col_bold:
                _shade(cells[i], "F2F5F9")
    t.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    t._tbl.tblPr.append(layout)
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        trPr.append(cs)
    if widths:
        scale = 16.2 / sum(widths) if sum(widths) > 16.2 else 1.0
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(round(w * scale, 2))
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(round(w * scale, 2))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(15)
    run.font.bold = True
    run.font.color.rgb = ACCENT
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "8")
    bottom.set(qn("w:space"), "3")
    bottom.set(qn("w:color"), "1F4E79")
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(11.5)
    run.font.bold = True
    run.font.color.rgb = INK
    return p


def _add_rich(p, text, size=10.5, color=INK, bold=False):
    """支持 `反引号` 内联等宽代码。"""
    parts = text.split("`")
    for i, seg in enumerate(parts):
        if not seg:
            continue
        r = p.add_run(seg)
        mono = i % 2 == 1
        r.font.name = MONO if mono else FONT
        r._element.rPr.rFonts.set(qn("w:eastAsia"), MONO if mono else FONT)
        r.font.size = Pt(size - 0.5 if mono else size)
        r.font.bold = bold
        r.font.color.rgb = CODE if mono else color


def para(text, size=10.5, color=INK, bold=False, space_after=4, indent=0, keep=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    if keep:
        p.paragraph_format.keep_with_next = True
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    _add_rich(p, text, size=size, color=color, bold=bold)
    return p


def bullet(lead, rest="", size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.35
    for txt, b in ((lead, True), (rest, False)):
        if not txt:
            continue
        _add_rich(p, txt, size=size, bold=b)
    return p


_NUM = [0]


def _reset_num():
    _NUM[0] = 0


def numbered(lead, rest="", size=10.5):
    """手写序号，避免 Word 自动编号在多组之间连号。"""
    _NUM[0] += 1
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.75)
    p.paragraph_format.first_line_indent = Cm(-0.75)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.35
    for txt, b in ((f"{_NUM[0]}. ", False), (lead, True), (rest, False)):
        if not txt:
            continue
        _add_rich(p, txt, size=size, bold=b)
    return p


def _no_split(t):
    trPr = t.rows[0]._tr.get_or_add_trPr()
    cs = OxmlElement("w:cantSplit")
    cs.set(qn("w:val"), "true")
    trPr.append(cs)


def callout(text, bg="EAF1F8", color=INK):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, color="C9DBEE", size="8")
    _no_split(t)
    c = t.rows[0].cells[0]
    _shade(c, bg)
    _cell_text(c, text, size=10.5, color=color)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def code_block(lines, caption=None):
    """等宽代码块：单格表格 + 浅灰底 + 细边框。"""
    if caption:
        para(caption, size=9, color=MUTED, space_after=2, keep=True)
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, color="DDDDDD", size="4")
    _no_split(t)
    c = t.rows[0].cells[0]
    _shade(c, "F6F6F4")
    c.text = ""
    first = True
    for ln in lines:
        p = c.paragraphs[0] if first else c.add_paragraph()
        first = False
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.05
        run = p.add_run(ln if ln else " ")
        run.font.name = MONO
        run._element.rPr.rFonts.set(qn("w:eastAsia"), MONO)
        run.font.size = Pt(8.8)
        run.font.color.rgb = CODE
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def code(text, caption=None):
    """便捷版代码块：直接传多行字符串。"""
    code_block(text.split("\n"), caption=caption)


def _rich(item):
    """只对显式 **加粗** 前缀做处理，避免同组列表里只有部分行加粗。"""
    import re as _re
    m = _re.match(r"\*\*(.+?)\*\*(.*)$", item, _re.S)
    if m:
        lead = m.group(1).rstrip("：:")
        rest = m.group(2)
        return lead + "：", rest
    return "", item.replace("**", "")


def bullets(items, size=10.5):
    for it in items:
        lead, rest = _rich(it)
        bullet(lead, rest, size=size)


def steps(items, size=10.5):
    _reset_num()
    for it in items:
        lead, rest = _rich(it)
        numbered(lead, rest, size=size)


def page_break():
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)


# ---------- 页脚 ----------
footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = footer_p.add_run("技术说明 · Steam 市场观察　|　F:\\steam-market-insight")
fr.font.name = FONT
fr._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
fr.font.size = Pt(8.5)
fr.font.color.rgb = MUTED

# ======================================================================
# 正文分片：按顺序执行同目录的 _tech_pN.py，最后统一保存
# ======================================================================
import os

_here = os.path.dirname(os.path.abspath(__file__))
for _name in ("_tech_p1.py", "_tech_p2.py", "_tech_p3.py", "_tech_p4.py", "_tech_p5.py", "_tech_p6.py"):
    _path = os.path.join(_here, _name)
    if not os.path.exists(_path):
        continue
    with open(_path, encoding="utf-8") as fh:
        exec(compile(fh.read(), _path, "exec"), globals())

os.makedirs(os.path.dirname(OUT), exist_ok=True)
doc.save(OUT)
print("saved", OUT)
