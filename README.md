# Steam 游戏市场洞察（Steam Market Insight）

> 把 Steam 上数万款游戏的数据，变成一张"只开一晚的游戏货架"海报：纸、墨、价签、奖牌，把市场判断印在墙上。

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
- 数据**每日自动更新**（Windows 计划任务，每天 22:00）
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

- **数据获取**：Kaggle《Steam Games Dataset 2025》全量数据集（约 175MB）；Steam 官方公开接口爬虫抓取 **123 款真实游戏**（覆盖热销、新品、特惠等榜单，含价格、好评率、类型、发售日期等字段）
- **每日自动更新**：Windows 计划任务 `SteamMarketCrawlerDaily` 每天 22:00 自动抓取，失败自动重试、不覆盖旧数据
- **本地数据服务**：Node 迷你服务器（静态页面托管 + `/api/games`、`/api/meta`、`/api/online` 数据接口）
- **可视化技术**：ECharts 全部基础图表 + 进阶图表（散点图、雷达图、热力图、词云图）练习完成，库已本地化到 `js/`，断网可运行
- **真实数据接入**："好评率 TOP10"页面已接入爬虫真实数据（含评价数门槛、防 XSS、数据更新时间显示）
- **工程基础**：Git 版本管理、需求文档（`doc/steam-crawler/`：roadmap + task-list）

### 进行中 🔄

- **三页洞察站**（第5周）：首页「只开一晚的游戏货架」+ 口碑分析页 + 市场趋势页；共享同一套 123 款样本与本地 ECharts。

### 下一步 ☐

- 补充更多年份/类型的交叉分析，完善移动端阅读
- 项目文档完善、演示视频录制、期末现场展示验收

---

## 目录说明（先看这一段）

- `practice/`：每周练习作业，不是主站代码；`practice/week03/第三周小页面.html` 是独立练习页，随时可以单独打开。
- `data/cleaned/`：另一套来自 `archive` 的 **107 款**清洗产物，用于对照实验；主站首页统一读取 `data/games.json` 的 **123 款**样本，两者不要混用。
- `js/papaparse.min.js`：练习页与 `scripts/verify_week9_data.js` 仍在使用，保留。
- `data/` 下的 `games.json`、`meta.json`、`online.json` 由 `npm run crawl` 生成；页面加载时优先请求 `/api/*`，失败则回退 `js/data.js` 的静态快照（双击 `index.html` 也能打开）。

## 快速开始

本机已装 Node.js（v22），**不需要安装任何依赖**。打开命令行（PowerShell），进入项目根目录 `F:\steam-market-insight`：

```bash
# 1. 抓取数据（首次约 1~3 分钟，会生成 data/games.json + data/meta.json + data/online.json）
npm run crawl

# 2. 启动本地服务器（保持这个窗口开着）
npm start

# 3. 浏览器打开 http://localhost:8080/
#    首页：          http://localhost:8080/index.html
#    口碑分析：      http://localhost:8080/index.html#chapter-reviews
#    市场趋势：      http://localhost:8080/index.html#chapter-trends
#    数据接口：      http://localhost:8080/api/games
#    练习索引：      http://localhost:8080/practice/
#    第5周练习：     http://localhost:8080/practice/week05/第五周练练合集.html
```

> 跑爬虫前，请先开加速器并选择 **“Steam 商店加速”**；不要登录 Steam 账号。

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
- **当前数据量**：123 款真实游戏（截至最近一次抓取，见 `data/meta.json` 的 `fetchedAt`）
- **实时在线**：`data/online.json`，由 mostplayed 页面 + `GetNumberOfCurrentPlayers` 生成，字段为 `rank / appid / current_players / last_week_rank`；前端归一化后同时兼容旧的 `peak_in_game` 快照。
- **更新频率**：每天自动更新一次 + 随时手动 `npm run crawl`（见下）
- **容错**：抓取失败自动重试、保留上一次数据；免费游戏价格 0；无评分的游戏 `rating` 为 null

## 每日自动更新（Windows 任务计划）

项目已配置一个 Windows 计划任务，**每天 22:00** 自动运行 `scripts/run-daily.bat` 抓取数据（当前触发时间：22:00，日期 2026-10-26 起生效）。
- 任务名 `SteamMarketCrawlerDaily`，触发方式：每日 22:00
- 执行内容：`F:\steam-market-insight\scripts\run-daily.bat` → `node scripts\crawler.js`，日志追加到 `data\crawler.log`
- 查看/修改：`Win + R` 输入 `taskschd.msc`，任务名 `SteamMarketCrawlerDaily`
- 改时间（命令行，不必开图形界面）：`schtasks /change /TN "SteamMarketCrawlerDaily" /ST 22:00`
- 立即手动触发：任务计划程序里右键该任务 → 运行；或直接 `npm run crawl`
- 注意：该任务为「仅在用户登录时运行」（交互式），保持当前 Windows 用户登录（不必开窗口）到 22:00 即可自动执行；抓取失败会保留上一次数据并返回非 0 退出码
- 已开启容错：错过 22:00（关机/休眠）后开机会尽快补跑一次；笔记本电池供电时也允许运行
- 网络依赖：这台机器直连 `store.steampowered.com` 会 TCP 超时（`api.steampowered.com` 正常），所以 `run-daily.bat` 会先调用 `scripts/start-proxy.ps1`：
  - 若 `127.0.0.1:7897` 已在监听（Clash Verge 开着），直接复用；
  - 否则用 `clash_verge_service` 的安装路径找到 `verge-mihomo.exe`，以 `-d <配置目录> -f clash-verge.yaml` 无界面启动，等端口就绪后再让 Node 走 `NODE_USE_ENV_PROXY=1 + HTTPS_PROXY=http://127.0.0.1:7897`；
  - 抓取结束由 `scripts/stop-proxy.ps1` **只关闭本次自己启动的** mihomo（有 `data/.proxy.pid` 才动手），不会误杀你手动开着的 Clash；
  - 找不到代理时自动退回直连，任务不会因此中断。
- 生成产物：爬虫成功后更新 `data/games.json`、`data/meta.json`、`data/online.json`；页面优先用 `/api/*`，失败时回退 `js/data.js` 的 123 款快照，页头标签会显示 `本地快照` / `离线快照` 以区分数据来源。

### 「数据更新时间」没变时怎么查

1. 看 `data/crawler.log` 末尾有没有 `update OK`；出现 `update FAILED` 说明当晚抓取失败（文件保留旧数据）。
2. 任务计划程序 → `SteamMarketCrawlerDaily` → 「上次运行结果」：`0x0` 成功，`0x1` 表示爬虫返回非 0。
3. 看 `data/meta.json` 的 `fetchedAt` 与 `data/online.json` 的 `fetchedAt`；两者都新 = 写作成功。
4. 页面标签若显示「离线快照」，说明 `/api/*` 没连上（例如直接双击 `index.html` 打开），此时数据来自 `js/data.js`；用 `npm start` 后访问 `http://localhost:8080/` 可看到 `/api/*` 的数据。

## 第九周学习指引（爬虫代码怎么读）

爬虫主脚本在 `scripts/crawler.js`，按这个顺序读：

1. **配置区**：所有可调参数（并发数、重试、榜单来源）都在文件顶部
2. **工具函数**：`sleep`（限速）、`fetchJson`（超时+重试）、`writeJsonAtomic`（原子写入）、`extractAppId`（从 URL 解析 appid）
3. **第 1 步 getAppIdPool**：怎么拿到"要抓哪些游戏"（游戏池）
4. **第 2+3 步 fetchOneGame**：单款游戏的详情 + 好评率抓取与字段组装
5. **第 4 步 main**：分批并发、进度统计、汇总写文件

三个爬虫铁律（代码里都有体现）：**限速**（别把服务器打爆）、**重试**（网络会抖）、**原子写**（失败不能覆盖旧数据）。

## 项目文件与练习的分界

根目录下**只有这些是项目本体**：`index.html`、`js\`、`CSS\`、`data\`、`scripts\`（爬虫与清洗）、`server.js`、`package.json`、`doc\`（需求与教程）、`README.md`。

**`practice\` 是课程练习区**，和项目无关，可以整体忽略或压缩备份；打开 `practice\index.html`（或 `npm start` 后访问 `/practice/`）即可按周查看所有练习。练习页仍在项目内，所以它们照常引用上级目录的 `js\` 与 `data\`，双击/本地服务器都能打开。

**`data\cleaned\` 是什么**：它是 archive 数据集里与项目游戏交集样本的清洗结果和核查报告，只用于核对数据质量 / 附录，不是首页 123 款叙事样本的直接来源；首页样本来自 `data\games.json`。

## 目录结构

```
F:\steam-market-insight\
├── index.html              首页「只开一晚的游戏货架」海报（含口碑分析、市场趋势两章）
├── js\                     echarts.min.js / echarts-wordcloud / papaparse（已本地化，断网可用）
│   ├── main.js             首页数据、图表与顶栏章节导航
│   ├── insight-core.js     口碑/趋势章节共享数据与工具
│   ├── reviews.js          口碑章节交互
│   └── trends.js           趋势章节交互
├── CSS\                    页面样式
├── practice\               课程练习区（与项目正式代码分开；练习页仍引用上级的 js\ 和 data\）
│   ├── index.html          练习索引页（打开 practice/ 即可看到全部练习）
│   ├── week01\ ~ week05\   第 1~5 周 HTML / ECharts 练习
│   ├── week09\             第 9 周练习
│   └── python\             第 7~8 周 Python 练习、清洗数据与洞察报告
├── assets\                 页面配图
├── data\
│   ├── games.json          爬虫输出的真实数据（123 款，活数据）
│   ├── online.json         TOP10 实时在线（mostplayed + GetNumberOfCurrentPlayers）
│   └── meta.json           抓取时间 / 条数等元信息
├── scripts\
│   ├── crawler.js          爬虫主脚本（教学式注释）
│   ├── clean_data.py       数据清洗（第二份原始数据 → 分析用）
│   └── run-daily.bat       每日自动更新用的批处理
├── server.js               迷你服务器（静态 + /api/games）
├── package.json            npm 脚本入口
└── doc\                    需求与教程（steam-crawler\、data-clean\）
```

## 常见问题

| 问题 | 处理 |
|---|---|
| `npm run crawl` 报"Steam 接口当前不可达" | 国内访问 Steam 会间歇性断连，等几分钟重试即可；旧数据不会丢 |
| 端口 8080 被占用 | `$env:PORT=8090; npm start`（或临时改 server.js 顶部 PORT） |
| 页面数据是旧的 | 看页面副标题的"更新于"时间；运行 `npm run crawl` 刷新 |
| 直接双击 html 打开（file:// 协议） | 页面会自动降级使用 `js/data.js` 的本地数据；实时 TOP10 仍以 `npm start` 时的 `/api/online` 为准 |
