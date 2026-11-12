# -*- coding: utf-8 -*-
"""生成答辩提纲 v2（Word）。"""
import sys
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"F:\steam-market-insight\答辩提纲-v2.docx"

INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x6B, 0x6B, 0x6B)
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
FONT = "微软雅黑"

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
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), size)
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)


def _cell_text(cell, text, bold=False, size=9.5, color=INK, align=None):
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1.5)
    p.paragraph_format.space_after = Pt(1.5)
    p.paragraph_format.line_spacing = 1.15
    if align:
        p.alignment = align
    run = p.add_run(text)
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def table(headers, rows, widths=None, header_bg="1F4E79", first_col_bold=False):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
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
            _cell_text(cells[i], v, bold=(first_col_bold and i == 0), size=9.5)
            if i == 0 and first_col_bold:
                _shade(cells[i], "F2F5F9")
    # 固定列宽布局，避免 LibreOffice/Word 自动均分
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    # 行内不跨页断开
    for row in t.rows:
        trPr = row._tr.get_or_add_trPr()
        cs = OxmlElement("w:cantSplit")
        cs.set(qn("w:val"), "true")
        trPr.append(cs)
    if widths:
        # 归一到版心宽度（16.2cm），避免表格超出正文边界
        scale = 16.2 / sum(widths) if sum(widths) > 16.2 else 1.0
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(round(w * scale, 2))   # 关键：写入 tblGrid
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
    # 下边框
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


def para(text, size=10.5, color=INK, bold=False, space_after=4, indent=0):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after)
    if indent:
        p.paragraph_format.left_indent = Cm(indent)
    run = p.add_run(text)
    run.font.name = FONT
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return p


def bullet(lead, rest, size=10.5):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.5
    r1 = p.add_run(lead)
    r1.font.name = FONT
    r1._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r1.font.size = Pt(size)
    r1.font.bold = True
    r2 = p.add_run(rest)
    r2.font.name = FONT
    r2._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r2.font.size = Pt(size)
    return p


def callout(text, bg="EAF1F8", color=INK):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    _borders(t, color="C9DBEE", size="8")
    c = t.rows[0].cells[0]
    _shade(c, bg)
    _cell_text(c, text, size=10.5, color=color)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


# ---------- 页脚 ----------
footer_p = sec.footer.paragraphs[0]
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
fr = footer_p.add_run("Steam 市场观察 · 答辩提纲 v2　|　F:\\steam-market-insight")
fr.font.name = FONT
fr._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
fr.font.size = Pt(8.5)
fr.font.color.rgb = MUTED

# ---------- 标题 ----------
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(2)
r = p.add_run("Steam 市场观察 · 答辩提纲")
r.font.name = FONT
r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
r.font.size = Pt(26)
r.font.bold = True
r.font.color.rgb = ACCENT

para("150,279 款全量游戏 · 2010—2025 供给曲线 · 2,000 份真实口碑样本 · 实时 TOP10", size=11, color=MUTED, space_after=2)
para("导师制项目　|　运行方式：项目根目录执行 npm start → http://localhost:8081/　|　版本：2026-11-12", size=9, color=MUTED, space_after=10)

callout("一句话：这不是一个游戏榜单，而是一份用全量 archive 数据 + 真实评价样本做出来的 Steam 市场结构报告。\n"
        "每一节都按「问题 → 证据 → 口径 → 限制」组织，所有数字都能回到 data/market/ 与 scripts/ 里复核。")

# ---------- 0 一页速览 ----------
h1("0　一页速览（老师只给你 1 分钟时讲这段）")
table(
    ["维度", "内容"],
    [
        ["做了什么", "把 150,279 款 Steam 游戏的供给、类型、价格、口碑、注意力五个问题，做成一个可点击、可复核的单页数据故事。"],
        ["关键数字", "供给 14 年 84 倍（2010 年 240 款 → 2024 年 20,203 款）；2025 年首次回落 11.5%；动作×独立共享 45,373 款；全样本均价 $5.26；S 级仅 11.2%；TOP3 在线占 65.0%。"],
        ["技术路线", "Python（pandas）清洗聚合 → Node 迷你服务器提供接口 → 原生 JS + ECharts 本地化渲染（断网可用）。"],
        ["工作量证据", "scripts/ 下 6 个数据脚本共 60KB+；js/lobby.js 48KB 渲染逻辑；data/market/market_full.csv 21 列 0 空值；git 13 次提交。"],
        ["诚实点", "口碑只有 2,000 款（覆盖率 1.3%，按推荐数选取），所有口碑结论只对样本负责；数据是 archive 快照，不是实时全站。"],
    ],
    widths=[2.8, 13.4],
    first_col_bold=True,
)

# ---------- 1 开场 ----------
h1("一　30 秒开场")
para("老师好，我的项目是 Steam 游戏市场洞察。")
para("我最初做的是一个「游戏大厅 + 榜单」：10 个类型角色、TOP500 档案，本质是把 Steam 首页搬过来。做完之后我发现一个问题——榜单只能回答「谁最火」，回答不了「这个市场长成什么样」。")
para("所以我把项目推翻重做，改成一份结论先行的数据报告，围绕四个问题展开：", space_after=3)
bullet("供给问题：", "Steam 的游戏数量到底是一路涨，还是有拐点？")
bullet("结构问题：", "十个类型是互相独立，还是共享同一批游戏？")
bullet("分层问题：", "价格和口碑怎么把游戏分开？免费是不是等于差？")
bullet("注意力问题：", "玩家的时间集中在头部，还是散在长尾？")
para("下面每一节，都是一个问题的证据。", space_after=2)

# ---------- 2 怎么完成 ----------
h1("二　项目是怎么完成的：五个阶段")
table(
    ["阶段", "做了什么", "产出物", "踩到的坑"],
    [
        ["① 转身\n（选题）", "把「游戏榜单」整体改造成「结论先行的数据报告」，砍掉大厅首页，首页只留 5 个发现。", "index.html 单页 9 节结构", "做完榜单才发现它回答不了结构问题——这是全项目最大的一次返工。"],
        ["② 找数据\n（三源）", "archive 全量表 + HuggingFace 真实评价 + Steam 实时在线；配置 Windows 计划任务每天 22:00 自动抓。", "data/market/、data/online.json", "Steam 评价接口限流/超时；本机直连 store.steampowered.com 会 TCP 超时，脚本里加了代理启停。"],
        ["③ 清洗聚合\n（核心）", "一个脚本完成：筛 type=game、汇率折算、提取年份、展开多类型、推断小标签、合并评价。", "build_market.py → CSV + 聚合 JSON + TOP500", "多币种价格、34,502 款缺发行日期、一款游戏多个类型导致数量重叠。"],
        ["④ 前端叙事", "9 节单页：摘要 / 类型 / 生命周期 / 时间线 / 价格 / 实时 / 口碑 / 档案 / 方法，全部可点击。", "js/lobby.js 48KB + 2 个 CSS", "15 万行不能塞进浏览器 → 后端预聚合成 1.2MB JSON。"],
        ["⑤ 自查与口径", "交叉核验 2025 年供给、0 空值校验、给每张图配口径注脚、把样本偏差写进页面。", "README 数据说明 + 页面 note", "发现 archive 9–12 月 release_date 只有 1,450 条，因此不做月度趋势。"],
    ],
    widths=[2.2, 5.4, 3.6, 5.0],
    first_col_bold=True,
)

# ---------- 3 数据 ----------
h1("三　数据：三个来源与清洗口径")
table(
    ["数据", "来源", "规模", "用途"],
    [
        ["全量游戏主表", "archive：applications.csv + application_genres.csv", "筛 type=game 后 150,279 款", "类型、价格、发行年、推荐数"],
        ["真实口碑样本", "HuggingFace Z02Z/steam-games-dataset（FronkonGames，CC-BY-4.0）", "2,000 款 positive/negative", "好评率、S/A/B/C 分层"],
        ["实时在线", "SteamCharts 榜单镜像 + GetNumberOfCurrentPlayers", "TOP10，10 款全有效", "今日谁在占用玩家时间"],
    ],
    widths=[3.0, 7.0, 3.4, 3.0],
    first_col_bold=True,
)
para("清洗口径（可复现，全部在 build_market.py 里）：", bold=True, space_after=3)
bullet("类型：", "按 Steam 官方大类映射，保留多主类型——一款游戏可以同时属于动作、独立、冒险，所以十类相加 406,518 > 150,279。")
bullet("价格：", "mat_final_price 原始单位是「分」，按币种 × 快照期汇率折美元；免费与未定价分开统计（price_unknown 标记），不把未知价格混成 0 元。")
bullet("年份：", "release_date 里正则提 4 位数字，缺失记 0；这类 34,502 款不进入年度曲线。")
bullet("小标签：", "从游戏名 + 简介关键词推断，页面上明确写「不是 Steam 用户标签」。")
bullet("口碑：", "archive 没有评论字段，只合并公开数据集的真实计数，不编造；覆盖率 1.3% 写在每一处结论旁。")
para("关键校验：150,279 行、免费 18,994、有价 90,311、重复 appid 0、CSV 空值 0；2025 年用 Steam Store 独立检索 17,801 款交叉核验，与 archive 的 17,876 款相差 75 款（0.4%）。", space_after=2)

# ---------- 4 五个结论 ----------
h1("四　五个结论：数字、证据、限制")
table(
    ["结论", "数字", "证据在页面哪一节", "必须一起说的限制"],
    [
        ["供给涨了 84 倍，2025 首次回落", "2010 年 240 → 2024 年 20,203 → 2025 年 17,876（-11.5%）", "03 供给曲线", "archive 快照，缺失发行年 34,502 款不入曲线；两源交叉 0.4%。"],
        ["类型高度重叠，独立是公共层", "动作×独立 45,373；冒险×独立 45,099；休闲×独立 45,098", "01 类型版图", "多标签包含关系，数量可重叠，不能相加当总量。"],
        ["免费把均价拉平", "全样本均价 $5.26 / 中位 $1.99；付费均价 $8.75 / 中位 $4.99", "04 价格分层", "快照期汇率折算，非当日汇率、非首发价。"],
        ["S 级只占一小撮", "2,000 样本中 S 级 224 款，占 11.2%", "06 口碑分层", "样本覆盖 1.3%，按推荐数选取，有选择偏差。"],
        ["注意力比供给更集中", "TOP10 合计 403.6 万在线，TOP3 占 65.0%", "05 实时切片", "只是 TOP10 榜内占比，不是平台总在线；单次快照。"],
    ],
    widths=[3.6, 5.0, 3.4, 4.4],
    first_col_bold=True,
)

# ---------- 5 任务书对照 ----------
h1("五　任务书逐条对照（自己先说，别等老师问）")
table(
    ["任务书要求", "现状", "说明 / 理由"],
    [
        ["≥4 个页面", "✅ 单页 9 节", "做的是数据故事单页，9 个章节相当于 9 个页面，导航可直达。"],
        ["图表 ≥8 个、≥5 种类型", "✅ 10 处可视化", "ECharts 5 种（柱/折/散点/热力/词云）+ SVG 类型关系网 + 自绘时间轴。"],
        ["标签词云 + 热力图", "✅ 都有", "词云在口碑节（点击筛选）；热力图是「类型×年份」生命周期矩阵。"],
        ["≥2 类「输入即展示」交互", "✅ 6 类", "悬停看关系、点格子翻档案、点事件锚点、S/A/B/C 切换、词云点标签、搜索+下拉筛选。"],
        ["CSV ≤5MB 且前端 fetch", "⚠️ 换了实现", "29MB 全量 CSV 不进浏览器，改为 fetch 1.2MB 预聚合 JSON —— 同一份数据的工程取舍。"],
        ["Python 抓 GetMostPlayedGames 存 JSON", "⚠️ 换了来源", "用 SteamCharts 镜像 + GetNumberOfCurrentPlayers，由 Node 脚本每日 22:00 跑，产物同样是 JSON。"],
        ["ECharts timeline 动画 + 播放/暂停", "⚠️ 换了做法", "用自绘逐帧回放实现 2010—2025 播放与暂停，没用 timeline 组件。"],
        ["实时模块 60 秒刷新 + 高亮", "❌ 未做", "当前是打开即拉取 + 每日任务；已列入下一步第一条。"],
        ["≥3 条洞察", "✅ 5 条", "首页五张卡 + 每节一条 takeaway。"],
        ["Git ≥15 次提交", "❌ 13 次", "早期几次改动合并了；后面按一次改动一次提交补齐。"],
        ["README 写运行方法", "✅", "环境、命令、端口、每日任务的排错都写了。"],
        ["平台纯前端双击可打开", "❌ 需服务器", "页面 fetch 本地 JSON，file:// 下会被浏览器拦截；用 npm start 后访问 8081。已在 README 标为已知限制。"],
    ],
    widths=[4.6, 2.6, 9.2],
    first_col_bold=True,
)
para("被问到时的话术：这四条我没照字面实现，但都换成了更合适的做法，缺的两条（60 秒刷新、15 次提交）我认，已经列进下一步。", size=9.5, color=MUTED)

# ---------- 6 演示 ----------
h1("六　演示路线：90 秒，三个必看动作")
para("不要把 9 节平铺讲完，那样一定超时。主讲三个动作，其余一句话带过。", space_after=3)
table(
    ["顺序", "动作", "说什么"],
    [
        ["1", "在「类型版图」把鼠标移到「独立」上", "看连线：动作×独立 45,373 款。独立不是小众孤岛，它是连接动作、冒险、休闲的公共层 —— 这就是「十块地盘会重叠」的直接证据。"],
        ["2", "在「生命周期」点任意一个格子", "从「十类都在涨」跳到「这个类型自己的档案」：年度走势、小标签墙、代表作品。一个点击把聚合数字落到具体游戏。"],
        ["3", "在「口碑」点词云里的一个标签", "词云不是装饰，点「Roguelike」就列出这个标签下的游戏，再配合右边 S/A/B/C 榜单看评价量。"],
    ],
    widths=[1.4, 5.6, 9.4],
)
para("其余章节一句话过：摘要（5 个数字）→ 时间线（播放 2010—2025，2025 首次回落）→ 价格（免费拉平均价，但口碑只差 2.8 分）→ 实时（10 名全有效）→ 档案（TOP500 可搜索）→ 方法（口径与限制）。", space_after=2)

# ---------- 7 Q&A ----------
h1("七　Q&A：老师最可能问的 12 个问题")
qa = [
    ("Q1　为什么是 150,279，不是「Steam 所有游戏」？",
     "A：archive 里 type=game 是 150,279 款，DLC、demo、原声不算游戏。它是 archive 快照，不是实时全站；页面上每一处都写「全量 archive 快照」。"),
    ("Q2　为什么只有 2,000 款有口碑？",
     "A：archive 没有评论字段，Steam 评价接口限流，所以用公开数据集的 positive/negative 补了 2,000 款，覆盖率 1.3%。所有口碑结论都标了「样本」，不外推全量。"),
    ("Q3　为什么类型数量相加超过 150,279？",
     "A：Steam 是多标签的，一款游戏可以同时是动作+独立+冒险。项目保留多主类型，十类相加 406,518，所以页面写「数量可重叠」，另有 8,870 款没命中任何大类。"),
    ("Q4　价格为什么是美元？怎么折的？",
     "A：archive 是多币种，原始单位是「分」，按快照期汇率折 USD。不是实时汇率，也不是历史首发价，页面标了「USD 快照」。"),
    ("Q5　TOP10 是当天的吗？可信吗？",
     "A：是 2026-11-11 22:32 的快照，10 款全部有效，合计 403.6 万在线。数据由每日 22:00 的计划任务抓取，失败会保留旧快照并标注时间，不补假数。"),
    ("Q6　这个项目的「分析」在哪里？不就是堆图吗？",
     "A：不是。①首页先给 5 个结论，图是为结论服务的；②每节都有「问题—证据—口径—限制」；③有可复现脚本和 0 空值校验；④主动写样本偏差，不把 2,000 当全量；⑤最后一节专门讲方法与限制。"),
    ("Q7　为什么用 JSON 不用 CSV？任务书要 CSV。",
     "A：任务书要求图表数据来自清洗后的本地 CSV 且 ≤5MB。全量 CSV 是 29MB、15 万行，塞进浏览器会卡死，所以我保留 CSV 作离线核对，前端改为 fetch 1.2MB 的预聚合 JSON —— 同一份数据，换了交付形态，结论完全可复现。"),
    ("Q8　热力图为什么是「类型×年份」，不是任务书说的「类型×好评率」？",
     "A：口碑只有 2,000 款，类型×好评率会有大量空格，不成立。所以热力图用来讲生命周期（类型×年份），价格×口碑放在价格节的散点图里（有价均价 vs 好评率），两个问题都覆盖了。"),
    ("Q9　数据怎么证明不是编的？",
     "A：三个可查点：scripts/build_market.py 能完整重跑；data/market/market_full.csv 有 150,279 行、0 空值；2025 年供给用 Steam Store 独立检索 17,801 款交叉核验，相差 0.4%。"),
    ("Q10　2025 年为什么跌 11.5%？能说 Steam 在衰退吗？",
     "A：不能。这是样本内首次年度回落，且 Steam Store 独立检索同步下降（17,801 款，-11.9%），两源一致，说明不是抓取误差；但它是 archive 快照，不能外推成行业结论。"),
    ("Q11　界面为什么做成游戏风、还有角色？",
     "A：这是叙事取舍。数据报告最大的敌人是没人看，所以用「走进数据世界」的场景降低门槛；但每一屏都保证有数字、有口径注脚，形式不牺牲严谨。"),
    ("Q12　你做得最对 / 最不满意的地方？",
     "A：最对的是把「游戏大厅」降为叙事外壳，先讲结论、保留多主类型和真实评价，不伪造数据。最不满意的是口碑样本仍偏小、实时模块缺 60 秒自动刷新、提交次数不够。"),
]
for q, a in qa:
    pq = para(q, bold=True, space_after=2)
    pq.paragraph_format.keep_with_next = True
    para(a, color=RGBColor(0x33, 0x33, 0x33), space_after=7)

# ---------- 8 不足 ----------
h1("八　不足与下一步（三条可验证的）")
table(
    ["#", "不足", "下一步怎么做（可验收）"],
    [
        ["1", "实时模块没有 60 秒自动刷新", "在 lobby.js 里加 60 秒定时拉取 /api/online，数据变化时高亮对应行；刷新时间戳显示在竞技场头部。"],
        ["2", "Git 提交 13 次，少于要求的 15 次", "接下来每个改动单独提交（修口径、补刷新、改文档分开提交），并保留有意义的 commit message。"],
        ["3", "口碑样本 1.3%，且按推荐数选取", "把样本扩到 1 万款以上，并用 bootstrap 置信区间检验 S/A/B/C 分档是否稳健。"],
    ],
    widths=[1.0, 6.0, 9.4],
)
para("补充一条已知限制：页面依赖 npm start 起的本地服务（file:// 下浏览器会拦截 fetch），这是纯前端双击可打开这条要求没做到的地方，已在 README 标明。", size=9.5, color=MUTED)

# ---------- 9 收尾 ----------
h1("九　30 秒收尾")
callout("这个项目最后不是「我做了很多图」，而是：\n"
        "我用 150,279 款全量游戏和 2,000 份真实评价，回答了 Steam 市场「供给、类型、价格、口碑、注意力」五个问题；"
        "每个结论都能回到数据和口径，每个口径都写在页面上。\n"
        "谢谢老师。")

# ---------- 附：检查清单 ----------
doc.add_page_break()
h1("附　答辩前 5 分钟检查清单")
checklist = [
    "npm start 已运行，http://localhost:8081/ 能打开，页面顶栏显示「全量快照 2026-11-11」与「在线数据 11-11 22:32」。",
    "首页五张卡的数字与本文第四节一致（84 倍 / 45,373 / $5.26 / 11.2% / 65.0%）。",
    "演示三个动作都试过一遍：悬停角色出连线、点热力图格子开档案、点词云标签出游戏列表。",
    "「打印报告」按钮能正常出 A4 版（老师要材料时可以直接给）。",
    "准备好一句兜底：如果数据接口挂了，改用 npm start 重启；若还是不通，用 data/ 里的静态 JSON 说明数据本身在仓库里。",
]
for i, item in enumerate(checklist, 1):
    para(f"{i}. {item}", space_after=5)

doc.save(OUT)
print("saved", OUT)
