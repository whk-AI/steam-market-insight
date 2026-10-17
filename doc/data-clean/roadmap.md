# Steam 项目数据清洗 · 全局规划（roadmap）

> 需求名：data-clean
> 创建日期：2026-10-04
> 状态：方案待确认（等待「OK开始」）

---

## 1. 需求总览

### 1.1 核心业务目标
对 Steam 2025 数据集（`F:\2026.9.1\archive\steam_dataset_2025_csv`）做数据清洗，**只清洗项目用到的数据**：
- 项目 `F:\steam-market-insight\data\games.json` 共 149 款游戏，数据集中命中 **107 款**（已探查确认）
- 清洗后产出与项目字段结构一致、可直接使用的干净数据：**CSV + JSON + 清洗报告**

### 1.2 用户价值
- 课程/项目作业的「数据清洗」交付物：规则可追溯、结果可留档
- 项目获得一份清洗过的静态数据源，可与爬虫数据（games.json）对照使用

### 1.3 本次迭代 MVP 交付范围
| 做 | 不做 |
|---|---|
| 命中 107 款游戏 × 项目 15 字段清洗 | 42 个未收录 appid（数据集里没有，继续由爬虫提供） |
| genres 关联：type（主类型）+ genres（列表） | 不碰开发者/发行商/平台/分类等其他表 |
| 价格：分→元 → 按 2026-10-04 汇率换算人民币 | 不联网抓取、不跑爬虫、不改动 crawler/server/前端 |
| rating / positive / total_reviews 置空保留 | 不伪造缺失数据（含好评率、缺失价格） |
| 输出 `data/cleaned/`：CSV + JSON + 清洗报告 | 不做汇率实时行情（仅用当日快照） |

### 1.4 数据字段口径
| 项目字段 | 来源（数据集列） | 清洗规则 |
|---|---|---|
| appid | applications.appid | int64，去重校验（探查无重复） |
| name | applications.name | 原样，去首尾空白 |
| price | mat_final_price | 分→元（/100）→ ×汇率 → 四舍五入为整数元；免费=0 |
| original_price | mat_initial_price | 同上 |
| final_price | = price | 与项目爬虫口径一致（爬虫 final_price=price） |
| discount_percent | mat_discount_percent | float，校验 0~100；缺失置空 |
| currency | mat_currency | 保留原始币种（标注换算前的币种） |
| rating | 无（缺 reviews.csv） | **置空保留** |
| positive | 无（缺 reviews.csv） | **置空保留** |
| total_reviews | 无（缺 reviews.csv） | **置空保留** |
| type | genres 列表第一个 | 取主分类；无匹配=「未知」 |
| genres | application_genres + genres | 关联后取名称列表，按数据集原始顺序 |
| year | release_date 提取 4 位年份 | 缺失置空 |
| release_date | applications.release_date | 统一为 ISO 格式（YYYY-MM-DD），缺失置空 |
| url | appid 拼接 | `https://store.steampowered.com/app/{appid}` |

**汇率口径（新浪财经，2026-10-04 行情，更新于 2026-10-03 收盘）**：

| 币种 | 1 外币 = 人民币 | 来源 |
|---|---|---|
| USD | 6.7050 | 新浪财经 USD/CNY |
| CAD | 4.7037 | 新浪财经 CAD/CNY |
| GBP | 8.8794 | 新浪财经 GBP/CNY |
| AUD | 4.6642 | 新浪财经 AUD/CNY |
| PHP | 0.1073 | 新浪财经 PHP/CNY |
| PLN | 1.7221 | 新浪财经 PLN/CNY |
| NOK | 0.6978 | 新浪财经 NOK/CNY |
| IDR | 0.0003752 | 新浪财经 IDR/CNY |
| CNY | 1.0 | 本币 |

> 币种缺失（43 行 mat_currency 为 NaN）的游戏：无法换算，价格置空，报告中统计说明（免费游戏除外，价格=0）。

---

## 2. 技术方案

### 2.1 技术选型（已确认）
| 项 | 选择 | 理由 |
|---|---|---|
| 语言 | Python 3.14 | 本机已装 |
| 数据处理 | pandas 3.0.6 + numpy | 已安装，能处理 24 万行主表 |
| 输出 | CSV（UTF-8-SIG，Excel 直接打开）+ JSON（项目同结构）| 满足交付要求 |
| 脚本 | `scripts/clean_archive.py`（新建）| 可重复运行、可追溯 |

### 2.2 模块划分与文件结构
```
scripts/
└── clean_archive.py         清洗脚本（读取→清洗→关联→换算→输出→统计）

data/cleaned/                清洗产物目录（新建）
├── games_cleaned.csv        清洗后表格（UTF-8-SIG）
├── games_cleaned.json       清洗后 JSON（项目字段结构）
└── 清洗报告.md              清洗说明（规则/统计/未收录清单/汇率表）

doc/data-clean/
├── roadmap.md               本文件
└── task-list.md             任务进度迭代台账
```

### 2.3 清洗流程（脚本内分步）
1. **读取**：applications.csv（仅项目用列）→ 按 appid ∈ 项目 149 款过滤
2. **去重校验**：appid 唯一性检查
3. **类型强转**：数值列 float、appid int64
4. **日期**：release_date 规范为 ISO；提取 year
5. **价格换算**：分→元 → ×当日汇率 → 整数元；免费游戏=0（显式赋值，非置空）；币种缺失（非免费）置空
6. **类型关联**：application_genres.csv 关联 genres.csv → type / genres
7. **空值**：rating/positive/total_reviews 置空；缺失价格/日期置空（免费游戏价格除外，显式=0）
8. **输出**：CSV + JSON + 清洗统计（写回报告所需数据）
9. **报告生成**：清洗前/后对比、缺失统计、42 个未收录 appid 清单、汇率表

---

## 3. 里程碑规划

| 里程碑 | 核心产出 | 交付目标 |
|---|---|---|
| M1 文档基建 | `roadmap.md` + `task-list.md` | 方案确认，开工依据 |
| M2 清洗脚本开发与执行 | `scripts/clean_archive.py` + `data/cleaned/` 三产物 | 跑通一次，拿到干净数据 |
| M3 校验与交付 | 抽样核对 + 条数/缺失对比 + 交付 | 数据正确、报告完整、交付验收 |

---

## 4. 里程碑依赖关系

```
M1 文档基建（当前）
   └──► M2 清洗执行 ──► M3 校验与交付
```

- M2 依赖 M1 确认；M3 依赖 M2 产物
- 无并行任务（单线小体量）

---

## 5. 详细执行顺序

1. ✅ 需求确认（说清楚）：范围/价格口径/好评率置空 已确认
2. ⏳ **M1** 文档基建（当前步，写完等「OK开始」）
3. **M2** 编写 `scripts/clean_archive.py` → 运行 → 生成 CSV + JSON
4. **M3** 校验：CSV/JSON 抽样核对、107 条数核对、价格复算（Rust 等已知样例）、缺失对比 → 有误则修正重跑
5. **M3** 生成清洗报告 → 更新 task-list → 交付（present_files）

---

## 6. 风险点与落地预案

| 风险 | 影响 | 预案 |
|---|---|---|
| 汇率时效性 | 换算价与真实购买价有偏差 | 报告中注明汇率日期与来源；只做一次性快照换算 |
| 币种缺失 43 行 | 无法换算人民币 | 价格置空 + 报告统计，不编造（免费游戏除外，价格=0） |
| release_date 缺失 22 行 | year 缺失 | 置空，报告统计 |
| genres 无匹配 | type/genres 空 | type=「未知」、genres=[]，报告统计 |
| 数据集价格为「分」的假设 | 换算数量级错误 | 用已知样例复算（如 Rust 3999 分 → 美元）验证 |
| pandas 3.0 API 差异 | 脚本报错 | 已实测读取正常；报错按提示修正 |
| Excel 打开 CSV 乱码 | 可读性差 | 输出 UTF-8-SIG |

---

## 7. 整体进度总览

| 里程碑 | 状态 |
|---|---|
| M1 文档基建 | 🔵 待确认（当前） |
| M2 清洗脚本开发与执行 | ⏳ 待开工 |
| M3 校验与交付 | ⏳ 待开工 |

> 进度更新区：2026-10-04 初始化，等待「OK开始」。
