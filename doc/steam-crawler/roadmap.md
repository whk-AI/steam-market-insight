# Steam 实时数据爬虫 · 全局规划（roadmap）

> 需求名：steam-crawler
> 创建日期：2026-09-22
> 状态：方案待确认（等待「OK开始」）

---

## 1. 需求总览

### 1.1 核心业务目标
把 `F:\steam-market-insight` 项目从「纯前端 + 死数据」升级为「前端 + 后端爬虫 + 活数据」：
- 编写爬虫脚本，从 **Steam 官方公开接口** 抓取真实游戏数据（价格、好评率、类型、发行年份等）
- 搭建迷你本地服务器，前端通过 `/api/games` 接口取数 —— **不再是纯前端**
- 数据**每日自动更新 + 手动可随时刷新**，保证不是死数据

### 1.2 用户价值
- 练习页、小页面、整个项目的数据从「假数据」变成「真数据、会更新」
- 爬虫代码按**教学式风格**编写（清晰分步 + 中文注释），用户第九周学爬虫时可对照学习
- 满足导师「项目不只是纯前端」的要求

### 1.3 本次迭代 MVP 交付范围
| 做 | 不做 |
|---|---|
| 爬虫脚本 `scripts/crawler.js`（Steam 官方接口） | 不接 Kaggle 静态数据集（仅参考字段名） |
| 真实数据文件 `data/games.json` + `data/meta.json` | 不做账号系统、不做数据库（文件即库） |
| 迷你服务器 `server.js`（静态托管 + `/api/games`） | 不部署公网服务器（本地运行即可） |
| 现有练习页数据源切换为真实数据 | 不改动模拟数据 `pratice/模拟data/`（保留为第三周数据） |
| 每日定时更新（Windows 任务计划，需用户确认后配置） | 不做实时轮询（每次访问现查接口会被限流） |

### 1.4 数据字段口径（对齐现有模拟数据 + 扩展）
现有模拟数据字段：`name / price / rating / type / year` —— **字段名保持不变**，前端现有代码可直接换数据源。
真实数据扩展字段：`appid / original_price / final_price / discount_percent / positive / total_reviews / genres[] / release_date / players(可选)`

- `price`：统一转成 **元（整数）**，免费游戏为 0
- `rating`：好评率（%）= 好评数 ÷ 总评价数 × 100，保留 1 位小数 —— 与模拟数据口径一致
- `type`：取 genres 的主分类（第一个）
- `year`：发行日期年份

---

## 2. 技术方案

### 2.1 技术选型（已确认）
| 项 | 选择 | 理由 |
|---|---|---|
| 语言 | **Node.js（v22，已安装）** | 与前端同语言；自带 `fetch` / `http`，**零第三方依赖**，无需 npm install |
| 爬虫 | `scripts/crawler.js`，内置 `fetch` | 代码教学友好，Node ≥ 18 即可 |
| 服务器 | `server.js`，内置 `http` 模块 | 静态托管 + `/api/games`，无框架依赖 |
| 定时 | Windows 任务计划程序（schtasks） | 每日跑一次爬虫；配置前征求用户确认 |
| 前端 | `fetch('/api/games')`，失败回退 `fetch('data/games.json')` | 走本服务器 = 活数据；直接 Live Server 打开也不白屏 |

### 2.2 数据源（均已实测可直连，无需 API Key）
| 接口 | 用途 |
|---|---|
| `store.steampowered.com/api/featuredcategories` | 获取 appid 池：热销榜 / 新品 / 特惠 |
| `store.steampowered.com/api/appdetails?appids=1,2,3` | 批量详情：名称、价格、类型、发行日期 |
| `store.steampowered.com/appreviews/570?json=1` | 评价数 → 好评率 |
| ~~steamspy.com~~ | ❌ 本机实测 403，弃用 |

appid 池策略：`top_sellers + new_releases + specials` 多个入口抓取 → 去重 → 预计 **100～200 款** → 逐款拉详情 + 好评率。

### 2.3 爬虫健壮性设计
- 请求间隔 ~400ms，控制频率防限流；单请求超时 15s；失败重试 2 次
- **原子写入**：先写临时文件再 rename 替换，抓取失败时**保留上一次数据**不覆盖
- 对无价格（coming soon）、免费游戏、接口字段缺失做兜底（`null` / `0`）
- 预留代理支持：若后续网络波动，可通过环境变量 `HTTP_PROXY` 走代理

### 2.4 目录结构
```
F:\steam-market-insight\
├── index.html                  （已有，后续作为项目首页）
├── CSS\CSS1.css                （已有，不动）
├── js\papaparse.min.js         （已有，不动）
├── pratice\                    （已有，全部不动）
│   ├── 模拟data\games.JSON / games.CSV   ← 保留，第三周数据
│   ├── 第一周基础语法.html
│   ├── 第二周数组高阶用法练习.html
│   ├── 第三周练练合集.html
│   └── 第三周小页面.html        ← 本次切换数据源
├── data\                       （新增）
│   ├── games.json              ← 爬虫输出：真实游戏数据
│   └── meta.json               ← 抓取时间 / 条数 / 成功失败数
├── scripts\                    （新增）
│   └── crawler.js              ← 爬虫主脚本（教学式注释）
├── server.js                   （新增）迷你服务器
├── package.json                （新增）npm run crawl / npm start
└── doc\steam-crawler\          （新增）本次需求文档
    ├── roadmap.md              ← 本文件
    └── task-list.md            ← 任务进度台账
```

---

## 3. 里程碑规划

| 里程碑 | 核心产出 | 交付目标 |
|---|---|---|
| M1 文档基建 | `roadmap.md` + `task-list.md` | 方案确认，开工依据 |
| M2 爬虫开发 | `scripts/crawler.js` + `data/games.json` + `data/meta.json` | 跑通一次，拿到真实数据文件 |
| M3 迷你服务器 | `server.js` + `package.json` | 浏览器访问 `/api/games` 返回真实数据 |
| M4 前端切换 | 第三周小页面等改用 `/api/games`（带本地回退） | 页面数据变活，模拟数据保留 |
| M5 自动化与交付 | 每日定时任务 + 全链路验证 + 使用说明 | 数据每日自动更新，交付验收 |

---

## 4. 里程碑依赖关系

```
M1 文档基建（当前）
   │
   └──► M2 爬虫开发 ──► M3 迷你服务器 ──► M4 前端切换 ──► M5 自动化与交付
```

- **前置依赖**：M2 依赖 M1 确认；M3 依赖 M2 产出数据文件；M4 依赖 M3 接口可用
- **可并行**：无（单线开发，体量小）
- **后置衔接**：M5 的定时任务只依赖 M2（爬虫可独立定时跑，不依赖服务器）

---

## 5. 详细执行顺序

1. ✅ 需求确认（说清楚）
2. ⏳ **M1** 文档基建（当前步，写完等「OK开始」）
3. **M2** 编写 `scripts/crawler.js` → 手动运行 → 校验 `data/games.json` 字段与条数 → 生成 `meta.json`
4. **M3** 编写 `server.js`（静态托管 + `/api/games` + `/api/meta`）→ 启动 → 浏览器验证接口
5. **M4** 改造第三周小页面数据源：优先 `/api/games`，失败回退本地 `data/games.json`；页面展示「数据更新时间」
6. **M5** 配置 Windows 任务计划每日定时跑爬虫（**征求用户同意后执行**）→ 全链路验证（跑一遍 → 看数据 → 看页面）→ 写使用说明
7. 收尾：更新 task-list 进度，交付验收，等用户反馈迭代

---

## 6. 风险点与落地预案

| 风险 | 影响 | 预案 |
|---|---|---|
| Steam 接口限流 / 超时 / 断连 | 抓取失败 | 请求间隔 400ms + 超时 15s + 重试 2 次；失败保留上次数据 |
| coming soon 游戏无价格 | 字段缺失 | 兜底 `null` / 0，不中断整体流程 |
| 前端直接 Live Server 打开（不走本服务器） | `/api/games` 404 | 前端自动回退本地 `data/games.json` + 标注更新时间 |
| 好评率接口偶发超时 | 个别游戏无评分 | 重试后仍失败则该条 `rating` 置 null，其余正常 |
| 在线人数接口（可选）可能被限 | players 拿不到 | 列为可选增强项，失败则降级省略，不影响主目标 |
| Node 版本过低无 fetch | 爬虫无法运行 | 已核实本机 v22（≥18），达标 |
| 网络后续波动（国内访问 Steam） | 数据更新失败 | 爬虫预留 `HTTP_PROXY` 代理支持 |

---

## 7. 整体进度总览

| 里程碑 | 状态 |
|---|---|
| M1 文档基建 | ✅ 完成 |
| M2 爬虫开发 | ✅ 完成（47 款真实数据） |
| M3 迷你服务器 | ✅ 完成（/api/games 200） |
| M4 前端切换 | ✅ 完成（第三周小页面接入真实数据） |
| M5 自动化与交付 | 🔵 进行中（计划任务已注册；待网络恢复扩池重抓） |

> 进度更新区：2026-09-22 开发完成，详细变更记录见 task-list.md 台账。
