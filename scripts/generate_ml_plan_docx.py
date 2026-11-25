# -*- coding: utf-8 -*-
"""Generate a readable Word proposal for the Steam ML prediction module."""

from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_BREAK
import os

OUT = "Steam机器学习预测方案.docx"

NAVY = "102A43"
INK = "243B53"
MUTED = "627D98"
AMBER = "F2A93B"
AMBER_LIGHT = "FFF7E6"
BLUE = "2F6FED"
BLUE_LIGHT = "EEF4FF"
TEAL = "18A999"
TEAL_LIGHT = "E9F8F5"
RED = "E25D5D"
RED_LIGHT = "FDEDED"
LINE = "D9E2EC"
PAPER = "FFFFFF"
SOFT = "F7F9FC"

FONT = "微软雅黑"


def set_run_font(run, size=None, bold=None, color=None, italic=None):
    run.font.name = FONT
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rfonts.set(qn(attr), FONT)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def para(text="", size=10.5, bold=False, color=INK, align=None,
         space_before=0, space_after=6, line=1.5, style=None):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    if align is not None:
        p.alignment = align
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if text:
        r = p.add_run(text)
        set_run_font(r, size=size, bold=bold, color=color)
    return p


def add_runs(p, parts, size=10.5, color=INK):
    """parts: list of (text, bold, color or None)"""
    for text, bold, c in parts:
        r = p.add_run(text)
        set_run_font(r, size=size, bold=bold, color=c or color)


def h1(num, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(f"{num}  ")
    set_run_font(r, size=17, bold=True, color=AMBER)
    r = p.add_run(text)
    set_run_font(r, size=17, bold=True, color=NAVY)
    # bottom rule
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "10")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), LINE)
    pbdr.append(bottom)
    pPr.append(pbdr)
    return p


def h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, size=12.5, bold=True, color=TEAL)
    return p


def h3(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, size=11, bold=True, color=NAVY)
    return p


def bullet(text, level=0, size=10.5):
    style = "List Bullet" if level == 0 else "List Bullet 2"
    p = doc.add_paragraph(style=style)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.4
    add_runs(p, [(text, False, INK)], size=size)
    return p


def numbered(text, size=10.5):
    p = doc.add_paragraph(style="List Number")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.4
    add_runs(p, [(text, False, INK)], size=size)
    return p


def shade(cell, color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    tcPr.append(shd)


def set_cell_margins(cell, top=100, bottom=100, left=120, right=120):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = tcPr.first_child_found_in("w:tcMar")
    if tcMar is None:
        tcMar = OxmlElement("w:tcMar")
        tcPr.append(tcMar)
    for tag, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = tcMar.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            tcMar.append(node)
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, color=LINE, size=4):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), str(size))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def set_col_widths(table, widths_cm):
    table.autofit = False
    for row in table.rows:
        for idx, width in enumerate(widths_cm):
            if idx < len(row.cells):
                row.cells[idx].width = Cm(width)


def cell_text(cell, text, size=9.5, bold=False, color=INK, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.25
    if align is not None:
        p.alignment = align
    add_runs(p, [(text, bold, color)], size=size)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER


def add_table(headers, rows, widths, font_size=9.5, header_fill=NAVY,
              highlight_rows=None, first_col_bold=True):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False
    set_table_borders(table)
    table.rows[0].height = Cm(0.8)
    for i, htext in enumerate(headers):
        c = table.rows[0].cells[i]
        shade(c, header_fill)
        set_cell_margins(c, 100, 100, 110, 110)
        cell_text(c, htext, size=font_size, bold=True, color="FFFFFF",
                  align=WD_ALIGN_PARAGRAPH.CENTER)
    # repeat the header row when a table spans pages
    trPr = table.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:tblHeader"))
    highlight_rows = highlight_rows or []
    for r_idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, text in enumerate(row):
            c = cells[i]
            if r_idx in highlight_rows:
                shade(c, BLUE_LIGHT)
            elif r_idx % 2 == 1:
                shade(c, SOFT)
            set_cell_margins(c, 90, 90, 110, 110)
            cell_text(c, text, size=font_size,
                      bold=(first_col_bold and i == 0),
                      align=WD_ALIGN_PARAGRAPH.LEFT if i else WD_ALIGN_PARAGRAPH.LEFT)
    set_col_widths(table, widths)
    # prevent row split
    for row in table.rows:
        trPr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trPr.append(cant)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def callout(title, body_lines, accent=AMBER, fill=AMBER_LIGHT, width=16.4):
    """Single-cell callout with a colored left rule; avoids half-page color blocks."""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.rows[0].cells[0].width = Cm(width)
    # borders: only the left edge is a thick accent rule
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        if edge == "left":
            el.set(qn("w:sz"), "24")
            el.set(qn("w:color"), accent)
        else:
            el.set(qn("w:sz"), "2")
            el.set(qn("w:color"), fill)
        el.set(qn("w:space"), "0")
        borders.append(el)
    tblPr.append(borders)
    cell = table.rows[0].cells[0]
    shade(cell, fill)
    set_cell_margins(cell, 140, 140, 180, 180)
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    add_runs(p, [(title, True, NAVY)], size=10.5)
    for line in body_lines:
        p2 = cell.add_paragraph()
        p2.paragraph_format.space_after = Pt(2)
        p2.paragraph_format.line_spacing = 1.35
        add_runs(p2, [(line, False, INK)], size=10)
    # do not split a short callout across pages
    trPr = table.rows[0]._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return table


def add_page_number_footer(section):
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    r = p.add_run("Steam 机器学习预测方案 · v0.1    |    ")
    set_run_font(r, size=8, color=MUTED)
    r = p.add_run("第 ")
    set_run_font(r, size=8, color=MUTED)
    fld1 = OxmlElement("w:fldChar"); fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText"); instr.set(qn("xml:space"), "preserve"); instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar"); fld2.set(qn("w:fldCharType"), "end")
    run_el = p.add_run()._r
    run_el.append(fld1); run_el.append(instr); run_el.append(fld2)
    r = p.add_run(" 页")
    set_run_font(r, size=8, color=MUTED)


def add_header(section):
    header = section.header
    header.is_linked_to_previous = False
    p = header.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("STEAM 游戏市场洞察平台")
    set_run_font(r, size=8, bold=True, color=NAVY)
    r = p.add_run("    /    机器学习模块 · 方案讨论稿")
    set_run_font(r, size=8, color=MUTED)
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), LINE)
    pbdr.append(bottom)
    pPr.append(pbdr)


def add_cover():
    # top accent
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_table_borders(t, color=AMBER, size=0)
    t.rows[0].cells[0].width = Cm(16.5)
    t.rows[0].height = Cm(0.18)
    shade(t.rows[0].cells[0], AMBER)

    para("STEAM MARKET OBSERVATORY  /  MACHINE LEARNING MODULE",
         size=8.5, bold=True, color=TEAL, space_before=26, space_after=18)

    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.12
    r = p.add_run("Steam 新游\n12 个月高热度预测")
    set_run_font(r, size=30, bold=True, color=NAVY)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(26)
    r = p.add_run("方案说明与实施计划")
    set_run_font(r, size=15, bold=False, color=AMBER)

    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(30)
    p.paragraph_format.line_spacing = 1.6
    r = p.add_run("从“预测到底指什么”讲起：\n"
                  "固定 12 个月窗口 · 时间外回测 · 可解释模型 · 静态页面离线推理")
    set_run_font(r, size=11.5, color=MUTED)

    callout("先读这一句",
            ["这不是“预测爆款”或“预测销量”。",
             "它只回答：一款刚发售的游戏，在只看发售时信息的条件下，12 个月内达到 1,000 条评价的概率有多大。"],
            accent=BLUE, fill=BLUE_LIGHT)

    meta = [
        ("项目", "Steam 游戏市场洞察平台 · 机器学习模块"),
        ("文档", "方案讨论稿（未开始编码）"),
        ("版本", "v0.1"),
        ("日期", "2026-11-19"),
        ("决策", "确认第 9 节后，再进入实现"),
    ]
    table = doc.add_table(rows=0, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for k, v in meta:
        cells = table.add_row().cells
        cells[0].width = Cm(3.0)
        cells[1].width = Cm(13.5)
        set_cell_margins(cells[0], 80, 80, 0, 80)
        set_cell_margins(cells[1], 80, 80, 0, 80)
        cell_text(cells[0], k, size=9.5, bold=True, color=MUTED)
        cell_text(cells[1], v, size=9.5, color=INK)

    doc.add_page_break()


def add_reading_route():
    h1("00", "阅读路线")
    para("这份文档按“先判断要不要做，再决定怎么做”的顺序写。你不需要一次读完。",
         size=10.5, color=MUTED, space_after=10)
    rows = [
        ("5 分钟", "第 0、1、8、9 节", "看清预测定义、成本和需要你拍板的事"),
        ("15 分钟", "全文", "理解 A/B/C/D 的取舍和 A0 的完整执行方案"),
        ("只关心能不能做", "第 1、3、4、9 节", "判断数据是否支持、值不值得投入"),
        ("只关心页面效果", "第 5、6 节", "看模型实验室长什么样、怎么交互"),
    ]
    add_table(["时间", "看哪里", "你会得到什么"], rows,
              [3.0, 4.6, 8.6], font_size=9.5)
    callout("本文的结论",
            ["先做 A0：5,000 款随机样本 + 固定 12 个月标签 + 逻辑回归主模型。",
             "有信心再扩到 20,000 款；如果 5,000 款都没有信号，停止，不硬做预测。"],
            accent=TEAL, fill=TEAL_LIGHT)


def add_section_0():
    h1("0", "一页看懂")
    rows = [
        ("预测什么", "一款游戏发售后 12 个月内，评价数是否达到 1,000 条", "高热度，不是销量"),
        ("用什么预测", "发售时的类型、genres、免费/付费、年份、首发价（可选）", "只用 t0 已知信息"),
        ("怎么验证", "训练 2015–2021，验证 2022，测试 2023–2025", "时间外回测"),
        ("主模型", "L2 逻辑回归", "可解释、可校准、可离线"),
        ("挑战者", "HistGradientBoosting", "只有明显更好才替换"),
        ("样本", "5,000 款随机分层样本；150k 只用于打分", "不抓 150k 标签"),
        ("成本", "顺利 5–7 个工作日；histogram 不可用 +2–4 天", "主要成本是标签"),
        ("结论", "先 A0；没信号就转 B 历史回测", "不包装成未来预测"),
    ]
    add_table(["项目", "方案", "一句话"], rows,
              [3.0, 9.4, 3.8], font_size=9.2, highlight_rows=[0, 7])
    callout("最重要的边界",
            ["预测单位：一款游戏。",
             "预测时点：发售日。",
             "结果窗口：发售后 12 个月。",
             "输出：概率，不是保证；不是因果；不是 2027 年市场预言。"],
            accent=RED, fill=RED_LIGHT)


def add_section_1():
    h1("1", "“预测”到底体现在哪")
    para("严格说，一个模型要同时满足下面四条，才配叫预测。缺一条，更准确的说法是分类、关联分析或历史回测。",
         size=10.5, space_after=8)
    rows = [
        ("1", "t0 只用当时已知的信息", "发售日之后的评价数、口碑、折扣不能进特征"),
        ("2", "结果是 t0 之后才发生的", "不是拿当前累计评价当“未来”"),
        ("3", "时间外评估", "用过去年份训练，用未来年份测试；不是随机切分"),
        ("4", "输出给没见过的对象", "一款新游戏，而不是训练集里的旧样本"),
    ]
    add_table(["条件", "要求", "本方案怎么做"], rows,
              [1.2, 6.2, 9.0], font_size=9.5)

    h2("1.1 本方案怎么满足")
    bullet("t0：只用发售时的类型、genres、免费/付费、年份、首发价；")
    bullet("结果窗口：统一取发售后 12 个月内的评价数；")
    bullet("时间外：2015–2021 训练，2022 验证，2023–2025 测试；")
    bullet("输出：页面输入一款“新游戏”的发售时信息，输出 12 个月高热度概率。")

    h2("1.2 哪些做法不算预测")
    rows = [
        ("用当前累计评价 ≥1000 做标签", "老游戏天然评价多；没有固定窗口"),
        ("随机切分训练/测试", "同年市场环境泄漏；不是未来"),
        ("只做特征重要性", "这是解释，不是预测"),
        ("页面放一个概率仪表盘", "没有时间外验证，仪表盘只是装饰"),
        ("把当前价/当前折扣放进特征", "用了发售后信息，属于泄漏"),
    ]
    add_table(["做法", "为什么不算"], rows,
              [7.0, 9.4], font_size=9.5)
    callout("一句话判断",
            ["如果模型用的是“今天才知道的结果”，去预测“今天已经发生的事”，那不是预测。",
             "A0 的区别是：标签是发售后 12 个月才发生的结果，特征只来自发售日。"],
            accent=BLUE, fill=BLUE_LIGHT)


def add_section_2():
    h1("2", "为什么不做“爆款/销量预测”")
    para("不是不想做，是当前数据不支持。硬做会变成“看起来像 AI，实际上在编”。",
         size=10.5, space_after=8)
    rows = [
        ("销量/收入", "Steam 不公开单款销量；没有可靠标签", "不能做回归/分类"),
        ("发行商/营销", "没有发行商、宣发预算、愿望单、首周曝光", "无法解释爆款"),
        ("历史时点", "只有当前快照，没有每款游戏 12 个月时点", "无法做严格窗口"),
        ("在线人数", "只有 10 条快照", "无法训练时间序列"),
        ("评价样本", "2,000 条，覆盖率 1.3%，按推荐数选取", "有选择偏差"),
    ]
    add_table(["缺什么", "现实", "后果"], rows,
              [3.4, 8.0, 5.0], font_size=9.5)
    callout("能诚实回答的问题",
            ["在只看发售时信息的条件下，哪些类型/价格/年份的游戏更可能达到 12 个月 1,000 条评价？",
             "这是“高热度概率”，不是“会不会爆”，更不是“能赚多少钱”。"],
            accent=TEAL, fill=TEAL_LIGHT)


def add_section_3():
    h1("3", "所有可选方案对比")
    para("A 不是唯一选项。下面把可做的都摆出来，按“预测含金量、成本、页面效果、答辩风险”比较。",
         size=10.5, space_after=8)
    rows = [
        ("A. 12 个月高热度", "高", "5k 标签；3–7 天", "高", "中", "首选"),
        ("B. 当前快照回测", "低", "1–2 天", "中高", "高（措辞）", "可做，改名"),
        ("C. 评论情感", "中（评论级）", "1–2 天", "中", "中", "快速真 ML"),
        ("C2. 早期评论→口碑", "中高（要时间戳）", "3–7 天", "中高", "高（数据）", "先验证"),
        ("D. 相似游戏", "无（推荐）", "1–2 天", "高", "低", "最佳副模块"),
        ("E. 聚类分群", "无", "1 天", "中", "低", "补充洞察"),
        ("O. 市场空白", "无", "0.5 天", "中高", "低", "洞察，不是 ML"),
        ("F. 价格回归", "低", "1–2 天", "低", "高（泄漏）", "不做"),
        ("G. 年度供给预测", "低", "0.5 天", "低", "高（16 个点）", "不做"),
    ]
    add_table(["方案", "预测含金量", "成本", "页面效果", "答辩风险", "结论"], rows,
              [4.4, 2.3, 3.0, 2.0, 2.5, 2.2], font_size=8.8,
              highlight_rows=[0, 4])
    para("说明：A 的“高”是严格意义上的固定窗口预测；B 的“低”不是模型弱，而是标签不是未来结果。",
         size=9, color=MUTED, space_after=6)

    h2("3.1 我的排序")
    rows = [
        ("答辩必须有“预测”", "A0", "唯一严格站得住；B 只能叫回测"),
        ("页面效果最好", "D + A0", "相似游戏负责交互，A0 负责预测"),
        ("成本最低", "O / E / D", "0.5–2 天；但不是预测"),
        ("只有 2–3 天", "B + D", "B 改名“历史回测”"),
        ("不想碰爬虫", "C + D", "评论级真 ML + 相似推荐"),
    ]
    add_table(["目标", "推荐", "理由"], rows,
              [4.2, 3.2, 9.0], font_size=9.5)
    callout("不要做的事",
            ["不要用 B 冒充 A。",
             "B 的 150k 全量、1–2 天很诱人，但“当前累计评价”不是“发售后 12 个月”，答辩时一句“老游戏天然评价多”就会被问住。"],
            accent=RED, fill=RED_LIGHT)


def add_section_4():
    h1("4", "A0 方案：5,000 款样本")
    para("A0 的目标不是“覆盖 150k 标签”，而是用 5,000 款有 12 个月标签的样本训练模型，再用现有元数据给 150k 打分。",
         size=10.5, space_after=8)

    h2("4.1 样本怎么抽")
    rows = [
        ("总体", "2015–2025 年发售、截至 2026-11-19 已满 12 个月"),
        ("抽样", "5,000 款，按年份、主类型、免费/付费分层随机"),
        ("扩样", "正例少于 150 个，扩到 8,000–10,000 款"),
        ("排除", "2026 年、无 release_date、非 game、无法访问、重复 appid"),
        ("用途", "5k 训练/验证/测试；150k 只做特征打分，不抓标签"),
    ]
    add_table(["项目", "规则"], rows, [3.4, 13.0], font_size=9.5)

    h2("4.2 标签怎么造")
    para("标签定义：", size=10.5, bold=True, color=NAVY, space_before=2, space_after=2)
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_after = Pt(6)
    add_runs(p, [("hot12 = 1  if  reviews_12m >= 1000  else 0", True, BLUE)], size=10.5)
    rows = [
        ("首选", "appreviewhistogram 月度评价数，取发售后 12 个月求和"),
        ("备选", "appreviews 翻页读 timestamp_created；有 start/end_date 就按窗口取"),
        ("停止", "累计到 1,000 条即可判正例，不必抓完所有评价"),
        ("校验", "reviews_12m ≤ total_reviews；抽查 20 款；异常单独记录"),
        ("口径", "抢先体验用商店 release_date；评论轰炸不特殊清洗，但在模型卡说明"),
    ]
    add_table(["步骤", "做法"], rows, [2.8, 13.6], font_size=9.3)
    callout("标签是最大成本",
            ["5,000 款 × 1 次 histogram ≈ 5,000 请求，约 2 小时。",
             "如果只能翻页，平均 3–5 页/款 ≈ 15,000–25,000 请求，约 5–8 小时；加限流 1–2 天。"],
            accent=AMBER, fill=AMBER_LIGHT)

    h2("4.3 特征怎么选")
    rows = [
        ("主类型", "10 类 one-hot", "发售时已知", "保留"),
        ("genres", "Top 20 多标签 0/1", "发售时已知", "保留"),
        ("是否免费", "0/1", "发售时已知", "保留"),
        ("发售年份", "数值或年代", "发售时已知", "保留"),
        ("首发价", "log1p", "能拿到才用", "可选"),
        ("发行商", "Top 50 + other", "可抓但高基数", "可选"),
        ("总评价/好评率", "—", "发售后结果", "禁止"),
        ("当前折扣/在线", "—", "发售后信息", "禁止"),
    ]
    add_table(["特征", "处理", "时点", "是否使用"], rows,
              [3.4, 4.4, 4.4, 4.2], font_size=9.2)
    callout("首发价拿不到怎么办",
            ["不要用当前价冒充首发价。",
             "直接删掉价格特征，只用类型/genres/免费/年份；模型弱一点，但口径干净。"],
            accent=BLUE, fill=BLUE_LIGHT)

    h2("4.4 训练/验证/测试")
    rows = [
        ("训练", "2015–2021", "学参数、预处理、特征编码"),
        ("验证", "2022", "调超参数、选阈值、校准"),
        ("测试", "2023–2025", "只看一次；2025 是完整年"),
        ("排除", "2026", "样本不完整，不做结论"),
        ("方式", "按年份切分", "不随机切分，不做随机 KFold"),
    ]
    add_table(["集合", "年份", "用途"], rows, [2.8, 4.2, 9.4], font_size=9.5)

    h2("4.5 模型")
    rows = [
        ("下限", "base rate", "正例率；所有模型必须超过它"),
        ("简单基线", "单变量逻辑回归", "检查单个特征有没有信号"),
        ("主模型", "L2 逻辑回归", "稳定、可解释、可校准、可导出 JS"),
        ("挑战者", "HistGradientBoosting", "非线性/交互；只有明显更好才替换"),
        ("不采用", "深度学习 / BERT", "5k 表格数据，过拟合且不可解释"),
    ]
    add_table(["角色", "模型", "理由"], rows, [3.0, 4.2, 9.2], font_size=9.5,
              highlight_rows=[2])
    para("选择规则：HistGB 的 PR-AUC 比逻辑回归高 0.03 以上，且校准不差，才替换；否则选逻辑回归。",
         size=9.5, color=MUTED, space_after=6)

    h2("4.6 评估指标")
    rows = [
        ("PR-AUC", "正例不均衡时，模型把高热度排前面吗", "主指标"),
        ("Brier", "概率准不准", "主指标"),
        ("校准曲线", "预测 30% 的组，实际是否约 30%", "主指标"),
        ("Top 10% 命中率", "最看好的 10% 里，真实高热度比例", "业务解释"),
        ("ROC-AUC", "整体区分度", "辅助"),
        ("Precision/Recall", "阈值下的取舍", "辅助"),
        ("Bootstrap CI", "指标波动范围", "必须报"),
    ]
    add_table(["指标", "回答什么", "地位"], rows, [3.4, 9.6, 3.4], font_size=9.4)
    callout("不要只报 accuracy",
            ["正例 15% 时，全猜“不热”也有 85% 准确率。",
             "PR-AUC、Brier、校准曲线、Top 10% 命中率，才说明模型有没有用。"],
            accent=RED, fill=RED_LIGHT)

    h2("4.7 停止条件")
    rows = [
        ("1", "标签覆盖率 < 80%", "抓取不可用，停止"),
        ("2", "正例率 < 5% 或 > 30%", "阈值或样本有问题，重设"),
        ("3", "PR-AUC 比 base rate 高不到 0.05", "信号弱，停止 A"),
        ("4", "2024–2025 测试明显崩", "过拟合/漂移，停止"),
        ("5", "校准曲线不可用", "概率不可信，停止"),
    ]
    add_table(["Gate", "条件", "动作"], rows, [1.4, 8.0, 6.0], font_size=9.4)

    h2("4.8 成本与产出")
    rows = [
        ("0", "字段审计 + histogram 可行性", "0.5 天", "可行性结论"),
        ("1", "抽 5,000 款 + 试抓 100 条", "0.5 天", "样本清单/字段确认"),
        ("2", "全量抓取 + checkpoint", "1–3 天", "12 个月标签"),
        ("3", "标签/特征/清洗", "0.5–1 天", "model_dataset.csv"),
        ("4", "基线 + 逻辑回归 + HistGB", "1 天", "模型指标/模型卡"),
        ("5", "页面模型实验室", "2 天", "交互 + 校准 + 限制"),
        ("6", "1280/768/离线/console 验收", "0.5 天", "截图/验收记录"),
    ]
    add_table(["阶段", "内容", "时间", "产出"], rows, [1.2, 7.8, 2.4, 5.0], font_size=9.3)
    para("合计：顺利 5–7 个工作日；histogram 不可用、翻页变慢 +2–4 天；A1（20k）约 1–2 周；A2（150k 标签）1–2 个月，不建议。",
         size=9.3, color=MUTED, space_after=4)


def add_section_5():
    h1("5", "模型选择：为什么是逻辑回归")
    para("5,000 行、20–30 个特征、二分类，逻辑回归不是“保守”，而是匹配数据规模。",
         size=10.5, space_after=8)
    rows = [
        ("逻辑回归", "稳定；系数可解释；校准好；可导出 JS", "线性边界；交互要手工做"),
        ("HistGB", "非线性；自动交互；5k 也能跑", "校准稍差；导出复杂"),
        ("RandomForest", "稳健", "概率差；体积大"),
        ("XGBoost/LightGBM", "强", "额外依赖；5k 上未必明显更好"),
        ("神经网络", "理论上强", "5k 过拟合；不可解释；离线部署重"),
    ]
    add_table(["模型", "优点", "缺点"], rows, [3.6, 7.4, 5.4], font_size=9.4,
              highlight_rows=[0, 1])
    callout("最终选择规则",
            ["逻辑回归和 HistGB 的 PR-AUC 差距 < 0.03：选逻辑回归。",
             "HistGB 高 0.03 以上且校准不差：树模型做离线评分；页面交互仍用逻辑回归代理，并标注清楚。"],
            accent=TEAL, fill=TEAL_LIGHT)

    h2("5.1 逻辑回归怎么导出到页面")
    rows = [
        ("model.json", "特征顺序、类别映射、均值/标准差、系数、截距、阈值"),
        ("js/model.js", "z = b0 + Σbi·xi；p = 1/(1+e^-z)"),
        ("页面", "输入 → 预处理 → 点积 → 概率；不请求后端"),
        ("限制", "页面只做推理，不训练；不引 CDN/框架"),
    ]
    add_table(["文件/环节", "内容"], rows, [4.2, 12.2], font_size=9.5)
    para("如果 HistGB 胜出：树模型只做离线评分/批量打分；页面交互仍用逻辑回归代理，模型卡写清“离线最佳为 HistGB”。",
         size=9.3, color=MUTED, space_after=6)


def add_section_6():
    h1("6", "页面怎么呈现")
    para("新增 09 模型实验室，放在 07 档案之后、08 方法之前。下面是信息结构，不是最终视觉稿。",
         size=10.5, space_after=8)

    # wireframe
    table = doc.add_table(rows=4, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table, color=LINE)
    widths = [8.2, 8.2]
    for row in table.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
    # merged top
    top = table.rows[0].cells[0].merge(table.rows[0].cells[1])
    shade(top, NAVY)
    cell_text(top, "09 模型实验室  /  12 个月高热度概率", size=12, bold=True, color="FFFFFF")
    set_cell_margins(top, 160, 160, 180, 180)

    left = table.rows[1].cells[0]
    right = table.rows[1].cells[1]
    shade(left, SOFT); shade(right, BLUE_LIGHT)
    left.text = ""; right.text = ""
    p = left.paragraphs[0]
    add_runs(p, [("输入（发售时）", True, NAVY)], size=9.5)
    for t in ["主类型", "genres（Top 10）", "免费 / 付费", "发售年份", "首发价（可选）"]:
        pp = left.add_paragraph()
        pp.paragraph_format.space_after = Pt(1)
        add_runs(pp, [("□  " + t, False, INK)], size=9)
    p = right.paragraphs[0]
    add_runs(p, [("输出", True, NAVY)], size=9.5)
    for t in ["[概率]  %", "基准率 [base rate]", "高于/低于基准", "不是保证"]:
        pp = right.add_paragraph()
        pp.paragraph_format.space_after = Pt(1)
        add_runs(pp, [(t, False, INK)], size=9)

    mid = table.rows[2].cells[0].merge(table.rows[2].cells[1])
    shade(mid, SOFT)
    cell_text(mid, "模型卡：样本量 · 正例率 · 训练/测试年份 · PR-AUC · Brier · 校准 · 阈值 · 限制",
              size=9, color=INK)
    set_cell_margins(mid, 120, 120, 160, 160)

    bottom = table.rows[3].cells[0].merge(table.rows[3].cells[1])
    shade(bottom, AMBER_LIGHT)
    cell_text(bottom, "驱动因素（系数条）  |  回测表（预测高概率组 vs 实际）  |  一句话限制",
              size=9, color=INK)
    set_cell_margins(bottom, 120, 120, 160, 160)
    para(" ", size=3, space_after=2)

    h2("6.1 必须写清楚的 5 句话")
    for t in [
        "预测的是发售后 12 个月高热度，不是销量、收入或在线人数。",
        "输入的是发售时信息，不是今天的评价/折扣。",
        "模型只说明相关，不说明因果。",
        "5,000 款是样本，不是全量 150k 标签。",
        "如果指标弱，页面必须展示弱结果，不伪造概率。",
    ]:
        bullet(t, size=9.8)

    h2("6.2 交互与离线")
    rows = [
        ("输入", "类型、genres、免费/付费、年份；价格有才显示"),
        ("输出", "概率 + base rate 对照 + 一句解释"),
        ("模型卡", "n、正例率、切分年份、PR-AUC、Brier、校准、Top 特征"),
        ("图表", "校准曲线、系数条、回测分档"),
        ("离线", "model.json + js/model.js；不请求后端/CDN"),
        ("降级", "模型未加载时显示“当前仅展示回测”，不显示假数字"),
    ]
    add_table(["模块", "做法"], rows, [2.8, 13.6], font_size=9.5)


def add_section_7():
    h1("7", "实施计划")
    para("批准后按下面顺序执行。每个阶段都有可检查的产出，不一次性黑箱做完。",
         size=10.5, space_after=8)
    rows = [
        ("Day 1 上午", "字段审计；验证 appreviewhistogram 是否全历史", "可行性结论；不通过则改方案"),
        ("Day 1 下午", "抽 5,000 款；试抓 100 条；确认限流", "样本清单；抓取脚本骨架"),
        ("Day 2–3", "全量抓取 5k；checkpoint；失败重试", "raw_labels + coverage"),
        ("Day 4", "构标签；特征；清洗；切分", "model_dataset.csv"),
        ("Day 5", "base rate + 逻辑回归 + HistGB；评估", "指标表；模型卡初稿"),
        ("Day 6–7", "页面 09；交互；校准图；1280/768", "截图；页面验收"),
        ("Day 8", "离线/console/文案复核", "最终交付；模型说明"),
    ]
    add_table(["时间", "做什么", "产出"], rows, [3.2, 7.6, 5.6], font_size=9.3)

    h2("7.1 如果 histogram 不可用")
    rows = [
        ("先试抓 100 款", "估算平均翻页数/限流", "决定是否继续"),
        ("可接受", "5k 翻页 1–2 天", "继续 A0"),
        ("不可接受", "缩到 2,000 款或转 B", "不硬上全量"),
    ]
    add_table(["情况", "动作", "结果"], rows, [4.0, 7.4, 5.0], font_size=9.4)

    h2("7.2 如果模型没信号")
    callout("提前停止，不丢人",
            ["PR-AUC 比 base rate 高不到 0.05：停止 A。",
             "页面改叫“高热度历史回测/风险分层”，不写“预测”。",
             "这比硬编一个好看的概率更可信。"],
            accent=RED, fill=RED_LIGHT)


def add_section_8():
    h1("8", "风险与红线")
    rows = [
        ("Steam 限流/429", "抓取慢/中断", "1–1.5s；指数退避；checkpoint；失败单列"),
        ("标签覆盖不足", "样本偏差", "覆盖率 <80% 停止；抽查 20 款"),
        ("首发价缺失", "价格特征泄漏/缺失", "删价格；绝不用当前价冒充"),
        ("正例太少", "模型不稳定", "扩样/调阈值；报 CI"),
        ("模型信号弱", "页面像噱头", "停止 A；转 B；展示负结果"),
        ("样本偏差", "不能代表全量", "随机分层；模型卡写清"),
        ("页面过度承诺", "答辩被问穿", "只写概率/相关；不写因果/销量"),
        ("文件过长", "维护困难", "模型逻辑独立 js/model.js；不合并"),
    ]
    add_table(["风险", "影响", "应对"], rows, [4.2, 4.8, 7.4], font_size=9.2)
    callout("三条红线",
            ["不伪造预测结果；指标弱就写弱。",
             "不用发售后信息做特征；随机切分不算时间外验证。",
             "不把“高热度概率”说成“销量/爆款/因果”。"],
            accent=RED, fill=RED_LIGHT)


def add_section_9():
    h1("9", "需要你确认的 5 件事")
    para("下面是默认建议。你可以在文档上改，也可以直接回复“按 A0 开始”或指出要改的项。",
         size=10.5, space_after=8)
    rows = [
        ("□ 1", "样本用 5,000 款", "正例不足再扩到 8,000–10,000", "建议 5,000"),
        ("□ 2", "允许抓 Steam 评价接口 1–3 天", "这是 A 成立的前提", "建议允许"),
        ("□ 3", "首发价拿不到就删价格特征", "绝不用当前价冒充", "建议接受"),
        ("□ 4", "页面新增 09 模型实验室", "放在档案与方法之间", "建议新增"),
        ("□ 5", "模型弱就如实展示并停止", "不硬包装成预测", "建议接受"),
    ]
    add_table(["确认", "事项", "说明", "默认"], rows, [1.4, 5.0, 7.2, 2.8],
              font_size=9.4, highlight_rows=[0, 4])
    callout("你确认后我再开始",
            ["回复示例：",
             "“按 A0 开始，5k 样本，接受弱结果。”",
             "或：“样本改 10k；价格必须保留；先只做回测报告，不做交互。”"],
            accent=BLUE, fill=BLUE_LIGHT)


def add_appendix():
    h1("A", "附录：数据字段与指标解释")
    h2("A.1 model_dataset.csv 建议字段")
    rows = [
        ("appid", "Steam App ID", "主键"),
        ("name", "游戏名", "仅展示"),
        ("release_date", "发售日", "算 12 个月窗口"),
        ("year", "发售年份", "特征/切分"),
        ("type", "主类型", "特征"),
        ("genres", "多标签", "特征"),
        ("is_free", "免费/付费", "特征"),
        ("launch_price", "首发价", "可选特征"),
        ("publisher", "发行商", "可选特征"),
        ("reviews_12m", "12 个月评价数", "标签来源"),
        ("hot12", "是否 ≥1000", "标签"),
        ("coverage", "histogram/fallback/failed", "数据质量"),
    ]
    add_table(["字段", "含义", "用途"], rows, [4.2, 7.0, 5.2], font_size=9.2)

    h2("A.2 指标一句话")
    rows = [
        ("base rate", "正例比例；所有模型的对照下限"),
        ("PR-AUC", "正例少时，模型把高热度排前面的能力"),
        ("ROC-AUC", "整体区分度；不如 PR-AUC 适合不均衡"),
        ("Brier", "概率误差；越小越好"),
        ("校准", "预测概率和实际频率是否一致"),
        ("leakage", "用了预测时点之后才知道的信息"),
        ("temporal split", "按时间切分；训练过去、测试未来"),
    ]
    add_table(["术语", "解释"], rows, [4.0, 12.4], font_size=9.4)

    h2("A.3 数据与假设")
    for t in [
        "现有 archive：150,279 款游戏；2,000 条真实评价；10 条在线快照。",
        "高热度用“12 个月评价数 ≥1000”代理，不等于销量/收入。",
        "抓取成本按 1.0–1.5 秒/请求估算，实际受 Steam 限流影响。",
        "首发价/发行商可能需要额外 appdetails 请求；拿不到就删特征。",
        "所有指标必须在 2023–2025 时间外测试集上报告。",
    ]:
        bullet(t, size=9.6)


doc = Document()
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(1.9)
sec.bottom_margin = Cm(1.8)
sec.left_margin = Cm(2.2)
sec.right_margin = Cm(2.2)
sec.header_distance = Cm(0.8)
sec.footer_distance = Cm(0.8)

# base style
normal = doc.styles["Normal"]
normal.font.name = FONT
normal.font.size = Pt(10.5)
normal.font.color.rgb = RGBColor.from_string(INK)
normal._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
normal.paragraph_format.line_spacing = 1.5
normal.paragraph_format.space_after = Pt(6)

for sname in ("List Bullet", "List Bullet 2", "List Number"):
    st = doc.styles[sname]
    st.font.name = FONT
    st.font.size = Pt(10.5)
    st.font.color.rgb = RGBColor.from_string(INK)

add_header(sec)
add_page_number_footer(sec)

doc.core_properties.title = "Steam 新游 12 个月高热度预测：方案说明与实施计划"
doc.core_properties.subject = "Steam 游戏市场洞察平台 · 机器学习模块"
doc.core_properties.author = "Steam 市场洞察项目组"
doc.core_properties.keywords = "Steam, 机器学习, 预测, 逻辑回归, 模型卡"
doc.core_properties.comments = "方案讨论稿；未经确认不开始编码。"

add_cover()
add_reading_route()
add_section_0()
add_section_1()
add_section_2()
add_section_3()
add_section_4()
add_section_5()
add_section_6()
add_section_7()
add_section_8()
add_section_9()
add_appendix()

# closing note
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(18)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("— 方案讨论稿 · 等你确认后再开始编码 —")
set_run_font(r, size=9, color=MUTED)

os.makedirs(".", exist_ok=True)
doc.save(OUT)
print("saved", OUT)
