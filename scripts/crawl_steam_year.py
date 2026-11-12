"""用 Steam Store 搜索的 Released_DESC 排序，核验 2025 年发售数量。

只读取公开搜索页（category1=998 游戏），不写入全量 CSV；结果保存为
data/steam_store_2025.json。需要本机代理 127.0.0.1:7897。

Steam 搜索是降序，2026 的条目很多；从 start=23000 附近开始扫，
只统计 2025 年，遇到 entirely 2024 的页就停止。
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "steam_store_2025.json"
PROXY = "http://127.0.0.1:7897"
START = 23000
BASE = (
    "https://store.steampowered.com/search/results/"
    "?query&start={start}&count=100&sort_by=Released_DESC"
    "&supportedlang=english&cc=US&category1=998"
)
DATE_RE = re.compile(
    r'<div class="search_released[^"]*"[^>]*>\s*([^<]+?)\s*</div>',
    re.I,
)


def parse_date(text: str):
    text = " ".join(text.split())
    for fmt in ("%b %d, %Y", "%d %b, %Y", "%b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def fetch(session, start):
    url = BASE.format(start=start)
    for attempt in range(6):
        try:
            response = session.get(url, timeout=35)
            if response.status_code == 429:
                print("429, sleep 15s", flush=True)
                time.sleep(15)
                continue
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            print("retry", attempt, exc, flush=True)
            time.sleep(5 + attempt * 3)
    raise RuntimeError("too many failures at start=%s" % start)


def main() -> None:
    session = requests.Session()
    session.proxies = {"http": PROXY, "https": PROXY}
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.8",
        }
    )
    monthly = Counter()
    total = 0
    pages = 0
    start = START
    first_year = None
    last_date = None
    for page in range(300):
        text = fetch(session, start)
        dates = [parse_date(value) for value in DATE_RE.findall(text)]
        valid = [date for date in dates if date]
        if not valid:
            print("empty page", start, "stop", flush=True)
            break
        newest = max(valid)
        oldest = min(valid)
        if first_year is None:
            first_year = newest.year
        for date in valid:
            if date.year == 2025:
                total += 1
                monthly[date.month] += 1
        pages += 1
        last_date = (oldest, newest)
        print(
            f"page={page:03d} start={start:5d} rows={len(valid):3d} {oldest}..{newest} 2025={total}",
            flush=True,
        )
        if newest.year < 2025:
            break
        start += 100
        time.sleep(1.05)

    result = {
        "fetchedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "Steam Store search, Released_DESC, category1=998",
        "url": BASE.format(start=0),
        "note": "Steam Store 搜索口径，游戏类目；用于核验 2025 年度数量级，不替代 archive 字段。",
        "start": START,
        "firstYear": first_year,
        "pages": pages,
        "lastPageRange": last_date,
        "total": total,
        "monthly": dict(sorted(monthly.items())),
    }
    OUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
