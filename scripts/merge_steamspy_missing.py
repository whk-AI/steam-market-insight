# -*- coding: utf-8 -*-
"""用 SteamSpy 快照补齐「推荐数前 2000」里数据集查不到的早期游戏。

SteamSpy 的 positive/negative 与 Steam appreviews 的 total_positive/total_negative 同口径
（全语言、全部评论类型），但对 2024 年后新游常返回 0，所以只能补到一部分。

用法：python scripts/merge_steamspy_missing.py [--proxy]
有成功记录才写回；成功条目带 "source": "steamspy"，便于页面标注。
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market"
TARGET = OUT / "reviews_enriched.json"
AGG = OUT / "market_agg.json"
FULL = OUT / "market_full.csv"
REPORT = OUT / "reviews_top2000_report.json"
API = "https://steamspy.com/api.php?request=appdetails&appid={}"
UA = {"User-Agent": "Mozilla/5.0"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", action="store_true")
    ap.add_argument("--delay", type=float, default=0.8)
    args = ap.parse_args()

    proxy = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"} if args.proxy else {}
    op = urllib.request.build_opener(urllib.request.ProxyHandler(proxy))

    payload = json.loads(TARGET.read_text(encoding="utf-8"))
    missing = payload.get("missing", [])
    order = [int(x) for x in json.loads(AGG.read_text(encoding="utf-8"))["top_by_recommendations"]]

    rec_map = {}
    with open(FULL, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            rec_map[row["appid"]] = int(float(row["recommendations"] or 0))

    def spy(appid, tries=3):
        for i in range(tries):
            try:
                return json.loads(op.open(urllib.request.Request(API.format(appid), headers=UA), timeout=25).read().decode())
            except Exception:
                time.sleep(2 + i * 2)
        return {}

    got = {}
    for i, m in enumerate(missing, 1):
        a = int(m["appid"])
        d = spy(a)
        pos, neg = (d.get("positive") or 0), (d.get("negative") or 0)
        if pos + neg > 0:
            got[a] = {
                "appid": a,
                "name": m.get("name", "") or d.get("name", ""),
                "rating": round(pos / (pos + neg) * 100, 2),
                "positive": int(pos),
                "total_reviews": int(pos + neg),
                "recommendations": rec_map.get(str(a), 0),
                "source": "steamspy",
            }
            print(f"[{i}/{len(missing)}] {a} {got[a]['name'][:26]:26s} {got[a]['rating']}%（{pos+neg} 条）", flush=True)
        else:
            print(f"[{i}/{len(missing)}] {a} 无数据", flush=True)
        time.sleep(args.delay)

    print(f"\n补齐 {len(got)} / {len(missing)}")
    if not got:
        print("没有可补的，未写回。")
        return

    items = {int(it["appid"]): it for it in payload["items"]}
    items.update(got)
    payload["items"] = [items[a] for a in order if a in items]
    payload["missing"] = [m for m in missing if int(m["appid"]) not in got]
    payload["updated"] = len(payload["items"])
    payload["fetchedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload["note"] = (
        "口径：推荐数前 2000 款（market_agg.top_by_recommendations）；"
        "主体来自 HuggingFace 数据集 Z02Z/steam-games-dataset（FronkonGames 抓取，CC-BY-4.0）；"
        f"其中 {len(got)} 款早期游戏用 SteamSpy 快照补齐（条目带 source=steamspy，非同一时点）；"
        "均非当天实时。"
    )

    backup = OUT / f"reviews_enriched.backup-{datetime.now():%Y%m%d-%H%M}.json"
    backup.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写回：updated={payload['updated']}，remaining={len(payload['missing'])}，备份 {backup.name}")

    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    rep["matched"] = payload["updated"]
    rep["unmatched"] = len(payload["missing"])
    rep["matchRate"] = round(payload["updated"] / payload["total"] * 100, 1)
    rep["steamspyFilled"] = len(got)
    rep["reviewsMedian"] = sorted(it["total_reviews"] for it in payload["items"])[payload["updated"] // 2]
    rep["reviewsMin"] = min(it["total_reviews"] for it in payload["items"])
    rep["missingAppids"] = [m["appid"] for m in payload["missing"]][:300]
    REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print("report 已更新")


if __name__ == "__main__":
    main()
