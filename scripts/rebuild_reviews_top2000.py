# -*- coding: utf-8 -*-
"""按「推荐数前 2000」口径重建口碑样本（duckdb + 远程 parquet，只读需要的列）。

背景：旧脚本 fetch_hf_reviews.py 按 total_reviews 排序取前 2000，
导致 66% 的样本评论数不足 1000 条，与 top_by_recommendations 只重叠 189 款。

本脚本：
  1) 白名单 = market_agg.json 的 top_by_recommendations（推荐数前 2000 appid）
  2) 远程读取 HuggingFace 数据集 parquet，只取 appID/name/positive/negative/recommendations 5 列
  3) 白名单内匹配，positive/(positive+negative) 算真实好评率
  4) 按白名单顺序（推荐数降序）输出 reviews_enriched.json，记录 missing
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market"
AGG = OUT / "market_agg.json"
TARGET = OUT / "reviews_enriched.json"
REPORT = OUT / "reviews_top2000_report.json"

# 走国内镜像直连：HF 官方源在本机会超时/SSL 中断
PARQUET = (
    "https://hf-mirror.com/datasets/Z02Z/steam-games-dataset/resolve/"
    "refs%2Fconvert%2Fparquet/default/train/0000.parquet"
)


def main():
    agg = json.loads(AGG.read_text(encoding="utf-8"))
    order = [int(x) for x in agg.get("top_by_recommendations", [])]
    names = agg.get("name_lookup", {})
    print(f"白名单 {len(order)} 款（推荐数前 {len(order)}）", flush=True)

    con = duckdb.connect()
    con.execute("LOAD httpfs")
    con.execute("SET http_timeout=600000")
    con.execute("SET http_retries=5")

    values = ",".join(f"({a})" for a in order)
    con.execute(f"CREATE TABLE white(appid BIGINT)")
    con.execute(f"INSERT INTO white VALUES {values}")

    sql = f"""
      SELECT CAST(p.appID AS BIGINT) AS appid,
             p.name,
             COALESCE(p.positive, 0) AS positive,
             COALESCE(p.negative, 0) AS negative,
             COALESCE(p.recommendations, 0) AS recommendations
      FROM read_parquet('{PARQUET}') p
      JOIN white w ON CAST(p.appID AS BIGINT) = w.appid
      WHERE COALESCE(p.positive, 0) > 0
    """
    t = time.time()
    rows = con.sql(sql).fetchall()
    print(f"查询返回 {len(rows)} 行，{time.time() - t:.0f}s", flush=True)

    best: dict[int, dict] = {}
    for appid, name, positive, negative, rec in rows:
        total = int(positive) + int(negative)
        if total <= 0:
            continue
        item = {
            "appid": int(appid),
            "name": (name or "").strip(),
            "rating": round(int(positive) / total * 100, 2),
            "positive": int(positive),
            "total_reviews": total,
            "recommendations": int(rec),
        }
        if appid not in best or total > best[appid]["total_reviews"]:
            best[appid] = item

    items = [best[a] for a in order if a in best]
    missing = [{"appid": a, "name": names.get(str(a), "")} for a in order if a not in best]

    if TARGET.exists():
        backup = OUT / f"reviews_enriched.backup-{datetime.now():%Y%m%d-%H%M}.json"
        backup.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"已备份旧文件 -> {backup.name}", flush=True)

    payload = {
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(order),
        "updated": len(items),
        "failed": 0,
        "items": items,
        "missing": missing,
        "note": (
            "口径：推荐数前 2000 款（market_agg.top_by_recommendations）；"
            "好评率来自 HuggingFace 数据集 Z02Z/steam-games-dataset（FronkonGames 抓取，CC-BY-4.0）"
            "的 positive/negative 真实计数，非当天实时。"
        ),
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    rec = [i["recommendations"] for i in items]
    tr = [i["total_reviews"] for i in items]
    report = {
        "builtAt": payload["fetchedAt"],
        "want": len(order),
        "matched": len(items),
        "unmatched": len(missing),
        "matchRate": round(len(items) / len(order) * 100, 1) if order else 0,
        "coverageOfAllGames": round(len(items) / 150279 * 100, 2),
        "recommendationsSum": sum(rec),
        "recommendationsMin": min(rec) if rec else 0,
        "recommendationsMax": max(rec) if rec else 0,
        "reviewsMedian": sorted(tr)[len(tr) // 2] if tr else 0,
        "reviewsMin": min(tr) if tr else 0,
        "missingAppids": [m["appid"] for m in missing][:300],
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"\n完成：匹配 {len(items)}/{len(order)}（{report['matchRate']}%），"
        f"未匹配 {len(missing)}，耗时 {time.time() - t:.0f}s\n"
        f"评论数中位数 {report['reviewsMedian']}，最少 {report['reviewsMin']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
