# -*- coding: utf-8 -*-
"""
构建 Steam 全量市场数据（150,279 款 game）

输出:
  data/market/market_full.csv   UTF-8-SIG 全量明细
  data/market/market_agg.json   前端预聚合统计
  data/market/top500.json       推荐数 TOP500 明细

口径:
  - 价格: mat_final_price 是"分"，按币种快照期近似汇率折算美元；非免费且无价 -> 未定价
  - 年份: release_date 提取 4 位数字，缺失为 0
  - 好评率: archive 无 reviews.csv；仅合并已有真实抓取结果，不编造
  - 小标签: 从 name + short_description 关键词推断，非 Steam 官方标签
"""

from __future__ import annotations

import json
import re
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# Windows 控制台默认 GBK，遇到 ® / 中文游戏名会 UnicodeEncodeError；
# 统一按 UTF-8 输出，保证校验段能完整跑完。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path(r"F:\2026.9.1\archive\steam_dataset_2025_csv")
OUT = ROOT / "data" / "market"
OUT.mkdir(parents=True, exist_ok=True)

# 快照期近似汇率（仅用于本地快照；非实时汇率）
CURRENCY_RATES = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "AUD": 0.66,
    "CAD": 0.73,
    "PLN": 0.25,
    "JPY": 0.0067,
    "CNY": 0.14,
    "KRW": 0.00073,
    "PHP": 0.017,
    "INR": 0.012,
    "RUB": 0.011,
    "VND": 0.000039,
    "IDR": 0.000063,
    "AED": 0.27,
    "BRL": 0.20,
    "HKD": 0.128,
    "THB": 0.028,
    "NOK": 0.094,
    "MYR": 0.22,
    "TWD": 0.031,
    "SGD": 0.75,
    "ZAR": 0.054,
    "ILS": 0.27,
    "MXN": 0.058,
    "CLP": 0.0010,
}

MAIN_GENRES = [
    "Action", "Casual", "Adventure", "Indie", "Simulation",
    "RPG", "Strategy", "Sports", "Free To Play", "Racing",
]
GENRE_CN = {
    "Action": "动作",
    "Casual": "休闲",
    "Adventure": "冒险",
    "Indie": "独立",
    "Simulation": "模拟",
    "RPG": "角色扮演",
    "Strategy": "策略",
    "Sports": "体育",
    "Free To Play": "免费开玩",
    "Racing": "竞速",
    "其他": "其他",
}

# 154 个多语言 genre 名 -> 英文规范名；未命中归“其他”
GENRE_MAP = {
    # Action
    "Action": "Action", "Acción": "Action", "Acțiune": "Action", "Actie": "Action",
    "Akció": "Action", "Akcja": "Action", "Aksi": "Action", "Aksiyon": "Action",
    "Azione": "Action", "Ação": "Action", "Бойовики": "Action", "Экшены": "Action",
    "アクション": "Action", "动作": "Action", "動作": "Action",
    # Adventure
    "Abenteuer": "Adventure", "Adventure": "Adventure", "Aventura": "Adventure",
    "Aventure": "Adventure", "Aventură": "Adventure", "Avventura": "Adventure",
    "Dobrodružné": "Adventure", "Eventyr": "Adventure", "Macera": "Adventure",
    "Petualangan": "Adventure", "Przygodowe": "Adventure", "Äventyr": "Adventure",
    "Пригоди": "Adventure", "Приключенческие игры": "Adventure",
    "冒险": "Adventure", "冒險": "Adventure", "アドベンチャー": "Adventure",
    # Indie
    "Indie": "Indie", "Indépendant": "Indie", "Nezávislé": "Indie",
    "Niezależne": "Indie", "Bağımsız Yapımcı": "Indie", "Інді": "Indie",
    "Инди": "Indie", "Независими": "Indie", "インディー": "Indie",
    "独立": "Indie", "獨立製作": "Indie",
    # RPG
    "RPG": "RPG", "RYO": "RPG", "Rol": "RPG", "Rollenspiel": "RPG",
    "Rollespill": "RPG", "Ролевые игры": "RPG", "Рольові ігри": "RPG",
    "角色扮演": "RPG",
    # Simulation
    "Simulation": "Simulation", "Simulaatio": "Simulation", "Simuladores": "Simulation",
    "Simulasi": "Simulation", "Simulatie": "Simulation", "Simulationen": "Simulation",
    "Simulatoare": "Simulation", "Simulazione": "Simulation", "Simulação": "Simulation",
    "Simulering": "Simulation", "Simuleringar": "Simulation", "Simulátory": "Simulation",
    "Simülasyon": "Simulation", "Symulacje": "Simulation", "Szimuláció": "Simulation",
    "Симулатори": "Simulation", "Симулятори": "Simulation", "Симуляторы": "Simulation",
    "模拟": "Simulation",
    # Strategy
    "Strategy": "Strategy", "Estrategia": "Strategy", "Estratégia": "Strategy",
    "Strategi": "Strategy", "Strategia": "Strategy", "Strategické": "Strategy",
    "Strategie": "Strategy", "Strateji": "Strategy", "Stratégia": "Strategy",
    "Stratégie": "Strategy", "Стратегии": "Strategy", "Стратегії": "Strategy",
    "策略": "Strategy", "ストラテジー": "Strategy",
    # Casual
    "Casual": "Casual", "Basit Eğlence": "Casual", "Fritid": "Casual",
    "Gelegenheitsspiele": "Casual", "Kasual": "Casual", "Passatempo": "Casual",
    "Rekreacyjne": "Casual", "Неангажиращи": "Casual", "休閒": "Casual",
    "カジュアル": "Casual",
    # Racing
    "Racing": "Racing", "Corrida": "Racing", "Corse": "Racing",
    "Rennspiele": "Racing", "Перегони": "Racing", "Гонки": "Racing",
    "竞速": "Racing",
    # Sports
    "Sports": "Sports", "Deportes": "Sports", "Esportes": "Sports",
    "Spor": "Sports", "Sport": "Sports", "Sportovní": "Sports",
    "Sportowe": "Sports", "Спорт": "Sports", "体育": "Sports",
    # Free To Play
    "Free To Play": "Free To Play", "Free to Play": "Free To Play",
    "Gratis at spille": "Free To Play", "Gratis att spela": "Free To Play",
    "Gratis te spelen": "Free To Play", "Gratuitos para Jogar": "Free To Play",
    "Бесплатные": "Free To Play", "مجانية": "Free To Play", "免费开玩": "Free To Play",
}

# 小标签关键词：英文用词边界，中文用子串；顺序即展示优先级
SUB_TAG_RULES = [
    ("恐怖", [r"\bhorror\b", r"恐怖", r"惊悚", r"\bcreepy\b"]),
    ("肉鸽", [r"\broguelike\b", r"\brogue[- ]?like\b", r"\broguelite\b", r"肉鸽"]),
    ("像素", [r"\bpixel\b", r"像素"]),
    ("动漫", [r"\banime\b", r"动漫", r"二次元"]),
    ("开放世界", [r"\bopen[- ]world\b", r"开放世界"]),
    ("射击", [r"\bshooter\b", r"\bfps\b", r"\bshoot(ing)?\b", r"射击"]),
    ("多人", [r"\bmultiplayer\b", r"\bco-?op\b", r"\bcoop\b", r"联机", r"多人"]),
    ("解谜", [r"\bpuzzle\b", r"解谜", r"益智"]),
    ("生存", [r"\bsurvival\b", r"生存"]),
    ("沙盒", [r"\bsandbox\b", r"沙盒"]),
    ("平台跳跃", [r"\bplatformer\b", r"\bplatform(ing)?\b", r"平台跳跃"]),
    ("模拟经营", [r"\bmanagement\b", r"\btycoon\b", r"\bsimulator\b", r"模拟经营", r"经营"]),
    ("建造", [r"\bbuilding\b", r"\bcraft(ing)?\b", r"建造", r"制作"]),
    ("卡牌", [r"\bcard\b", r"\bdeck[- ]?build", r"卡牌"]),
    ("音乐", [r"\bmusic\b", r"\brhythm\b", r"音乐", r"节奏"]),
    ("科幻", [r"\bsci[- ]?fi\b", r"\bscience fiction\b", r"科幻"]),
    ("奇幻", [r"\bfantasy\b", r"奇幻", r"魔法"]),
    ("僵尸", [r"\bzombie\b", r"僵尸", r"喪屍"]),
    ("太空", [r"\bspace\b", r"太空", r"星际"]),
    ("农场", [r"\bfarm(ing)?\b", r"农场", r"种田"]),
    ("钓鱼", [r"\bfishing\b", r"钓鱼"]),
    ("视觉小说", [r"\bvisual novel\b", r"视觉小说"]),
    ("塔防", [r"\btower defense\b", r"塔防"]),
    ("回合制", [r"\bturn[- ]based\b", r"回合制"]),
    ("大逃杀", [r"\bbattle royale\b", r"大逃杀", r"吃鸡"]),
    ("剧情", [r"\bstory[- ]rich\b", r"\bnarrative\b", r"剧情", r"故事"]),
    ("赛博朋克", [r"\bcyberpunk\b", r"赛博朋克"]),
    ("篮球", [r"\bbasketball\b", r"篮球"]),
    ("足球", [r"\bfootball\b", r"\bsoccer\b", r"足球"]),
    ("烹饪", [r"\bcooking\b", r"\bchef\b", r"烹饪", r"料理"]),
    ("跑酷", [r"\bparkour\b", r"\brunner\b", r"跑酷"]),
    ("弹幕", [r"\bbullet hell\b", r"\bbullet[- ]?hell\b", r"弹幕"]),
]


def clean_text(value) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "null", "<na>"} else text


def to_number(value, default=0.0) -> float:
    try:
        number = float(value)
        return default if math.isnan(number) else number
    except (TypeError, ValueError):
        return default


def extract_year(value) -> int:
    match = re.search(r"(\d{4})", clean_text(value))
    if not match:
        return 0
    year = int(match.group(1))
    return year if 1970 <= year <= 2035 else 0


def load_genres():
    genres = pd.read_csv(ARCHIVE / "genres.csv", dtype={"id": "int64", "name": "string"})
    genre_id_to_name = {
        int(row.id): GENRE_MAP.get(clean_text(row.name), "其他")
        for row in genres.itertuples(index=False)
    }
    links = pd.read_csv(
        ARCHIVE / "application_genres.csv",
        dtype={"appid": "int64", "genre_id": "int64"},
    )
    links["canon"] = links["genre_id"].map(genre_id_to_name).fillna("其他")
    links = links[links["canon"].ne("其他")]
    grouped = (
        links.drop_duplicates(["appid", "canon"])
        .groupby("appid", sort=False)["canon"]
        .apply(lambda values: list(dict.fromkeys(values)))
        .to_dict()
    )
    return grouped


def infer_sub_tags(name: str, description: str) -> list[str]:
    text = f" {name} {description} ".lower()
    hits = []
    for tag, patterns in SUB_TAG_RULES:
        if any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns):
            hits.append(tag)
    return hits


def load_reviews() -> dict[int, dict]:
    path = OUT / "reviews_enriched.json"
    if not path.exists():
        seed_path = ROOT / "data" / "games.json"
        items = []
        if seed_path.exists():
            for game in json.loads(seed_path.read_text(encoding="utf-8")):
                appid = int(game.get("appid") or 0)
                rating = to_number(game.get("rating"))
                total = int(to_number(game.get("total_reviews")))
                if appid and total > 0 and rating > 0:
                    items.append({
                        "appid": appid,
                        "rating": round(rating, 2),
                        "positive": int(round(total * rating / 100)),
                        "total_reviews": total,
                    })
        payload = {
            "fetchedAt": "2026-10-18T10:36:35Z",
            "total": len(items),
            "updated": len(items),
            "failed": [],
            "items": items,
            "note": "archive 无 reviews.csv；这里只合并历史已抓到的真实评价，不编造",
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {int(item["appid"]): item for item in payload.get("items", [])}


def main():
    print(">>> 读取 applications.csv ...", flush=True)
    apps = pd.read_csv(
        ARCHIVE / "applications.csv",
        usecols=[
            "appid", "name", "type", "is_free", "release_date", "short_description",
            "mat_initial_price", "mat_final_price", "mat_discount_percent",
            "mat_currency", "metacritic_score", "recommendations_total",
        ],
        dtype={"appid": "int64", "type": "string", "mat_currency": "string"},
        low_memory=False,
    )
    apps = apps[apps["type"].eq("game")].copy()
    print(">>> game 行数:", len(apps), flush=True)

    print(">>> 读取 genres 关联 ...", flush=True)
    genre_lists = load_genres()

    print(">>> 关键词推断小标签 ...", flush=True)
    sub_tags = [
        infer_sub_tags(clean_text(name), clean_text(desc))
        for name, desc in zip(apps["name"], apps["short_description"])
    ]

    reviews = load_reviews()
    records = []
    for i, row in enumerate(apps.itertuples(index=False)):
        appid = int(row.appid)
        name = clean_text(row.name) or "Unknown"
        is_free = bool(row.is_free) if not pd.isna(row.is_free) else False
        currency = clean_text(row.mat_currency).upper()
        raw_price = to_number(row.mat_final_price)
        raw_original = to_number(row.mat_initial_price)
        rate = CURRENCY_RATES.get(currency, 0.0)
        price_unknown = False

        if is_free:
            price = 0.0
            original_price = 0.0
            discount = 0
        elif raw_price <= 0 or rate <= 0:
            price = 0.0
            original_price = 0.0
            discount = 0
            price_unknown = True
        else:
            price = round((raw_price / 100.0) * rate, 2)
            original_price = round(((raw_original if raw_original > 0 else raw_price) / 100.0) * rate, 2)
            discount = int(round(to_number(row.mat_discount_percent)))

        genres = genre_lists.get(appid, [])
        first_genre = next((g for g in genres if g in MAIN_GENRES), "")
        # Free To Play 是一个独立的官方大类；免费游戏统一落在这个角色下，
        # 避免“免费”被 Action/Indie 吸走，导致 F2P 角色失真。
        main_genre = "Free To Play" if is_free else (first_genre or "其他")

        # 多主类型：保留 genres 顺序，命中的所有 Steam 大类都计入；
        # 免费游戏强制带上 Free To Play（放在最前），保证 F2P 角色可见。
        all_genres = [g for g in genres if g in MAIN_GENRES]
        if is_free and "Free To Play" not in all_genres:
            all_genres = ["Free To Play"] + all_genres
        if not all_genres:
            all_genres = ["其他"]

        if not genres:
            genres = ["未知"]

        year = extract_year(row.release_date)
        meta_score = int(round(to_number(row.metacritic_score)))
        recommendations = int(round(to_number(row.recommendations_total)))
        review = reviews.get(appid, {})
        rating = round(to_number(review.get("rating")), 2)
        total_reviews = int(to_number(review.get("total_reviews")))
        positive = int(to_number(review.get("positive")))

        records.append({
            "appid": appid,
            "name": name,
            "type": "game",
            "is_free": is_free,
            "price": price,
            "original_price": original_price,
            "discount_percent": discount,
            "currency": currency or "UNKNOWN",
            "price_unknown": price_unknown,
            "year": year,
            "release_date": clean_text(row.release_date) or "UNKNOWN",
            "genres": ",".join(genres),
            "main_genre": main_genre,
            "all_genres": ",".join(all_genres),
            # 空字符串在 CSV 回读时会被 pandas 当 NaN；用“未标注”保证 df.isnull().sum()=0。
            "sub_tags": ",".join(sub_tags[i]) or "未标注",
            "metacritic": meta_score,
            "recommendations": recommendations,
            "rating": rating,
            "positive": positive,
            "total_reviews": total_reviews,
            "url": f"https://store.steampowered.com/app/{appid}",
        })

    full = pd.DataFrame.from_records(records)
    full = full.sort_values(["recommendations", "appid"], ascending=[False, True]).reset_index(drop=True)
    print(">>> 写出 market_full.csv ...", flush=True)
    full.to_csv(OUT / "market_full.csv", index=False, encoding="utf-8-sig")

    # ---------- 聚合 ----------
    total = len(full)
    free_count = int(full["is_free"].sum())
    with_price = int((full["price"] > 0).sum())
    with_date = int((full["release_date"].astype(str).str.len() > 0).sum())
    with_meta = int((full["metacritic"] > 0).sum())
    with_rec = int((full["recommendations"] > 0).sum())

    def band_of(row):
        if row["price_unknown"]:
            return "未定价"
        if row["is_free"] or row["price"] <= 0:
            return "免费"
        if row["price"] <= 30:
            return "1-30"
        if row["price"] <= 60:
            return "31-60"
        if row["price"] <= 100:
            return "61-100"
        if row["price"] <= 200:
            return "101-200"
        return "200+"

    full["price_band"] = full.apply(band_of, axis=1)
    price_order = ["免费", "1-30", "31-60", "61-100", "101-200", "200+", "未定价"]
    price_bands = [
        {"band": band, "count": int((full["price_band"] == band).sum())}
        for band in price_order
    ]

    priced_all = full[full["price"] > 0]
    rated_all = full[full["rating"] > 0]
    rated_free = rated_all[rated_all["is_free"]]
    rated_paid = rated_all[~rated_all["is_free"]]
    price_stats = {
        "allMean": round(float(full["price"].mean()), 2) if total else 0,
        "allMedian": round(float(full["price"].median()), 2) if total else 0,
        "paidMean": round(float(priced_all["price"].mean()), 2) if len(priced_all) else 0,
        "paidMedian": round(float(priced_all["price"].median()), 2) if len(priced_all) else 0,
        "freeCount": int(full["is_free"].sum()),
        "paidCount": int(len(priced_all)),
        "ratingCount": int(len(rated_all)),
        "freeRating": round(float(rated_free["rating"].mean()), 1) if len(rated_free) else 0,
        "paidRating": round(float(rated_paid["rating"].mean()), 1) if len(rated_paid) else 0,
    }

    # 多主类型布尔掩码：一款游戏可同时命中多个大类，后续统计全部按此展开。
    genre_masks = {
        genre: full["all_genres"].fillna("").apply(
            lambda value, target=genre: target in str(value).split(",")
        )
        for genre in MAIN_GENRES + ["其他"]
    }

    type_dist = []
    for genre in MAIN_GENRES + ["其他"]:
        subset = full[genre_masks[genre]]
        priced = subset[subset["price"] > 0]
        rated = subset[subset["rating"] > 0]
        type_dist.append({
            "name": genre,
            "name_cn": GENRE_CN.get(genre, genre),
            "count": int(len(subset)),
            "share": round(len(subset) / total * 100, 2) if total else 0,
            "avgPrice": round(float(priced["price"].mean()), 2) if len(priced) else 0,
            "avgRating": round(float(rated["rating"].mean()), 2) if len(rated) else 0,
            "ratingCount": int(len(rated)),
        })

    year_dist_map = full["year"].value_counts().to_dict()
    year_dist = [
        {"year": int(year), "count": int(count)}
        for year, count in sorted(year_dist_map.items(), key=lambda item: item[0])
    ]

    year_rows = []
    for year in range(2009, 2027):
        subset = full[full["year"] == year]
        priced = subset[subset["price"] > 0]
        year_rows.append({
            "year": year,
            "count": int(len(subset)),
            "hits": int((subset["recommendations"] >= 1000).sum()),
            "free": int(subset["is_free"].sum()),
            "avgPrice": round(float(priced["price"].mean()), 2) if len(priced) else 0,
            "reviews": int(subset["total_reviews"].sum()),
            "recommendations": int(subset["recommendations"].sum()),
        })
    unknown = full[full["year"] == 0]
    year_rows.insert(0, {
        "year": 0,
        "count": int(len(unknown)),
        "hits": int((unknown["recommendations"] >= 1000).sum()),
        "free": int(unknown["is_free"].sum()),
        "avgPrice": round(float(unknown[unknown["price"] > 0]["price"].mean()), 2) if (unknown["price"] > 0).any() else 0,
        "reviews": int(unknown["total_reviews"].sum()),
        "recommendations": int(unknown["recommendations"].sum()),
    })

    timeline_years = list(range(2010, 2026))
    type_year = []
    for genre in MAIN_GENRES + ["其他"]:
        row = {"name": genre, "name_cn": GENRE_CN.get(genre, genre), "values": {}}
        for year in timeline_years:
            row["values"][str(year)] = int(((genre_masks[genre]) & (full["year"] == year)).sum())
        row["values"]["其他"] = int(((genre_masks[genre]) & (~full["year"].isin(timeline_years))).sum())
        type_year.append(row)

    sub_tag_dist = {}
    for genre in MAIN_GENRES + ["其他"]:
        subset = full[genre_masks[genre]]
        counts = {}
        for tags in subset["sub_tags"]:
            for tag in [item for item in str(tags).split(",") if item and item != "未标注"]:
                counts[tag] = counts.get(tag, 0) + 1
        sub_tag_dist[genre] = [
            {"tag": tag, "count": count}
            for tag, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:16]
        ]

    reviewed = full[(full["recommendations"] > 0) & full["rating"].notna()].copy()
    top2000 = reviewed.head(2000)[["appid"]].to_dict(orient="records")
    top500_cols = [
        "appid", "name", "main_genre", "all_genres", "genres", "sub_tags", "price", "original_price",
        "discount_percent", "is_free", "price_unknown", "year", "release_date",
        "metacritic", "recommendations", "rating", "positive", "total_reviews", "url",
    ]
    top500 = reviewed.head(500)[top500_cols].to_dict(orient="records")
    top_by_type = {}
    for genre in MAIN_GENRES + ["其他"]:
        top_by_type[genre] = (
            reviewed[genre_masks[genre]]
            .head(50)[top500_cols]
            .to_dict(orient="records")
        )

    name_lookup = {}
    for row in reviewed.itertuples(index=False):
        name_lookup[str(int(row.appid))] = row.name
    online_path = ROOT / "data" / "online.json"
    if online_path.exists():
        online = json.loads(online_path.read_text(encoding="utf-8"))
        for item in online.get("top", []):
            appid = str(int(item.get("appid") or 0))
            if appid not in name_lookup:
                matched = full[full["appid"] == int(appid)]
                if len(matched):
                    name_lookup[appid] = matched.iloc[0]["name"]

    pair_counts = {}
    for value in full["all_genres"].fillna(""):
        genres = sorted({item for item in str(value).split(",") if item in MAIN_GENRES})
        for index, first in enumerate(genres):
            for second in genres[index + 1:]:
                key = (first, second)
                pair_counts[key] = pair_counts.get(key, 0) + 1
    type_pairs = [
        {"a": first, "b": second, "count": count}
        for (first, second), count in sorted(pair_counts.items(), key=lambda item: -item[1])
    ]

    agg = {
        "type_dist": type_dist,
        "type_pairs": type_pairs,
        "sub_tag_dist": sub_tag_dist,
        "price_bands": price_bands,
        "price_stats": price_stats,
        "year_dist": year_dist,
        "year_price_rating": year_rows,
        "type_x_year": type_year,
        "type_x_year_years": [str(y) for y in timeline_years] + ["其他"],
        "top_by_recommendations": [int(item["appid"]) for item in top2000],
        "top_by_type": top_by_type,
        "name_lookup": name_lookup,
        "meta": {
            "source": "Steam 2025 archive (applications.csv + application_genres.csv) + reviews_enriched.json",
            "totalGames": total,
            "withPrice": with_price,
            "freeCount": free_count,
            "withDate": with_date,
            "withMetacritic": with_meta,
            "withRecommendations": with_rec,
            "reviewsUpdated": len(reviews),
            "builtAt": datetime.now(timezone.utc).isoformat(),
            "note": "代表作品与类型统计按多主类型归属：一款游戏可属于多个 Steam 大类（数量可重叠）；代表作品每类取推荐数前 50。",
            "subTagNote": "小标签数量基于游戏描述关键词推断，非 Steam 官方精确值",
            "priceNote": "价格按快照期近似汇率折算 USD，非实时汇率",
        },
    }

    (OUT / "market_agg.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "top500.json").write_text(json.dumps(top500, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 校验 ----------
    print("\n>>> 校验", flush=True)
    print("rows:", total, "expect 150279", flush=True)
    print("free:", free_count, "expect 18994", flush=True)
    print("withPrice:", with_price, "expect 90311", flush=True)
    print("duplicate appid:", int(full["appid"].duplicated().sum()), flush=True)
    print("null cells:", int(full.isna().sum().sum()), flush=True)
    print("price_unknown:", int(full["price_unknown"].sum()), flush=True)
    racing_top6 = top_by_type["Racing"][:6]
    print("Racing top6:", [(item["appid"], item["name"]) for item in racing_top6], flush=True)
    print("Racing contains Forza Horizon 5 (1551360):", any(int(item["appid"]) == 1551360 for item in racing_top6), flush=True)
    type_sum = int(sum(item["count"] for item in type_dist))
    other_count = int(next(item["count"] for item in type_dist if item["name"] == "其他"))
    print("type sum:", type_sum, "> totalGames:", type_sum > total, flush=True)
    print("other count:", other_count, flush=True)
    print("year sum:", int(sum(item["count"] for item in year_dist)), flush=True)
    print("reviews updated:", len(reviews), flush=True)
    print("output:", OUT, flush=True)


if __name__ == "__main__":
    main()
