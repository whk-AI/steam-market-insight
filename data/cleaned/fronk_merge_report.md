# Fronk 晚期条目合并清洗报告

- 生成时间：2026-11-25T06:10:01.922954+00:00
- 数据源：FronkonGames/steam-games-dataset@2026-09-08
- 本地基线：archive `applications.csv`（type=game）150279 款

## 1. 清洗流水

| 阶段 | 数量 |
|---|---|
| Fronk 快照总数 | 124146 |
| 本地已存在（跳过不覆盖） | 118702 |
| 非晚期 / 日期异常（<2025-09-01） | 296 |
| 剔除软件工具类 | 53 |
| 剔除版本包变体重复 | 2 |
| 空名 | 0 |
| **最终追加** | **5093** |

## 2. 追加条目月度分布

| 月份 | 款数 |
|---|---|
| 2025-09 | 592 |
| 2025-10 | 1192 |
| 2025-11 | 1139 |
| 2025-12 | 1136 |
| 2026-01 | 993 |
| 2026-02 | 39 |
| 2026-03 | 1 |
| 2026-09 | 1 |

## 3. 补充字段覆盖率（仅本次新条目）

| 字段 | 有值款数 | 覆盖率 |
|---|---|---|
| 开发商 | 4273 | 83.9% |
| 发行商 | 4273 | 83.9% |
| Windows | 5091 | 100.0% |
| macOS | 581 | 11.4% |
| Linux | 498 | 9.8% |
| 语言 | 4273 | 83.9% |
| DLC>0 | 207 | 4.1% |
| 成就>0 | 2019 | 39.6% |
| 有时长 | 54 | 1.1% |

## 4. 剔除样例

### 软件工具类（前 15）

| appid | 名称 | 命中类别 |
|---|---|---|
| 3920410 | Desktop Companion | Animation & Modeling/Design & Illustration/Utilities |
| 4056970 | Live Wallpaper | Animation & Modeling/Design & Illustration/Utilities |
| 4095940 | ReFrame | Utilities |
| 4066680 | Spacer — Tag-based File Explorer | Utilities |
| 4027790 | Relight Studio | Photo Editing |
| 3993700 | EaseUS Partition Master | Utilities |
| 4069200 | ComboBench | Utilities |
| 3751880 | Multiplicity 4 Pro | Accounting/Animation & Modeling/Audio Production/Design & Illustration/Photo Editing/Software Training/Utilities/Video Production/Web Publishing/Game Development |
| 3911020 | Anime Art Generator - Unlimited AI | Animation & Modeling/Design & Illustration/Photo Editing |
| 3981980 | rhodopsin | Photo Editing/Video Production |
| 2609100 | AFK Companion | Utilities |
| 4067590 | VirtuStick | Utilities/Game Development |
| 4138740 | IDLE PET UFO | Utilities |
| 4104760 | Fixer Toolkit – Window & Layout Manager | Utilities |
| 4106410 | Path of the Herald: Character Creator | Utilities |

### 版本包变体（前 10）

| appid | 名称 | 日期 |
|---|---|---|
| 3484440 | EA SPORTS FC™ 26 | Sep 25, 2025 |
| 3484390 | EA SPORTS FC™ 26 | Sep 25, 2025 |

## 5. 口径与边界

- 好评率 / 评论数：晚期新游在源数据中 positive/negative 全空，`rating/positive/total_reviews` 一律为 0，不编造；不进好评率年度趋势与口碑榜。
- 推荐数：晚期源数据评论字段全空，推荐数无交叉验证，主表 `recommendations` 一律置 0，原始值存补充表 `recommendations_raw` 备查；新条目不进入推荐量榜与头部集中度统计。
- 时长：仅源数据有值的 54 款（探查口径）写入补充表，其余为 0。
- 价格：Fronk 价格为美元口径；无折扣原价快照，`original_price=price`、`discount_percent=0`。
- 免费判定：价格为 0 或官方类别含 Free To Play。
- 补充字段（开发商/发行商/平台/owners/时长/语言/DLC/成就/类别/标签）单独存 `hf_enriched.csv`，主表 21 列结构不变。
- 本地已有条目不被本次合并覆盖；存量条目的补充字段 join 另行处理。