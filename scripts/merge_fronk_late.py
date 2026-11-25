# -*- coding: utf-8 -*-
"""
合并 FronkonGames 数据集（快照 2026-09-08）中本地缺失的 2025-09 之后新条目。

输入:
  data/market/market_full.csv        现有全量明细（21 列）
  data/raw/fronk_steam.parquet       Fronk 全量快照

输出:
  data/market/extra_fronk.csv        本次追加条目（21 列，供 build_market.py 合并）
  data/market/hf_enriched.csv        新条目补充字段（开发商/平台/owners/时长/语言/DLC/成就/类别/标签）
  data/cleaned/fronk_merge_report.md 清洗报告

口径:
  - 只追加本地不存在的 appid；本地已有条目不覆盖
  - 仅保留 release_date >= 2025-09-01 的晚期条目
  - 剔除 Steam 软件工具类（Utilities / Animation & Modeling 等）
  - 同名同日期同价格的版本包变体只保留最小 appid
  - 新游好评率/评论数源数据全空，一律留 0，不编造；时长有值才进补充表
  - 价格口径 USD；Fronk 无折扣原价快照，original_price 取 price，discount=0
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 复用主清洗脚本的常量与规则，保证类型/小标签口径一致
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_market import (  # noqa: E402
    ARCHIVE,
    MAIN_GENRES,
    clean_text,
    extract_year,
    infer_sub_tags,
)

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "data" / "market"
RAW = ROOT / "data" / "raw"
CLEANED = ROOT / "data" / "cleaned"
CLEANED.mkdir(parents=True, exist_ok=True)

PARQUET = RAW / "fronk_steam.parquet"
EXTRA_CSV = MARKET / "extra_fronk.csv"
ENRICH_CSV = MARKET / "hf_enriched.csv"
REPORT_MD = CLEANED / "fronk_merge_report.md"

CUTOFF = pd.Timestamp("2025-09-01")
SOURCE_TAG = "FronkonGames/steam-games-dataset@2026-09-08"

# Steam 商店里的软件/工具类，不是游戏，剔除
NON_GAME_GENRES = {
    "Utilities", "Animation & Modeling", "Design & Illustration", "Photo Editing",
    "Video Production", "Game Development", "Audio Production", "Software Training",
    "Web Publishing", "Accounting", "Software",
}

REPORT_COLS = [
    "appid", "name", "type", "is_free", "price", "original_price", "discount_percent",
    "currency", "price_unknown", "year", "release_date", "genres", "main_genre",
    "all_genres", "sub_tags", "metacritic", "recommendations", "rating", "positive",
    "total_reviews", "url",
]


def as_list(value) -> list[str]:
    if value is None:
        return []
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    if isinstance(value, np.ndarray):
        return [str(x).strip() for x in value if str(x).strip()]
    if isinstance(value, (list, tuple)):
        return [str(x).strip() for x in value if str(x).strip()]
    text = str(value).strip()
    return [] if text.lower() in {"", "nan", "none", "null", "<na>"} else [text]


def parse_release(value: str):
    text = clean_text(value)
    if not text:
        return pd.NaT
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return pd.to_datetime(text, format=fmt)
        except (ValueError, TypeError):
            continue
    return pd.to_datetime(text, errors="coerce")


def main():
    if not PARQUET.exists():
        raise SystemExit(f"缺少 parquet: {PARQUET}")

    print(">>> 读取 archive 原始基线（type=game）...", flush=True)
    base = pd.read_csv(
        ARCHIVE / "applications.csv",
        usecols=["appid", "type"],
        dtype={"appid": "int64", "type": "string"},
        low_memory=False,
    )
    base = base[base["type"].eq("game")]
    local_ids = set(base["appid"].astype(str))
    print(f"    archive 基线 {len(base)} 款", flush=True)

    print(">>> 读取 Fronk parquet ...", flush=True)
    fr = pd.read_parquet(PARQUET)
    fr["appid_s"] = fr["appID"].astype(str)
    print(f"    Fronk 共 {len(fr)} 款", flush=True)

    stats = {"fronk_total": len(fr), "already_local": 0, "early_or_bad_date": 0,
             "non_game": 0, "empty_name": 0, "variant_dup": 0, "kept": 0}
    dropped_non_game, dropped_early, dropped_variant = [], [], []

    only = fr[~fr["appid_s"].isin(local_ids)].copy()
    stats["already_local"] = stats["fronk_total"] - len(only)
    print(f"    本地缺失 {len(only)} 款", flush=True)

    only["dt"] = only["release_date"].apply(parse_release)
    late = only[(only["dt"] >= CUTOFF)].copy()
    stats["early_or_bad_date"] = len(only) - len(late)
    bad_date = only[only["dt"] < CUTOFF]
    for r in bad_date.itertuples(index=False):
        dropped_early.append((r.appid_s, clean_text(r.name), clean_text(r.release_date)))
    print(f"    晚于 2025-09-01: {len(late)} 款", flush=True)

    records, enrich_rows = [], []
    seen_variant = {}  # (name, date_str, price) -> appid 最小者

    for row in late.itertuples(index=False):
        appid = str(row.appid_s)
        name = clean_text(row.name)
        genres = as_list(row.genres)
        devs = as_list(row.developers)
        pubs = as_list(row.publishers)
        cats = as_list(row.categories)
        tags = as_list(row.tags)
        langs = as_list(row.supported_languages)

        # 1) 剔软件工具类
        hit_non_game = [g for g in genres if g in NON_GAME_GENRES]
        if hit_non_game:
            stats["non_game"] += 1
            dropped_non_game.append((appid, name, "/".join(hit_non_game)))
            continue

        # 2) 空名
        if not name:
            stats["empty_name"] += 1
            continue

        # 3) 版本包变体：同名 + 同日期 + 同价格，保留最小 appid
        date_str = clean_text(row.release_date)
        price = round(float(row.price) if pd.notna(row.price) else 0.0, 2)
        vkey = (name.lower(), date_str, price)
        if vkey in seen_variant:
            stats["variant_dup"] += 1
            dropped_variant.append((appid, name, date_str))
            continue
        seen_variant[vkey] = appid

        is_free = (price <= 0) or ("Free To Play" in genres)
        if is_free:
            price = 0.0
        price_unknown = bool(pd.isna(row.price))

        main_genres = [g for g in genres if g in MAIN_GENRES]
        all_genres = list(dict.fromkeys(main_genres))
        if is_free and "Free To Play" not in all_genres:
            all_genres = ["Free To Play"] + all_genres
        if not all_genres:
            all_genres = ["其他"]
        if is_free:
            main_genre = "Free To Play"
        else:
            main_genre = main_genres[0] if main_genres else "其他"

        genres_out = genres if genres else ["未知"]
        sub_tags = infer_sub_tags(name, f"{clean_text(row.short_description)} {' '.join(tags)}")

        year = extract_year(date_str)
        metacritic = int(round(float(row.metacritic_score))) if pd.notna(row.metacritic_score) else 0
        recommendations_raw = int(round(float(row.recommendations))) if pd.notna(row.recommendations) else 0
        # 晚期源数据评论字段全空，推荐数无评论交叉验证，主表口径置 0，原始值留存补充表备查
        recommendations = 0

        records.append({
            "appid": int(appid),
            "name": name,
            "type": "game",
            "is_free": is_free,
            "price": price,
            "original_price": price,
            "discount_percent": 0,
            "currency": "USD",
            "price_unknown": price_unknown,
            "year": year,
            "release_date": date_str or "UNKNOWN",
            "genres": ",".join(genres_out),
            "main_genre": main_genre,
            "all_genres": ",".join(all_genres),
            "sub_tags": ",".join(sub_tags) or "未标注",
            "metacritic": metacritic,
            "recommendations": recommendations,
            # 源数据 positive/negative 全空：好评率留 0，不编造
            "rating": 0,
            "positive": 0,
            "total_reviews": 0,
            "url": f"https://store.steampowered.com/app/{appid}",
        })

        enrich_rows.append({
            "appid": int(appid),
            "developers": ";".join(devs),
            "publishers": ";".join(pubs),
            "windows": bool(row.windows) if pd.notna(row.windows) else False,
            "mac": bool(row.mac) if pd.notna(row.mac) else False,
            "linux": bool(row.linux) if pd.notna(row.linux) else False,
            "estimated_owners": clean_text(row.estimated_owners),
            "avg_playtime_forever": int(row.average_playtime_forever) if pd.notna(row.average_playtime_forever) else 0,
            "median_playtime_forever": int(row.median_playtime_forever) if pd.notna(row.median_playtime_forever) else 0,
            "supported_languages": ";".join(langs),
            "dlc_count": int(row.dlc_count) if pd.notna(row.dlc_count) else 0,
            "achievements": int(row.achievements) if pd.notna(row.achievements) else 0,
            "categories": ";".join(cats),
            "tags": ";".join(tags),
            "recommendations_raw": recommendations_raw,
            "source": SOURCE_TAG,
        })

    extra = pd.DataFrame.from_records(records, columns=REPORT_COLS)
    enrich = pd.DataFrame.from_records(enrich_rows)
    stats["kept"] = len(extra)

    print(f"\n>>> 清洗结果: 保留 {stats['kept']} 款", flush=True)
    print(f"    剔软件工具类 {stats['non_game']} | 变体重复 {stats['variant_dup']} | 非晚期/日期异常 {stats['early_or_bad_date']} | 空名 {stats['empty_name']}", flush=True)

    # 写出
    extra.to_csv(EXTRA_CSV, index=False, encoding="utf-8-sig")
    enrich.to_csv(ENRICH_CSV, index=False, encoding="utf-8-sig")
    print(f">>> 写出 {EXTRA_CSV.name} / {ENRICH_CSV.name}", flush=True)

    # ---------- 覆盖率统计 ----------
    def cov(col):
        return int((enrich[col].astype(str).str.len() > 0).sum()) if len(enrich) else 0

    coverage = {
        "开发商": cov("developers"), "发行商": cov("publishers"),
        "Windows": int(enrich["windows"].sum()) if len(enrich) else 0,
        "macOS": int(enrich["mac"].sum()) if len(enrich) else 0,
        "Linux": int(enrich["linux"].sum()) if len(enrich) else 0,
        "语言": cov("supported_languages"), "DLC>0": int((enrich["dlc_count"] > 0).sum()) if len(enrich) else 0,
        "成就>0": int((enrich["achievements"] > 0).sum()) if len(enrich) else 0,
        "有时长": int((enrich["avg_playtime_forever"] > 0).sum()) if len(enrich) else 0,
    }
    month_dist = extra["release_date"].apply(
        lambda s: pd.to_datetime(s, format="%b %d, %Y", errors="coerce")
    ).dt.to_period("M").value_counts().sort_index()

    # ---------- 报告 ----------
    L = []
    L.append("# Fronk 晚期条目合并清洗报告\n")
    L.append(f"- 生成时间：{datetime.now(timezone.utc).isoformat()}")
    L.append(f"- 数据源：{SOURCE_TAG}")
    L.append(f"- 本地基线：archive `applications.csv`（type=game）{len(base)} 款\n")

    L.append("## 1. 清洗流水\n")
    L.append("| 阶段 | 数量 |")
    L.append("|---|---|")
    L.append(f"| Fronk 快照总数 | {stats['fronk_total']} |")
    L.append(f"| 本地已存在（跳过不覆盖） | {stats['already_local']} |")
    L.append(f"| 非晚期 / 日期异常（<2025-09-01） | {stats['early_or_bad_date']} |")
    L.append(f"| 剔除软件工具类 | {stats['non_game']} |")
    L.append(f"| 剔除版本包变体重复 | {stats['variant_dup']} |")
    L.append(f"| 空名 | {stats['empty_name']} |")
    L.append(f"| **最终追加** | **{stats['kept']}** |\n")

    L.append("## 2. 追加条目月度分布\n")
    L.append("| 月份 | 款数 |")
    L.append("|---|---|")
    for period, count in month_dist.items():
        L.append(f"| {period} | {count} |")
    L.append("")

    L.append("## 3. 补充字段覆盖率（仅本次新条目）\n")
    L.append("| 字段 | 有值款数 | 覆盖率 |")
    L.append("|---|---|---|")
    for k, v in coverage.items():
        pct = round(v / len(enrich) * 100, 1) if len(enrich) else 0
        L.append(f"| {k} | {v} | {pct}% |")
    L.append("")

    L.append("## 4. 剔除样例\n")
    L.append("### 软件工具类（前 15）\n")
    L.append("| appid | 名称 | 命中类别 |")
    L.append("|---|---|---|")
    for appid, name, genres in dropped_non_game[:15]:
        L.append(f"| {appid} | {name} | {genres} |")
    L.append("")
    L.append("### 版本包变体（前 10）\n")
    L.append("| appid | 名称 | 日期 |")
    L.append("|---|---|---|")
    for appid, name, date_str in dropped_variant[:10]:
        L.append(f"| {appid} | {name} | {date_str} |")
    L.append("")

    L.append("## 5. 口径与边界\n")
    L.append("- 好评率 / 评论数：晚期新游在源数据中 positive/negative 全空，`rating/positive/total_reviews` 一律为 0，不编造；不进好评率年度趋势与口碑榜。")
    L.append("- 推荐数：晚期源数据评论字段全空，推荐数无交叉验证，主表 `recommendations` 一律置 0，原始值存补充表 `recommendations_raw` 备查；新条目不进入推荐量榜与头部集中度统计。")
    L.append("- 时长：仅源数据有值的 54 款（探查口径）写入补充表，其余为 0。")
    L.append("- 价格：Fronk 价格为美元口径；无折扣原价快照，`original_price=price`、`discount_percent=0`。")
    L.append("- 免费判定：价格为 0 或官方类别含 Free To Play。")
    L.append("- 补充字段（开发商/发行商/平台/owners/时长/语言/DLC/成就/类别/标签）单独存 `hf_enriched.csv`，主表 21 列结构不变。")
    L.append("- 本地已有条目不被本次合并覆盖；存量条目的补充字段 join 另行处理。")

    REPORT_MD.write_text("\n".join(L), encoding="utf-8")
    print(f">>> 报告: {REPORT_MD.name}", flush=True)

    # ---------- 自检 ----------
    print("\n>>> 自检")
    print("rows:", len(extra))
    print("dup appid:", int(extra["appid"].duplicated().sum()))
    print("null cells:", int(extra.isna().sum().sum()))
    print("free:", int(extra["is_free"].sum()), "paid:", int((~extra["is_free"]).sum()))
    print("price>0 mean:", round(float(extra.loc[extra["price"] > 0, "price"].mean()), 2))
    print("rating>0:", int((extra["rating"] > 0).sum()))
    print("year range:", int(extra["year"].min()), "-", int(extra["year"].max()))


if __name__ == "__main__":
    main()
