# -*- coding: utf-8 -*-
"""补齐「推荐数前 2000」里在 HuggingFace 数据集查不到评论的游戏。

Steam 的 appreviews 接口（store.steampowered.com）对非浏览器请求会重定向到首页，
所以本机直连拿不到 JSON。禁用/可用条件：
  - 开游戏加速器（UU / 雷神等会改写 Steam 商店流量），或
  - 从已登录 Steam 的浏览器导出 cookie 到 Netscape 格式 cookies.txt，用 --cookie-file 传入

用法：
  python scripts/fetch_missing_reviews.py            # 直连
  python scripts/fetch_missing_reviews.py --proxy    # 走 127.0.0.1:7897
  python scripts/fetch_missing_reviews.py --cookie-file cookies.txt

有成功记录才会写回 reviews_enriched.json（先自动备份），否则只打印诊断。
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "market"
TARGET = OUT / "reviews_enriched.json"
AGG = OUT / "market_agg.json"
REPORT = OUT / "reviews_top2000_report.json"

API = ("https://store.steampowered.com/appreviews/{appid}"
       "?json=1&filter=all&language=all&review_type=all&purchase_type=all&num_per_page=0")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def build_opener(proxy: bool, cookie_file: str | None):
    handlers = []
    if proxy:
        handlers.append(urllib.request.ProxyHandler(
            {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}))
    else:
        handlers.append(urllib.request.ProxyHandler({}))
    if cookie_file:
        jar = http.cookiejar.MozillaCookieJar(cookie_file)
        jar.load(ignore_discard=True, ignore_expires=True)
        handlers.append(urllib.request.HTTPCookieProcessor(jar))
        print(f"已加载 cookie：{len(jar)} 条", flush=True)
    return urllib.request.build_opener(*handlers)


def fetch(op, appid: int, retries: int = 2) -> tuple[dict | None, str]:
    req = urllib.request.Request(API.format(appid=appid), headers={
        "User-Agent": UA,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"https://store.steampowered.com/app/{appid}/",
        "X-Requested-With": "XMLHttpRequest",
    })
    for attempt in range(retries + 1):
        try:
            raw = op.open(req, timeout=30).read()
            text = raw.decode("utf-8", "ignore").lstrip()
            if text[:1] == "{":
                data = json.loads(text)
                if data.get("success"):
                    return data.get("query_summary") or {}, "ok"
                return None, "success=false"
            return None, f"重定向到商店首页（{len(raw)} 字节 HTML）"
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}"
        except Exception as e:
            err = f"{type(e).__name__}: {str(e)[:60]}"
        if attempt < retries:
            time.sleep(2 + attempt * 2)
    return None, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proxy", action="store_true", help="走 127.0.0.1:7897 代理")
    ap.add_argument("--cookie-file", default=None, help="浏览器导出的 Netscape cookies.txt")
    ap.add_argument("--delay", type=float, default=1.2, help="每次请求间隔秒")
    args = ap.parse_args()

    payload = json.loads(TARGET.read_text(encoding="utf-8"))
    missing = payload.get("missing", [])
    order = [int(x) for x in json.loads(AGG.read_text(encoding="utf-8")).get("top_by_recommendations", [])]
    if not missing:
        print("没有 missing，无需补齐。")
        return

    op = build_opener(args.proxy, args.cookie_file)
    got: dict[int, dict] = {}
    errors: list[str] = []

    for i, m in enumerate(missing, 1):
        appid = int(m["appid"])
        q, status = fetch(op, appid)
        if q and (q.get("total_positive", 0) + q.get("total_negative", 0)) > 0:
            pos, neg = int(q["total_positive"]), int(q["total_negative"])
            got[appid] = {
                "appid": appid,
                "name": m.get("name", ""),
                "rating": round(pos / (pos + neg) * 100, 2),
                "positive": pos,
                "total_reviews": pos + neg,
                "recommendations": 0,
            }
            print(f"[{i}/{len(missing)}] {appid} OK 好评率 {got[appid]['rating']}%（{pos+neg} 条）", flush=True)
        else:
            errors.append(f"{appid}:{status}")
            print(f"[{i}/{len(missing)}] {appid} 失败 {status}", flush=True)
        time.sleep(args.delay)

    print(f"\n成功 {len(got)} / {len(missing)}")
    if not got:
        print(
            "\n全部失败，没有写回数据。原因通常是 Steam 把 store.steampowered.com 的接口请求\n"
            "重定向到商店首页（反爬 / 地区处理）。可以这样解决：\n"
            "  1) 开游戏加速器（UU、雷神等），然后重跑本脚本；\n"
            "  2) 浏览器登录 Steam 后导出 cookie，重跑：--cookie-file cookies.txt；\n"
            "  3) 用 --proxy 试本地代理。"
        )
        return

    # 合并：按白名单顺序重排
    items = {int(it["appid"]): it for it in payload["items"]}
    items.update(got)
    payload["items"] = [items[a] for a in order if a in items]
    payload["missing"] = [m for m in missing if int(m["appid"]) not in got]
    payload["updated"] = len(payload["items"])
    payload["fetchedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    payload["note"] += " 其中补齐部分来自 Steam appreviews 官方接口。"

    backup = OUT / f"reviews_enriched.backup-{datetime.now():%Y%m%d-%H%M}.json"
    backup.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
    TARGET.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写回：updated={payload['updated']}，remaining missing={len(payload['missing'])}，备份 {backup.name}")

    if REPORT.exists():
        rep = json.loads(REPORT.read_text(encoding="utf-8"))
        rep["matched"] = payload["updated"]
        rep["unmatched"] = len(payload["missing"])
        rep["matchRate"] = round(payload["updated"] / payload["total"] * 100, 1)
        REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
