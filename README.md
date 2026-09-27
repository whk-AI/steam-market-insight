# Steam 游戏市场洞察（Steam Market Insight）

前端页面 + Node 爬虫 + 迷你服务器。数据来自 **Steam 官方公开接口**，不再是死数据。

## 快速开始

本机已装 Node.js（v22），**不需要安装任何依赖**。打开命令行（PowerShell），进入项目根目录 `F:\steam-market-insight`：

```bash
# 1. 抓取数据（首次约 1~3 分钟，会生成 data/games.json + data/meta.json）
npm run crawl

# 2. 启动本地服务器（保持这个窗口开着）
npm start

# 3. 浏览器打开
#    首页：          http://localhost:8080/
#    第三周小页面：  http://localhost:8080/pratice/第三周小页面.html
#    数据接口：      http://localhost:8080/api/games
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
├── index.html / CSS / js       前端（已有）
├── pratice\                    每周练习页（已有，模拟数据保留在 模拟data\）
├── data\
│   ├── games.json              爬虫输出的真实数据（活数据）
│   └── meta.json               抓取时间 / 条数等元信息
├── scripts\
│   ├── crawler.js              爬虫主脚本（教学式注释）
│   └── run-daily.bat           每日自动更新用的批处理
├── server.js                   迷你服务器（静态 + /api/games）
├── package.json                npm 脚本入口
└── doc\steam-crawler\          需求文档（roadmap + task-list）
```

## 常见问题

| 问题 | 处理 |
|---|---|
| `npm run crawl` 报"Steam 接口当前不可达" | 国内访问 Steam 会间歇性断连，等几分钟重试即可；旧数据不会丢 |
| 端口 8080 被占用 | `$env:PORT=8090; npm start`（或临时改 server.js 顶部 PORT） |
| 页面数据是旧的 | 看页面副标题的"更新于"时间；运行 `npm run crawl` 刷新 |
| 直接双击 html 打开（file:// 协议） | 浏览器会拦截 fetch，请用 `npm start` 后访问 localhost |
