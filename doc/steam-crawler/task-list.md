# Steam 实时数据爬虫 · 任务进度台账（task-list）

> 需求名：steam-crawler
> 创建日期：2026-09-22
> 状态：开发完成，待验收（③做出来 → ④你验收）

---

## 1. 里程碑速览

| 里程碑 | 说明 | 状态 |
|---|---|---|
| M1 文档基建 | roadmap + task-list | ✅ 完成 |
| M2 爬虫开发 | crawler.js → data/games.json | ✅ 完成（47 款真实数据） |
| M3 迷你服务器 | server.js → /api/games | ✅ 完成 |
| M4 前端切换 | 练习页改用真实数据 | ✅ 完成 |
| M5 自动化与交付 | 每日定时 + 验证 + 说明 | 🔵 进行中（等待网络恢复扩池） |

---

## 2. 精细化任务拆解

### M1 文档基建
- [x] 创建 `doc/steam-crawler/` 目录
- [x] 编写 `roadmap.md`（需求总览 / 技术方案 / 里程碑 / 风险预案）
- [x] 编写 `task-list.md`（本台账）
- [x] 用户审阅方案，发送「OK开始」（2026-09-22）

### M2 爬虫开发
- [x] 编写 `scripts/crawler.js`：appid 池获取（featuredcategories + 搜索接口双来源）
- [x] 编写详情抓取（appdetails，含价格/类型/年份解析）
- [x] 编写好评率抓取（appreviews，重试与超时控制）
- [x] 编写请求节流（批并发 4）、重试（2 次）、原子写入（临时文件 + rename）
- [x] 编写字段兜底（免费游戏 / coming soon / 字段缺失）
- [x] 运行爬虫，生成 `data/games.json` + `data/meta.json`
- [x] 校验数据：JSON 有效、47 款、字段完整、抽查与 Steam 页面一致
- [x] 处理搜索接口无 id 字段问题（appid 从 logo URL 解析，`extractAppId`）

### M3 迷你服务器
- [x] 编写 `server.js`：静态文件托管（含路径穿越防护）
- [x] 实现 `/api/games` 接口（读 data/games.json）
- [x] 实现 `/api/meta` 接口（数据更新时间）
- [x] 编写 `package.json`：`npm run crawl` / `npm start`
- [x] 启动服务器，浏览器/请求验证接口返回真实数据

### M4 前端切换
- [x] 改造第三周小页面：优先 `fetch('/api/games')`，失败回退 `../data/games.json`
- [x] 页面展示「数据更新时间」（来自 meta.json）
- [x] 好评率榜单加"最低 1000 条评价"门槛（避免冷门新游霸榜）
- [x] 防 XSS：游戏名 HTML 转义
- [x] 核对前端字段（name/price/rating/type/year）与真实数据对齐
- [x] 确认模拟数据 `pratice/模拟data/` 未被改动

### M5 自动化与交付
- [x] 配置 Windows 计划任务 `SteamMarketCrawlerDaily`（每日 08:00，已注册验证）
- [x] 编写 `scripts/run-daily.bat` 启动脚本
- [x] 全链路验证：爬虫 → 数据 → 服务器接口 → 页面逻辑（模拟 TOP10 渲染）
- [x] 编写 README 使用说明（含第九周学习指引）
- [ ] 网络恢复后扩池重抓（搜索池修复已就绪，后台自动重试中）
- [ ] 用户验收反馈

---

## 3. 进度变更台账

| 日期 | 变更内容 | 进度状态 | 备注 |
|---|---|---|---|
| 2026-09-22 | 需求确认：Node.js 技术栈、方案 B（服务器+接口）、每日更新、保留模拟数据 | M1 进行中 | 用户确认「按你推荐的来」 |
| 2026-09-22 | 创建 doc/steam-crawler/，输出 roadmap.md + task-list.md | M1 进行中 | 待用户「OK开始」 |
| 2026-09-22 | 用户发送「OK开始」 | M1 → M2 | 进入开发 |
| 2026-09-22 | 实测接口连通性：appdetails/appreviews 直连 200，steamspy 403 弃用；期间网络多次断连 | M2 | 验证了重试+原子写兜底 |
| 2026-09-22 | 爬虫首跑成功：46 候选 → 39 款；重跑 47 款（0 失败） | M2 完成 | 数据写入 data/games.json |
| 2026-09-22 | 发现搜索接口 item 无 id 字段，appid 藏于 logo URL | M2 迭代 | 新增 extractAppId 修复 |
| 2026-09-22 | server.js + package.json 完成，接口 200 验证 | M3 完成 | 服务器 pid 3516 运行中 |
| 2026-09-22 | 第三周小页面接入 /api/games（带回退+更新时间+评价门槛+转义） | M4 完成 | TOP10 逻辑模拟验证通过 |
| 2026-09-22 | 注册计划任务 SteamMarketCrawlerDaily（08:00）+ README + run-daily.bat | M5 大部分完成 | 任务状态 Ready |
| 2026-09-22 | 网络再次断连，后台重试循环运行中（搜索池扩池待网络恢复） | M5 进行中 | 旧数据完好 |

---

> 铁律提醒：每完成一个 Task 立即勾选并同步更新台账与 roadmap 进度总览；③④⑤循环直到用户验收通过。
