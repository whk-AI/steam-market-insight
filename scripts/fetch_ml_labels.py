"""Fetch 12-month review counts from Steam's appreviewhistogram.

The histogram returns monthly up/down counts. For each sampled game we sum
the 12 calendar months starting at its release month. This is a monthly
approximation of the "first 12 months" window; the release day is not used
because Steam exposes monthly buckets.

Checkpoint: data/ml/labels.csv is appended every 25 completed rows and can be
resumed. Failed rows are recorded with error text, never silently treated as 0.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "ml" / "train_sample.csv"
OUT = ROOT / "data" / "ml" / "labels.csv"
PROXY = "http://127.0.0.1:7897"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36"
FIELDS = ["appid", "reviews_12m", "up_12m", "down_12m", "months_seen", "status", "error"]

_lock = threading.Lock()
_last = 0.0


def month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def add_months(d: date, n: int) -> date:
    y = d.year + (d.month - 1 + n) // 12
    m = (d.month - 1 + n) % 12 + 1
    return date(y, m, 1)


def fetch_one(appid: int, release: str) -> dict:
    global _last
    url = f"https://store.steampowered.com/appreviewhistogram/{appid}?l=english&days=365"
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})
    )
    last_err = ""
    for attempt in range(4):
        with _lock:
            wait = 0.40 - (time.time() - _last)
            if wait > 0:
                time.sleep(wait)
            _last = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with opener.open(req, timeout=30) as r:
                data = json.loads(r.read().decode("utf-8", "replace"))
            if not data.get("success"):
                raise ValueError(f"success={data.get('success')}")
            rollups = data.get("results", {}).get("rollups") or []
            rdate = date.fromisoformat(release[:10])
            start = month_start(rdate)
            end = add_months(start, 12)
            up = down = seen = 0
            for row in rollups:
                try:
                    d = date.fromtimestamp(int(row["date"]))
                except Exception:
                    continue
                m = date(d.year, d.month, 1)
                if start <= m < end:
                    up += int(row.get("recommendations_up") or 0)
                    down += int(row.get("recommendations_down") or 0)
                    seen += 1
            return {
                "appid": appid,
                "reviews_12m": up + down,
                "up_12m": up,
                "down_12m": down,
                "months_seen": seen,
                "status": "ok",
                "error": "",
            }
        except Exception as exc:  # noqa: BLE001 - record the real failure
            last_err = f"{type(exc).__name__}: {exc}"
            if "429" in last_err or "Too Many" in last_err:
                time.sleep(20 + attempt * 15)
            else:
                time.sleep(2 + attempt * 2)
    return {
        "appid": appid,
        "reviews_12m": None,
        "up_12m": None,
        "down_12m": None,
        "months_seen": 0,
        "status": "error",
        "error": last_err[:300],
    }


def read_done(path: Path) -> set[int]:
    if not path.exists():
        return set()
    try:
        old = pd.read_csv(path)
        return set(int(x) for x in old["appid"].dropna())
    except Exception:
        return set()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    args = ap.parse_args()

    sample = pd.read_csv(SAMPLE)
    sample["release_date"] = sample["release_date"].astype(str)
    out_path = Path(args.out)
    done = read_done(OUT) | read_done(out_path)
    todo = [r for _, r in sample.iterrows() if int(r.appid) not in done]
    # Fetch across release years instead of finishing 2015-2017 first.
    # Put validation/test years first, then older training years, one per round.
    priority = [2022, 2023, 2024, 2025, 2021, 2020, 2019, 2018, 2017, 2016, 2015]
    groups: dict[int, list] = {year: [] for year in priority}
    for row in todo:
        year = int(row["year"])
        groups.setdefault(year, []).append(row)
    ordered: list = []
    while any(groups.values()):
        for year in priority:
            bucket = groups.get(year) or []
            if bucket:
                ordered.append(bucket.pop(0))
        for year, bucket in list(groups.items()):
            if year not in priority and bucket:
                ordered.append(bucket.pop(0))
    todo = ordered
    if args.shards > 1:
        todo = todo[args.shard::args.shards]
    if args.limit:
        todo = todo[: args.limit]
    print(f"sample={len(sample)} done={len(done)} shard={args.shard}/{args.shards} todo={len(todo)}", flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not out_path.exists() or out_path.stat().st_size == 0
    fh = out_path.open("a", newline="", encoding="utf-8-sig")
    writer = csv.DictWriter(fh, fieldnames=FIELDS)
    if write_header:
        writer.writeheader()
        fh.flush()

    completed = 0
    try:
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futs = {
                pool.submit(fetch_one, int(r.appid), str(r.release_date)): int(r.appid)
                for r in todo
            }
            for fut in as_completed(futs):
                row = fut.result()
                with _lock:
                    writer.writerow(row)
                    fh.flush()
                    completed += 1
                if completed % 25 == 0:
                    ok = sum(1 for x in [row] if x["status"] == "ok")
                    print(f"done={completed}/{len(todo)} last={row['appid']} {row['status']} reviews={row['reviews_12m']}", flush=True)
    finally:
        fh.close()


if __name__ == "__main__":
    main()
