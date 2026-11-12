# -*- coding: utf-8 -*-
"""
增量补 Steam 好评率（archive 没有 reviews.csv）

只补 market_agg.json 的 top_by_recommendations（约 2000 款）：
  https://store.steampowered.com/appreviews/{appid}?json=1&language=all&purchase_type=all&num_per_page=0

输出 data/market/reviews_enriched.json，失败不阻塞；已有 appid 会跳过。
跑前如需代理：powershell -ExecutionPolicy Bypass -File scripts/start-proxy.ps1
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market"
AGG = OUT / "market_agg.json"
TARGET = OUT / "reviews_enriched.json"
API = "https://store.steampowered.com/appreviews/{appid}"


def opener():
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        return build_opener(ProxyHandler({"http": proxy, "https": proxy}))
    return build_opener()


def fetch_one(appid: int, timeout: int = 20) -> dict:
    query = urlencode({
        "json": 1,
        "language": "all",
        "purchase_type": "all",
        "num_per_page": 0,
    })
    request = Request(
        API.format(appid=appid) + "?" + query,
        headers={"User-Agent": "SteamMarketInsight/1.0 (local teaching project)"},
    )
    with opener().open(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8", errors="replace"))
    summary = data.get("query_summary") or {}
    total = int(summary.get("total_reviews") or 0)
    positive = int(summary.get("total_positive") or 0)
    if total <= 0:
        raise ValueError("no reviews")
    return {
        "appid": int(appid),
        "rating": round(positive / total * 100, 2),
        "positive": positive,
        "total_reviews": total,
    }


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save(payload: dict):
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="只补前 N 个缺失 appid")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--sleep", type=float, default=0.6, help="每批之间等待秒数")
    args = parser.parse_args()

    agg = load_json(AGG, {})
    targets = [int(x) for x in agg.get("top_by_recommendations", [])]
    current = load_json(TARGET, {
        "fetchedAt": "",
        "total": 0,
        "updated": 0,
        "failed": [],
        "items": [],
        "note": "archive 无 reviews.csv；仅合并真实已抓评价，不编造",
    })
    existing = {int(item["appid"]): item for item in current.get("items", [])}
    missing = [appid for appid in targets if appid not in existing and appid not in {int(x.get("appid", 0)) for x in current.get("failed", [])}]
    if args.limit:
        missing = missing[: args.limit]

    print(f"目标 {len(targets)} 款，已有 {len(existing)} 款，本次补 {len(missing)} 款", flush=True)
    if not missing:
        print("没有需要补的 appid。", flush=True)
        return

    failed = list(current.get("failed", []))
    added = 0
    for start in range(0, len(missing), args.workers):
        batch = missing[start:start + args.workers]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(fetch_one, appid): appid for appid in batch}
            for future in as_completed(futures):
                appid = futures[future]
                try:
                    item = future.result()
                    existing[appid] = item
                    added += 1
                    print(f"  + {appid} {item['rating']}% / {item['total_reviews']}", flush=True)
                except (HTTPError, URLError, TimeoutError, ValueError, OSError) as error:
                    reason = f"{type(error).__name__}: {error}"
                    failed.append({"appid": appid, "reason": reason[:180]})
                    print(f"  ! {appid} {reason[:100]}", flush=True)
        # 每批都落盘，进程中断也不丢已完成数据
        payload = {
            "fetchedAt": datetime.now(timezone.utc).isoformat() if added else current.get("fetchedAt", ""),
            "total": len(targets),
            "updated": len(existing),
            "failed": failed[-300:],
            "items": sorted(existing.values(), key=lambda item: item["appid"]),
            "note": "archive 无 reviews.csv；仅合并真实已抓评价，不编造",
        }
        save(payload)
        current = payload
        if start + args.workers < len(missing):
            time.sleep(args.sleep)

    print(f"完成：本次新增 {added}，累计 {len(existing)} / {len(targets)}，失败 {len(failed)}", flush=True)


if __name__ == "__main__":
    main()
