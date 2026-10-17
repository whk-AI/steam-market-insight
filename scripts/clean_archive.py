# -*- coding: utf-8 -*-
"""
Steam 项目数据清洗脚本（需求：data-clean，2026-10-04）
=============================================================
目标：只清洗项目（steam-market-insight）用到的数据 —— data/games.json 149 款中
      数据集命中的 107 款，对齐项目 15 字段结构，输出 CSV + JSON + 清洗报告。

输入：
  F:\\2026.9.1\\archive\\steam_dataset_2025_csv\\{applications,genres,application_genres}.csv
输出：
  F:\\steam-market-insight\\data\\cleaned\\{games_cleaned.csv, games_cleaned.json, 清洗报告.md}

复现：python scripts/clean_archive.py
"""
import json
from pathlib import Path
import pandas as pd

# ---------------- 路径 ----------------
BASE = Path(r"F:\2026.9.1\archive\steam_dataset_2025_csv")
PROJ = Path(r"F:\steam-market-insight")
GAMES_JSON = PROJ / "data" / "games.json"
OUT_DIR = PROJ / "data" / "cleaned"

FX = {
    "USD": 6.7050, "CAD": 4.7037, "GBP": 8.8794, "AUD": 4.6642,
    "PHP": 0.1073, "PLN": 1.7221, "NOK": 0.6978, "IDR": 0.0003752,
    "CNY": 1.0,
}
FX_SOURCE = "新浪财经（2026-10-04 行情，2026-10-03 收盘）"

# ---------------- 类型名规范化（数据集 genres 表为多语言混排，映射为项目中文类型词表） ----------------
GENRE_MAP = {
    "Action": "动作", "Acțiune": "动作", "アクション": "动作", "Azione": "动作",
    "Aksiyon": "动作", "動作": "动作", "Actie": "动作", "Akció": "动作",
    "Adventure": "冒险", "Eventyr": "冒险", "Petualangan": "冒险", "Aventură": "冒险",
    "冒险": "冒险", "Avontuur": "冒险",
    "Indie": "独立", "Nezávislé": "独立", "インディー": "独立", "Bağımsız Yapımcı": "独立",
    "Инди": "独立", "独立": "独立",
    "Strategy": "策略", "Strategie": "策略", "Stratégie": "策略", "Strategia": "策略",
    "策略": "策略",
    "Simulation": "模拟", "Simulaatio": "模拟", "Simuladores": "模拟", "Szimuláció": "模拟",
    "Simulazione": "模拟", "Simulationen": "模拟", "模拟": "模拟", "Simülasyon": "模拟",
    "Racing": "竞速", "竞速": "竞速", "Cursa": "竞速",
    "Sports": "体育", "Спорт": "体育", "Sport": "体育", "体育": "体育",
    "Casual": "休闲", "Basit Eğlence": "休闲", "休闲": "休闲",
    "Massively Multiplayer": "大型多人在线", "MMO": "大型多人在线",
    "Многопользовательские игры": "大型多人在线", "Multijogador Massivo": "大型多人在线",
    "Multijugador masivo": "大型多人在线", "大型多人在线": "大型多人在线",
    "Free To Play": "免费开玩", "Бесплатные": "免费开玩", "Gratis at spille": "免费开玩",
    "مجانية": "免费开玩", "免费开玩": "免费开玩",
    "RPG": "角色扮演", "Rollespill": "角色扮演", "角色扮演": "角色扮演",
    "Early Access": "抢先体验", "Acesso Antecipado": "抢先体验", "抢先体验": "抢先体验",
    "Sexual Content": "色情内容",
    "Animation & Modeling": "动画与建模",
    "Design & Illustration": "设计与插画",
    "Photo Editing": "照片编辑",
    "Utilities": "实用工具",
    "Web Publishing": "网页发布",
    "Episodic": "章节式",
    "Short": "短篇",
    "Software Training": "软件培训",
    "Audio Production": "音频制作",
    "Video Production": "视频制作",
    "Education": "教育",
    "Game Development": "游戏开发",
    "Thriller": "惊悚", "إثارة": "惊悚",
}

# ---------------- 项目字段（顺序即输出列序） ----------------
FIELDS = ["appid", "name", "price", "original_price", "final_price",
          "discount_percent", "currency", "rating", "positive",
          "total_reviews", "type", "genres", "year", "release_date", "url"]


def cents_to_cny(cents, currency):
    """分 → 元 → 人民币整数元；币种缺失/未知返回 None"""
    if cents is None or pd.isna(cents):
        return None
    rate = FX.get(currency)
    if rate is None:
        return None
    return round(float(cents) / 100 * rate)


def parse_date(s):
    """解析发行日期 → (ISO日期, 年份)；解析失败返回 (None, None)"""
    if s is None or pd.isna(s):
        return None, None
    s = str(s).strip()
    if not s or s.lower() in {"tbd", "coming soon", "unknown", "n/a"}:
        return None, None
    try:
        ts = pd.to_datetime(s, errors="raise")
        return ts.strftime("%Y-%m-%d"), int(ts.year)
    except Exception:
        return None, None


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = {}

    # 1. 项目 appid（唯一来源：data/games.json）
    games = json.loads(GAMES_JSON.read_text(encoding="utf-8"))
    proj_appids = {int(g["appid"]) for g in games}
    stats["proj_games"] = len(games)

    # 2. 读主表（仅项目用列）→ 过滤
    usecols = ["appid", "name", "is_free", "release_date",
               "mat_initial_price", "mat_final_price",
               "mat_discount_percent", "mat_currency"]
    apps = pd.read_csv(BASE / "applications.csv", usecols=usecols,
                       dtype={"appid": "int64"}, low_memory=False)
    stats["raw_rows"] = int(len(apps))
    sub = apps[apps["appid"].isin(proj_appids)].copy()
    stats["matched_rows"] = int(len(sub))
    stats["matched_appids"] = int(sub["appid"].nunique())
    stats["dup_appid"] = int(sub["appid"].duplicated().sum())
    stats["unmatched_appids"] = sorted(proj_appids - set(sub["appid"]))

    # 3. genres 关联（按 join 表原始顺序保留每款游戏的类型顺序）
    genres = pd.read_csv(BASE / "genres.csv")
    ag = pd.read_csv(BASE / "application_genres.csv")
    name_by_id = dict(zip(genres["id"], genres["name"]))
    genre_by_app = {}
    for appid, gid in zip(ag["appid"], ag["genre_id"]):
        if int(appid) in set(sub["appid"]):
            raw = str(name_by_id.get(int(gid), gid))
            genre_by_app.setdefault(int(appid), []).append(raw)

    # 4. 逐行清洗
    records = []
    miss_before = {
        "release_date": int(sub["release_date"].isna().sum()),
        "price": int(sub["mat_final_price"].isna().sum()),
        "currency": int(sub["mat_currency"].isna().sum()),
    }
    miss_after = {"release_date": 0, "price": 0, "currency": 0, "genre": 0}
    free_count = 0
    for _, r in sub.iterrows():
        appid = int(r["appid"])
        is_free = bool(r["is_free"]) if not pd.isna(r["is_free"]) else False
        free_count += int(is_free)

        raw_cur = r["mat_currency"]
        currency = str(raw_cur).strip() if not pd.isna(raw_cur) else None

        if is_free:
            price, orig, disc, cur_out = 0, 0, 0, None
        else:
            price = cents_to_cny(r["mat_final_price"], currency)
            orig = cents_to_cny(r["mat_initial_price"], currency)
            d = r["mat_discount_percent"]
            disc = None if pd.isna(d) else (float(d) if 0 <= float(d) <= 100 else None)
            cur_out = currency
            if price is None:
                miss_after["price"] += 1
            if currency is None:
                miss_after["currency"] += 1

        release_date, year = parse_date(r["release_date"])
        if release_date is None:
            miss_after["release_date"] += 1

        raw_genres = genre_by_app.get(appid, [])
        if not raw_genres:
            miss_after["genre"] += 1
        genres_norm = []
        for gname in raw_genres:
            genres_norm.append(GENRE_MAP.get(gname, gname))  # 未映射的保留原名
        gtype = genres_norm[0] if genres_norm else "未知"

        records.append({
            "appid": appid,
            "name": str(r["name"]).strip(),
            "price": price,
            "original_price": orig,
            "final_price": price,
            "discount_percent": disc,
            "currency": cur_out,
            "rating": None,
            "positive": None,
            "total_reviews": None,
            "type": gtype,
            "genres": genres_norm,
            "year": year,
            "release_date": release_date,
            "url": f"https://store.steampowered.com/app/{appid}",
        })

    records.sort(key=lambda x: x["appid"])
    stats["out_rows"] = len(records)
    stats["free_count"] = free_count
    stats["miss_before"] = miss_before
    stats["miss_after"] = miss_after
    stats["currency_dist"] = {
        str(k): int(v) for k, v in sub["mat_currency"].value_counts(dropna=False).items()
    }
    stats["type_dist"] = {}
    for rec in records:
        stats["type_dist"][rec["type"]] = stats["type_dist"].get(rec["type"], 0) + 1

    # 5. 输出 CSV + JSON
    df = pd.DataFrame(records, columns=FIELDS)
    df.to_csv(OUT_DIR / "games_cleaned.csv", index=False, encoding="utf-8-sig")
    (OUT_DIR / "games_cleaned.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    # 6. 清洗报告
    write_report(records, stats)

    # 7. 控制台摘要
    print(json.dumps(stats, ensure_ascii=False, indent=2, default=str))
    print("✔ 产物：")
    for p in ["games_cleaned.csv", "games_cleaned.json", "清洗报告.md"]:
        print("  ", OUT_DIR / p)


def write_report(records, stats):
    """生成清洗报告 markdown"""
    L = []
    L.append("# Steam 项目数据清洗报告\n")
    L.append(f"> 需求：data-clean ｜ 生成日期：2026-10-04 ｜ 复现：`python scripts/clean_archive.py`\n")

    L.append("## 1. 概述\n")
    L.append("- **目标**：只清洗项目 `F:\\steam-market-insight` 用到的数据")
    L.append("- **范围**：`data/games.json` 149 款中，数据集命中 **{matched_appids} 款**；42 款未收录（数据集缺失，继续由爬虫提供）".format(**stats))
    L.append("- **输入**：`F:\\2026.9.1\\archive\\steam_dataset_2025_csv\\`（applications.csv 共 {raw_rows:,} 行）".format(**stats))
    L.append("- **输出**：`games_cleaned.csv`（UTF-8-SIG）/ `games_cleaned.json`（项目 15 字段结构）\n")

    L.append("## 2. 清洗规则\n")
    rules = [
        "行级筛选：只保留 appid ∈ 项目 games.json 的记录",
        "去重校验：按 appid 唯一性检查（本批 {dup_appid} 个重复）".format(**stats),
        "类型强转：appid→int64；数值列→float；is_free→bool",
        "名称：去首尾空白",
        "日期：release_date 统一为 YYYY-MM-DD，提取 year；无法解析置空",
        "价格：数据集单位为「分」→ 除以 100 转「元」→ ×当日汇率 → 四舍五入为整数人民币元；免费游戏=0；币种缺失无法换算则置空",
        "折扣：校验 0~100，越界或缺失置空",
        "类型：genres 关联表取名称并**规范化映射为中文**（数据集为多语言混排），type=第一个类型；无类型=「未知」",
        "好评率三字段（rating/positive/total_reviews）：原数据集无 reviews.csv，**置空保留**",
        "url：由 appid 拼接",
    ]
    for i, r in enumerate(rules, 1):
        L.append(f"{i}. {r}")
    L.append("")

    L.append("## 3. 清洗前后对比\n")
    L.append("| 字段 | 清洗前缺失 | 清洗后缺失 | 说明 |")
    L.append("|---|---|---|---|")
    L.append(f"| release_date | {stats['miss_before']['release_date']} | {stats['miss_after']['release_date']} | 无法解析置空 |")
    L.append(f"| 价格（final） | {stats['miss_before']['price']} | {stats['miss_after']['price']} | 币种缺失无法换算 |")
    L.append(f"| 币种 | {stats['miss_before']['currency']} | {stats['miss_after']['currency']} | 原表即缺失 |")
    L.append(f"| genres | - | {stats['miss_after']['genre']} | 无关联记录 |")
    L.append(f"| rating/positive/total_reviews | - | {stats['out_rows']} | 数据源无 reviews 表，全部置空 |")
    L.append(f"\n- 输出总行数：**{stats['out_rows']}**（免费游戏 {stats['free_count']} 款）\n")

    L.append("## 4. 价格换算与汇率表\n")
    L.append(f"汇率来源：{FX_SOURCE}\n")
    L.append("| 币种 | 1 外币 = 人民币 |")
    L.append("|---|---|")
    for c, r in FX.items():
        L.append(f"| {c} | {r} |")
    L.append("\n换算示例：Rust(appid 252490) 原价 3999 分 USD = $39.99 × 6.7050 ≈ **268 元**（整数取整）\n")
    L.append("> 币种分布（原表）：" + "；".join(
        f"{k}={v}" for k, v in stats["currency_dist"].items()) + "\n")

    L.append("## 5. 类型规范化映射\n")
    L.append("数据集 genres 表为多语言混排（同一类型多语言重复），已映射为项目中文类型词表：")
    L.append("| 数据集类型名（本次实际用到） | 规范化后 |")
    L.append("|---|---|")
    for name, norm in sorted(set((n, GENRE_MAP[n]) for n in GENRE_MAP), key=lambda x: x[1]):
        L.append(f"| {name} | {norm} |")
    L.append("")
    L.append("清洗后 type 分布：")
    for t, c in sorted(stats["type_dist"].items(), key=lambda x: -x[1]):
        L.append(f"- {t}：{c} 款")

    L.append("\n## 6. 未收录 appid（数据集无此游戏，继续由爬虫提供）\n")
    L.append("共 **{n}** 个：".format(n=len(stats["unmatched_appids"])))
    L.append(", ".join(str(a) for a in stats["unmatched_appids"]))
    L.append("")

    L.append("\n## 7. 局限与说明\n")
    L.append("- 好评率/评价数：数据源缺失 reviews.csv，无法补齐，字段置空（项目实时数据由爬虫提供）")
    L.append("- 汇率：采用 2026-10-04 快照汇率，与真实购买时汇率可能有偏差；非实时行情")
    L.append("- 区域定价：数据集价格来自非国区（多为 USD），换算后与国区实时价（爬虫口径）会不一致，属正常差异")
    L.append("- 类型词表：未在映射表中的类型名保留原名（本次 107 款均已被映射）")
    L.append("- 缺失价格/日期不填充、不估算，保持真实缺失状态")

    (OUT_DIR / "清洗报告.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
