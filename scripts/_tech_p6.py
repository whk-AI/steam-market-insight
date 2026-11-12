# -*- coding: utf-8 -*-
# 分片 6：第 8 节 动手改 + 第 9 节 答辩讲技术 + 第 10 节 名词表 + 附录

h1("8　动手改五处：从「看得懂」到「改得动」")
para("看懂代码的标准不是能复述，而是能安全地改一个地方并且知道后果。下面五个练习按难度排序，"
     "每一处都给了改哪个文件、哪一行、改完怎么验证。建议真的动手做一遍——做完这五个，这个项目就是你自己的了。", space_after=4)

h2("练习 1（10 分钟）改一句文案")
para("目标：把首页摘要卡里的一句话换成你自己的说法，并确认刷新后真的变了。", space_after=2)
steps([
    "打开 index.html，搜 `#brief`（第 67 行），找到五张发现卡里的文字。",
    "注意：卡里的数字是 JS 填的（`char__count` 之类），但**标题和副标题是静态 HTML**，直接改。",
    "保存 → 浏览器刷新（服务器不用重启，静态文件每次现读）。",
])
para("验证：改对了就变；没变说明你改的是另一处同名文案，用 Ctrl+F 数一数出现了几次。", size=9.5, color=MUTED, space_after=4)

h2("练习 2（30 分钟）给 TOP500 表加一个「按年份过滤」")
para("目标：在档案区加一个年份下拉，选 2020 只看 2020 年发行的游戏。这是最典型的「加一个筛选项」需求，套路固定："
     "HTML 加控件 → 读控件的值 → 过滤数据 → 重新渲染。", space_after=2)
steps([
    "index.html 第 352 行附近，照着已有的 `<select id=\"archive-genre\">` 复制一个 `<select id=\"archive-year\">`，选项先写 2020/2021/2022。",
    "lobby.js 的 initArchive（700）里，找到给 `#archive-genre` 绑 change 的那一行（723），照抄一份给 `#archive-year`。",
    "在 render 闭包（705–721）的过滤条件里，加一条 `if (year && g.year !== year) return false;`——"
    "注意 year 要 number 型，`select.value` 是字符串，用 `Number()` 转。",
    "保存 → 刷新 → 选一个年份，表格行数应该变少且都符合年份。",
])
callout("这类需求的风险点永远在数据类型：HTML 里取出来的值都是字符串，JSON 里 year 是数字，"
        "用 `===` 比较会永远不相等。这不是 bug，是语言特性——所以第 3 步特意写了 Number()。", bg="FDF3E7")

h2("练习 3（1 小时）加第六张图：年度发行量折线")
para("目标：数据里已经有 `year_dist`（每年发行多少款），但页面没单独画它。加一张折线图，正好验证你理解了「数据 → setOption」。", space_after=2)
steps([
    "index.html：在 `#season`（229）里或新开一个 section，放一个空容器 `<div class=\"chart\" id=\"year-line\"></div>`。",
    "lobby.js：写一个新函数 `initYearLine(agg)`，里面 `echarts.init(document.getElementById('year-line'))`，"
    "xAxis.data 用 `Object.keys(agg.year_dist).sort()`，series.data 用对应的值，type 写 `line`。",
    "在 init（1030）里，数据加载完之后调一次 `initYearLine(state.agg)`——位置放在其他 init 后面。",
    "保存刷新，看图上有没有一条 2010 到 2025 的曲线。没有就打开浏览器 F12 的 Console 看报错。",
])
para("注意两点：`year_dist` 里有一个 key 是 0（缺年份的 34,502 款），画折线前要 filter 掉，否则会出现一个离谱的尖峰；"
     "另外容器必须有明确高度（CSS 的 `.chart` 已给 420px），否则 ECharts 画出来是 0 高——这是新手最常踩的坑。",
     size=10, space_after=4)

h2("练习 4（1 小时）改一个数据口径并重跑")
para("目标：把价格分箱的边界改一下（比如把 1-30 拆成 1-10 和 11-30），看看从数据到页面的整条链路怎么联动。", space_after=2)
steps([
    "scripts/build_market.py 第 381–394 行的 band_of 函数，改分档的阈值和标签。",
    "项目根目录执行 `python scripts/build_market.py`，等它打印完自检信息（约 1–2 分钟）。",
    "它会重写 data/market/market_agg.json 与 market_full.csv；刷新页面，价格带图自动变成 7 根柱子。",
    "如果页面没变，检查是不是浏览器缓存：Ctrl+F5 强刷。",
])
callout("这一步是「可复核」的实证：改一行 Python → 重跑 → 页面数字随之变化，说明页面上每个数字都真的来自数据，不是手写的。\n"
        "答辩演示这个动作，比讲十句「数据驱动」都有用。", bg="F2F7EE")

h2("练习 5（进阶）修两个已知 bug")
para("诚实地修自己代码里的问题，比再做一个新功能更能证明成长。这两处都在 build_market.py：", space_after=2)
table(["位置", "现在的写法", "问题", "怎么修"],
      [["377 行附近 withDate", "用「日期列非空」计数", "空日期早在 354 行被写成字符串 UNKNOWN，所以永远非空，withDate 恒等于总行数",
        "改成 `sum(1 for v in dates if v != 'UNKNOWN')`，或干脆在 354 行前统计"],
       ["493 行 top500 排序", "按 `rating.notna()` 过滤后按推荐数排序", "archive 没有 rating 字段，该条件恒真，结果实为「推荐数 TOP500」，与命名不符",
        "要么改名为 top_by_recommendations（已经这么存了，改页面文案即可），要么换成按评论数/好评率排"]],
      [3.0, 5.0, 4.4, 3.8],
      caption="表 8-1　两个已知 bug 的位置与修法")
para("修完重跑脚本、刷新页面、用 git 提交一次——顺便把提交次数从 13 次往上加，任务书要求的 15 次就从这里开始补。",
     size=10, space_after=4)

h1("9　答辩时怎么讲「技术」")
para("老师问技术，通常不是要你背名词，而是想确认三件事：这些代码是不是你写的、你知不知道为什么这么写、你知不知道自己哪里没做好。"
     "所以讲技术不是「念技术栈」，而是「讲取舍」。", space_after=4)

h2("9.1　30 秒版（如果只让你说一句）")
callout("技术上我用的是最朴素的组合：Python 做数据清洗和聚合，Node 起一个 149 行的静态服务器提供接口，"
        "前端是原生 JS 加 ECharts 画 5 张图。没有框架、没有数据库，因为数据是静态快照，加这些东西只会增加复杂度。"
        "代价我也写在 README 里：必须 npm start，不能双击打开。", bg="EAF1F8")

h2("9.2　2 分钟版（讲清链路）")
para("按「数据从哪来 → 怎么变干净 → 怎么进浏览器 → 怎么变成图」四段讲，每段带一个具体数字或行号：", space_after=2)
steps([
    "来源：archive 全量表 15 万款游戏 + HuggingFace 2,000 条真实评价 + Steam 官方榜单实时 TOP10，三源互不重叠。",
    "清洗：一个 587 行的 Python 脚本，只留 type=game、价格按币种汇率折算、缺失年份单独标记，产出 1.2MB 聚合 JSON。",
    "服务：149 行 Node 服务器，6 个 /api 路由 + 静态托管，处理了路径穿越、gzip、畸形 URL 编码。",
    "呈现：单页 9 节，5 张 ECharts 图 + 6 类交互，所有结论都标注口径和限制。",
], size=10)
para("然后补一句「这套流程里我最想讲的是三个取舍」——把第 7 节的三条决策说出来（预聚合 vs 直接读 CSV、多主类型 vs 强行分类、"
     "保留旧快照 vs 补数字），每条都带代价。这样老师会从「考你」变成「跟你讨论」。", space_after=4)

h2("9.3　被追问时的三条原则")
table(["原则", "怎么说", "为什么有效"],
      [["先给结论，再给行号", "「因为浏览器解析 15 万行会卡死，所以预聚合。具体在 build_market.py 534 行。」",
        "有结论说明你想过，有行号说明是你写的"],
       ["主动交代限制", "「这块我只做到了 X，没做 Y，原因是 Z。」", "比被问出来强十倍，也显得诚实"],
       ["不会就说没做", "「60 秒自动刷新我没做，只做了打开即拉取，已经写进下一步。」", "含糊其辞才会被追打"]],
      [3.2, 8.4, 4.6],
      caption="表 9-1　技术追问的应答原则")
para("八个最可能被问的技术点，答案都已经在本文里：为什么不用框架（第 7 节①）、为什么不用数据库（同）、"
     "为什么 CSV 换成 JSON（第 6 节）、为什么必须起服务（5.2）、词云标签哪来的（4.2、第 7 节⑨）、"
     "热力图为什么不是类型×好评率（答辩提纲 Q8）、数据怎么保证没编（第 6 节最后一段）、你负责哪部分（全部）。", space_after=4)

h1("10　名词表：看代码时遇到的词，一句话解释")
glossary = [
    ("HTML", "网页的骨架，用标签描述「这里有什么」。"),
    ("CSS", "网页的皮肤，用选择器描述「长什么样」。"),
    ("DOM", "浏览器把 HTML 解析成的一棵树，JS 通过它找元素、改内容。"),
    ("IIFE", "立即执行的函数表达式 `(function(){...})()`，用来把变量关在局部，不污染全局。"),
    ("fetch", "浏览器发网络请求的函数，返回 Promise。"),
    ("JSON", "一种文本格式，长得像 JS 对象，前后端交换数据的通用语言。"),
    ("Promise / async-await", "表示「未来才有结果」的对象；await 就是等它兑现。"),
    ("API / 接口", "程序之间的约定地址，比如 /api/market/agg 返回聚合数据。"),
    ("HTTP 状态码", "200 成功、404 找不到、403 禁止、500 服务器出错。"),
    ("MIME", "告诉浏览器这份内容是 html、json 还是 png，决定它怎么解析。"),
    ("gzip", "传输前压缩，浏览器自动解压；文本文件能省 70% 流量。"),
    ("路由", "服务器按 URL 路径决定执行哪段代码。"),
    ("ECharts option", "图表的全部配置：坐标系、数据系列、提示框、配色。"),
    ("series", "option 里的数据系列，一个 series 就是一组图。"),
    ("pandas DataFrame", "带列名的二维表，可以理解成「代码里的 Excel」。"),
    ("groupby", "按某列分组再统计，等于 Excel 的数据透视表。"),
    ("正则表达式", "用模式匹配文本，比如从 HTML 里抠出 appid。"),
    ("setInterval / setTimeout", "定时器：前者每 N 毫秒重复，后者延迟一次。"),
    ("IntersectionObserver", "监听元素是否滚进视口，用来做入场动画和导航高亮。"),
    ("sticky", "CSS 定位：滚动到边界时「粘住」，表格头常用。"),
    ("媒体查询", "@media，按屏幕宽度/打印切换样式。"),
    ("环境变量", "进程启动时传入的配置，比如 PORT、STEAM_API_KEY。"),
    ("计划任务", "Windows 的定时执行器，本项目每天 22:00 跑抓取。"),
    ("git commit", "把一次改动记进版本历史，带一句说明。"),
]
table(["词", "一句话解释"],
      [[k, v] for k, v in glossary],
      [4.0, 12.2],
      caption="表 10-1　项目里出现的技术名词")

h1("附录")
h2("附录 A　四周补课路线（每天 1 小时）")
para("如果时间紧，就按这个顺序补，每一步都对着本项目的真实文件练，不要看纯教程：", space_after=2)
table(["周", "补什么", "对着哪个文件练", "练完能做到"],
      [["第 1 周", "HTML + CSS 基础（标签、选择器、盒模型、flex/grid）", "index.html 的一个 section + CSS/lobby.css 对应块",
        "能改布局、加一个卡片、调间距"],
       ["第 2 周", "JS 基础（变量、函数、数组方法、DOM 操作、事件）", "js/lobby.js 的 fmt/esc/initMeta",
        "能读懂 100 行 JS，能加一个筛选"],
       ["第 3 周", "fetch + JSON + ECharts", "apiWithFallback（76）+ initPrice（436）",
        "能加一张新图"],
       ["第 4 周", "pandas 三招 + 一个 Node 服务器", "build_market.py 270–417 + server.js 全文",
        "能改口径重跑、能解释每条路由"]],
      [1.6, 6.4, 6.0, 4.0],
      caption="表 A-1　按周补课，全部对着真实代码")

h2("附录 B　命令速查")
for _cmd, _desc in [
    ("npm start", "启动服务器，访问 http://localhost:8081/（答辩前必做）"),
    ("node server.js", "同上，不经 npm 脚本；可用 PORT=8090 node server.js 换端口"),
    ("python scripts/build_market.py", "重跑数据清洗与聚合，重写 data/market/*"),
    ("python scripts/fetch_hf_reviews.py", "重新抓 2,000 条 HuggingFace 评价"),
    ("node scripts/fetch_online.js", "手动刷一次实时 TOP10（失败不覆盖旧文件）"),
    ("npm run crawl", "跑 123 款演示数据的抓取"),
    ("git log --oneline", "看提交历史；答辩时证明迭代过程"),
    ("git status", "看有哪些改动还没提交"),
    ("schtasks /query /tn SteamMarketCrawlerDaily", "确认每日 22:00 的抓取任务还在"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r1 = p.add_run(_cmd.ljust(42))
    r1.font.name = MONO
    r1._element.rPr.rFonts.set(qn("w:eastAsia"), MONO)
    r1.font.size = Pt(9.5)
    r1.font.color.rgb = ACCENT
    r2 = p.add_run(_desc)
    r2.font.name = FONT
    r2._element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
    r2.font.size = Pt(9.5)
    r2.font.color.rgb = MUTED

h2("附录 C　出问题时的排查表")
table(["现象", "先看哪里", "常见原因"],
      [["页面能开但没图 / 顶部显示错误条", "F12 Console + Network 里 /api 请求是否 200", "服务器没起、端口被占、JSON 路径写错"],
       ["整页白屏", "F12 Console 第一条红色的错误", "JS 语法错误、脚本 404、ECharts 没加载成功"],
       ["中文变乱码", "Network 里响应的 Content-Type", "缺 charset=utf-8（server.js 的 MIME 表）"],
       ["改了数据页面没变", "Ctrl+F5 强刷；再确认 JSON 的修改时间", "浏览器缓存 / 脚本跑失败没写入"],
       ["node 进程莫名退出", "终端里的 URIError 报错", "畸形 URL 编码（safeDecode 已修，改代码时别退回旧写法）"],
       ["双击 index.html 打不开图", "地址栏是不是 file://", "fetch 被跨域拦截，必须 npm start"]],
      [5.0, 6.4, 4.8],
      caption="表 C-1　六个高频现象的排查顺序")

h2("附录 D　如果只记住十句话")
steps([
    "页面上的每个数字都来自 data/market/ 里的 JSON，JSON 来自 scripts/ 里的脚本，脚本读的是 archive 的 CSV。",
    "浏览器不能直接读硬盘，所以必须有一个服务器（npm start），这是 file:// 打不开的原因。",
    "ECharts 的画法只有一个：给容器 + 给 option，改图就是再 setOption 一次。",
    "交互的写法只有一个：听事件 → 改 state → 调 render。",
    "pandas 的三招是 read_csv、布尔掩码、groupby，其余都是组合。",
    "服务器就是「等请求 → 看路径 → 回内容」，149 行不神秘。",
    "动画回放就是定时器改数组再重画，难点在收尾（停定时器）。",
    "类型数量相加超过总量是正常的，因为是多标签——口径写在页面上。",
    "口碑只覆盖 1.3%，所有结论只对样本负责，这句话必须主动说。",
    "没做的（60 秒刷新、15 次提交）主动写进下一步，比藏着强。",
], size=10)
