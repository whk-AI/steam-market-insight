# -*- coding: utf-8 -*-
# 分片 4：4.4 展示层 + 第 5 节 核心原理 + 第 6 节 端到端走查

h2("4.4　展示层：页面、图表、交互是怎么来的")

para("前端只有一个业务脚本 js/lobby.js（1,065 行，整个文件用一个 IIFE 包住，避免变量污染全局），"
     "但读它不能从头读到尾——正确顺序是：先看 index.html 的 9 个 section 认骨架，再按「每个 section 对应哪个 init 函数」跳读。",
     space_after=4)

table(["#", "section id", "行号", "这一节讲什么", "涉及交互"],
      [["1", "#brief", "67", "研究摘要：一句结论 + 5 张数字发现卡", "滚动进入时数字滚动"],
       ["2", "#lobby", "115", "类型版图：10 个类型角色 + 类型关系网", "悬停角色高亮连线"],
       ["3", "#cycle", "204", "类型生命周期：年份×类型热力图", "点格子开档案、切数量/份额"],
       ["4", "#season", "229", "2010–2025 供给曲线 + 4 张事件卡 + 16 根柱回放", "播放/暂停、点事件卡"],
       ["5", "#price", "277", "价格分层：价格带柱图 + 类型散点", "悬停看类型明细"],
       ["6", "#arena", "306", "实时 TOP10 在线人数", "读接口、显示抓取时间"],
       ["7", "#reputation", "327", "口碑分层：S/A/B/C 分档 + 标签词云", "切换分档、点词云标签"],
       ["8", "#archive", "352", "TOP500 明细表", "搜索 + 类型下拉 + 点行开抽屉"],
       ["9", "#method", "386", "方法论与敏感性说明", "切换门槛重算"]],
      [0.8, 3.8, 2.4, 6.6, 5.4],
      caption="表 4-2　index.html 的 9 个 section（行号以当前版本为准，改动后会平移）")

para("那 5 张图分别在哪一行画的？全部用 window.echarts，同一个模式：init 函数里 echarts.init(容器) 拿实例，"
     "再 setOption({...}) 把数据灌进去。", space_after=3)

table(["图", "画它的函数", "行号", "图表类型", "吃的数据键"],
      [["价格带分布", "initPrice", "441", "柱状图 bar", "price_bands"],
       ["类型性价比", "initPrice", "481", "散点图 scatter", "type_dist（x 均价 / y 好评率 / 气泡=评论数）"],
       ["标签词云", "renderReputationCloud", "659", "词云 wordCloud", "sub_tag_dist 汇总取前 72"],
       ["单类型趋势", "renderDossierTrend", "777", "折线+面积 line", "type_x_year 的 values[2010..2025]"],
       ["类型生命周期", "initCycle", "843", "热力图 heatmap", "type_x_year + type_x_year_years"]],
      [2.8, 4.6, 2.0, 3.2, 6.6],
      caption="表 4-3　5 张 ECharts 图的数据来源")

para("交互是「任务书要求至少 2 类」的地方，实际做了 6 类。注意每类都指向具体事件和函数，答辩被问「交互在哪」直接报行号：",
     space_after=3)

table(["交互", "怎么触发", "代码位置", "触发后发生什么"],
      [["悬停类型关系网", ".char 的 mouseenter / focus", "289–294；highlight 272–287", "其余角色变暗、相关连线亮起，SVG 重画（draw 250–270）"],
       ["点热力图格子", "chart.on('click')", "926–929", "按格子对应的类型打开右侧档案抽屉"],
       ["点时间轴", "事件委托 closest('.season-event')", "374–382；柱子 369–373", "先停播放，再跳到那一年的状态"],
       ["S/A/B/C 切换", "#rep-grades 委托", "602–608 → renderReputation 687", "按评论数档位重排榜单和词云"],
       ["点词云标签", "chart.on('click') / 标签按钮", "662；按钮 667–672", "列出该标签下的代表性游戏（showTagResult 676）"],
       ["搜索 + 类型下拉", "input / change", "722、723；render 闭包 705–721", "按类型和关键词过滤 TOP500 表，行点击开抽屉"]],
      [3.4, 5.0, 4.6, 7.0],
      caption="表 4-4　6 类「输入即展示」交互")

para("CSS 只挑三个真正在用的技术点说，其余是审美问题，不必背：", space_after=3)
bullets([
    "**变量**：颜色、间距都写成 --token（CSS/lobby.css:1–19），换肤只改一处；角色卡片的 3D 倾斜用 --x/--y/--z 内联变量"
    "（index.html:135 写入，lobby.css:381–395 消费），鼠标位置写 --mx/--my（lobby.js:321）。",
    "**Grid 做布局**：4 列统计卡（lobby.css:465）、260px+1fr 双栏（:481）、1fr+320px 主图+抽屉（:539）。",
    "**整页滚动叙事**：每个 section 撑满一屏（100vh）+ scroll-snap-align（:146），顶栏 fixed，表格头 sticky（:558），"
    "打印时另有一套媒体查询（:1175）。",
])

para("页面启动的完整顺序只有四步（也是你排查「白屏」的顺序）：", space_after=2)
steps([
    "浏览器按 index.html:461–464 的顺序加载 ECharts → 词云插件 → data.js → lobby.js（顺序不能乱，后者依赖前者）。",
    "lobby.js 最后一行 init()（1030）在 DOMContentLoaded 后执行。",
    "init 里用 Promise.all 并发打四路数据（1035–1040），每路都是 apiWithFallback：先请求 /api/xxx，失败才读静态 JSON。",
    "数据齐了以后，initMeta 填数字、各 init 函数画图、initNav 挂滚动监听。任何一路失败都会走 setBootError（88）显示错误而不是白屏。",
])

h1("5　七块核心原理：不懂这几个概念，代码永远是别人的")
para("这一节是给你补「地基」的。每块只讲三件事：这个概念解决什么问题、最小的代码长什么样、在这个项目里出现在哪一行。"
     "把这七块看懂，再看任何 Web 数据可视化项目都能上手。", space_after=4)

# 5.1
h2("5.1　HTML / CSS / JS 是三份文件，各管一件事")
para("一句话：HTML 是骨架（有什么），CSS 是皮肤（长什么样），JS 是肌肉（会做什么）。"
     "浏览器把三份文件合起来渲染成一张画面，它们之间靠「选择器」和「DOM 元素」对上号。", space_after=3)
code("""<!-- HTML：定义一个盒子，给它一个 id -->
<div id="price-chart" class="chart"></div>

/* CSS：选中所有 class=chart 的元素，给它高度 */
.chart { width: 100%; height: 420px; }

// JS：按 id 找到这个盒子，往里塞一张图
const el = document.getElementById('price-chart');
echarts.init(el).setOption({ xAxis: { data: ['免费', '1-30'] }, series: [{ type: 'bar', data: [18994, 88168] }] });""")
para("对应到项目：index.html 里每个图表容器都是空的 `<div class=\"chart\" id=\"...\">`，真正的内容是 lobby.js 运行时塞进去的。"
     "所以「页面看起来有图」不等于「HTML 里有图」——搜 HTML 搜不到数据是正常的。", space_after=4)

# 5.2
h2("5.2　浏览器怎么拿到数据：fetch 请求一个 JSON 文件")
para("浏览器不能直接读硬盘上的文件（安全限制），只能向「地址」要东西。fetch 就是这个「要」的动作，"
     "它返回一个 Promise（未来才会有结果），所以要 await。拿到的响应再 .json() 转成对象。", space_after=3)
code("""const res = await fetch('data/market/market_agg.json');  // 发起请求
const data = await res.json();                          // 把响应体解析成 JS 对象
console.log(data.price_bands[0]);                       // { band: '免费', count: 18994 }""")
para("两个必须知道的坑：① 双击打开页面时地址是 file://，浏览器会以跨域为由拒绝 fetch 本地文件——"
     "这是本项目「必须 npm start」的根本原因，不是配置问题；② 请求可能失败，所以 lobby.js 用 apiWithFallback 包了一层，"
     "先试 /api/...（服务器给），失败再试静态文件（服务器也能直接托管），两道保险。", space_after=4)

# 5.3
h2("5.3　ECharts 的图表是「配置」出来的，不是画出来的")
para("ECharts 的用法只有一个：给它一个容器 + 一个 option 对象，它负责画。option 里 xAxis/yAxis 是坐标系，series 是数据系列，"
     "一个 option 可以放多个 series，就变成多图叠加。改图不是重画，而是再 setOption 一次（它做增量合并）。", space_after=3)
code("""const chart = echarts.init(document.getElementById('price-chart'));
chart.setOption({
  xAxis: { type: 'category', data: bands.map(b => b.band) },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: bands.map(b => b.count) }],
  tooltip: { trigger: 'axis' }        // 鼠标悬停时的提示框
});""")
para("项目里 5 张图共用这个套路，区别只在 type 和数据键（见下表 4-3）。想改配色就改 option.color，想改柱子宽度就改 series.barWidth，"
     "不需要碰任何绘制逻辑——这就是用图表库的意义。", space_after=4)

# 5.4
h2("5.4　交互 = 听事件 → 改状态 → 局部重绘")
para("浏览器里一切「用户做了什么」都是事件（click、input、mouseenter）。处理函数里只做两件事：更新一个变量（state），"
     "然后调用重绘函数。不要直接改 DOM 的每个数字——那是 jQuery 时代的写法，越写越乱。", space_after=3)
code("""let grade = 'S';
document.querySelector('#rep-grades').addEventListener('click', (e) => {
  const btn = e.target.closest('[data-grade]');
  if (!btn) return;                 // 点到空白就退出（事件委托的必备判断）
  grade = btn.dataset.grade;        // 1. 只改状态
  renderReputation();               // 2. 交给渲染函数重新算、重新画
});""")
para("项目里 6 类交互全是这个结构：事件监听 → 写 state / 取数据 → 调对应的 render 函数。"
     "注意「事件委托」这个词：把监听挂在父容器上，靠 e.target.closest() 判断点到哪个子元素——"
     "这样列表里 500 行只挂 1 个监听，而不是 500 个。", space_after=4)

# 5.5
h2("5.5　pandas 不是数据库：它就是「带列名的 Excel 操作」")
para("pandas 的核心只有三招：read_csv 读表、布尔掩码筛行、groupby 分组算。剩下的都是组合。"
     "看懂这三招，587 行的 build_market.py 就不会显得神秘。", space_after=3)
code("""import pandas as pd
df = pd.read_csv('applications.csv', usecols=['appid', 'name', 'type', 'price'])
games = df[df['type'] == 'game']                       # 掩码筛选（像 Excel 的筛选器）
by_year = games.groupby('year')['appid'].count()       # 分组计数
print(games.shape, len(by_year))""")
para("这个脚本「手工感」很重，是故意的：作者没用 dropna/merge/cut/explode，而是用 clean_text、dict.get、手写 band_of、split(',') "
     "一步步替换——好处是每一步都能 print 出来核对，出错时能定位到具体一行。代价是代码长。这也是答辩时一个很好的回答："
     "「我知道 pandas 有一行写法，但我要每一步可验证」。", space_after=4)

# 5.6
h2("5.6　HTTP 服务器不是魔法：一个循环 + 一张路由表")
para("服务器本质就是「等请求 → 看路径 → 回内容」。Node 自带的 http 模块 20 行就能做一个能用的静态服务器，"
     "不需要 Express。理解这一点，你就知道 npm start 之后发生了什么。", space_after=3)
code("""const http = require('http');
const fs = require('fs');
http.createServer((req, res) => {
  const url = req.url === '/' ? '/index.html' : req.url;   // 默认首页
  fs.readFile('.' + url, (err, buf) => {
    if (err) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(buf);
  });
}).listen(8081, () => console.log('http://localhost:8081/'));""")
para("项目的 server.js 就是这个结构的强化版：加了 MIME 表（决定浏览器当文本还是图片解析）、gzip 压缩、"
     "路径穿越防护（`../` 攻击）、/api 路由表。多出来的代码几乎都是「安全和体验」，不是「功能」。", space_after=4)

# 5.7
h2("5.7　「动画回放」= 定时器 + 改数组 + 重画")
para("ECharts 的 timeline 组件是做「多帧切换」的，而项目要的是「曲线一年一年长出来」，所以是手写："
     "一个定时器每 760ms 把 index 加一，把前 index 年的数据截出来重新 setOption，暂停就 clearInterval。", space_after=3)
code("""let i = 0;
const timer = setInterval(() => {
  i += 1;
  if (i > years.length) return clearInterval(timer);
  chart.setOption({ series: [{ data: values.slice(0, i) }] });
}, 760);""")
para("就这么简单——但要做对，得处理：播放到末尾自动停、手动点某年时先停掉定时器、离开这一节时停掉（省 CPU）。"
     "这三件事分别在 lobby.js 的 toggleSeason（409）、事件委托（374–382）、stopSeason（426）里。", space_after=4)

h1("6　一张图从 CSV 到屏幕：亲手走一遍价格带柱图")
para("「代码是怎么来的」的答案是：它是一步步长出来的。挑最简单的价格带柱图，把同一条数据走过的 6 步全走一遍，"
     "每一步都能在仓库里找到对应文件和行号。走完这一遍，你就知道改任何一个数字该动哪里。", space_after=4)

h2("第 1 步　原始表：archive 的 CSV")
para("起点是 F:\\2026.9.1\\archive\\steam_dataset_2025_csv\\applications.csv（约 20 万行），其中 type 字段有 game / dlc / demo / music 等。"
     "价格字段 mat_final_price 的单位是「分」，还有货币字段，免费游戏是 0，未定价是空。", space_after=3)

h2("第 2 步　清洗 + 分箱：build_market.py 298–401")
para("读表（270–279）→ 只留 type=='game'（280）→ 价格 ÷100 再按币种乘汇率（314）→ 空值写 price_unknown 而不是 0（301–312）"
     "→ 按阈值切档（band_of 381–394）→ 统计每档数量（403–417）→ 写进 market_agg.json 的 price_bands（563）。", space_after=3)
code("""// 产物长这样（data/market/market_agg.json 里的一小段）
"price_bands": [
  { "band": "免费",   "count": 18994 },
  { "band": "1-30",   "count": 88168 },
  { "band": "31-60",  "count": 1736 },
  { "band": "61-100", "count": 153 },
  { "band": "101-200","count": 240 },
  { "band": "200+",   "count": 14 },
  { "band": "未定价", "count": 40974 }
]""")

h2("第 3 步　服务器把它变成接口：server.js 132–137")
para("npm start 之后，访问 http://localhost:8081/api/market/agg 返回的正是这个 JSON。"
     "路由表就是几行 if-else：路径匹配上就读对应的文件、加 no-store 头返回。这一步的意义是「同一个数据既给页面用，也能被浏览器控制台直接看」。", space_after=3)

h2("第 4 步　前端请求：lobby.js 76 与 1035–1040")
para("init 里四路并发：/api/market/agg、/api/market/reviews、/api/market/top500、/api/online。"
     "apiWithFallback 先打接口，失败读 data/market/*.json——所以删掉服务器也能看（只要不双击打开）。", space_after=3)

h2("第 5 步　画图：lobby.js 436–450")
para("initPrice 拿到 agg.price_bands，先 filter 掉「未定价」（438，否则柱子会被 4 万这个空值撑爆），"
     "再 echarts.init + setOption（441）——它画的是 6 根柱子，而不是 7 根。这个「先过滤再画」是图表数据处理的常态。", space_after=3)

h2("第 6 步　屏幕上出现数字，并且能反查")
para("柱高对应 count，鼠标悬停出提示框，右边的文字写「免费游戏 18,994 款，占全量 12.6%」——12.6% 是 18994/150279 算出来的。"
     "任何一个人都能顺着这 6 步倒着走回去：屏幕上的数 → option 里的数组 → JSON 里的键 → build_market.py 的某一行 → 原始 CSV。"
     "这就是「可复核」。", space_after=4)
callout("把这张图换成任何一张：词云是 sub_tag_dist、散点是 type_dist、热力图是 type_x_year、折线是 type_x_year 的 values。\n"
        "数据键不同，但「CSV → 清洗 → JSON → 接口 → fetch → setOption」这 6 步一模一样。", bg="F2F7EE")
