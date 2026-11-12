# -*- coding: utf-8 -*-
"""从公开 Steam 游戏数据集补全 2000 款真实好评率。

数据源：HuggingFace `Z02Z/steam-games-dataset`（FronkonGames 抓取，CC-BY-4.0）。
只读取 positive/negative 计数，不抓 Steam 页面，避免 403/Cloudflare。
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "market" / "reviews_enriched.json"
API = "https://datasets-server.huggingface.co/rows"
DATASET = "Z02Z/steam-games-dataset"
WANTED = 2000
SCAN = 11000
START = int(os.environ.get("REVIEW_START", "0"))


def opener():
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        return build_opener(ProxyHandler({"http": proxy, "https": proxy}))
    return build_opener()


def fetch_page(offset: int):
    query = urlencode({
        "dataset": DATASET,
        "config": "default",
        "split": "train",
        "offset": offset,
        "length": 100,
    })
    request = Request(API + "?" + query, headers={"User-Agent": "SteamMarketInsight/1.0"})
    with opener().open(request, timeout=40) as response:
        return json.loads(response.read().decode("utf-8"))


def main():
    existing = {}
    if TARGET.exists():
        try:
            payload = json.loads(TARGET.read_text(encoding="utf-8"))
            existing = {int(item["appid"]): item for item in payload.get("items", [])}
        except (OSError, ValueError):
            existing = {}

    found = {}
    for offset in range(START, SCAN, 100):
        try:
            data = fetch_page(offset)
        except Exception as exc:
            print("page", offset, "failed", exc)
            time.sleep(2)
            continue
        for item in data.get("rows", []):
            row = item.get("row") or {}
            try:
                appid = int(row.get("appID") or 0)
                positive = int(row.get("positive") or 0)
                negative = int(row.get("negative") or 0)
            except (TypeError, ValueError):
                continue
            total = positive + negative
            if appid <= 0 or positive <= 0 or total < 10:
                continue
            found[appid] = {
                "appid": appid,
                "name": row.get("name") or "",
                "rating": round(positive / total * 100, 2),
                "positive": positive,
                "total_reviews": total,
            }
        print("scanned", offset + 100, "valid", len(found))
        time.sleep(0.9)
        if len(found) >= WANTED * 2:
            break

    merged = dict(existing)
    for appid, item in found.items():
        merged[appid] = {k: item[k] for k in ("appid", "rating", "positive", "total_reviews")}

    items = sorted(merged.values(), key=lambda x: x["total_reviews"], reverse=True)[:WANTED]
    payload = {
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(items),
        "updated": len(items),
        "failed": 0,
        "items": items,
        "note": "Steam 公开数据集 positive/negative 快照（FronkonGames / HuggingFace Z02Z/steam-games-dataset，CC-BY-4.0）；非当天实时。",
    }
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", len(items), "reviews ->", TARGET)


if __name__ == "__main__":
    main()
