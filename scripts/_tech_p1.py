# -*- coding: utf-8 -*-
# 分片 1：标题 + 第 0、1 节
p = doc.add_paragraph()
p.paragraph_format.space_after = Pt(2)
r = p.add_run("技术说明：这个项目是怎么做出来的")
r.font.name = FONT
r._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
r.font.size = Pt(24)
r.font.bold = True
r.font.color.rgb = ACCENT

para("从「我不知道这些代码哪来的」到「我能指着每一行说出它为什么在这」", size=11, color=MUTED, space_after=2)
para("配套项目：Steam 市场观察（F:\\steam-market-insight）　|　读者：项目作者本人　|　版本：2026-11-12",
     size=9, color=MUTED, space_after=10)

callout("这份文档不教你写代码，而是回答三个问题：\n"
        "① 这个项目用了哪些技术，每样技术各自解决什么问题；\n"
        "② 这些代码是怎么一步步长出来的（包括中间踩的坑和返工）；\n"
        "③ 怎么读它——从哪个文件开始、哪些可以先跳过、想改功能该动哪一行。\n"
        "读完的检验标准：合上文档，把任意一张图，从「哪份原始数据」一路讲到「哪一段 JS 把它画出来」。")

h1("0　先看这一页：项目到底是怎么跑起来的")
para("看自己的项目会懵，通常是因为一直在「从代码往里读」。正确的顺序是反的：先看数据怎么流，再看代码。"
     "这个项目从头到尾只有一条数据流，分三层：", space_after=6)

table(
    ["层", "用什么做的", "做什么", "产物 / 入口", "能不能跳过"],
    [
        ["① 数据层", "Python 3 + pandas", "读本地 archive 全量表，筛游戏、折汇率、提年份、展开类型，聚合成前端能吃的 JSON",
         "scripts/build_market.py → data/market/*.json", "初学可跳，只看产物"],
        ["② 展示层", "HTML + CSS + 原生 JS + ECharts", "把 JSON 变成 9 节可点击的数据故事：柱状、折线、散点、热力、词云、关系网、时间轴回放",
         "index.html、js/lobby.js、CSS/", "重点，答辩全靠它"],
        ["③ 服务层", "Node.js（149 行，无框架）", "开 8081 端口：把本地文件变成网页、把 data/ 下的 JSON 变成 /api/* 接口；另负责每日抓实时在线",
         "server.js、scripts/fetch_online.js", "理解「为什么需要它」即可"],
    ],
    widths=[1.8, 3.4, 6.6, 4.4, 2.6],
    first_col_bold=True,
)

para("一条数据从原始 CSV 走到屏幕上的图，经过 6 步——这张表建议背下来，答辩时就叫「技术路线」：", space_after=4)
table(
    ["步", "动作", "具体做什么", "落在哪个文件"],
    [
        ["1", "采集", "archive 全量表（本地 CSV）＋ HuggingFace 评价子集 ＋ Steam 实时在线 TOP10", "build_market.py、fetch_hf_reviews.py、fetch_online.js"],
        ["2", "清洗", "筛 type=game；价格「分」÷100 再乘汇率；年份正则提 4 位；缺失记 0 不丢行", "build_market.py 清洗函数"],
        ["3", "聚合", "按类型/年份/价格段/标签分组统计，交叉表、TOP 榜、名称索引", "build_market.py main()"],
        ["4", "落盘", "29MB 明细 CSV 留档；1.2MB 聚合 JSON 给前端；500 条 TOP 榜单独出", "data/market/"],
        ["5", "取数", "页面 fetch('/api/market/agg')，失败自动降级读本地 JSON", "js/lobby.js 的 apiWithFallback"],
        ["6", "渲染", "ECharts 用「数据 + option 配置」画图；点击事件改 option 再重绘", "js/lobby.js 各 init* 函数"],
    ],
    widths=[1.0, 2.2, 9.2, 5.2],
)
para("记住这条链，就不会再问「代码哪来的」：每一段代码都对应链上某个格子，没有多余的代码；反过来，"
     "任何一段看不懂的代码，都能在链上找到它的位置。", size=9.5, color=MUTED)

h1("1　技术栈地图：每样技术到底在解决什么问题")
para("先把技术名词翻译成「它解决什么问题」。表里每一样都只解决一个问题；能说出它解决的问题，就算懂了八成。", space_after=4)
table(
    ["技术", "在本项目里干什么", "对应文件", "要学到什么程度", "学校大概哪门课"],
    [
        ["HTML", "页面骨架：9 个 section、标题、图表容器、按钮", "index.html", "看懂标签嵌套、id/class、data-* 属性", "Web 前端"],
        ["CSS", "排版与视觉：网格、颜色变量、动画、响应式；游戏风界面与奶蛙角色也靠它", "CSS/lobby.css、CSS/style.css", "会改颜色/间距/字号即可", "Web 前端"],
        ["JavaScript", "交互与取数：监听点击、拼 option、算数字、改 DOM", "js/lobby.js（约 1200 行）", "看懂函数、事件回调、数组方法 map/filter/sort", "JavaScript 程序设计"],
        ["fetch + JSON", "向服务器要数据：发请求 → 拿 JSON → 转对象", "js/lobby.js 数据加载段", "知道「同源」和 file:// 为什么不行", "Web 前端 / 网络"],
        ["ECharts", "画图库：给数据和配置，还你可交互的图", "js/echarts.min.js、各 init* 函数", "会读 option 结构，知道 series/data 在哪", "数据可视化（可能没开课）"],
        ["SVG", "手画「类型关系网」：上千条线用矢量图元拼", "js/lobby.js 关系网段", "知道 circle/line 与坐标概念", "前端 / 图形"],
        ["Python 3", "跑数据处理脚本", "scripts/*.py", "会装环境、会跑脚本、会看报错栈", "Python 程序设计"],
        ["pandas", "表格处理：读 CSV、筛选、合并、分组统计、导出", "build_market.py", "会 read_csv、布尔筛选、groupby、merge 就够", "数据分析"],
        ["numpy", "pandas 的底层，做数值计算（本项目用得少）", "build_market.py 少量", "知道它存在即可", "数据分析"],
        ["Node.js", "跑 JS 的服务端：开端口、读文件、返回 JSON；也跑抓取脚本", "server.js、scripts/*.js", "理解「监听端口 + 收请求 + 返回」", "可能没开课，自学"],
        ["HTTP", "浏览器与服务器说话的语言：GET、状态码、Content-Type", "server.js", "知道 200/404、请求头响应头", "计算机网络"],
        ["Windows 计划任务 + VBS", "每天 22:00 自动抓实时在线且不弹黑窗", "run-daily.bat、run-daily-hidden.vbs", "会看任务计划程序里的任务", "操作系统"],
        ["PowerShell", "抓取前启停代理（本机直连 Steam 会超时）", "start-proxy.ps1、stop-proxy.ps1", "知道这是一段命令行脚本", "操作系统"],
        ["Git", "版本管理：每次改动留一个提交，能回退、能证明工作量", ".git、提交记录", "会用 add / commit / log / diff", "软件工程"],
    ],
    widths=[2.4, 6.4, 4.4, 5.2, 2.6],
    first_col_bold=True,
)

callout("看清一件事：这个项目的难点不在技术，而在把 5 个各自简单的东西接成一条不出错的链。\n"
        "没有数据库、没有框架、没有机器学习，全部是「读文件 → 算数 → 画图」。\n"
        "所以你完全有能力讲清楚它——只要按上面那条链讲。", bg="F2F7EE")
