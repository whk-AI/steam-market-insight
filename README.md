# Steam 游戏市场洞察（Steam Market Insight）

> 把 Steam 上数万款游戏的数据，变成"一眼看懂"的市场洞察大屏。

## 这个项目是做什么的

**一句话定位**：一个自动抓取 Steam 真实数据、用可视化图表回答"Steam 游戏市场长什么样"的数据洞察平台。

**它解决什么问题**：Steam 上有数万款游戏，价格、类型、口碑千差万别，玩家和开发者很难快速看清市场全貌。本项目把散落的数据整理成直观图表，直接回答这些问题：

- Steam 上什么类型的游戏最流行？（类型分布 / 词云）
- 游戏价格集中在哪个区间？（价格分布）
- 哪些游戏口碑最好、评价最多？（好评率榜单）
- 游戏发售数量、口碑随时间怎么变化？（年度趋势）

**给谁用**：
- **玩家**——买游戏前看市场口碑、价格与类型热度
- **开发者 / 市场观察者**——了解品类分布与发售趋势
- **数据可视化学习者**——一个"数据获取 → 处理 → 分析 → 可视化"全链路的真实案例

**项目亮点**：
- 全链路**真实数据**，不是演示假数据：Steam 官方公开接口爬虫 + Kaggle 开源数据集
- 数据**每日自动更新**（Windows 计划任务，每天 08:00）
- **断网可运行**：ECharts 等第三方库已本地化，不依赖 CDN
- 爬虫代码带**教学式注释**，适合边读边学

---

## 项目进度（截至 2026年10月 · 第5周）

> 项目按 2026-2027 第一学期导师制 16 周规划推进，当前处于**第5周：可视化进阶 / 数据大屏制作中**。

### 里程碑总览

| 阶段 | 内容 | 状态 |
|---|---|---|
| 第1-2周 | 基础准备：JS 基础、Kaggle 数据集、Git | ✅ 已完成 |
| 第3-4周 | 数据处理 + 爬虫 + 本地服务器 | ✅ 已完成 |
| 第5-6周 | 可视化进阶 + **数据大屏制作** | 🔄 进行中 |
| 第7-8周 | 交互完善（多图联动、筛选、指标卡） | ☐ 待开始 |
| 第9-12周 | 分析深化 + 平台整合 | ☐ 待开始 |
| 第13-16周 | 文档整理、演示视频、期末验收 | ☐ 待开始 |

### 已完成 ✅

- **数据获取**：Kaggle《Steam Games Dataset 2025》全量数据集（约 175MB）；Steam 官方公开接口爬虫抓取 **149 款真实游戏**（覆盖热销、新品、特惠等 6 个榜单，含价格、好评率、类型、发售日期等字段）
- **每日自动更新**：Windows 计划任务 `SteamMarketCrawlerDaily` 每天 08:00 自动抓取，失败自动重试、不覆盖旧数据
- **本地数据服务**：Node 迷你服务器（静态页面托管 + `/api/games` 数据接口）
- **可视化技术**：ECharts 全部基础图表 + 进阶图表（散点图、雷达图、热力图、词云图）练习完成，库已本地化到 `js/`，断网可运行
- **真实数据接入**："好评率 TOP10"页面已接入爬虫真实数据（含评价数门槛、防 XSS、数据更新时间显示）
- **工程基础**：Git 版本管理、需求文档（`doc/steam-crawler/`：roadmap + task-list）

### 进行中 🔄

- **Steam 数据大屏**（第5周）：制作集中展示 ≥5 个图表的可视化大屏（散点 / 雷达 / 热力 / 词云 + 基础统计图表），完成后将作为平台首页入口

### 下一步 ☐

- 大屏整合为项目首页（`index.html`）
- 交互完善：多图联动、数据筛选、指标卡
- 跨维度专题分析页面
- 项目文档完善、演示视频录制、期末现场展示验收

---

## 快速开始

本机已装 Node.js（v22），**不需要安装任何依赖**。打开命令行（PowerShell），进入项目根目录 `F:\steam-market-insight`：

```bash
# 1. 抓取数据（首次约 1~3 分钟，会生成 data/games.json + data/meta.json）
npm run crawl

# 2. 启动本地服务器（保持这个窗口开着）
npm start

# 3. 浏览器打开
#    数据接口：      http://localhost:8080/api/games
#    好评率 TOP10： http://localhost:8080/practice/第三周小页面.html
#    第5周练习：    http://localhost:8080/practice/第五周练练合集.html
```

## 常用命令

| 命令 | 作用 |
|---|---|
| `npm run crawl` | 手动更新数据（网络失败会保留旧数据，不会清空） |
| `npm run crawl -- --limit 10` | 只抓 10 款快速测试 |
| `npm start` | 启动迷你服务器（静态文件 + `/api/games`） |
| 关服务器 | 在运行 `npm start` 的窗口按 `Ctrl + C` |

## 数据说明

- **来源**：Steam 官方接口（无需 API Key）
  - `store.steampowered.com/api/featuredcategories` —— 首页榜单（游戏池）
  - `store.steampowered.com/search/results/?json=1` —— 搜索接口（榜单更全）
  - `store.steampowered.com/api/appdetails` —— 游戏详情（名称/价格/类型/发行日期）
  - `store.steampowered.com/appreviews` —— 官方评价数（算出好评率）
- **字段**：`data/games.json` 每款游戏包含
  `appid / name / price(元) / original_price / final_price / discount_percent / currency / rating(好评率%) / positive / total_reviews / type(主分类) / genres / year / release_date / url`
- **当前数据量**：149 款真实游戏（截至最近一次抓取，见 `data/meta.json` 的 `fetchedAt`）
- **更新频率**：每天自动更新一次 + 随时手动 `npm run crawl`（见下）
- **容错**：抓取失败自动重试、保留上一次数据；免费游戏价格 0；无评分的游戏 `rating` 为 null

## 每日自动更新（Windows 任务计划）

项目已配置一个 Windows 计划任务，每天 **08:00** 自动运行 `scripts/run-daily.bat` 抓取数据。
- 查看/修改：`Win + R` 输入 `taskschd.msc`，任务名 `SteamMarketCrawlerDaily`
- 立即手动触发：任务计划程序里右键该任务 → 运行；或直接 `npm run crawl`

## 第九周学习指引（爬虫代码怎么读）

爬虫主脚本在 `scripts/crawler.js`，按这个顺序读：

1. **配置区**：所有可调参数（并发数、重试、榜单来源）都在文件顶部
2. **工具函数**：`sleep`（限速）、`fetchJson`（超时+重试）、`writeJsonAtomic`（原子写入）、`extractAppId`（从 URL 解析 appid）
3. **第 1 步 getAppIdPool**：怎么拿到"要抓哪些游戏"（游戏池）
4. **第 2+3 步 fetchOneGame**：单款游戏的详情 + 好评率抓取与字段组装
5. **第 4 步 main**：分批并发、进度统计、汇总写文件

三个爬虫铁律（代码里都有体现）：**限速**（别把服务器打爆）、**重试**（网络会抖）、**原子写**（失败不能覆盖旧数据）。

## 目录结构

```
F:\steam-market-insight\
├── index.html              平台首页（数据大屏整合中）
├── js\                     echarts.min.js / echarts-wordcloud / papaparse（已本地化，断网可用）
├── CSS\                    页面样式
├── practice\               每周练习页（第1~5周，含真实数据接入页）
├── data\
│   ├── games.json          爬虫输出的真实数据（149 款，活数据）
│   └── meta.json           抓取时间 / 条数等元信息
├── scripts\
│   ├── crawler.js          爬虫主脚本（教学式注释）
│   └── run-daily.bat       每日自动更新用的批处理
├── server.js               迷你服务器（静态 + /api/games）
├── package.json            npm 脚本入口
└── doc\steam-crawler\      需求文档（roadmap + task-list）
```

## 常见问题

| 问题 | 处理 |
|---|---|
| `npm run crawl` 报"Steam 接口当前不可达" | 国内访问 Steam 会间歇性断连，等几分钟重试即可；旧数据不会丢 |
| 端口 8080 被占用 | `$env:PORT=8090; npm start`（或临时改 server.js 顶部 PORT） |
| 页面数据是旧的 | 看页面副标题的"更新于"时间；运行 `npm run crawl` 刷新 |
| 直接双击 html 打开（file:// 协议） | 浏览器会拦截 fetch，请用 `npm start` 后访问 localhost |
