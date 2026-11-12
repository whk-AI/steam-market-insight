# Steam 游戏市场洞察（Steam Market Insight）

> 一份关于 Steam 市场结构的数据报告：150,279 款游戏、2010—2025 供给曲线、2,000 份真实口碑样本。先给结论，再给证据、口径和限制。

## 这个项目是做什么的

**一句话定位**：用全量 Steam archive 数据与真实评价样本，回答“Steam 市场怎么长、怎么分层”的数据分析项目。

**它解决什么问题**：Steam 游戏数量大、类型重叠、价格与口碑差异大，单看榜单很难理解结构。本项目用可复核的数据回答：

- 供给真的在无限增长吗？2010—2024 的曲线是什么形状，2025 为何首次回落？
- 十大类型是互相独立，还是共享同一批游戏？
- 免费与付费的价格、口碑差在哪里？
- 2,000 份真实评价样本里，S/A/B/C 如何分层？
- 玩家注意力集中在头部，还是分散在长尾？

**给谁用**：
- **玩家**——理解类型、价格与口碑的结构，而不是只看单个榜单
- **开发者 / 市场观察者**——看供给、价格带与注意力集中度
- **数据分析学习者**——一个“采集 → 清洗 → 统计 → 可视化 → 口径说明”的完整案例

**项目亮点**：
- 全量 archive：150,279 款 type=game；多主类型统计，不把重叠强行抹平
- 2,000 份真实好评/差评样本：S/A/B/C 分档，不伪造 Steam 实时评价
- 结论先行：首页先给 5 个发现，再展开证据与限制
- 断网可运行：ECharts 等第三方库已本地化，不依赖 CDN
- 可复核：`scripts/build_market.py`、`scripts/fetch_hf_reviews.py` 与 `data/market/` 全链路保留
- 答辩材料：`docs/答辩提纲.md`（数据链路、5 个结论、演示顺序、常见问答）

---

## 项目进度（截至 2026年11月 · 数据故事版）

> 项目按 2026-2027 第一学期导师制 16 周规划推进，当前为**数据故事版**：全量 150,279 款 + 2,000 份口碑样本。

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

- **数据获取**：Kaggle《Steam Games Dataset 2025》全量数据集（约 175MB）；清洗出 **150,279 款 type=game** 的全量市场表（`data/market/market_full.csv`，21 列，0 空值），另用公开 Steam 数据集补齐 **2,000 款** 真实好评/差评样本
- **2025 交叉核验**：`data/steam_store_2025.json` 记录 Steam Store 独立检索 17,801 款（196 页，从 `start=23000` 向旧扫到 2024-12）；archive 2025 为 17,876 款，两源差 75 款（0.4%）。2025 较 2024 的 20,203 款少 2,327 款，约 -11.5%。archive 的 9–12 月 `release_date` 仅 1,450 条，月字段不完整，不用于月度趋势。
- **每日自动更新**：Windows 计划任务 `SteamMarketCrawlerDaily` 每天 22:00 抓取实时 TOP10 与增量评价，失败自动重试、不覆盖旧数据
- **本地数据服务**：Node 迷你服务器（8081，静态页面托管 + `/api/market/agg`、`/api/market/reviews`、`/api/market/top500`、`/api/online` 数据接口）
- **可视化技术**：ECharts 全部基础图表 + 进阶图表（词云、热力图、时间线、类型分布），库已本地化到 `js/`，断网可运行
- **真实数据接入**：10 个 Steam 大类的全量档案、供给时间线、实时 TOP10、S/A/B/C 口碑分层与 TOP500 档案库
- **工程基础**：Git 版本管理、需求文档（`doc/steam-crawler/`：roadmap + task-list）

### 进行中 🔄

- **数据故事页**：`index.html` 为「Steam 市场观察」单页——开放世界背景 + 10 个奶蛙类型角色、2010—2025 供给时间线（2025 首次回落 11.5%）、类型生命周期矩阵、实时 TOP10、2,000 份口碑样本的 S/A/B/C 分层 + 词云、TOP500 档案库；全量数据只加载聚合 JSON 与 TOP500，不把 15 万行塞进浏览器。

### 下一步 ☐

- 补充更多年份/类型的交叉分析，完善移动端阅读
- 项目文档完善、演示视频录制、期末现场展示验收

---

## 目录说明（先看这一段）

- `practice/`：每周练习作业，不是主站代码；`practice/week03/第三周小页面.html` 是独立练习页，随时可以单独打开。
- `data/cleaned/`：另一套来自 `archive` 的 **107 款**清洗产物，只用于历史对照；主站使用 `data/market/` 的 **150,279 款全量聚合** + `reviews_enriched.json` 的 2,000 款评价样本，两者不要混用。
- `js/papaparse.min.js`：练习页与 `scripts/verify_week9_data.js` 仍在使用，保留。
- `data/market/`：全量市场数据（`market_full.csv` 仅用于离线核对，不进入前端；页面只读 `market_agg.json`、`top500.json`、`reviews_enriched.json`）。
- 角色素材：`assets/characters/naiwa/` 的 10 个 APNG 来自 [timerring/codex-pet-naiwa](https://github.com/timerring/codex-pet-naiwa)（MIT），按 Steam 大类语义匹配；原图可在 `naifrog/previews/` 核对。
- 评价样本：2,000 款真实好评/差评计数来自公开数据集 [Z02Z/steam-games-dataset](https://huggingface.co/datasets/Z02Z/steam-games-dataset)（CC-BY-4.0），只覆盖有评价记录的样本。

## 快速开始

本机已装 Node.js（v22），**不需要安装任何依赖**。打开命令行（PowerShell），进入项目根目录 `F:\steam-market-insight`：

```bash
# 1. 生成 15 万款全量市场快照（需要 Python + pandas，已生成可跳过）
python scripts/build_market.py

# 2. 可选：补 2,000 款真实好评/差评样本（公开数据集，失败可跳过）
python scripts/fetch_hf_reviews.py

# 3. 可选：只刷新实时 TOP10
node scripts/fetch_online.js

# 4. 启动本地服务器（保持这个窗口开着）
npm start

# 4. 浏览器打开 http://localhost:8081/
#    市场大厅：      http://localhost:8081/index.html
#    数据接口：      http://localhost:8081/api/market/agg
#    实时 TOP10：    http://localhost:8081/api/online
#    档案 TOP500：   http://localhost:8081/api/market/top500
#    练习索引：      http://localhost:8081/practice/
```

> 8080 可能被其他程序占用；本项目默认使用 **8081**。若端口仍冲突，用 `$env:PORT=8090; npm start`。

## 常用命令

| 命令 | 作用 |
|---|---|
| `python scripts/build_market.py` | 从 archive 生成全量 CSV / 聚合 JSON / TOP500 |
| `python scripts/fetch_reviews.py` | 增量补真实好评率（4 并发、600ms） |
| `npm start` | 启动迷你服务器（静态文件 + `/api/market/*` + `/api/online`） |
| 关服务器 | 在运行 `npm start` 的窗口按 `Ctrl + C` |

## 数据说明

- **全量主表**：archive `applications.csv` + `application_genres.csv`，筛 `type=game` 共 150,279 款；20 列、0 null；价格按快照期汇率折算 USD。
- **口碑样本**：公开数据集 `Z02Z/steam-games-dataset`（FronkonGames，CC-BY-4.0）的 positive/negative 计数，补 2,000 款；覆盖率 1.3%，按推荐数选取。
- **实时 TOP10**：`data/online.json`，由 mostplayed 页面 + `GetNumberOfCurrentPlayers` 生成；当前为 2026-11-11 19:51 的完整 10 名快照（SteamCharts 镜像）；原 Steam API 第 10 名 404，已用完整快照补全，并保留第 11 名 fallback。
- **字段**：`data/market/market_full.csv` 21 列，核心字段：`appid / name / type / all_genres / price / price_unknown / rating / total_reviews / year / recommendations / sub_tags`。
- **口径**：多主类型可重叠，十类数量相加会大于 150,279；8,870 款没有命中任何大类；小标签由名称/简介关键词推断，不是 Steam 用户标签。
- **更新频率**：全量快照随 archive 重新生成；实时 TOP10 可手动 `node scripts/fetch_online.js`，失败时保留旧快照并标注时间。

## 每日自动更新（Windows 任务计划）

项目已配置一个 Windows 计划任务，**每天 22:00** 自动运行 `scripts/run-daily.bat` 抓取数据（当前触发时间：22:00，日期 2026-10-26 起生效）。
- 任务名 `SteamMarketCrawlerDaily`，触发方式：每日 22:00
- 执行内容：`wscript.exe "scripts\run-daily-hidden.vbs"` → `scripts\run-daily.bat` → `node scripts\crawler.js`，日志追加到 `data\crawler.log`
  - 用 `wscript` 隐藏启动，**22:00 不会再弹出黑色 cmd 窗口**（以前窗口会亮 25 分钟，一旦被关掉更新就中断，10-30 至 11-04 有 5 次就是这么没写进数据的）；
  - `run-daily-hidden.vbs` 会等批处理结束再退出，任务状态因此能反映真实结果（`0x0` = 已写入，非 0 = 保留旧数据）。
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
- 生成产物：`data/market/market_full.csv`、`market_agg.json`、`top500.json`，以及 `data/online.json`；页面只请求聚合接口，15 万行明细不进入浏览器。
- 全量快照没有评论字段；口碑只对已补到真实评价的 2,000 款游戏展示，不伪造；详情见 `data/market/`。

### 「数据更新时间」没变时怎么查

1. 看 `data/crawler.log` 末尾有没有 `update OK`；出现 `update FAILED` 说明当晚抓取失败（文件保留旧数据）。
2. 任务计划程序 → `SteamMarketCrawlerDaily` → 「上次运行结果」：`0x0` 成功，`0x1` 表示爬虫返回非 0。
3. 看 `data/meta.json` 的 `fetchedAt` 与 `data/online.json` 的 `fetchedAt`；两者都新 = 写作成功。
4. 页面顶栏有两个时间：`全量快照 2026-11-04` 是 15 万款 archive 数据集的构建日期（`scripts/build_market.py` 生成，不随每日任务变化）；`· 在线数据 11-11 19:51` 才是每晚 22:00 抓取的实时榜单时间，它变了就说明当晚跑通了。
5. 页面打不开/读取错误，说明 `/api/market/*` 没连上，用 `npm start` 后访问 `http://localhost:8081/`。

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

**`data\cleaned\` 是什么**：它是 archive 数据集里与旧项目游戏交集样本的清洗结果和核查报告，只用于历史核对 / 附录，不是当前首页的数据源；当前首页使用 `data/market/` 的 150,279 款全量聚合与 2,000 款评价样本。

## 目录结构

```
F:\steam-market-insight\
├── index.html              数据故事单页（摘要/类型/生命周期/时间线/价格/实时/口碑/档案/方法）
├── js\                     echarts.min.js / data.js（已本地化，断网可用）
│   └── lobby.js            数据接入、类型关系网、生命周期矩阵、赛季、价格、口碑、档案
├── CSS\                    style.css + lobby.css（深色开放世界 + 纸色档案）
├── docs\答辩提纲.md         面向老师的 1 分钟开场、数据链路、演示路线与问答
├── assets\characters\naiwa 10 个分类奶蛙 APNG（MIT，来源见下）
├── practice\               课程练习区（与项目正式代码分开；练习页仍引用上级的 js\ 和 data\）
│   ├── index.html          练习索引页（打开 practice/ 即可看到全部练习）
│   ├── week01\ ~ week05\   第 1~5 周 HTML / ECharts 练习
│   ├── week09\             第 9 周练习
│   └── python\             第 7~8 周 Python 练习、清洗数据与洞察报告
├── data\
│   ├── market\             全量市场：market_full.csv / market_agg.json / top500.json / reviews_enriched.json
│   ├── games.json          旧的 123 款样本（保留作历史核对）
│   └── online.json         Steam 实时 TOP10 快照
├── scripts\
│   ├── build_market.py     全量 archive 清洗与聚合（含类型生命周期）
│   ├── fetch_hf_reviews.py 2,000 款真实好评/差评样本
│   ├── fetch_reviews.py    Steam 评价接口版本（保留）
│   ├── fetch_online.js     只刷新 data/online.json
│   └── run-daily.bat       每日自动更新
├── server.js               迷你服务器（静态 + /api/market/* + /api/online）
├── package.json            npm 脚本入口
└── doc\                    需求与教程（steam-crawler\、data-clean\）
```

## 常见问题

| 问题 | 处理 |
|---|---|
| `npm run crawl` 报"Steam 接口当前不可达" | 国内访问 Steam 会间歇性断连，等几分钟重试即可；旧数据不会丢 |
| 端口 8081 被占用 | `$env:PORT=8090; npm start`（或临时改 server.js 顶部 PORT） |
| 页面数据是旧的 | 全量快照看顶栏；实时榜看竞技场单独时间；`npm run crawl` 只刷新实时榜 |
| 直接双击 html 打开（file:// 协议） | 页面会自动降级使用 `js/data.js` 的本地数据；实时 TOP10 仍以 `npm start` 时的 `/api/online` 为准 |
